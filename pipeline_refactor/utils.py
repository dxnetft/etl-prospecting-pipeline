# utils.py — Shared pipeline utilities
# Used by part2, part3, part4

import re
import numpy as np
import pandas as pd
import pycountry
import gender_guesser.detector as gender
from fuzzywuzzy import fuzz

# ─── Timer ────────────────────────────────────────────────────────────────────

class Timer:
    """Lightweight per-stage timer using perf_counter."""

    def __init__(self):
        import time as _t
        self._time = _t
        self._t0 = _t.perf_counter()
        self._checkpoints = []

    def checkpoint(self, label: str):
        now = self._time.perf_counter()
        elapsed = now - self._t0
        self._checkpoints.append((label, elapsed))
        self._t0 = now
        return elapsed

    def summary(self, records: int = 0) -> str:
        lines = ["\n╔══════════════════════════════════════════════════════════╗",
                 "║  PERFORMANCE PROFILE                                     ║",
                 "╠══════════════════════════════════════════════════════════╣"]
        total = 0.0
        for i, (label, elapsed) in enumerate(self._checkpoints):
            total += elapsed
            bar = "█" * max(1, int(elapsed * 40 / max(
                self._checkpoints, key=lambda x: x[1]
            )[1]))
            lines.append(f"║  {label:<40s} {elapsed:>7.3f}s {bar}")
        lines.append("╠══════════════════════════════════════════════════════════╣")
        lines.append(f"║  {'TOTAL':<40s} {total:>7.3f}s")
        if records and total > 0:
            lines.append(f"║  {'THROUGHPUT':<40s} {records/total:>7.0f} rec/s")
        lines.append("╚══════════════════════════════════════════════════════════╝")
        return "\n".join(lines)


# ─── Constants ────────────────────────────────────────────────────────────────

PRIVATE_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.de", "hotmail.com", "aol.com",
    "outlook.com", "icloud.com", "mail.com", "live.com", "t-online.de",
    "web.de", "gmx.de", "info.com"
}

WORDS_TO_REMOVE = {
    # English
    'inc', 'llc', 'ltd', 'corporation', 'corp', 'company', 'co', 'and',
    # German
    'gmbh', 'ag', 'kg', 'ohg', 'gbr', 'ug', 'eg', 'ev', 'se', 'kgaa',
    'betrieb', 'unternehmen', 'firma', 'holding', 'gruppe', 'group',
    # Switzerland
    'sa', 'sarl', 'sàrl', 'kollektivgesellschaft', 'kommanditgesellschaft',
    'einzelfirma', 'einzelunternehmen', 'genossenschaft', 'verein', 'stiftung',
    'société', 'societe', 'anonyme', 'responsabilité', 'responsabilite',
    'limitée', 'limitee', 'simple', 'commandite', 'coopérative', 'cooperative',
    'fondation', 'association', 'società', 'societa', 'anonima',
    'responsabilità', 'responsabilita', 'limitata', 'semplice', 'accomandita',
    'cooperativa', 'fondazione', 'associazione',
    # Austria
    'og', 'reg', 'gen', 'privatstiftung', 'gemeinnützige', 'gemeinnuetzige',
    'sparkasse', 'bank', 'versicherung', 'aktiengesellschaft', 'gesellschaft',
    'beschränkter', 'beschraenkter', 'haftung', 'offene', 'handelsgesellschaft',
    'beteiligungsgesellschaft', 'verwaltungs', 'beteiligungs', 'investment',
    'capital', 'venture', 'partners', 'mbh',
    # Poland
    'sp', 'zoo', 'spka', 'spółka', 'spolka', 'jawna', 'komandytowa', 'partnerska',
    # Czech Republic
    'sro', 'ks', 'vos', 'komanditni', 'verejne', 'obchodni', 'spolecnost',
    # Slovakia
    'doo', 'akciova', 'spolocnost', 'komanditna', 'verejná', 'obchodná',
    # Hungary
    'kft', 'rt', 'nyrt', 'zrt', 'bt', 'kkt', 'korlátolt', 'felelősségű',
    'társaság', 'felelossegu', 'tarsasag', 'részvénytársaság', 'resvenytarsasag',
    # Slovenia
    'dd', 'kd', 'družba', 'druzba', 'delniška', 'delnicka', 'omejeno',
    'odgovornostjo',
    # Croatia
    'jdoo', 'jdd', 'dioničko', 'dionicko', 'društvo', 'drustvo', 'ograničena',
    'ogranicena', 'odgovornost',
    # Serbia
    'ad', 'ortačko', 'ortacko', 'preduzeće', 'preduzece', 'ograničenom',
    'ogranicenom', 'odgovornošću', 'odgovornoscu',
    # Bulgaria
    'ood', 'eood', 'дружество', 'druzhestvo', 'ограничена', 'otgovornost',
    'отговорност',
    # Romania
    'srl', 'societate', 'responsabilitate', 'anonim', 'actiuni', 'acțiuni',
    'cu', 'pe', 'în', 'comandită',
    # Baltic states
    'oü', 'osaühing', 'osauhing', 'aktsiaselts', 'täisühing', 'taisuhing',
    'usaldusühing', 'usaldusushing', 'sia', 'sabiedrība', 'sabiedriba',
    'ierobežotu', 'ierobezotu', 'atbildību', 'atbildibu', 'akciju',
    'uab', 'ab', 'uždaroji', 'uzdaroji', 'akcinė', 'akcine', 'bendrovė',
    'bendrove', 'atsakomybe', 'atsakomybė',
    # Central Asia
    'too', 'ao', 'товарищество', 'tovarishchestvo', 'ограниченной',
    'ogranichennoj', 'ответственностью', 'otvetstvennostyu', 'акционерное',
    'aktsionernoe', 'общество', 'obshchestvo', 'жауапкершілігі',
    'zhauapkershiligi', 'шектеулі', 'shekteuli', 'серіктестік', 'seriktest',
    'серіктес', 'seriktes', 'акционерлік', 'aktsionerlik', 'қоғам', 'qogam',
    'mchj', 'ak', 'унитарное', 'unitarnoe', 'предприятие', 'predpriyatie',
    'масъулияти', 'masuliyati', 'маҳдуд', 'mahdud', 'жамият', 'jamiyat',
    'акциядорлик', 'aksiyadirlik', 'жамиятлар', 'jamiyatlar', 'корхона',
    'korhona', 'ташкилот', 'tashkilot', 'бирлашма', 'birlashma',
    'mmc', 'məhdud', 'mehdud', 'məsuliyyətli', 'mesuliyyetli', 'cəmiyyət',
    'cemiyyet', 'səhmdar', 'sehmdar', 'şirkət', 'shirket', 'məsuliyyət',
    'mesuliyyet', 'ortaqliq', 'müəssisə', 'muessise', 'təşkilat', 'teshkilat',
    'birlik', 'ittifaq',
    # Russia/Soviet legacy
    'ooo', 'ооо', 'zao', 'зао', 'oao', 'оао', 'cjsc', 'ojsc', 'pao', 'пао',
    'нпо', 'npo', 'гуп', 'gup', 'фгуп', 'fgup', 'мп', 'mp', 'ип', 'ip',
    'чп', 'chp', 'пвт', 'pvt', 'лтд', 'коллективное', 'kollektivnoe',
    'государственное', 'gosudarstvennoe', 'муниципальное', 'munitsipalnoe',
    # Common articles/prepositions
    'the', 'der', 'die', 'das', 'von', 'zu', 'im', 'am', 'an', 'auf',
    'za', 'na', 'od', 'do', 'po', 'pre', 've', 'ke', 'se',
    'və', 'va', 'ва', 'и', 'i', 'у', 'u', 'о',
    # North Macedonia / Montenegro
    'dooel', 'trading', 'друштво',
}

