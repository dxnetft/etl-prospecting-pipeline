# part2_outreach_prospects.py
# Part 2 - Outreach Prospects
# Input : Name_Tag_Outreach.csv  +  Name_Tag_Accounts.csv
# Output: Name_Tag_Outreach Prospects.xlsx, Name_Tag_Deliverable.xlsx,
#         Name_Tag_Emails.csv, Name_Tag_Accounts with Insufficient Prospects.csv

import sys
import numpy as np
import pandas as pd
from utils import (
    detect_gender, is_private_email, is_bad_email, domain_match_score,
)

np.set_printoptions(threshold=sys.maxsize)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

# ─── Inputs ───────────────────────────────────────────────────────────────────
file_name = input("Please enter the Excel file name (including .csv extension): ")
base_name = file_name.replace("_Outreach.csv", "")

df = pd.read_csv(file_name, sep=",", encoding="utf-8-sig")
df = df.dropna(subset=["Email"])
df = df.dropna(subset=["Custom Field 32"])
print(len(df), " - # Rows after excluding records without emails and account assignments")
df["Custom Field 32"] = pd.to_numeric(df["Custom Field 32"], errors="coerce").fillna(0).astype(int)
df.to_csv(file_name, index=False, encoding="utf-8-sig")

threshold = int(input("Enter the number of prospects per account requested: "))
hide_email_choice = int(input("Do you want to hide Email column in Deliverable.xlsx? (1 = Hide, 2 = Keep): "))
hide_email = (hide_email_choice == 1)

# ─── Rename & select columns ──────────────────────────────────────────────────
df = df.rename(columns={
    "Custom Field 32": "Custom Id",
    "Custom Field 18": "ZoomInfo Contact ID (Custom 18)",
    "LinkedIn": "LinkedIn URL",
    "Street": "Address",
    "Zipcode": "Zip",
})
desired = [
    "Custom Id", "Account Name", "First Name", "Middle Name", "Last Name",
    "Gender", "Title", "Email", "Work Phone", "Mobile Phone",
    "LinkedIn URL", "Address", "City", "State", "Zip", "Country",
]
for col in desired:
    if col not in df.columns:
        df[col] = ""
df = df[desired]

# ─── Merge accounts ───────────────────────────────────────────────────────────
accounts = pd.read_csv(base_name + "_Accounts.csv", sep=",", encoding="utf-8-sig")
accounts = accounts.rename(columns={"Country": "Account Country"})
df["Custom Id"] = pd.to_numeric(df["Custom Id"], errors="coerce").fillna(0).astype(int)
accounts["Custom Id"] = pd.to_numeric(accounts["Custom Id"], errors="coerce").fillna(0).astype(int)
df = pd.merge(df, accounts[["Custom Id", "Account Name", "Tags", "Account Country"]],
              on="Custom Id", how="left")

# ─── Assign IDs, source, issue column ────────────────────────────────────────
df.insert(0, "Prospect ID", ["O" + str(i + 1).zfill(4) for i in range(len(df))])
df["Source"] = "Outreach"
df["Issue"] = ""
df["Plausible Gender"] = df["First Name"].apply(detect_gender)
df["Domain Score"] = ""

# ─── Validation ───────────────────────────────────────────────────────────────
mask = pd.Series([True] * len(df), index=df.index)
bad_email_rows = df[mask].apply(is_bad_email, axis=1)
df.loc[bad_email_rows[bad_email_rows].index, "Issue"] += "+Bad Email"
private_rows = df[mask]["Email"].apply(is_private_email)
df.loc[private_rows[private_rows].index, "Issue"] += "+Private Email"

df["Gender"] = (df["Gender"].astype(str).str.strip().str.lower()
                .map({"male": "Male", "female": "Female"}).fillna("Unknown"))
bad_gender = (df["Gender"] != df["Plausible Gender"]) & (df["Plausible Gender"] != "Unknown")
df.loc[bad_gender, "Issue"] += "+Bad Gender"
df["Issue"] = df["Issue"].str.strip("+")

# ─── Threshold ────────────────────────────────────────────────────────────────
counts = df.groupby("Custom Id").size()
df["# Prospects/Account Range"] = df["Custom Id"].map(counts)

# ─── Export Issues ────────────────────────────────────────────────────────────
issue_cols = [
    "Issue", "# Prospects/Account Range", "Custom Id", "Account Name",
    "First Name", "Last Name", "Title", "Gender", "Plausible Gender",
    "Email", "Domain Score", "LinkedIn URL", "Work Phone", "Mobile Phone",
    "City", "State", "Zip", "Country", "Tags", "Prospect ID",
]
issues_file = base_name + "_Prospect Issues.xlsx"
with pd.ExcelWriter(issues_file, engine="xlsxwriter") as writer:
    df[[c for c in issue_cols if c in df.columns]].to_excel(writer, sheet_name="Issues", index=False)
print(f"Please review: {issues_file}")
input("Press Enter when done reviewing issues...")

# ─── Re-import, build deliverable, export ────────────────────────────────────
df_rev = pd.read_excel(issues_file, sheet_name="Issues")
df_rev = df_rev[df_rev["Issue"].isna() | (df_rev["Issue"].astype(str).str.strip() == "")]

deliverable_cols = [
    "Prospect ID", "Custom Id", "Account Name", "Tags", "First Name",
    "Last Name", "Title", "Gender", "Email", "LinkedIn URL",
    "Work Phone", "Mobile Phone", "Country", "Source",
]
deliverable = df_rev[[c for c in deliverable_cols if c in df_rev.columns]].copy()

prospects_export = df.drop(columns=["Issue", "# Prospects/Account Range", "Plausible Gender",
                                     "Domain Score"], errors="ignore")
with pd.ExcelWriter(base_name + "_Outreach Prospects.xlsx", engine="xlsxwriter") as writer:
    prospects_export.to_excel(writer, sheet_name="Prospects", index=False)

deliverable.to_excel(base_name + "_Deliverable.xlsx", index=False)
deliverable[[c for c in ["Email", "First Name", "Last Name"] if c in deliverable.columns]].to_csv(
    base_name + "_Emails.csv", index=False
)
print("Done.")
