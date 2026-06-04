# part5_xlsx_to_csv.py
# Part 5 - XLSX to CSV Converter
# Input : Name_Tag_Deliverable.xlsx
#         Name_Tag_Outreach Prospects.xlsx (optional)
#         Name_Tag_LG Prospects.xlsx       (optional)
#         Name_Tag_ZI Prospects.xlsx       (optional)
# Output: Name_Tag_Outreach Prospects.csv
#         Name_Tag_LG Prospects.csv
#         Name_Tag_ZI Prospects.csv
#         Name_Tag_Prospect Upload.csv     (if template sheet has data)
#
# File naming convention: "Requestor Name_Outreach Tag_Deliverable.xlsx"

#v2025-11

import numpy as np
import pandas as pd
import pycountry
import sys
import os
import time as _time

np.set_printoptions(threshold=sys.maxsize)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

# ─── Timer ────────────────────────────────────────────────────────────────────

class _Timer:
    def __init__(self):
        self._t0 = _time.perf_counter()
        self._cps = []
    def cp(self, label):
        now = _time.perf_counter()
        elapsed = now - self._t0
        self._cps.append((label, elapsed))
        self._t0 = now
        return elapsed
    def summary(self, records=0):
        print("\n+----------------------------------------------------------+")
        print("|  PERFORMANCE PROFILE                                     |")
        print("+----------------------------------------------------------+")
        total = 0.0
        for label, elapsed in self._cps:
            total += elapsed
            bar = "#" * max(1, int(elapsed * 40 / max(self._cps, key=lambda x: x[1])[1]))
            print(f"|  {label:<40s} {elapsed:>7.3f}s {bar}")
        print("+----------------------------------------------------------+")
        print(f"|  {'TOTAL':<40s} {total:>7.3f}s")
        if records and total > 0:
            print(f"|  {'THROUGHPUT':<40s} {records/total:>7.0f} rec/s")
        print("+----------------------------------------------------------+")

_timer = _Timer()

# ─── Load Deliverable ─────────────────────────────────────────────────────────

file_name = input("Please enter the Excel file name (including .xlsx extension): ")
base_name = file_name.replace("_Deliverable.xlsx", "")

prospects = pd.read_excel(file_name, sheet_name="Prospects")
print(len(prospects), " - # Rows in Prospects Data\n")
print(prospects["Tags"].value_counts().sort_index(), "\n")
_timer.cp("Load Deliverable.xlsx")

# ─── Helper Functions ─────────────────────────────────────────────────────────

def apply_additional_transformations(df):
    """Rename Custom Id → Account custom ID and Account Name → Company if needed."""
    if "Custom Id" in df.columns and (df["Custom Id"].fillna(0) != 0).any():
        df = df.rename(columns={"Custom Id": "Account custom ID"})
        df["Account custom ID"] = df["Account custom ID"].astype(int)
    if "Company" not in df.columns and "Account Name" in df.columns:
        df = df.rename(columns={"Account Name": "Company"})
    return df


def process_file(file_name, remove_source=False, output_name=None):
    """
    Load a Prospects xlsx, merge Tags from the Deliverable by Prospect ID,
    apply transformations, and export as CSV.
    """
    if not os.path.exists(file_name):
        print(f"File not found: {file_name}")
        return

    df = pd.read_excel(file_name)
    df = apply_additional_transformations(df)

    if "Tags" in df.columns:
        df.drop(columns=["Tags"], inplace=True)

    if "Prospect ID" in df.columns and "Prospect ID" in prospects.columns:
        df = df.merge(
            prospects[["Prospect ID", "Tags"]],
            on="Prospect ID",
            how="left"
        )
    else:
        print(f"'Prospect ID' missing in either Deliverable or {file_name}.")
        return

    if "Tags" in df.columns:
        df.rename(columns={"Tags": "tags"}, inplace=True)

    if remove_source and "Source" in df.columns:
        df.drop(columns=["Source"], inplace=True)

    if "Prospect ID" in df.columns:
        df.drop(columns=["Prospect ID"], inplace=True)

    df.to_csv(output_name, index=False, sep=",", encoding="utf-8-sig")
    print(f"File saved as {output_name}")
    _timer.cp(f"Export {output_name.split(chr(92))[-1].split('/')[-1]}")


# ─── Export CSVs ──────────────────────────────────────────────────────────────

process_file(
    base_name + "_Outreach Prospects.xlsx",
    remove_source=True,
    output_name=base_name + "_Outreach Prospects.csv"
)

process_file(
    base_name + "_LG Prospects.xlsx",
    remove_source=False,
    output_name=base_name + "_LG Prospects.csv"
)

process_file(
    base_name + "_ZI Prospects.xlsx",
    remove_source=False,
    output_name=base_name + "_ZI Prospects.csv"
)

# ─── Prospect Upload (from template sheet) ────────────────────────────────────

if not os.path.exists(base_name + "_Deliverable.xlsx"):
    print("Deliverable file not found, skipping Prospect Upload export.")