COUNTRY_OPTIONS = [
    "AL - Albania", "AM - Armenia", "AT - Austria", "AZ - Azerbaijan",
    "BA - Bosnia/Herzeg.", "BG - Bulgaria", "HR - Croatia", "CZ - Czech Republic",
    "GE - Georgia", "HU - Hungary", "KZ - Kazakhstan", "KG - Kyrgyzstan",
    "MK - Macedonia", "MD - Moldavia", "ME - Montenegro", "PL - Poland",
    "RO - Romania", "RU - Russia", "RS - Serbia", "SK - Slovakia",
    "SI - Slovenia", "TJ - Tajikistan", "TM - Turkmenistan", "UA - Ukraine",
    "UZ - Uzbekistan", "DE - Germany", "LI - Liechtenstein", "CH - Switzerland",
    "BE - Belgium", "LU - Luxembourg", "NL - Netherlands", "FR - France",
    "PF - Frenc.Polynesia", "GP - Guadeloupe", "MQ - Martinique", "YT - Mayotte",
    "MC - Monaco", "NC - New Caledonia", "RE - Reunion", "IT - Italy",
    "SM - San Marino", "VA - Vatican City", "AF - Afghanistan", "DZ - Algeria",
    "BH - Bahrain", "BJ - Benin", "BF - Burkina Faso", "CM - Cameroon",
    "TD - Chad", "CD - Dem. Rep. Congo", "DJ - Djibouti", "EG - Egypt",
    "GA - Gabon", "GN - Guinea", "IQ - Iraq", "CI - Ivory coast", "KW - Kuwait",
    "ML - Mali", "MR - Mauretania", "MA - Morocco", "NE - Niger", "PK - Pakistan",
    "CG - Rep. of Congo", "SA - Saudi Arabia", "SN - Senegal", "TG - Togo",
    "TN - Tunisia", "AO - Angola", "BW - Botswana", "GB - Brit.Ind.Oc.Ter",
    "BI - Burundi", "CV - Cabo Verde", "GQ - Equatorial Guinea", "ER - Eritrea",
    "SZ - Eswatini", "ET - Ethiopia", "GM - Gambia", "GH - Ghana", "JO - Jordan",
    "KE - Kenya", "LB - Lebanon", "LS - Lesotho", "LR - Liberia", "LY - Libya",
    "MG - Madagascar", "MW - Malawi", "MU - Mauritius", "MZ - Mozambique",
    "NG - Nigeria", "OM - Oman", "PS - Palestine Reg.", "QA - Qatar", "RW - Rwanda",
    "ST - S.Tome,Principe", "SC - Seychelles", "SL - Sierra Leone",
    "ZA - South Africa", "SS - South Sudan", "SD - Sudan", "TZ - Tanzania",
    "UG - Uganda", "AE - Unit.Arab Emir.", "YE - Yemen", "ZM - Zambia",
    "ZW - Zimbabwe", "DK - Denmark", "EE - Estonia", "FO - Faroe Islands",
    "FI - Finland", "GL - Greenland", "IS - Iceland", "LV - Latvia",
    "LT - Lithuania", "NO - Norway", "SE - Sweden", "AD - Andorra", "CY - Cyprus",
    "GI - Gibraltar", "GR - Greece", "IL - Israel", "MT - Malta", "PT - Portugal",
    "ES - Spain", "TR - Turkey", "GG - Guernsey", "IE - Ireland", "IM - Isle of Man",
    "JE - Jersey", "AU - Australia", "CK - Cook Islands", "FJ - Fiji",
    "FM - Micronesia", "NZ - New Zealand", "PG - Pap. New Guinea",
    "SB - Solomon Islands", "TO - Tonga", "VU - Vanuatu", "CN - China",
    "HK - Hong Kong", "MO - Macao", "MN - Mongolia", "TW - Taiwan",
    "BD - Bangladesh", "IN - India", "LK - Sri Lanka", "JP - Japan",
    "KR - South Korea", "BT - Bhutan", "BN - Brunei Daruss.", "KH - Cambodia",
    "ID - Indonesia", "LA - Laos", "MY - Malaysia", "MV - Maldives", "MM - Myanmar",
    "NP - Nepal", "PH - Philippines", "SG - Singapore", "TH - Thailand",
    "TP - Timor-Leste", "VN - Vietnam", "VI - Amer.Virgin Is.", "AI - Anguilla",
    "AG - Antigua/Barbuda", "AR - Argentina", "AW - Aruba", "BS - Bahamas",
    "BB - Barbados", "BZ - Belize", "BM - Bermuda", "BO - Bolivia",
    "BQ - Bonaire, Saba", "BR - Brazil", "VG - Brit.Virgin Is.",
    "KY - Cayman Islands", "CL - Chile", "CO - Colombia", "CR - Costa Rica",
    "CW - Curaçao", "DM - Dominica", "DO - Dominican Rep.", "EC - Ecuador",
    "SV - El Salvador", "GD - Grenada", "GT - Guatemala", "GY - Guyana",
    "HT - Haiti", "HN - Honduras", "JM - Jamaica", "MX - Mexico", "NI - Nicaragua",
    "PA - Panama", "PY - Paraguay", "PE - Peru", "PR - Puerto Rico",
    "SX - Sint Maarten", "KN - St Kitts&Nevis", "LC - St. Lucia", "VC - St. Vincent",
    "SR - Suriname", "TT - Trinidad,Tobago", "TC - Turksh Caicosin", "UY - Uruguay",
    "VE - Venezuela", "CA - Canada", "GU - Guam", "US - United States",
]

