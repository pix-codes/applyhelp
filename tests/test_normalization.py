from app.utils.normalization import normalize_company_name, normalize_job_title


def test_normalize_company_name():
    assert normalize_company_name("Acme, Inc.") == "acme"
    assert normalize_company_name("Vercel LLC") == "vercel"
    assert normalize_company_name("GitHub") == "github"


def test_normalize_job_title():
    assert "senior software engineer" in normalize_job_title("Sr. Software Engineer")
    assert "software engineer" in normalize_job_title("Backend SWE")
