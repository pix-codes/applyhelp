from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.discovery.sheets import (
    ColumnMapping,
    GoogleSheetsService,
    convert_google_sheets_url_to_csv_export,
)
from app.services.llm.base import LLMResponse


def test_convert_google_sheets_urls():
    # Sharing edit link
    url1 = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?usp=sharing"
    assert convert_google_sheets_url_to_csv_export(url1) == "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/export?format=csv&gid=0"

    # Tab with specific gid
    url2 = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=98765"
    assert convert_google_sheets_url_to_csv_export(url2) == "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/export?format=csv&gid=98765"

    # Published sheet
    url3 = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRe123/pubhtml"
    assert convert_google_sheets_url_to_csv_export(url3) == "https://docs.google.com/spreadsheets/d/e/2PACX-1vRe123/pub?output=csv"


@pytest.mark.asyncio
async def test_google_sheets_ai_ingestion():
    mock_db = MagicMock()
    mock_job_repo = MagicMock()
    mock_company_repo = MagicMock()

    csv_data = (
        "Job Name,Employer,Location,Link,Lead Person,Lead Email\n"
        "Staff Python Engineer,Acme Global,Worldwide,https://acme.com/apply,Sarah Lee,sarah@acme.com\n"
        "Lead Backend Architect,Beta Tech,Remote - Nepal,https://beta.com/jobs,John Doe,john@beta.com\n"
    )

    mapping = ColumnMapping(
        data_type="jobs",
        title_column="Job Name",
        company_column="Employer",
        location_column="Location",
        url_column="Link",
        contact_name_column="Lead Person",
        contact_email_column="Lead Email",
    )

    with patch("app.services.discovery.sheets.GoogleSheetsService.fetch_csv_content", AsyncMock(return_value=csv_data)), \
         patch("app.services.discovery.sheets.GoogleSheetsService.infer_column_mapping", AsyncMock(return_value=mapping)), \
         patch("app.services.discovery.sheets.JobRepository", return_value=mock_job_repo), \
         patch("app.services.discovery.sheets.CompanyRepository", return_value=mock_company_repo):

        mock_company = MagicMock()
        mock_company.id = "mock-company-id"
        mock_company.contacts = []
        mock_company_repo.get_or_create.return_value = mock_company

        svc = GoogleSheetsService(mock_db)
        res = await svc.import_from_sheet("https://docs.google.com/spreadsheets/d/test/edit")

        assert res.total_rows == 2
        assert res.jobs_imported == 2
        assert res.contacts_imported == 2
        assert mock_job_repo.create_or_update.call_count == 2
        assert mock_company_repo.add_contact.call_count == 2


@pytest.mark.asyncio
async def test_google_sheets_banner_header_skipping():
    mock_db = MagicMock()
    mock_job_repo = MagicMock()
    mock_company_repo = MagicMock()

    # Row 1 is a promotional banner across cell A1
    csv_data = (
        '"Looking for remote startup roles? Use textbackdoor.com →",,,,\n'
        "Job Title,Company,Location,URL\n"
        "Fullstack Engineer,Startup Inc,Remote Worldwide,https://startup.io/apply\n"
    )

    mapping = ColumnMapping(
        data_type="jobs",
        title_column="Job Title",
        company_column="Company",
        location_column="Location",
        url_column="URL",
    )

    with patch("app.services.discovery.sheets.GoogleSheetsService.fetch_csv_content", AsyncMock(return_value=csv_data)), \
         patch("app.services.discovery.sheets.GoogleSheetsService.infer_column_mapping", AsyncMock(return_value=mapping)), \
         patch("app.services.discovery.sheets.JobRepository", return_value=mock_job_repo), \
         patch("app.services.discovery.sheets.CompanyRepository", return_value=mock_company_repo):

        mock_company = MagicMock()
        mock_company.id = "mock-company-id"
        mock_company_repo.get_or_create.return_value = mock_company

        svc = GoogleSheetsService(mock_db)
        res = await svc.import_from_sheet("https://docs.google.com/spreadsheets/d/test/edit")

        assert res.total_rows == 1
        assert res.jobs_imported == 1
        assert "Job Title" in res.headers_detected
        assert "Looking for remote startup roles?" not in res.headers_detected[0]