# ─── Gender detector (module-level singleton) ─────────────────────────────────
_gender_detector = gender.Detector()


# ─── Text helpers ─────────────────────────────────────────────────────────────

def clean_text(text):
    """Normalize umlauts and strip non-alphanumeric characters."""
    if pd.isna(text):
        return ""
    text = str(text)
    umlaut_map = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
        'ß': 'ss'
    }
    for k, v in umlaut_map.items():
        text = text.replace(k, v)
    return re.sub(r'[^a-zA-Z0-9]', '', text)


def convert_country_to_code(country):
    """Convert full country name to ISO alpha-2 code. Returns original if not found."""
    country_codes = {c.name: c.alpha_2 for c in pycountry.countries}
    return country_codes.get(str(country).strip(), country)


# ─── Validation functions ─────────────────────────────────────────────────────

def is_private_email(email):
    """Return True if email belongs to a known private domain."""
    if pd.isna(email):
        return False
    domain = str(email).split("@")[-1].lower()
    return domain in PRIVATE_DOMAINS


def is_bad_email(row):
    """
    Return True if the email does not match the prospect's name via fuzzy match.
    Uses first name, last name, and initials.
    """
    first = str(row["First Name"]).lower()
    last = str(row["Last Name"]).lower()
    email = str(row["Email"]).lower()
    if not email or email.strip() == "" or email == "nan":
        return False
    threshold = 75
    return not (
        fuzz.partial_ratio(first, email) > threshold or
        fuzz.partial_ratio(last, email) > threshold or
        (first[0] + last[0]).lower() in email
    )


def domain_match_score(row):
    """
    Return fuzzy match score (0-100) between cleaned company name and email domain.
    Returns np.nan if either side is empty or email has no @.
    """
    company_name = str(row['Account Name']).lower()
    email = str(row['Email']).lower()

    if '@' not in email:
        return np.nan

    domain_core = email.split('@', 1)[1].split('.', 1)[0]

    for w in WORDS_TO_REMOVE:
        company_name = re.sub(r'\b' + re.escape(w) + r'\b', '', company_name)

    company_clean = clean_text(company_name)
    domain_clean = clean_text(domain_core)

    if not company_clean or not domain_clean:
        return np.nan

    return fuzz.partial_ratio(company_clean, domain_clean)


def format_domain_score(score):
    """Format a numeric domain score into a human-readable string."""
    if pd.isna(score):
        return ""
    score = int(score)
    if score == 0:
        return "0 - No Match"
    elif score <= 49:
        return f"{score} - Poor Match"
    else:
        return f"{score} - Good Match"


def detect_gender(name):
    """
    Detect gender from first name using gender_guesser.
    Handles hyphenated names by checking each part.
    Returns 'Male', 'Female', or 'Unknown'.
    """
    if not isinstance(name, str) or not name.strip():
        return "Unknown"
    name = name.strip()
    if "-" in name:
        for part in name.split("-"):
            g = _gender_detector.get_gender(part)
            if g in ("male", "mostly_male"):
                return "Male"
            elif g in ("female", "mostly_female"):
                return "Female"
        return "Unknown"
    g = _gender_detector.get_gender(name)
    if g in ("male", "mostly_male"):
        return "Male"
    elif g in ("female", "mostly_female"):
        return "Female"
    return "Unknown"


# ─── Validation pipeline ──────────────────────────────────────────────────────

