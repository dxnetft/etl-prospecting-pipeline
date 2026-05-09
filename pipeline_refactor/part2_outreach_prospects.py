# part2_outreach_prospects.py
# Part 2 - Outreach Prospects
# Input : Name_Tag_Outreach.csv  +  Name_Tag_Accounts.csv
# Output: Name_Tag_Outreach Prospects.xlsx
#         Name_Tag_Deliverable.xlsx
#         Name_Tag_Emails.csv
#         Name_Tag_Accounts with Insufficient Prospects.csv
#
# File naming convention: "Requestor Name_Outreach Tag_Outreach.csv"

#v2026-04

import numpy as np
import pandas as pd
import sys
import os

from utils import run_prospect_pipeline

np.set_printoptions(threshold=sys.maxsize)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

CONFIG = {
    "source_label": "Outreach",
    "prospect_id_prefix": "O",
    "reader": "csv",
    "sheet": None,
    "filter_verified": False,
    "rename_cols": {
        "Custom Field 32": "Custom Id",
        "Custom Field 18": "ZoomInfo Contact ID (Custom 18)",
        "Custom Field 29": "LG_Source Evidence (Custom 29)",
        "LinkedIn": "LinkedIn URL",
        "Street": "Address",
        "Zipcode": "Zip",
        "Custom Field 19": "ZoomInfo Company ID (Custom 19)",
        "Company Natural": "Company natural",
        "Company Founded At": "Company founded date",
        "Custom Field 12": "Company SIC Code (Custom 12)",
        "Custom Field 11": "Company NAICS Code (Custom 11)",
    },
    "desired_columns": [
        "Custom Id", "Account Name", "First Name", "Middle Name", "Last Name",
        "Gender", "Title", "Email", "Work Phone", "Mobile Phone",
        "LinkedIn URL", "Address", "City", "State", "Zip", "Country",
    ],
    "columns_to_delete": [],
    "merge_strategy": "custom_id",
    "filter_same_country": False,
    "convert_country": False,
    "convert_account_country": False,
    "format_phones": False,
    "validation": {
        "include_bad_gender": True,
        "include_bad_country": False,
    },
    "optional_inputs": [],
    "issue_cols": [
        "Issue", "# Prospects/Account Range", "Custom Id", "Account Name",
        "First Name", "Last Name", "Title", "Gender", "Plausible Gender",
        "Email", "Domain Score", "LinkedIn URL", "Work Phone", "Mobile Phone",
        "City", "State", "Zip", "Country", "Tags", "Prospect ID",
    ],
    "prospects_output": "_Outreach Prospects.xlsx",
    "drop_from_prospects_export": [
        "Issue", "# Prospects/Account Range", "Plausible Gender", "Domain Score",
    ],
    "deliverable_extra_cols": [],
    "source_from_zi": False,
}

# ─── Interactive inputs ───────────────────────────────────────────────────────

file_name = input("Please enter the Excel file name (including .csv extension): ")
base_name = file_name.replace("_Outreach.csv", "")

# Pre-process: drop rows without email or account assignment, overwrite CSV in place
with open(file_name, encoding="utf-8-sig") as _f:
    _first = _f.readline()
_sep = ";" if _first.count(";") > _first.count(",") else ","
_df = pd.read_csv(file_name, sep=_sep, encoding="utf-8-sig")
_df = _df.dropna(subset=["Email"])
_df = _df.dropna(subset=["Custom Field 32"])
print(len(_df), " - # Rows after excluding records without emails and account assignments")
_df["Custom Field 32"] = pd.to_numeric(_df["Custom Field 32"], errors="coerce").fillna(0).astype(int)
_df.to_csv(file_name, index=False, encoding="utf-8-sig")  # overwrite in place

threshold = int(input("Enter the number of prospects per account requested: "))
hide_email_choice = int(input("Do you want to hide Email column in Deliverable.xlsx? (1 = Hide, 2 = Keep): "))
hide_email = (hide_email_choice == 1)

# ─── Run pipeline ─────────────────────────────────────────────────────────────

run_prospect_pipeline(CONFIG, base_name, threshold, hide_email)
