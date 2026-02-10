# part1_account_setup.py
# Part 1 - Account Setup
# Input : Name_Tag_Accounts.xlsx  +  1_Account Master Data Analytics_Report.xlsx
# Output: Name_Tag_Accounts.csv
#
# File naming convention: "Requestor Name_Outreach Tag_Accounts.xlsx"

#v2025-11

import numpy as np
import pandas as pd
import pycountry
import sys

np.set_printoptions(threshold=sys.maxsize)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

# ─── Load Accounts ────────────────────────────────────────────────────────────

file_name = input("Please enter the Excel file name (including .xlsx extension): ")
base_name = file_name.replace(".xlsx", "")

accounts = pd.read_excel(
    file_name,
    sheet_name="Template",
    skiprows=4
).rename(columns={
    "Website URL (if Account ID is not available)": "Website URL"
})

print(len(accounts), " - # Rows in Accounts Data")

# ─── Load CRM ─────────────────────────────────────────────────────────────────

crm_data = pd.read_excel(
    "1_Account Master Data Analytics_Report.xlsx",
    sheet_name="EMDA Account Master Data",
    skiprows=5
).rename(columns={
    "Business Partner ID": "Account ID",
    "Organization Name1": "Account Name Name",
    "Account Web Address": "Website URL",
    "GEO Level 3 Country Descr": "Country"
})

# ─── Fix Data Types ───────────────────────────────────────────────────────────

accounts["Account ID"] = pd.to_numeric(accounts["Account ID"], errors="coerce")
accounts["Website URL"] = accounts["Website URL"].astype(str)
accounts["Country"] = accounts["Country"].astype(str)

# ─── Duplicate Checks ─────────────────────────────────────────────────────────

valid_id_mask = accounts["Account ID"].notna() & (accounts["Account ID"] >= 10000)

if valid_id_mask.any():
    duplicates_id = accounts[
        accounts.duplicated(subset="Account ID", keep=False) & valid_id_mask
    ]
    if not duplicates_id.empty:
        print("\n⚠️ Duplicate records found based on valid Account ID:\n")
        print(duplicates_id.to_string())
    else:
        print("\n✅ No duplicates found based on valid Account ID.")
else:
    print("\nℹ️ No valid Account IDs found, skipping Account ID duplicate check.")

name_mask = accounts["Account Name"].notna() & (accounts["Account Name"].str.strip() != "")
duplicates_name = accounts[name_mask & accounts.duplicated(subset="Account Name", keep=False)]

if not duplicates_name.empty:
    print("\n⚠️ Duplicate records found based on Account Name:\n")
    print(duplicates_name.to_string())
else:
    print("\n✅ No duplicates found based on Account Name.")

blanks_name = accounts[~name_mask]
if not blanks_name.empty:
    print("\n Records found with blank Account Name:\n")
    print(blanks_name.to_string())
else:
    print("\n No blank Account Names found.")

dummy_accounts = accounts[
    accounts["Account Name"].astype(str).str.lower().str.contains("dummy")
]
if not dummy_accounts.empty:
    print(f"\n🚩 Found {len(dummy_accounts)} accounts containing the word 'dummy':\n")
    print(dummy_accounts.to_string())
else:
    print("\n✅ No accounts found with the word 'dummy'.")

# ─── Enrich from CRM ──────────────────────────────────────────────────────────

crm_data["Account ID"] = pd.to_numeric(crm_data["Account ID"], errors="coerce")
crm_lookup = crm_data.set_index("Account ID")

for idx in accounts[valid_id_mask].index:
    acc_id = accounts.at[idx, "Account ID"]
    if acc_id in crm_lookup.index:
        if pd.isna(accounts.at[idx, "Website URL"]) or str(accounts.at[idx, "Website URL"]).strip() in ("", "nan"):
            accounts.at[idx, "Website URL"] = crm_lookup.at[acc_id, "Website URL"]
        if pd.isna(accounts.at[idx, "Country"]) or str(accounts.at[idx, "Country"]).strip() in ("", "nan"):
            accounts.at[idx, "Country"] = crm_lookup.at[acc_id, "Country"]

# ─── Clean Website URLs ───────────────────────────────────────────────────────

valid_website_mask = (
    accounts["Website URL"].notna() &
    (accounts["Website URL"].astype(str).str.strip() != "") &
    (accounts["Website URL"].astype(str).str.strip() != "#")
)

accounts.loc[valid_website_mask, "Website URL"] = (
    accounts.loc[valid_website_mask, "Website URL"]
    .astype(str)
    .str.lower()
    .str.replace(r"^https?://", "", regex=True)
    .str.split("/")
    .str[0]
    .str.replace(r"^www[0-9]*\.", "", regex=True)
)

missing_websites_count = (~valid_website_mask).sum()
print(f"\nAccounts without valid Website URLs: {missing_websites_count}")

# ─── Clean Countries ──────────────────────────────────────────────────────────

def resolve_country(name):
    name = str(name).strip()
    if len(name) == 2:
        try:
            return pycountry.countries.get(alpha_2=name.upper()).name
        except Exception:
            return name.title()
    return name.title()

accounts["Country"] = accounts["Country"].astype(str).apply(resolve_country)

# ─── Sort & Rename ────────────────────────────────────────────────────────────

accounts.rename(columns={"Account ID": "Custom Id"}, inplace=True)
accounts = accounts.sort_values(by="Account Name")

if "Assigned to" in accounts.columns:
    accounts.rename(columns={"Assigned to": "Tags"}, inplace=True)

if "Tags" in accounts.columns:
    accounts["Tags"] = accounts["Tags"].astype(str)

accounts.reset_index(drop=True, inplace=True)

if valid_id_mask.any():
    unique_accounts = accounts.loc[valid_id_mask, "Custom Id"].nunique()
    print(f"\nNumber of Accounts: {unique_accounts}")
else:
    unique_accounts = accounts["Account Name"].dropna().nunique()
    print(f"\nNumber of Accounts: {unique_accounts}")

print(accounts["Country"].value_counts(dropna=False))

# ─── Export ───────────────────────────────────────────────────────────────────

output_file = base_name + ".csv"
accounts.to_csv(output_file, sep=",", encoding="utf-8-sig", index=False)
print(f"\nFile saved as {output_file}")