def run_validation_checks(prospects, mask, include_bad_gender=True, include_bad_country=False):
    """
    Run all validation checks on rows selected by `mask`.
    Appends issues to the 'Issue' column using '+' separator.

    Parameters
    ----------
    prospects : pd.DataFrame  (modified in-place)
    mask      : boolean Series selecting rows to validate
    include_bad_gender  : if True, flags 'Bad Gender' for mismatches (Parts 2 & 4)
                          if False, only flags 'Unknown Gender' (Part 3)
    include_bad_country : if True, flags 'Bad Country' when Country != Account Country (Part 4)
    """

    # 1. Bad Email Format
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    bad_fmt = mask & prospects["Email"].notna() & (prospects["Email"].str.strip() != "") & \
              ~prospects["Email"].str.match(email_pattern, na=False)
    prospects.loc[bad_fmt, "Issue"] += "+Bad Email Format"

    # 2. Private Email
    private = mask & prospects["Email"].apply(is_private_email)
    prospects.loc[private, "Issue"] += "+Private Email"

    # 3. Bad Names
    prospects.loc[mask, "First Name"] = prospects.loc[mask, "First Name"].astype(str).str.title()
    prospects.loc[mask, "Last Name"] = prospects.loc[mask, "Last Name"].astype(str).str.title()
    bad_name = mask & (
        (prospects["First Name"].str.strip() == "") |
        (prospects["Last Name"].str.strip() == "")
    )
    prospects.loc[bad_name, "Issue"] += "+Bad Name"

    # 4. Bad Email (fuzzy name match)
    prospects.loc[mask, "Email"] = prospects.loc[mask, "Email"].astype(str).str.lower()
    bad_email_check = prospects.loc[mask].apply(is_bad_email, axis=1)
    prospects.loc[bad_email_check[bad_email_check].index, "Issue"] += "+Bad Email"

    # 5. Bad Domain
    valid_domain_mask = mask & prospects["Email"].notna() & \
                        prospects["Email"].astype(str).str.contains("@", na=False)
    prospects.loc[valid_domain_mask, "Domain Score Numeric"] = \
        prospects.loc[valid_domain_mask].apply(domain_match_score, axis=1)
    prospects["Domain Score"] = prospects["Domain Score Numeric"].apply(format_domain_score)
    company_mismatch = valid_domain_mask & \
                       prospects["Domain Score Numeric"].notna() & \
                       (prospects["Domain Score Numeric"] < 50)
    prospects.loc[company_mismatch, "Issue"] += "+Bad Domain"
    prospects.drop(columns=["Domain Score Numeric"], inplace=True, errors="ignore")

    # 6. Bad LinkedIn
    li_filled = mask & prospects["LinkedIn URL"].notna() & \
                (prospects["LinkedIn URL"].str.strip() != "")
    bad_li = li_filled & ~prospects["LinkedIn URL"].str.contains("linkedin", case=False, na=False)
    prospects.loc[bad_li, "Issue"] += "+Bad LinkedIn"

    # 7. Bad Country (Part 4 only)
    if include_bad_country and "Account Country" in prospects.columns:
        bad_country = mask & (prospects["Country"] != prospects["Account Country"])
        prospects.loc[bad_country, "Issue"] += "+Bad Country"

    # 8. Gender
    prospects.loc[mask, "Plausible Gender"] = \
        prospects.loc[mask, "First Name"].apply(detect_gender)

    if include_bad_gender:
        # Parts 2 & 4: normalize existing gender field, flag Bad Gender or Unknown Gender
        prospects.loc[mask, "Gender"] = (
            prospects.loc[mask, "Gender"]
            .astype(str).str.strip().str.lower()
            .replace("unknown", np.nan)
            .map({"male": "Male", "female": "Female"})
            .fillna("Unknown")
        )

        def _gender_issue(row):
            actual = row["Gender"]
            plausible = row["Plausible Gender"]
            if actual != plausible and plausible != "Unknown":
                return "Bad Gender"
            elif actual == "Unknown" and plausible == "Unknown":
                return "Unknown Gender"
            return None

        gender_issue = prospects.loc[mask].apply(_gender_issue, axis=1)
        idx_with_issue = gender_issue[gender_issue.notna()].index
        prospects.loc[idx_with_issue, "Issue"] = (
            prospects.loc[idx_with_issue, "Issue"]
            .astype(str).replace("nan", "").str.strip()
            + "+" + gender_issue[idx_with_issue]
        ).str.strip("+")
    else:
        # Part 3: just assign detected gender; flag Unknown Gender only
        prospects.loc[mask, "Gender"] = prospects.loc[mask, "Plausible Gender"]
        unknown_mask = mask & (prospects["Gender"] == "Unknown")
        prospects.loc[unknown_mask, "Issue"] = (
            prospects.loc[unknown_mask, "Issue"]
            .astype(str).replace("nan", "").str.strip("+")
            + "+Unknown Gender"
        ).str.strip("+")

    # 9. Duplicates (full dataset, not just mask)
    prospects["_full_name"] = (
        prospects["First Name"].str.strip().str.lower() + "_" +
        prospects["Last Name"].str.strip().str.lower()
    )
    reversed_name = (
        prospects["Last Name"].str.strip().str.lower() + "_" +
        prospects["First Name"].str.strip().str.lower()
    )
    dup_idx = prospects[
        prospects["_full_name"].duplicated(keep=False) |
        reversed_name.duplicated(keep=False)
    ].index
    prospects.loc[dup_idx, "Issue"] += "+Duplicate"
    prospects.drop(columns=["_full_name"], inplace=True)

    # 10. Clean Issue column
    prospects["Issue"] = (
        prospects["Issue"]
        .str.strip("+")
        .str.replace("++", "+", regex=False)
    )

    return prospects


# ─── Excel export helpers ─────────────────────────────────────────────────────

def write_issues_xlsx(filepath, prospects_df, cols):
    """
    Write the Prospect Issues xlsx with autofilter and auto-sized columns.

    Parameters
    ----------
    filepath     : output file path (str)
    prospects_df : DataFrame already sorted
    cols         : list of column names to include
    """
    existing_cols = [c for c in cols if c in prospects_df.columns]
    with pd.ExcelWriter(filepath, engine="xlsxwriter") as writer:
        prospects_df[existing_cols].to_excel(writer, sheet_name="Issues", index=False)
        ws = writer.sheets["Issues"]
        for i, col in enumerate(existing_cols):
            col_vals = prospects_df[col].fillna("").astype(str)
            length = max(col_vals.map(len).max(), len(col))
            ws.set_column(i, i, length)
        ws.autofilter(0, 0, len(prospects_df), len(existing_cols) - 1)


