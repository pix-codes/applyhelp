

import re

# ISO country names and common abbreviations that indicate country restrictions
EUROPE_COUNTRIES = {
    "france", "germany", "italy", "portugal", "spain", "uk", "united kingdom",
    "netherlands", "poland", "sweden", "switzerland", "ireland", "denmark",
    "norway", "finland", "austria", "belgium", "czech republic", "estonia",
    "romania", "hungary", "bulgaria", "croatia", "greece", "slovakia"
}
AMERICAS_COUNTRIES = {
    "usa", "united states", "us", "canada", "brazil", "mexico", "argentina",
    "colombia", "chile", "latam", "latin america"
}


def classify_geographic_eligibility(location_raw: str, description_raw: str = "") -> tuple[str, bool, str]:
    """
    Classifies geographic eligibility into:
    - 'Worldwide'
    - 'Country-specific'
    - 'Region-specific'
    - 'Nepal-eligible'
    - 'Excluded'
    - 'Unknown'

    Returns:
    (eligibility_category, is_nepal_eligible, explanation)
    """
    loc_clean = (location_raw or "").strip().lower()
    desc_clean = (description_raw or "").strip().lower()
    combined = f"{loc_clean} {desc_clean}"

    # 1. Explicit Exclusions
    if "no nepal" in combined or "nepal excluded" in combined:
        return "Excluded", False, "Explicitly excludes candidates from Nepal"

    if "us only" in combined or "usa only" in combined or "only us candidates" in combined:
        return "Country-specific", False, "Restricted to United States"

    # 2. Check location_restrictions field for explicit countries / lists of countries
    loc_parts = [p.strip().strip(",") for p in re.split(r"[,/|;]", loc_clean) if p.strip()]

    # If location lists specific European or Americas countries, it is NOT worldwide
    has_euro_country = any(c in EUROPE_COUNTRIES for c in loc_parts) or any(c in loc_clean for c in ["europe only", "eu only", "emea only", "uk only"])
    has_americas_country = any(c in AMERICAS_COUNTRIES for c in loc_parts) or any(c in loc_clean for c in ["north america only", "us/canada"])

    if has_euro_country and "nepal" not in loc_clean and "worldwide" not in loc_clean and "anywhere" not in loc_clean:
        return "Region-specific", False, f"Restricted to specific European countries ({location_raw})"

    if has_americas_country and "nepal" not in loc_clean and "worldwide" not in loc_clean and "anywhere" not in loc_clean:
        return "Region-specific", False, f"Restricted to North/South America ({location_raw})"

    # 3. Explicit Nepal eligibility
    if "nepal" in loc_clean or "nepal" in desc_clean:
        return "Nepal-eligible", True, "Explicitly mentions Nepal eligibility"

    # 4. Explicit Worldwide Remote (check location field first, then strict phrases in description)
    # Be careful: only treat as worldwide if the location field itself says worldwide/anywhere,
    # or if the description specifically says "hire anywhere in the world" or "work from anywhere in the world"
    if loc_clean in ["worldwide", "anywhere", "global", "remote worldwide", "remote (worldwide)"]:
        return "Worldwide", True, "Explicitly advertised as Worldwide / Global remote"

    if "anywhere in the world" in desc_clean or "worldwide remote" in desc_clean or "work from anywhere in the world" in desc_clean:
        return "Worldwide", True, "Explicitly advertised as Worldwide / Global remote in description"

    # 5. Asia / APAC timezone
    if "apac" in loc_clean or "south asia" in loc_clean or "asia" in loc_clean:
        return "Region-specific", True, "Region-specific including Asia/APAC timezone"

    # 6. Default: Unknown (Never assume unknown is worldwide!)
    return "Unknown", False, "Eligibility not explicitly declared; requires manual verification"
