# part2_outreach_prospects.py
# Part 2 - Outreach Prospects
# Input : Name_Tag_Outreach.csv  +  Name_Tag_Accounts.csv
# Output: Name_Tag_Outreach Prospects.xlsx, Name_Tag_Deliverable.xlsx,
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

PRIVATE_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "aol.com", "outlook.com",
    "icloud.com", "mail.com", "live.com"
}
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

def is_private_email(email):
    if pd.isna(email): return False
    return str(email).split("@")[-1].lower() in PRIVATE_DOMAINS

def is_bad_email(row):
    first = str(row["First Name"]).lower()
    last = str(row["Last Name"]).lower()
    email = str(row["Email"]).lower()
    if not email or email == "nan": return False
    return not (
        fuzz.partial_ratio(first, email) > 75 or
        fuzz.partial_ratio(last, email) > 75 or
        (first[0] + last[0]) in email
    )

def domain_match_score(row):
    company = str(row["Account Name"]).lower()
    email = str(row["Email"]).lower()
    if "@" not in email: return np.nan
    domain_core = email.split("@", 1)[1].split(".", 1)[0]
    company_clean = clean_text(company)
    domain_clean = clean_text(domain_core)
    if not company_clean or not domain_clean: return np.nan
    return fuzz.partial_ratio(company_clean, domain_clean)

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
df = pd.merge(df, accounts[["Custom Id", "Account Name", "Tags", "Account Country"]], on="Custom Id", how="left")

# ─── Assign IDs & source ──────────────────────────────────────────────────────
df.insert(0, "Prospect ID", ["O" + str(i + 1).zfill(4) for i in range(len(df))])
df["Source"] = "Outreach"
df["Issue"] = ""
df["Plausible Gender"] = df["First Name"].apply(detect_gender)
df["Domain Score"] = ""

# Validate
mask = pd.Series([True] * len(df), index=df.index)
bad_email_rows = df[mask].apply(is_bad_email, axis=1)
df.loc[bad_email_rows[bad_email_rows].index, "Issue"] += "+Bad Email"
private_rows = df[mask]["Email"].apply(is_private_email)
df.loc[private_rows[private_rows].index, "Issue"] += "+Private Email"

# Gender
df["Gender"] = (df["Gender"].astype(str).str.strip().str.lower()
                .map({"male": "Male", "female": "Female"}).fillna("Unknown"))
bad_gender = (df["Gender"] != df["Plausible Gender"]) & (df["Plausible Gender"] != "Unknown")
df.loc[bad_gender, "Issue"] += "+Bad Gender"
df["Issue"] = df["Issue"].str.strip("+")

# Threshold
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
existing = [c for c in issue_cols if c in df.columns]
with pd.ExcelWriter(issues_file, engine="xlsxwriter") as writer:
    df[existing].to_excel(writer, sheet_name="Issues", index=False)
print(f"Please review: {issues_file}")
input("Press Enter when done reviewing issues...")

# Re-import reviewed issues
df_reviewed = pd.read_excel(issues_file, sheet_name="Issues")
df_reviewed = df_reviewed[df_reviewed["Issue"].isna() | (df_reviewed["Issue"].astype(str).str.strip() == "")]

# ─── Build deliverable ────────────────────────────────────────────────────────
deliverable_cols = [
    "Prospect ID", "Custom Id", "Account Name", "Tags", "First Name",
    "Last Name", "Title", "Gender", "Email", "LinkedIn URL",
    "Work Phone", "Mobile Phone", "Country", "Source",
]
deliverable = df_reviewed[[c for c in deliverable_cols if c in df_reviewed.columns]].copy()

# ─── Exports ─────────────────────────────────────────────────────────────────
prospect_drop = ["Issue", "# Prospects/Account Range", "Plausible Gender", "Domain Score"]
prospects_export = df.drop(columns=[c for c in prospect_drop if c in df.columns])
with pd.ExcelWriter(base_name + "_Outreach Prospects.xlsx", engine="xlsxwriter") as writer:
    prospects_export.to_excel(writer, sheet_name="Prospects", index=False)

deliverable.to_excel(base_name + "_Deliverable.xlsx", index=False)
email_cols = [c for c in ["Email", "First Name", "Last Name"] if c in deliverable.columns]
deliverable[email_cols].to_csv(base_name + "_Emails.csv", index=False)

print("Done. All outputs written.")
