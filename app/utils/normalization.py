import re


def normalize_string(val: str | None) -> str:
    if not val:
        return ""
    # Lowercase, strip punctuation and collapse whitespace
    val = val.lower().strip()
    val = re.sub(r"[^\w\s]", "", val)
    return re.sub(r"\s+", " ", val)


def normalize_company_name(name: str) -> str:
    s = normalize_string(name)
    # Remove common suffixes
    suffixes = [" inc", " llc", " ltd", " corp", " corporation", " co", " gmbh", " pvt ltd", " technologies", " tech"]
    for suf in suffixes:
        if s.endswith(suf):
            s = s[:-len(suf)].strip()
    return s


def normalize_job_title(title: str) -> str:
    s = normalize_string(title)
    # Standardize common engineering patterns
    s = re.sub(r"\b(sr|sr\.)\b", "senior", s)
    s = re.sub(r"\b(jr|jr\.)\b", "junior", s)
    s = re.sub(r"\b(sw|swe)\b", "software engineer", s)
    return s