def write_deliverable_xlsx(
    filepath,
    prospects_df,
    accounts_wo_prospects_df,
    highlight_columns,
    autofit_columns,
):
    """
    Write the final Deliverable xlsx with:
    - 'Prospects' sheet (formatted, protected, with Issue Category dropdown)
    - 'Accounts without Prospects' sheet
    - 'Prospect Upload' template sheet with instructions and dropdowns
    - Hidden 'DropdownLists' sheet for country validation

    Parameters
    ----------
    filepath                  : output file path (str)
    prospects_df              : deliverable rows (already sorted, cleaned)
    accounts_wo_prospects_df  : accounts with zero prospects
    highlight_columns         : column names to get yellow header
    autofit_columns           : column names to auto-size
    """
    prospect_columns = ["Issue Category", "Comments"] + list(prospects_df.columns)

    with pd.ExcelWriter(filepath, engine="xlsxwriter") as writer:
        workbook = writer.book

        # ── Formats ──
        header_fmt = workbook.add_format({
            "bold": True, "align": "left", "valign": "vcenter", "bg_color": "yellow"
        })
        reg_header_fmt = workbook.add_format({
            "bold": True, "align": "left", "valign": "vcenter"
        })
        locked_fmt = workbook.add_format({"align": "left", "valign": "vcenter", "locked": True})
        unlocked_fmt = workbook.add_format({"align": "left", "valign": "vcenter", "locked": False})

        # ── Prospects sheet ──
        deliverable_with_meta = pd.DataFrame(columns=prospect_columns)
        for col in prospects_df.columns:
            deliverable_with_meta[col] = prospects_df[col].values

        deliverable_with_meta.to_excel(writer, sheet_name="Prospects", index=False)
        ws = writer.sheets["Prospects"]

        for col_num, col_name in enumerate(prospect_columns):
            fmt = header_fmt if col_name in highlight_columns else reg_header_fmt
            ws.write(0, col_num, col_name, fmt)

        for row_num, row in deliverable_with_meta.iterrows():
            for col_num, value in enumerate(row):
                col_name = deliverable_with_meta.columns[col_num]
                if pd.isna(value):
                    value = ""
                fmt = unlocked_fmt if col_name in ["Issue Category", "Comments", "Tags", "Gender"] else locked_fmt
                ws.write(row_num + 1, col_num, value, fmt)

        ws.set_column(0, 0, 30)
        ws.set_column(1, 1, 30)
        for i, col in enumerate(prospects_df.columns, start=2):
            if col in autofit_columns:
                max_len = max(prospects_df[col].fillna("").astype(str).map(len).max(), len(col)) + 2
                ws.set_column(i, i, max_len)
            else:
                ws.set_column(i, i, 10)

        ws.autofilter(0, 0, len(deliverable_with_meta), len(prospect_columns) - 1)

        error_types = [
            "Bad Name", "Bad Email", "Gender", "Duplicate", "Bad Domain",
            "No longer with the company", "Private Email", "Bad Country"
        ]
        ws.data_validation(1, 0, 1000, 0, {"validate": "list", "source": error_types})
        ws.protect("MEE@dac", {
            "select_locked_cells": True,
            "select_unlocked_cells": True,
            "autofilter": True
        })

        # ── Accounts without Prospects sheet ──
        accounts_wo_prospects_df.to_excel(
            writer, sheet_name="Accounts without Prospects", index=False
        )
        ws_acc = writer.sheets["Accounts without Prospects"]
        hdr_fmt = workbook.add_format({"bold": True, "align": "left", "valign": "vcenter"})
        dat_fmt = workbook.add_format({"align": "left", "valign": "vcenter"})
        for col_num, col_name in enumerate(accounts_wo_prospects_df.columns):
            ws_acc.write(0, col_num, col_name, hdr_fmt)
        for i, col in enumerate(accounts_wo_prospects_df.columns):
            max_len = max(
                accounts_wo_prospects_df[col].fillna("").astype(str).map(len).max(), len(col)
            ) + 2
            ws_acc.set_column(i, i, max_len, dat_fmt)
        ws_acc.autofilter(0, 0, len(accounts_wo_prospects_df), len(accounts_wo_prospects_df.columns) - 1)

        # ── Prospect Upload template sheet ──
        template_columns = [
            "Custom Id", "Account Name", "Tags", "First Name", "Last Name",
            "Title", "Gender", "Email", "LinkedIn URL", "Work Phone",
            "Mobile Phone", "Source", "Country"
        ]
        ws_tmpl = workbook.add_worksheet("Prospect Upload")

        instructions = [
            "Instructions:",
            "* If Custom Ids (=Account IDs) are not available (not in CRM), it is mandatory to provide the Account Name (for NNN accounts)",
            "* It is mandatory to provide the First Name, Last Name, Title, Gender (for salutations), Country (2-letter code), Source of the prospect",
            "* For contact details, it is mandatory to provide either Email ID or Work Phone/Mobile Phone (with +country code format)",
            "* Fill in Tags column with your Outreach Tag and you can provide multiple tags if needed (e.g., multiple SDE/AE names)"
        ]
        instr_fmt = workbook.add_format({"bold": True, "align": "left", "valign": "vcenter"})
        for idx, instr in enumerate(instructions):
            ws_tmpl.merge_range(idx, 0, idx, len(template_columns) - 1, instr, instr_fmt)

        tmpl_hdr_fmt = workbook.add_format({
            "bold": True, "align": "center", "valign": "vcenter",
            "bg_color": "black", "font_color": "white"
        })
        for col_num, col_name in enumerate(template_columns):
            ws_tmpl.write(6, col_num, col_name, tmpl_hdr_fmt)
            ws_tmpl.set_column(col_num, col_num, max(len(col_name) + 2, 18))
        ws_tmpl.autofilter(6, 0, 6, len(template_columns) - 1)

        gender_col = template_columns.index("Gender")
        ws_tmpl.data_validation(7, gender_col, 1000, gender_col, {
            "validate": "list", "source": ["Male", "Female"],
            "input_message": "Select Male or Female"
        })

        source_col = template_columns.index("Source")
        ws_tmpl.data_validation(7, source_col, 1000, source_col, {
            "validate": "list", "source": ["SDE Sourced", "AE Sourced"],
            "input_message": "Select Source"
        })

        # Country dropdown via hidden sheet
        dropdown_df = pd.DataFrame({"Countries": COUNTRY_OPTIONS})
        dropdown_df.to_excel(writer, sheet_name="DropdownLists", index=False)
        writer.sheets["DropdownLists"].hide()
        workbook.define_name("CountryList", f"='DropdownLists'!$A$2:$A${len(COUNTRY_OPTIONS) + 1}")

        country_col = template_columns.index("Country")
        ws_tmpl.data_validation(7, country_col, 1000, country_col, {
            "validate": "list", "source": "=CountryList",
            "input_message": "Select a country (e.g., DE - Germany)"
        })


# ─── Account/prospect counting helpers ───────────────────────────────────────

def is_valid_id(x):
    try:
        return int(x) > 0
    except:
        return False


def clean_id_and_name(df):
    df = df.copy()
    if "Custom Id" in df.columns:
        df["Custom Id"] = df["Custom Id"].apply(lambda x: int(x) if is_valid_id(x) else 0)
    df["Account Name"] = df["Account Name"].astype(str).str.strip()
    return df


def unique_account_count(df):
    df = clean_id_and_name(df)
    if "Custom Id" in df.columns and (df["Custom Id"] > 0).any():
        return df.loc[df["Custom Id"] > 0, "Custom Id"].nunique()
    return df["Account Name"].nunique()


def total_account_count(df):
    df = clean_id_and_name(df)
    return len(df)


