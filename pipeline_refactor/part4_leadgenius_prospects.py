# part4_leadgenius_prospects.py
# Part 4 - LeadGenius Prospects
# Input : Name_Tag_LG.xlsx  +  Name_Tag_Accounts.csv
#         (optionally) Name_Tag_Outreach Prospects.xlsx, Name_Tag_ZI Prospects.xlsx
# Output: Name_Tag_LG Prospects.xlsx
#         Name_Tag_Deliverable.xlsx
#         Name_Tag_Emails.csv
#         Name_Tag_Accounts with Insufficient Prospects.csv
#
# File naming convention: "Requestor Name_Outreach Tag_LG.xlsx"

#v2026-04

import numpy as np
import pandas as pd
import sys

from utils import run_prospect_pipeline

np.set_printoptions(threshold=sys.maxsize)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

CONFIG = {
    "source_label": "LeadGenius",
    "prospect_id_prefix": "L",
    "reader": "xlsx",
    "sheet": "Sheet1",
    "filter_verified": True,
    "rename_cols": {
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
        "Prospect Persona": "Persona name",
        "Prospect Stage": "Stage",
        "WBS Code": "WBS Code (Custom 20)",
        "LG_Outcome_Status": "LG_Outcome_Status (Custom 30)",
        "source": "Source",
    },
    "desired_columns": [
        "Company Status", "Contact Status", "Custom Id", "Account Name",
        "Account Country", "Company", "Tags", "Website", "First Name", "Last Name",
        "Title", "Gender", "Email", "LinkedIn URL", "City", "State", "Country", "Zip",
        "Work Phone", "Mobile Phone", "Company LinkedIn", "Persona name", "Stage",
        "WBS Code (Custom 20)", "LG_Outcome_Status (Custom 30)", "Source",
    ],
    "columns_to_delete": [
        "Street", "City", "State", "Country", "Zip", "industry",
        "Employee Range", "Revenue Range", "tags", "Prospect.tags",
        "Last Updated", "Created Date", "Account CRM ID", "Contact CRM ID",
        "LG Account ID", "LG Contact ID",
    ],
    "merge_strategy": "company_name",
    "filter_same_country": False,
    "convert_country": True,
    "convert_account_country": True,
    "format_phones": True,
    "validation": {
        "include_bad_gender": True,
        "include_bad_country": True,
    },
    "optional_inputs": [
        "_Outreach Prospects.xlsx",
        "_ZI Prospects.xlsx",
    ],
    "issue_cols": [
        "Issue", "# Prospects/Account Range", "Custom Id", "Account Name",
        "First Name", "Last Name", "Title", "Gender", "Plausible Gender",
        "Email", "Domain Score", "LinkedIn URL", "Company LinkedIn",
        "Work Phone", "Mobile Phone", "City", "State", "Zip", "Country",
        "Tags", "Prospect ID", "Source",
    ],
    "prospects_output": "_LG Prospects.xlsx",
    "drop_from_prospects_export": [
        "Company Status", "Contact Status", "Issue", "# Prospects/Account Range",
        "Plausible Gender", "Domain Score",
    ],
    "deliverable_extra_cols": ["Company LinkedIn"],
    "source_from_zi": False,
}

# ─── Interactive inputs ───────────────────────────────────────────────────────

file_name = input("Please enter the Excel file name (including .xlsx extension): ")
base_name = file_name.replace("_LG.xlsx", "")

threshold = int(input("Enter the number of prospects per account requested: "))
hide_email_choice = int(input("Do you want to hide Email column in Deliverable.xlsx? (1 = Hide, 2 = Keep): "))
hide_email = (hide_email_choice == 1)

# ─── Run pipeline ─────────────────────────────────────────────────────────────

run_prospect_pipeline(CONFIG, base_name, threshold, hide_email)
