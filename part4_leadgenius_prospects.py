# part4_leadgenius_prospects.py
# Part 4 - LeadGenius Prospects
# Input : Name_Tag_LG.xlsx  +  Name_Tag_Accounts.csv
# Output: Name_Tag_LG Prospects.xlsx, Name_Tag_Deliverable.xlsx,
#         Name_Tag_Emails.csv, Name_Tag_Accounts with Insufficient Prospects.csv

import re, os, sys
import numpy as np
import pandas as pd
import pycountry
import phonenumbers
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

def format_phone(phone_str, country_code="DE"):
    if pd.isna(phone_str) or str(phone_str).strip() == "": return ""
    try:
        parsed = phonenumbers.parse(str(phone_str), country_code)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass
    return str(phone_str)

def fuzzy_match_company(name, accounts_df):
    if not isinstance(name, str): return None
    best_score, best_id = 0, None
    for _, row in accounts_df.iterrows():
        score = fuzz.partial_ratio(clean_text(name), clean_text(str(row["Account Name"])))
        if score > best_score:
            best_score, best_id = score, row["Custom Id"]
    return best_id if best_score >= 70 else None

# ─── Inputs ───────────────────────────────────────────────────────────────────
file_name = input("Please enter the Excel file name (including .xlsx extension): ")
base_name = file_name.replace("_LG.xlsx", "")
threshold = int(input("Enter the number of prospects per account requested: "))
hide_email_choice = int(input("Do you want to hide Email column in Deliverable.xlsx? (1 = Hide, 2 = Keep): "))
hide_email = (hide_email_choice == 1)

# ─── Load & filter ────────────────────────────────────────────────────────────
df = pd.read_excel(file_name, sheet_name="Sheet1")
df = df[df["Contact Status"] == "Verified"]
df = df.rename(columns={
    "Website URL": "Website",
    "Company Name": "Company",
    "otherPhones": "Mobile Phone",
    "Company Phone": "Work Phone",
    "LinkedIn URL": "Company LinkedIn",
    "Job Title": "Title",
    "LinkedIn Profile URL": "LinkedIn URL",
    "Contact City": "City",
    "Contact State": "State",
    "Contact Country": "Country",
    "Contact Zip code": "Zip",
    "gender": "Gender",
    "source": "Source",
})

# Drop unwanted columns
drop_cols = [
    "Street", "industry", "Employee Range", "Revenue Range",
    "Last Updated", "Created Date", "Account CRM ID", "Contact CRM ID",
    "LG Account ID", "LG Contact ID",
]
df = df.drop(columns=[c for c in drop_cols if c in df.columns])

# ─── Merge accounts ───────────────────────────────────────────────────────────
accounts = pd.read_csv(base_name + "_Accounts.csv", sep=",", encoding="utf-8-sig")
accounts = accounts.rename(columns={"Country": "Account Country"})

if "Company" in df.columns:
    df["Custom Id"] = df["Company"].apply(lambda n: fuzzy_match_company(n, accounts))
    _extra = ["Tags"] if "Tags" in accounts.columns else []
    df = df.merge(accounts[["Custom Id", "Account Name", "Account Country"] + _extra],
                  on="Custom Id", how="left")
else:
    df = df.rename(columns={"Country": "Account Country"})

# ─── Country & phone conversion ───────────────────────────────────────────────
df["Country"] = df["Country"].apply(convert_country_to_code)
df["Account Country"] = df["Account Country"].apply(convert_country_to_code)
df["Work Phone"] = df.apply(lambda r: format_phone(r.get("Work Phone"), r.get("Account Country", "DE")), axis=1)
df["Mobile Phone"] = df.apply(lambda r: format_phone(r.get("Mobile Phone"), r.get("Account Country", "DE")), axis=1)

# ─── Assign IDs ───────────────────────────────────────────────────────────────
df.insert(0, "Prospect ID", ["L" + str(i + 1).zfill(4) for i in range(len(df))])
if "Source" not in df.columns:
    df["Source"] = "LeadGenius"
df["Issue"] = ""
df["Plausible Gender"] = df["First Name"].apply(detect_gender)
df["Domain Score"] = ""

# Gender validation
df["Gender"] = (df["Gender"].astype(str).str.strip().str.lower()
                .map({"male": "Male", "female": "Female"}).fillna("Unknown"))
bad_gender = (df["Gender"] != df["Plausible Gender"]) & (df["Plausible Gender"] != "Unknown")
df.loc[bad_gender, "Issue"] += "+Bad Gender"
bad_country = df["Country"] != df["Account Country"]
df.loc[bad_country, "Issue"] += "+Bad Country"
df["Issue"] = df["Issue"].str.strip("+")

# Threshold
counts = df.groupby("Custom Id").size()
df["# Prospects/Account Range"] = df["Custom Id"].map(counts)

# ─── Export Issues ────────────────────────────────────────────────────────────
issue_cols = [
    "Issue", "# Prospects/Account Range", "Custom Id", "Account Name",
    "First Name", "Last Name", "Title", "Gender", "Plausible Gender",
    "Email", "Domain Score", "LinkedIn URL", "Company LinkedIn",
    "Work Phone", "Mobile Phone", "City", "State", "Zip", "Country",
    "Tags", "Prospect ID", "Source",
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
prospect_drop = [
    "Company Status", "Contact Status", "Issue", "# Prospects/Account Range",
    "Plausible Gender", "Domain Score",
]
prospects_export = df.drop(columns=[c for c in prospect_drop if c in df.columns])
with pd.ExcelWriter(base_name + "_LG Prospects.xlsx", engine="xlsxwriter") as writer:
    prospects_export.to_excel(writer, sheet_name="Prospects", index=False)

deliverable_cols = [
    "Prospect ID", "Custom Id", "Account Name", "Tags", "First Name",
    "Last Name", "Title", "Gender", "Email", "Company LinkedIn",
    "LinkedIn URL", "Work Phone", "Mobile Phone", "Country", "Source",
]
deliverable = df_reviewed[[c for c in deliverable_cols if c in df_reviewed.columns]].copy()
deliverable.to_excel(base_name + "_Deliverable.xlsx", index=False)
deliverable[["Email", "First Name", "Last Name"]].to_csv(base_name + "_Emails.csv", index=False)
print("Done.")
