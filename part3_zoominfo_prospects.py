# part3_zoominfo_prospects.py
# Part 3 - ZoomInfo Prospects
# Input : Name_Tag_ZI.csv  +  Name_Tag_Accounts.csv
# Output: Name_Tag_ZI Prospects.xlsx, Name_Tag_Deliverable.xlsx,
#         Name_Tag_Emails.csv, Name_Tag_Accounts with Insufficient Prospects.csv

import re, os, sys
import numpy as np
import pandas as pd
import pycountry
import gender_guesser.detector as gender
from fuzzywuzzy import fuzz

np.set_printoptions(threshold=sys.maxsize)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

_gender_detector = gender.Detector()

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text)
    for k, v in {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}.items():
        text = text.replace(k, v)
    return re.sub(r"[^a-zA-Z0-9]", "", text)

def detect_gender(name):
    if not isinstance(name, str) or not name.strip(): return "Unknown"
    g = _gender_detector.get_gender(name.strip())
    if g in ("male", "mostly_male"): return "Male"
    if g in ("female", "mostly_female"): return "Female"
    return "Unknown"

def convert_country_to_code(country):
    codes = {c.name: c.alpha_2 for c in pycountry.countries}
    return codes.get(str(country).strip(), country)

def fuzzy_match_company(name, accounts_df):
    if not isinstance(name, str): return None
    best_score, best_id = 0, None
    for _, row in accounts_df.iterrows():
        score = fuzz.partial_ratio(clean_text(name), clean_text(str(row["Account Name"])))
        if score > best_score:
            best_score, best_id = score, row["Custom Id"]
    return best_id if best_score >= 70 else None

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

# ─── Merge accounts via ZI Company ID, fall back to fuzzy name ───────────────
accounts = pd.read_csv(base_name + "_Accounts.csv", sep=",", encoding="utf-8-sig")
accounts = accounts.rename(columns={"Country": "Account Country"})
df["Custom Id"] = np.nan

if "ZoomInfo Company ID" in df.columns and "ZoomInfo Company ID (Custom 19)" in accounts.columns:
    zi_map = accounts[["ZoomInfo Company ID (Custom 19)", "Custom Id"]].dropna()
    df = df.merge(zi_map.rename(columns={"ZoomInfo Company ID (Custom 19)": "ZoomInfo Company ID"}),
                  on="ZoomInfo Company ID", how="left")

unmatched = df["Custom Id"].isna()
if unmatched.any():
    df.loc[unmatched, "Custom Id"] = df.loc[unmatched, "Company natural"].apply(
        lambda n: fuzzy_match_company(n, accounts)
    )

df = df.merge(
    accounts[["Custom Id", "Account Name", "Account Country", "Tags"]],
    on="Custom Id", how="left"
)

# ─── Country filter ───────────────────────────────────────────────────────────
df["Country"] = df["Country"].apply(convert_country_to_code)
df = df[df["Country"] == df["Account Country"]]

# ─── Assign IDs, source, gender ──────────────────────────────────────────────
df.insert(0, "Prospect ID", ["Z" + str(i + 1).zfill(4) for i in range(len(df))])
df["Source"] = df.get("Source", pd.Series(["ZoomInfo"] * len(df)))
df["Issue"] = ""
df["Plausible Gender"] = df["First Name"].apply(detect_gender)
df["Gender"] = df["Plausible Gender"]
unknown = df["Gender"] == "Unknown"
df.loc[unknown, "Issue"] += "+Unknown Gender"
df["Issue"] = df["Issue"].str.strip("+")

# Threshold
counts = df.groupby("Custom Id").size()
df["# Prospects/Account Range"] = df["Custom Id"].map(counts)

# ─── Export Issues ────────────────────────────────────────────────────────────
issue_cols = [
    "Issue", "# Prospects/Account Range", "Custom Id", "Account Name",
    "First Name", "Last Name", "Title", "Gender", "Email",
    "LinkedIn URL", "Work Phone", "Mobile Phone", "City", "State",
    "Zip", "Country", "Tags", "Prospect ID", "Source",
]
issues_file = base_name + "_Prospect Issues.xlsx"
existing = [c for c in issue_cols if c in df.columns]
with pd.ExcelWriter(issues_file, engine="xlsxwriter") as writer:
    df[existing].to_excel(writer, sheet_name="Issues", index=False)
print(f"Please review: {issues_file}")
input("Press Enter when done reviewing issues...")

df_reviewed = pd.read_excel(issues_file, sheet_name="Issues")
df_reviewed = df_reviewed[df_reviewed["Issue"].isna() | (df_reviewed["Issue"].astype(str).str.strip() == "")]

# ─── Exports ─────────────────────────────────────────────────────────────────
prospect_drop = ["Issue", "# Prospects/Account Range", "Plausible Gender", "Combined_Key"]
prospects_export = df.drop(columns=[c for c in prospect_drop if c in df.columns])
with pd.ExcelWriter(base_name + "_ZI Prospects.xlsx", engine="xlsxwriter") as writer:
    prospects_export.to_excel(writer, sheet_name="Prospects", index=False)

deliverable_cols = [
    "Prospect ID", "Custom Id", "Account Name", "Tags", "First Name",
    "Last Name", "Title", "Gender", "Email", "LinkedIn URL",
    "Work Phone", "Mobile Phone", "Country", "Source",
]
deliverable = df_reviewed[[c for c in deliverable_cols if c in df_reviewed.columns]].copy()
deliverable.to_excel(base_name + "_Deliverable.xlsx", index=False)
deliverable[["Email", "First Name", "Last Name"]].to_csv(base_name + "_Emails.csv", index=False)
print("Done.")
