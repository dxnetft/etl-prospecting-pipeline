# etl-prospecting-pipeline

Python ETL pipeline for B2B prospect data enrichment across three sources:
**Outreach**, **ZoomInfo**, and **LeadGenius**.

## Pipeline Overview

| Part | Script | Description |
|------|--------|-------------|
| 1 | `part1_account_setup.py` | Load and clean account master data |
| 2 | `part2_outreach_prospects.py` | Process Outreach CRM exports |
| 3 | `part3_zoominfo_prospects.py` | Process ZoomInfo CSV exports |
| 4 | `part4_leadgenius_prospects.py` | Process LeadGenius XLSX exports |
| 5 | `part5_xlsx_to_csv.py` | Convert Prospects XLSX to CSV for Outreach upload |

## Outputs per run
- `*_Prospects.xlsx` — enriched prospect list
- `*_Deliverable.xlsx` — formatted delivery file with issue categories
- `*_Emails.csv` — email-only export
- `*_Accounts with Insufficient Prospects.csv` — accounts below threshold

## Requirements
```
pip install pandas numpy pycountry fuzzywuzzy gender-guesser xlsxwriter phonenumbers openpyxl
```
