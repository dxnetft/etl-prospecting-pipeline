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

_raw = pd.read_excel(file_name, sheet_name="Template", header=None, nrows=10)
_header_row = _raw.index[
    _raw.apply(
        lambda row: row.astype(str).str.strip().eq("Account ID").any()
                  & row.astype(str).str.strip().eq("Account Name").any(),
        axis=1
    )
]
if _header_row.empty:
    raise ValueError("Could not find header row (with 'Account ID' and 'Account Name') in the accounts file.")
header_idx = int(_header_row[0])
del _raw
accounts = pd.read_excel(
    file_name,
    sheet_name="Template",
    skiprows=header_idx
).rename(columns={
    "Website URL (if Account ID is not available)": "Website URL"
})
# Drop rows where Account ID is not numeric (instruction / blank / note rows)
accounts["_id_num"] = pd.to_numeric(accounts["Account ID"], errors="coerce")
accounts = accounts.dropna(subset=["_id_num"]).drop(columns="_id_num").reset_index(drop=True)

print(len(accounts), " - # Rows in Accounts Data")

# ─── Load CRM ─────────────────────────────────────────────────────────────────

_crm_raw = pd.read_excel(
    "1_Account Master Data Analytics_Report.xlsx",
    sheet_name="EMDA Account Master Data",
    header=None,
    nrows=10
)
_crm_header_row = _crm_raw.index[
    _crm_raw.apply(
        lambda row: row.astype(str).str.strip().eq("Business Partner ID").any()
                  & row.astype(str).str.strip().eq("Organization Name1").any(),
        axis=1
    )
]
if _crm_header_row.empty:
    raise ValueError("Could not find header row in the CRM file.")
_crm_header_idx = int(_crm_header_row[0])
crm_data = pd.read_excel(
    "1_Account Master Data Analytics_Report.xlsx",
    sheet_name="EMDA Account Master Data",
    skiprows=_crm_header_idx
).rename(columns={
    "Business Partner ID": "Account ID",
    "Organization Name1": "Account Name Name",
    "Account Web Address": "Website URL",
    "GEO Level 3 Country Descr": "Country"
})
# Drop rows where Account ID is not numeric (instruction / blank rows)
crm_data["_crm_id_num"] = pd.to_numeric(crm_data["Account ID"], errors="coerce")
crm_data = crm_data.dropna(subset=["_crm_id_num"]).drop(columns="_crm_id_num").reset_index(drop=True)

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
        print("\n[WARNING] Duplicate records found based on valid Account ID:\n")
        print(duplicates_id.to_string())
    else:
        print("\n[OK] No duplicates found based on valid Account ID.")
else:
    print("\n[INFO] No valid Account IDs found, skipping Account ID duplicate check.")

name_mask = accounts["Account Name"].notna() & (accounts["Account Name"].str.strip() != "")
duplicates_name = accounts[name_mask & accounts.duplicated(subset="Account Name", keep=False)]

if not duplicates_name.empty:
    print("\n[WARNING] Duplicate records found based on Account Name:\n")
    print(duplicates_name.to_string())
else:
    print("\n[OK] No duplicates found based on Account Name.")

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
    print(f"\n[FLAG] Found {len(dummy_accounts)} accounts containing the word 'dummy':\n")
    print(dummy_accounts.to_string())
else:
    print("\n[OK] No accounts found with the word 'dummy'.")

# ─── Enrich from CRM ──────────────────────────────────────────────────────────

crm_data["Account ID"] = pd.to_numeric(crm_data["Account ID"], errors="coerce")
crm_data = crm_data.drop_duplicates(subset="Account ID", keep="first")
crm_lookup = crm_data.set_index("Account ID")

for idx in accounts[valid_id_mask].index:
    acc_id = accounts.at[idx, "Account ID"]
    if acc_id in crm_lookup.index:
        if pd.isna(accounts.at[idx, "Website URL"]) or str(accounts.at[idx, "Website URL"]).strip() in ("", "nan"):
            accounts.at[idx, "Website URL"] = crm_lookup.at[acc_id, "Website URL"]
        if pd.isna(accounts.at[idx, "Country"]) or str(accounts.at[idx, "Country"]).strip() in ("", "nan"):
            accounts.at[idx, "Country"] = crm_lookup.at[acc_id, "Country"]

# ─── Clean Website URLs ───────────────────────────────────────────────────────

_valid_url = accounts["Website URL"].str.strip()
valid_website_mask = (
    (accounts["Website URL"] != "") &
    (_valid_url != "#") &
    (_valid_url.str.lower() != "nan") &
    (_valid_url != "None")
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

print(f"\nNumber of Accounts: {len(accounts)}")

print(accounts["Country"].value_counts(dropna=False))

# ─── Export ───────────────────────────────────────────────────────────────────

output_file = base_name + ".csv"
accounts.to_csv(output_file, sep=",", encoding="utf-8-sig", index=False)
print(f"\nFile saved as {output_file}")
