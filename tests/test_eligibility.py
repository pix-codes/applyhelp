from app.services.discovery.eligibility import classify_geographic_eligibility


def test_classify_nepal_eligible():
    cat, is_nepal, _ = classify_geographic_eligibility("Worldwide", "We hire developers worldwide")
    assert cat == "Worldwide"
    assert is_nepal is True

    cat, is_nepal, _ = classify_geographic_eligibility("Remote", "Candidates in Nepal or South Asia welcome")
    assert is_nepal is True


def test_classify_restricted():
    cat, is_nepal, _ = classify_geographic_eligibility("USA Only", "Must reside in United States")
    assert cat == "Country-specific"
    assert is_nepal is False


def test_classify_unknown():
    cat, is_nepal, _ = classify_geographic_eligibility("", "")
    assert cat == "Unknown"
    assert is_nepal is False
