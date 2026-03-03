# part3_zoominfo_prospects.py
# Part 3 - ZoomInfo Prospects
# Input : Name_Tag_ZI.csv  +  Name_Tag_Accounts.csv
# Output: Name_Tag_ZI Prospects.xlsx, Name_Tag_Deliverable.xlsx,
#         Name_Tag_Emails.csv, Name_Tag_Accounts with Insufficient Prospects.csv

import sys
import numpy as np
import pandas as pd
from utils import detect_gender, convert_country_to_code, fuzzy_match_company

np.set_printoptions(threshold=sys.maxsize)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

# ─── Inputs ───────────────────────────────────────────────────────────────────
file_name = input("Please enter the Excel file name (including .csv extension): ")
base_name = file_name.replace("_ZI.csv", "")
threshold = int(input("Enter the number of prospects per account requested: "))
hide_email_choice = int(input("Do you want to hide Email column in Deliverable.xlsx? (1 = Hide, 2 = Keep): "))
hide_email = (hide_email_choice == 1)

# ─── Load & rename ────────────────────────────────────────────────────────────
df = pd.read_csv(file_name, sep=",", encoding="utf-8-sig")
df = df.rename(columns={
    "ZoomInfo Contact ID": "ZoomInfo Contact ID (Custom 18)",
    "Job Title": "Title",
    "Direct Phone Number": "Work Phone",
    "Email Address": "Email",
    "Mobile phone": "Mobile Phone",
    "LinkedIn Contact Profile URL": "LinkedIn URL",
    "Person City": "City",
    "Person State": "State",
    "Person Zip Code": "Zip",
    "Company Name": "Company natural",
})

# ─── Merge accounts ───────────────────────────────────────────────────────────
accounts = pd.read_csv(base_name + "_Accounts.csv", sep=",", encoding="utf-8-sig")
accounts = accounts.rename(columns={"Country": "Account Country"})
df["Custom Id"] = float("nan")

if "ZoomInfo Company ID" in df.columns and "ZoomInfo Company ID (Custom 19)" in accounts.columns:
    zi_map = accounts[["ZoomInfo Company ID (Custom 19)", "Custom Id"]].dropna()
    df = df.merge(zi_map.rename(columns={"ZoomInfo Company ID (Custom 19)": "ZoomInfo Company ID"}),
                  on="ZoomInfo Company ID", how="left")

unmatched = df["Custom Id"].isna()
if unmatched.any():
    df.loc[unmatched, "Custom Id"] = df.loc[unmatched, "Company natural"].apply(
        lambda n: fuzzy_match_company(n, accounts)
    )

df = df.merge(accounts[["Custom Id", "Account Name", "Account Country", "Tags"]],
              on="Custom Id", how="left")

# ─── Country filter ───────────────────────────────────────────────────────────
df["Country"] = df["Country"].apply(convert_country_to_code)
df = df[df["Country"] == df["Account Country"]]

# ─── IDs, source, gender ──────────────────────────────────────────────────────
df.insert(0, "Prospect ID", ["Z" + str(i + 1).zfill(4) for i in range(len(df))])
df["Source"] = df.get("Source", pd.Series(["ZoomInfo"] * len(df)))
df["Issue"] = ""
df["Plausible Gender"] = df["First Name"].apply(detect_gender)
df["Gender"] = df["Plausible Gender"]
df.loc[df["Gender"] == "Unknown", "Issue"] += "+Unknown Gender"
df["Issue"] = df["Issue"].str.strip("+")

counts = df.groupby("Custom Id").size()
df["# Prospects/Account Range"] = df["Custom Id"].map(counts)

# ─── Issues export ────────────────────────────────────────────────────────────
issue_cols = [
    "Issue", "# Prospects/Account Range", "Custom Id", "Account Name",
    "First Name", "Last Name", "Title", "Gender", "Email",
    "LinkedIn URL", "Work Phone", "Mobile Phone", "City", "State",
    "Zip", "Country", "Tags", "Prospect ID", "Source",
]
issues_file = base_name + "_Prospect Issues.xlsx"
with pd.ExcelWriter(issues_file, engine="xlsxwriter") as writer:
    df[[c for c in issue_cols if c in df.columns]].to_excel(writer, sheet_name="Issues", index=False)
print(f"Please review: {issues_file}")
input("Press Enter when done reviewing issues...")

df_rev = pd.read_excel(issues_file, sheet_name="Issues")
df_rev = df_rev[df_rev["Issue"].isna() | (df_rev["Issue"].astype(str).str.strip() == "")]

prospects_export = df.drop(columns=["Issue", "# Prospects/Account Range",
                                     "Plausible Gender", "Combined_Key"], errors="ignore")
with pd.ExcelWriter(base_name + "_ZI Prospects.xlsx", engine="xlsxwriter") as writer:
    prospects_export.to_excel(writer, sheet_name="Prospects", index=False)

deliverable_cols = [
    "Prospect ID", "Custom Id", "Account Name", "Tags", "First Name",
    "Last Name", "Title", "Gender", "Email", "LinkedIn URL",
    "Work Phone", "Mobile Phone", "Country", "Source",
]
deliverable = df_rev[[c for c in deliverable_cols if c in df_rev.columns]].copy()
deliverable.to_excel(base_name + "_Deliverable.xlsx", index=False)
deliverable[["Email", "First Name", "Last Name"]].to_csv(base_name + "_Emails.csv", index=False)
print("Done.")
