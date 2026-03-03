# utils.py — Shared pipeline utilities
# Extracted from parts 2, 3, 4 to eliminate duplicated helper code.

import re
import numpy as np
import pandas as pd
import pycountry
import gender_guesser.detector as gender
from fuzzywuzzy import fuzz

# ─── Constants ────────────────────────────────────────────────────────────────

PRIVATE_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.de", "hotmail.com", "aol.com",
    "outlook.com", "icloud.com", "mail.com", "live.com", "t-online.de",
    "web.de", "gmx.de", "info.com"
}

WORDS_TO_REMOVE = {
    "inc", "llc", "ltd", "corporation", "corp", "company", "co", "and",
    "gmbh", "ag", "kg", "ohg", "gbr", "ug", "se", "holding", "group",
    "sa", "sarl", "srl", "doo", "kft", "rt", "ab", "as", "oy",
    "the", "der", "die", "das", "von", "zu", "im", "am", "an",
}

# ─── Gender detector (singleton) ─────────────────────────────────────────────
_gender_detector = gender.Detector()

# ─── Text helpers ─────────────────────────────────────────────────────────────

def clean_text(text):
    """Normalize umlauts and strip non-alphanumeric characters."""
    if pd.isna(text): return ""
    text = str(text)
    for k, v in {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}.items():
        text = text.replace(k, v)
    return re.sub(r"[^a-zA-Z0-9]", "", text)

def convert_country_to_code(country):
    """Convert full country name to ISO alpha-2 code. Returns original if not found."""
    codes = {c.name: c.alpha_2 for c in pycountry.countries}
    return codes.get(str(country).strip(), country)

def detect_gender(name):
    """Detect gender from first name using gender_guesser. Handles hyphenated names."""
    if not isinstance(name, str) or not name.strip(): return "Unknown"
    name = name.strip()
    if "-" in name:
        for part in name.split("-"):
            g = _gender_detector.get_gender(part)
            if g in ("male", "mostly_male"): return "Male"
            if g in ("female", "mostly_female"): return "Female"
        return "Unknown"
    g = _gender_detector.get_gender(name)
    if g in ("male", "mostly_male"): return "Male"
    if g in ("female", "mostly_female"): return "Female"
    return "Unknown"

# ─── Validation helpers ───────────────────────────────────────────────────────

def is_private_email(email):
    """Return True if email belongs to a known private (consumer) domain."""
    if pd.isna(email): return False
    return str(email).split("@")[-1].lower() in PRIVATE_DOMAINS

def is_bad_email(row):
    """Return True if email does not match prospect's name via fuzzy match."""
    first = str(row["First Name"]).lower()
    last = str(row["Last Name"]).lower()
    email = str(row["Email"]).lower()
    if not email or email == "nan": return False
    return not (
        fuzz.partial_ratio(first, email) > 75 or
        fuzz.partial_ratio(last, email) > 75 or
        (first[0] + last[0]).lower() in email
    )

def domain_match_score(row):
    """Return fuzzy match score (0-100) between company name and email domain."""
    company = str(row["Account Name"]).lower()
    email = str(row["Email"]).lower()
    if "@" not in email: return np.nan
    domain_core = email.split("@", 1)[1].split(".", 1)[0]
    for w in WORDS_TO_REMOVE:
        company = re.sub(r"\b" + re.escape(w) + r"\b", "", company)
    company_clean = clean_text(company)
    domain_clean = clean_text(domain_core)
    if not company_clean or not domain_clean: return np.nan
    return fuzz.partial_ratio(company_clean, domain_clean)

def fuzzy_match_company(name, accounts_df):
    """Fuzzy-match a company name against accounts, return Custom Id or None."""
    if not isinstance(name, str): return None
    best_score, best_id = 0, None
    for _, row in accounts_df.iterrows():
        score = fuzz.partial_ratio(clean_text(name), clean_text(str(row["Account Name"])))
        if score > best_score:
            best_score, best_id = score, row["Custom Id"]
    return best_id if best_score >= 70 else None

def format_phone(phone_str, country_code="DE"):
    """Format phone number to E.164 using phonenumbers library."""
    try:
        import phonenumbers
        if pd.isna(phone_str) or str(phone_str).strip() == "": return ""
        parsed = phonenumbers.parse(str(phone_str), country_code)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass
    return str(phone_str) if not pd.isna(phone_str) else ""