def compute_stats(accounts_df, deliverable_df, threshold):
    """
    Compute and print enrichment statistics.
    Returns (accounts_wo_prospects, accounts_with_few, accounts_insufficient).
    """
    accounts_df = clean_id_and_name(accounts_df.copy())
    deliverable_df = clean_id_and_name(deliverable_df.copy())

    has_valid_ids = (
        "Custom Id" in deliverable_df.columns and
        (deliverable_df["Custom Id"] > 0).any()
    )

    if has_valid_ids:
        prospect_counts = deliverable_df.loc[
            deliverable_df["Custom Id"] > 0, "Custom Id"
        ].value_counts()
        accounts_df["Prospect Count"] = accounts_df["Custom Id"].map(prospect_counts).fillna(0).astype(int)
    else:
        prospect_counts = deliverable_df["Account Name"].value_counts()
        accounts_df["Prospect Count"] = accounts_df["Account Name"].map(prospect_counts).fillna(0).astype(int)

    accounts_wo = accounts_df[accounts_df["Prospect Count"] == 0].copy()
    accounts_few = accounts_df[
        (accounts_df["Prospect Count"] > 0) & (accounts_df["Prospect Count"] < threshold)
    ].copy()
    accounts_insufficient = pd.concat([accounts_wo, accounts_few], ignore_index=True)

    accounts_submitted = unique_account_count(accounts_df)
    prospects_found = len(deliverable_df)
    prospects_with_emails = (
        deliverable_df["Email"].dropna()
        .apply(lambda x: str(x).strip())
        .loc[lambda x: x != ""]
        .nunique()
        if "Email" in deliverable_df.columns else 0
    )
    prospects_with_linkedin = (
        deliverable_df["LinkedIn URL"].dropna()
        .apply(lambda x: str(x).strip())
        .loc[lambda x: x != ""]
        .nunique()
        if "LinkedIn URL" in deliverable_df.columns else 0
    )
    accounts_with_prospects = unique_account_count(deliverable_df)
    enrichment_rate = (
        (accounts_with_prospects / accounts_submitted * 100).__ceil__()
        if accounts_submitted else 0
    )

    import math
    enrichment_rate = math.ceil(
        (accounts_with_prospects / accounts_submitted) * 100
    ) if accounts_submitted else 0

    accounts_total = total_account_count(accounts_df)
    print(f"# Accounts Submitted: {accounts_total}")
    print(f"\n# Prospects Found (deliverable only): {prospects_found}")
    print(f"# Prospects with Emails: {prospects_with_emails}")
    print(f"# Prospects with LinkedIn URLs: {prospects_with_linkedin}")
    print(f"# Accounts with Prospects: {accounts_with_prospects}")
    print(f"\nEnrichment Rate: {enrichment_rate}%")
    print(f"\n# Accounts without Prospects: {total_account_count(accounts_wo)}")
    print(f"# Accounts with Fewer than {threshold} Prospects: {total_account_count(accounts_few)}")
    print(f"Total Accounts needing more prospects: {unique_account_count(accounts_insufficient)}")

    return accounts_wo, accounts_few, accounts_insufficient


# ─── Config-driven prospect pipeline engine ───────────────────────────────────

