# part3_zoominfo_prospects.py
# Part 3 - ZoomInfo Prospects
# Input : Name_Tag_ZI.csv  +  Name_Tag_Accounts.csv
#         (optionally) Name_Tag_Outreach Prospects.xlsx, Name_Tag_LG Prospects.xlsx
# Output: Name_Tag_ZI Prospects.xlsx
#         Name_Tag_Deliverable.xlsx
#         Name_Tag_Emails.csv
#         Name_Tag_Accounts with Insufficient Prospects.csv
#
# File naming convention: "Requestor Name_Outreach Tag_ZI.csv"

#v2026-04

import numpy as np
import pandas as pd
import sys

from utils import run_prospect_pipeline

np.set_printoptions(threshold=sys.maxsize)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

CONFIG = {
    "source_label": "ZoomInfo",
    "prospect_id_prefix": "Z",
    "reader": "csv",
    "sheet": None,
    "filter_verified": False,
    "rename_cols": {
        "ZoomInfo Contact ID": "ZoomInfo Contact ID (Custom 18)",
        "Job Title": "Title",
        "Direct Phone Number": "Work Phone",
        "Email Address": "Email",
        "Mobile phone": "Mobile Phone",
        "ZoomInfo Contact Profile URL": "LG_Source Evidence (Custom 29)",
        "LinkedIn Contact Profile URL": "LinkedIn URL",
        "Person Street": "Address",
        "Person City": "City",
        "Person State": "State",
        "Person Zip Code": "Zip",
        "ZoomInfo Company ID": "ZoomInfo Company ID (Custom 19)",
        "Company Name": "Company natural",
        "Founded Year": "Company founded date",
        "SIC Code 1": "Company SIC Code (Custom 12)",
        "NAICS Code 1": "Company NAICS Code (Custom 11)",
    },
    "desired_columns": [
        "Custom Id", "Account Name", "Account Country", "Company natural", "Tags",
        "ZoomInfo Contact ID (Custom 18)", "Last Name", "First Name", "Middle Name",
        "Gender", "Title", "Work Phone", "Email", "Mobile Phone",
        "LG_Source Evidence (Custom 29)", "LinkedIn URL", "Address", "City", "State",
        "Zip", "Country", "ZoomInfo Company ID (Custom 19)", "Website",
        "Company founded date", "Company SIC Code (Custom 12)", "Company NAICS Code (Custom 11)",
    ],
    "columns_to_delete": [],
    "merge_strategy": "zi_fallback",
    "filter_same_country": True,
    "convert_country": True,
    "convert_account_country": False,
    "format_phones": False,
    "validation": {
        "include_bad_gender": False,
        "include_bad_country": False,
    },
    "optional_inputs": [
        "_Outreach Prospects.xlsx",
    ],
    "issue_cols": [
        "Issue", "# Prospects/Account Range", "Custom Id", "Account Name",
        "First Name", "Last Name", "Title", "Gender", "Email", "Domain Score",
        "LinkedIn URL", "Work Phone", "Mobile Phone", "City", "State", "Zip",
        "Country", "Tags", "Prospect ID", "Source",
    ],
    "prospects_output": "_ZI Prospects.xlsx",
    "drop_from_prospects_export": [
        "Company Status", "Contact Status", "Issue", "# Prospects/Account Range",
        "Plausible Gender", "Domain Score", "Combined_Key",
    ],
    "deliverable_extra_cols": [],
    "source_from_zi": True,
}

# ─── Interactive inputs ───────────────────────────────────────────────────────

file_name = input("Please enter the Excel file name (including .csv extension): ")
base_name = file_name.replace("_ZI.csv", "")

threshold = int(input("Enter the number of prospects per account requested: "))
hide_email_choice = int(input("Do you want to hide Email column in Deliverable.xlsx? (1 = Hide, 2 = Keep): "))
hide_email = (hide_email_choice == 1)

# ─── Run pipeline ─────────────────────────────────────────────────────────────

run_prospect_pipeline(CONFIG, base_name, threshold, hide_email)