else:
    try:
        upload_df = pd.read_excel(file_name, sheet_name="Prospect Upload", skiprows=6)

        if upload_df.empty or upload_df.dropna(how="all").empty:
            print("Prospect Upload sheet is empty — skipping.")
        else:
            print(upload_df.shape, " - Prospects Data")
            print(upload_df.head(3).to_string())

            upload_df.columns = (
                upload_df.columns.str.strip().str.replace(r'\s+', ' ', regex=True)
            )

            # ── Step 1: Custom Id / Account Name presence ──
            has_account_id = "Custom Id" in upload_df.columns
            has_company_name = "Account Name" in upload_df.columns

            if has_account_id and has_company_name:
                print("You can proceed: Both columns have values.")
            elif has_account_id:
                print("Proceed: 'Custom Id' column has values.")
            elif has_company_name:
                print("Proceed: 'Account Name' column has values.")
            else:
                print("Error: Both 'Custom Id' and 'Account Name' are missing.")

            # ── Steps 2–7: Missing value checks ──
            for col, label in [
                ("Email", "Email"),
                ("Title", "Title"),
                ("First Name", "First Name"),
                ("Last Name", "Last Name"),
                ("Gender", "Gender"),
            ]:
                if col in upload_df.columns:
                    empty = upload_df[upload_df[col].isna() | (upload_df[col] == "")]
                    if not empty.empty:
                        print(f"\nRows with missing '{col}':")
                    else:
                        print(f"No missing values found in '{col}'.")
                    print(empty.shape, f" - Empty {label}")
                else:
                    print(f"\n'{col}' column is missing.")

            # ── Step 8: Fix Countries ──
            country_codes = {c.name: c.alpha_2 for c in pycountry.countries}

            def convert_country(val):
                return country_codes.get(str(val).strip(), val)

            if "Country" in upload_df.columns:
                upload_df["Country"] = upload_df["Country"].apply(convert_country)
                print("# Countries:", upload_df["Country"].nunique())
                print(upload_df["Country"].value_counts())

            # ── Step 9: Fix Work Phone ──
            def add_plus_to_phone(number):
                if pd.notnull(number):
                    s = str(number).strip().replace(" ", "")
                    if s.isdigit():
                        return f"+{s}"
                return number

            if "Work Phone" in upload_df.columns:
                upload_df["Work Phone"] = upload_df["Work Phone"].apply(add_plus_to_phone)

            # ── Step 10: Email or Work Phone existence ──
            has_email = "Email" in upload_df.columns and upload_df["Email"].notna().any()
            has_phone = "Work Phone" in upload_df.columns and upload_df["Work Phone"].notna().any()
            if has_email or has_phone:
                print("Proceed: At least one of 'Email' or 'Work Phone' has data.")
            else:
                print("Error: Both 'Email' and 'Work Phone' are missing or empty.")

            # ── Step 11: Source ──
            if "Source" in upload_df.columns:
                empty_source = upload_df[upload_df["Source"].isna() | (upload_df["Source"] == "")]
                if not empty_source.empty:
                    print("\nRows with missing 'Source':")
                    print(empty_source.to_string())
                else:
                    print("No missing values found in 'Source'.")
                print(empty_source.shape, " - Empty Source")
            else:
                print("\n'Source' column is missing.")

            # ── Step 12: Missing Country ──
            if "Country" in upload_df.columns:
                empty_country = upload_df[upload_df["Country"].isna() | (upload_df["Country"] == "")]
                if not empty_country.empty:
                    print("\nRows with missing 'Country':")
                    print(empty_country.to_string())
                else:
                    print("No missing values found in 'Country'.")
                print(empty_country.shape, " - Empty Country")

                # Strip "XX - Country Name" → "XX"
                def extract_country_code(val):
                    if pd.isna(val) or not str(val).strip():
                        return val
                    return str(val).split("-")[0].strip()

                upload_df["Country"] = upload_df["Country"].apply(extract_country_code)
                print("# Countries:", upload_df["Country"].nunique())
                print(upload_df["Country"].value_counts())

            # ── Rename and export ──
            upload_df = upload_df.rename(columns={"Custom Id": "Account custom ID"})
            if "Account custom ID" in upload_df.columns:
                upload_df["Account custom ID"] = (
                    pd.to_numeric(upload_df["Account custom ID"], errors="coerce")
                    .fillna(0).astype(int)
                )

            print("# Tags:", upload_df["Tags"].value_counts().sort_index() if "Tags" in upload_df.columns else "N/A")

            upload_output = base_name + "_Prospect Upload.csv"
            upload_df.to_csv(upload_output, sep=",", encoding="utf-8-sig", index=False)
            print(f"File saved as {upload_output}")
            _timer.cp("Export Prospect Upload.csv")

    except Exception as e:
        print(f"Could not process Prospect Upload sheet: {e}")

# ── Performance summary ──
_timer.summary(records=len(prospects))