def run_prospect_pipeline(config, base_name, threshold, hide_email):
    """
    Execute the full prospect processing pipeline for Parts 2, 3, and 4.

    Parameters
    ----------
    config    : dict  — pipeline configuration (see plan for full schema)
    base_name : str   — file name prefix (e.g. "John_TAG")
    threshold : int   — prospects per account requested
    hide_email: bool  — whether to hide Email column in Deliverable
    """
    import os
    import math

    prefix = config["prospect_id_prefix"]
    source_label = config["source_label"]

    # ── Performance instrumentation ──
    _timer = Timer()

    # ── Load main input ──
    if config["reader"] == "csv":
        ext = "_ZI.csv" if prefix == "Z" else "_Outreach.csv"
        df = pd.read_csv(base_name + ext, sep=",", encoding="utf-8-sig")
    else:
        sheet = config.get("sheet") or 0
        df = pd.read_excel(base_name + ("_LG.xlsx" if prefix == "L" else ".xlsx"), sheet_name=sheet)

    # ── Load accounts ──
    accounts = pd.read_csv(
        base_name + "_Accounts.csv", sep=",", encoding="utf-8-sig"
    ).rename(columns={"Country": "Account Country", "Website": "Website URL"})

    _timer.checkpoint("Load (prospects + accounts)")

    print(len(accounts), " - # Rows in Accounts Data\n")
    print(len(df), " - # Rows in Prospects Data")

    # ── Filter verified (Part 4 only) ──
    if config.get("filter_verified") and "Contact Status" in df.columns:
        _before = len(df)
        df = df[df["Contact Status"] == "Verified"]
        print(f"  Verified filter: {_before} -> {len(df)} rows ({_before - len(df)} dropped)")
        print(len(df), " - # Rows after retaining Verified Prospects")

    _timer.checkpoint("Filter + dtypes")

    # ── Fix data types ──
    for _col in ["ZoomInfo Contact ID", "Person Zip Code", "ZoomInfo Company ID",
                 "Founded Year", "Employees", "SIC Code 1", "NAICS Code 1",
                 "Contact Zip code", "customId"]:
        if _col in df.columns:
            df[_col] = pd.to_numeric(df[_col], errors="coerce").fillna(0).astype(int)
    for _col in ["Direct Phone Number", "Mobile phone", "Website", "Company Phone",
                 "Contact State"]:
        if _col in df.columns:
            df[_col] = df[_col].astype(str)
    if "Custom Id" in accounts.columns:
        accounts["Custom Id"] = pd.to_numeric(accounts["Custom Id"], errors="coerce").fillna(0).astype(int)
    if "customId" in df.columns:
        df = df.rename(columns={"customId": "Custom Id"})
        df["Custom Id"] = pd.to_numeric(df["Custom Id"], errors="coerce").fillna(0).astype(int)

    # ── Rename columns ──
    df = df.rename(columns=config.get("rename_cols", {}))

    # ── Merge accounts ──
    _extra = ["Tags"] if "Tags" in accounts.columns else []
    strategy = config["merge_strategy"]

    if strategy == "custom_id":
        _acct_dedup = accounts.drop_duplicates(subset="Custom Id", keep="first")
        df = pd.merge(df, _acct_dedup[["Custom Id", "Account Name", "Account Country"] + _extra],
                      on="Custom Id", how="left")
    elif strategy == "zi_fallback":
        if "Custom Id" in df.columns:
            _acct_dedup = accounts.drop_duplicates(subset="Custom Id", keep="first")
            df = pd.merge(df, _acct_dedup[["Custom Id", "Account Name", "Account Country"] + _extra],
                          on="Custom Id", how="left")
        elif "Website URL" in df.columns:
            df = pd.merge(df, accounts[["Website URL", "Account Name", "Account Country"] + _extra],
                          on="Website URL", how="left")
        elif "Query Name" in df.columns:
            df = df.rename(columns={"Query Name": "Account Name"})
            _acct_dedup = accounts.drop_duplicates(subset="Account Name", keep="first")
            df = pd.merge(df, _acct_dedup[["Account Name", "Custom Id", "Account Country"] + _extra],
                          on="Account Name", how="left")
        else:
            print(f"[WARNING] Could not merge accounts: no 'Custom Id', 'Website URL', or 'Query Name' in file.")
            print(f"    Columns: {list(df.columns)}")
            raise SystemExit(1)
    elif strategy == "company_name":
        if "Company" in df.columns:
            _company_extra = ["Tags"] if "Tags" in accounts.columns else []
            df = pd.merge(
                df,
                accounts[["Custom Id", "Account Name", "Account Country"] + _company_extra],
                left_on="Company", right_on="Account Name", how="left"
            )
        else:
            df = df.rename(columns={"Country": "Account Country"})

    _timer.checkpoint("Merge accounts")

    # ── Drop unwanted columns ──
    columns_to_delete = config.get("columns_to_delete", [])
    df = df.drop(columns=[c for c in columns_to_delete if c in df.columns])

    # ── Reorder columns ──
    if "Gender" not in df.columns:
        df["Gender"] = ""
    desired = config.get("desired_columns", list(df.columns))
    df = df[[c for c in desired if c in df.columns]]

    # ── Assign Prospect IDs ──
    df = df.sort_values(by=["Account Name", "First Name", "Last Name"])
    df.reset_index(drop=True, inplace=True)
    df["Prospect ID"] = (df.index + 1).map(lambda x: f"{prefix}{x:04d}")
    df_sample = df.copy()

    # ── Filter same country (Part 3 only) ──
    if config.get("filter_same_country") and "Account Country" in df.columns and "Country" in df.columns:
        _before = len(df)
        df = df[df["Account Country"] == df["Country"]]
        print(f"  Same-country filter: {_before} -> {len(df)} rows ({_before - len(df)} dropped)")

    # ── Country code conversion ──
    if config.get("convert_country") and "Country" in df.columns:
        df["Country"] = df["Country"].apply(convert_country_to_code)
    if config.get("convert_account_country") and "Account Country" in df.columns:
        df["Account Country"] = df["Account Country"].apply(convert_country_to_code)

    # ── Phone formatting (Part 4 only) ──
    if config.get("format_phones"):
        import phonenumbers

        def _add_country_code(number, country):
            if pd.isnull(number) or pd.isnull(country):
                return number
            s = str(number).strip()
            if not s or s == "nan":
                return number
            if s.startswith("+"):
                return s
            cc = str(country).strip().upper()
            try:
                parsed = phonenumbers.parse("+" + s, None)
                if phonenumbers.is_valid_number(parsed):
                    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            except Exception:
                pass
            try:
                parsed = phonenumbers.parse(s, cc)
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            except Exception:
                return s

        if "Work Phone" in df.columns:
            df["Work Phone"] = df.apply(lambda r: _add_country_code(r["Work Phone"], r.get("Country")), axis=1)
        if "Mobile Phone" in df.columns:
            df["Mobile Phone"] = df.apply(lambda r: _add_country_code(r["Mobile Phone"], r.get("Country")), axis=1)

    # ── Fix Custom Id if missing (Part 4 edge case) ──
    if "Custom Id" not in df.columns or df["Custom Id"].isna().all():
        if "Account Name" in df.columns and "Custom Id" in accounts.columns:
            acct_map = accounts.drop_duplicates(subset="Account Name", keep="first").set_index("Account Name")["Custom Id"]
            df["Custom Id"] = df["Account Name"].map(acct_map).fillna(0).astype(int)

    _timer.checkpoint("Country conversion + phone format")

    # ── Set Source ──
    if "Source" in df.columns:
        df["Source"] = df["Source"].apply(
            lambda x: source_label if pd.isna(x) or str(x).strip() == "" else x
        )
    else:
        df["Source"] = source_label

    # ── Build combined prospects DataFrame ──
    cols = [
        "Custom Id", "Account Name", "Tags", "First Name", "Last Name", "Title",
        "Gender", "Email", "LinkedIn URL", "Work Phone", "Mobile Phone",
        "City", "State", "Zip", "Country", "Account Country", "Source", "Prospect ID",
    ]

    _optional_prefixes = {
        "_Outreach Prospects.xlsx": "O",
        "_ZI Prospects.xlsx": "Z",
        "_LG Prospects.xlsx": "L",
    }

    def _load_optional(filepath, file_prefix):
        if os.path.exists(filepath):
            d = pd.read_excel(filepath)
            if "Prospect ID" in d.columns and file_prefix:
                d = d[d["Prospect ID"].astype(str).str.startswith(file_prefix)]
            d = d[[c for c in cols if c in d.columns]]
            for c in cols:
                if c not in d.columns:
                    d[c] = ""
            return d
        print(f"File not found: {filepath}")
        return pd.DataFrame(columns=cols)

    optional_dfs = [
        _load_optional(base_name + p, _optional_prefixes.get(p, ""))
        for p in config.get("optional_inputs", [])
    ]
    main_df = df[[c for c in cols if c in df.columns]].copy()

    # Part 4: clear Mobile Phone (populated later from enrichment)
    if prefix == "L":
        main_df["Mobile Phone"] = ""

    dataframes = [d for d in optional_dfs + [main_df] if not d.empty and not d.isna().all().all()]
    prospects = pd.concat(dataframes, ignore_index=True)
    prospects["Issue"] = ""

    _timer.checkpoint("Concat sources + set source")

    # ── Validation ──
    mask = prospects["Prospect ID"].astype(str).str.startswith(prefix)
    prospects = run_validation_checks(
        prospects, mask,
        include_bad_gender=config["validation"]["include_bad_gender"],
        include_bad_country=config["validation"]["include_bad_country"],
    )

    # ── Threshold check ──
    prospects["# Prospects/Account Range"] = (
        prospects.groupby("Account Name").cumcount().add(1)
        .where(
            prospects.groupby("Account Name")["Account Name"].transform("count") <= threshold,
            prospects.groupby("Account Name").cumcount().add(1).apply(lambda x: f"Extra {x}")
        )
        .mask(
            prospects.groupby("Account Name")["Account Name"].transform("count") <= threshold,
            "OK"
        )
    )
    extra_accounts = prospects[
        prospects["# Prospects/Account Range"].str.contains("Extra")
    ]["Account Name"].nunique()
    print(f"\nAccounts with more than {threshold} prospects: {extra_accounts}")

    # ── Issue summary ──
    issues_only = prospects[prospects["Issue"].str.strip() != ""]
    print(f"\nTotal records with issues: {issues_only.shape[0]}\n")
    print(issues_only["Issue"].str.split("+").explode().value_counts())

    # ── Export Issues ──
    issue_cols = config.get("issue_cols", [])
    sort_cols = [c for c in ["Tags", "Account Name", "First Name", "Last Name", "Issue"] if c in prospects.columns]
    prospects = prospects.sort_values(by=sort_cols, ascending=[True] * len(sort_cols))
    issues_file = base_name + "_Prospect Issues.xlsx"
    write_issues_xlsx(issues_file, prospects, issue_cols)
    print(f"\nFile saved as {issues_file}")

    # ── Manual fix pause ──
    input("\n[WARNING] PLEASE FIX THE PROSPECTS ISSUES FILE BEFORE PROCEEDING.\nPress Enter when done...")

    # ── Re-import fixed prospects ──
    edited = pd.read_excel(issues_file, sheet_name="Issues")
    edited["Prospect ID"] = edited["Prospect ID"].astype(str)

    df = edited.copy().reset_index(drop=True)
    prospects = edited.copy().reset_index(drop=True)

    # ── Re-enrich from original sample ──
    df_sample = df_sample.sort_values(by=["Account Name", "First Name", "Last Name"]).reset_index(drop=True)
    # df_sample["Prospect ID"] = (df_sample.index + 1).map(lambda x: f"{prefix}{x:04d}")

    protected_cols = [
        "Issue", "# Prospects/Account Range", "Custom Id", "Account Name",
        "First Name", "Last Name", "Title", "Gender", "Email", "Domain Score",
        "LinkedIn URL", "Company LinkedIn", "Work Phone", "Mobile Phone",
        "City", "State", "Zip", "Country", "Tags", "Prospect ID",
    ]

    df_enriched = df.merge(
        df_sample.drop_duplicates(subset="Prospect ID"),
        on="Prospect ID", how="left", suffixes=("", "_ref")
    )
    for col in df_sample.columns:
        if col not in protected_cols and col != "Prospect ID":
            ref_col = col + "_ref"
            if ref_col in df_enriched.columns:
                df_enriched[col] = df_enriched[col].fillna(df_enriched[ref_col])
                df_enriched.drop(columns=[ref_col], inplace=True)
    df_enriched = df_enriched[[c for c in df_enriched.columns if not c.endswith("_ref")]]
    df = df_enriched.reset_index(drop=True)

    # ── Deliverable ──
    if "Tags" in prospects.columns:
        _has_tags = (
            prospects["Tags"].notna() &
            (prospects["Tags"].astype(str).str.strip() != "") &
            (prospects["Tags"].astype(str).str.lower() != "nan")
        )
        # Include rows from optional inputs (no Tags yet) alongside rows with valid Tags
        _tag_mask = _has_tags
        deliverable = prospects[_tag_mask].copy().reset_index(drop=True)
    else:
        deliverable = prospects.copy().reset_index(drop=True)
    deliverable = clean_id_and_name(deliverable)

    accounts_wo, accounts_few, accounts_insufficient = compute_stats(accounts, prospects, threshold)

    # Part 3: merge Source from df onto deliverable
    if config.get("source_from_zi") and "Source" in df.columns:
        deliverable = deliverable.merge(
            df[["Prospect ID", "Source"]].rename(columns={"Source": "_zi_source"}),
            on="Prospect ID", how="left"
        )
        deliverable["Source"] = deliverable["_zi_source"].fillna(source_label)
        deliverable.drop(columns=["_zi_source"], inplace=True)

    # ── Export: main prospects xlsx ──
    df_export = df.drop(config.get("drop_from_prospects_export", []), axis=1, errors="ignore")
    df_export = df_export.replace("nan", "").replace(np.nan, "")
    _sort_export = [c for c in ["Tags", "Account Name", "First Name", "Last Name", "Source"] if c in df_export.columns]
    df_export = df_export.sort_values(by=_sort_export, ascending=[True] * len(_sort_export))
    prospects_out = base_name + config["prospects_output"]
    df_export.to_excel(prospects_out, sheet_name="Prospects", index=False)
    print(f"File saved as {prospects_out}")

    # ── Export: Emails CSV ──
    prospects["Email"].to_csv(
        base_name + "_Emails.csv", index=False, header=["Email"], encoding="utf-8-sig"
    )
    print(f"File saved as {base_name}_Emails.csv\n")

    # ── Export: Accounts with Insufficient Prospects CSV ──
    _sort_insuff = [c for c in ["Tags", "Account Name"] if c in accounts_insufficient.columns]
    accounts_insufficient = accounts_insufficient.sort_values(by=_sort_insuff, ascending=[True] * len(_sort_insuff)).reset_index(drop=True)
    accounts_insufficient.to_csv(
        base_name + "_Accounts with Insufficient Prospects.csv",
        index=False, sep=",", encoding="utf-8-sig"
    )
    print(f"File saved as {base_name}_Accounts with Insufficient Prospects.csv")

    # ── Export: Deliverable xlsx ──
    deliverable = deliverable.drop(
        ["Issue", "Plausible Gender", "# Prospects/Account Range"], axis=1, errors="ignore"
    )
    deliverable = deliverable.replace("nan", "").replace(np.nan, "")
    _sort_deliv = [c for c in ["Tags", "Account Name", "First Name", "Last Name", "Source"] if c in deliverable.columns]
    deliverable = deliverable.sort_values(by=_sort_deliv, ascending=[True] * len(_sort_deliv))

    base_keep = ["Custom Id", "Account Name", "Tags", "First Name", "Last Name", "Title", "Gender"]
    if not hide_email:
        base_keep.append("Email")
    base_keep.extend(config.get("deliverable_extra_cols", []))
    base_keep.extend(["LinkedIn URL", "Work Phone", "Mobile Phone", "Source",
                       "City", "State", "Zip", "Country", "Prospect ID"])
    deliverable = deliverable[[c for c in base_keep if c in deliverable.columns]]

    highlight_columns = ["Account Name", "Title"]
    if "Custom Id" in deliverable.columns and (deliverable["Custom Id"] != 0).any():
        highlight_columns.append("Custom Id")
    if "Tags" in deliverable.columns and deliverable["Tags"].nunique() > 1:
        highlight_columns.append("Tags")

    autofit_columns = ["Custom Id", "Account Name", "Tags", "Title", "Work Phone", "Mobile Phone"]
    if not hide_email:
        autofit_columns.append("Email")

    write_deliverable_xlsx(
        base_name + "_Deliverable.xlsx",
        deliverable,
        accounts_wo,
        highlight_columns,
        autofit_columns,
    )
    print(f"File saved as {base_name}_Deliverable.xlsx")
