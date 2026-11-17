import csv
import io
import json
import logging
import re
from typing import Any, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import Company, CompanyContact
from app.repositories.company import CompanyRepository
from app.repositories.job import JobRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.company import CompanyContactCreate, CompanyCreate
from app.schemas.job import JobCreate
from app.services.discovery.eligibility import classify_geographic_eligibility
from app.services.llm.factory import LLMFactory, record_llm_usage
from app.services.llm.prompts import get_prompt

logger = logging.getLogger(__name__)


def convert_google_sheets_url_to_csv_export(url: str) -> str:
    """
    Transforms any standard public Google Sheets URL into its direct CSV export download URL.
    Examples handled:
    - https://docs.google.com/spreadsheets/d/{spreadsheetId}/edit?usp=sharing
    - https://docs.google.com/spreadsheets/d/{spreadsheetId}/edit#gid=123456
    - https://docs.google.com/spreadsheets/d/e/2PACX-.../pubhtml
    - https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?output=csv
    """
    url = url.strip()

    # If it's already an export link or pub csv link
    if "output=csv" in url:
        return url

    # Published sheet: .../pubhtml -> .../pub?output=csv
    if "/pubhtml" in url:
        return url.replace("/pubhtml", "/pub?output=csv")

    # Standard doc link: /spreadsheets/d/{KEY}/...
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if match:
        sheet_id = match.group(1)
        # Check for gid (sheet tab)
        gid = "0"
        parsed = urlparse(url)
        # gid might be in query or fragment
        query_params = parse_qs(parsed.query)
        if "gid" in query_params:
            gid = query_params["gid"][0]
        elif parsed.fragment and "gid=" in parsed.fragment:
            fragment_params = parse_qs(parsed.fragment)
            if "gid" in fragment_params:
                gid = fragment_params["gid"][0]

        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    return url


class ColumnMapping(BaseModel):
    data_type: str = Field(
        description="Either 'jobs' (table primarily represents job openings) or 'leads' (table primarily represents companies/leads/contacts)"
    )
    # Job-related fields
    title_column: Optional[str] = Field(default=None, description="Header name for Job Title / Position / Role")
    company_column: Optional[str] = Field(default=None, description="Header name for Company / Organization / Employer")
    url_column: Optional[str] = Field(default=None, description="Header name for Application URL, Posting Link, or Website")
    location_column: Optional[str] = Field(default=None, description="Header name for Location / Remote status / Country / Region")
    description_column: Optional[str] = Field(default=None, description="Header name for Job Description / Notes / Requirements")
    salary_column: Optional[str] = Field(default=None, description="Header name for Salary / Compensation / Range")

    # Lead/Contact-related fields
    contact_name_column: Optional[str] = Field(default=None, description="Header name for Contact Person / Founder / Recruiter Name")
    contact_email_column: Optional[str] = Field(default=None, description="Header name for Contact Email / Recruiter Email")
    contact_role_column: Optional[str] = Field(default=None, description="Header name for Contact Role / Title")
    company_website_column: Optional[str] = Field(default=None, description="Header name for Company Website / Domain")


class GoogleSheetsIngestionResult(BaseModel):
    total_rows: int = 0
    jobs_imported: int = 0
    contacts_imported: int = 0
    detected_type: str = "jobs"
    headers_detected: List[str] = Field(default_factory=list)
    mapping_used: dict = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)


class GoogleSheetsService:
    def __init__(self, db: Session):
        self.db = db
        self.job_repo = JobRepository(db)
        self.company_repo = CompanyRepository(db)

    async def fetch_csv_content(self, sheet_url: str) -> str:
        """Downloads the public sheet as CSV text with redirection support."""
        export_url = convert_google_sheets_url_to_csv_export(sheet_url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(export_url, headers=headers)
            if resp.status_code != 200:
                raise ValueError(
                    f"Failed to fetch Google Sheet CSV (HTTP {resp.status_code}). "
                    f"Ensure the Google Sheet is set to 'Anyone with the link can view'."
                )
            # Check if Google returned an HTML login page instead of CSV
            text = resp.text
            if "<html" in text.lower() and "sign in - google accounts" in text.lower():
                raise ValueError(
                    "Google Sheet requires sign-in. Please change sharing permissions to 'Anyone with the link can view'."
                )
            return text

    async def infer_column_mapping(self, headers: List[str], sample_rows: List[dict]) -> ColumnMapping:
        """Uses LLM to dynamically determine headers for jobs, companies, URLs, contacts, etc."""
        repo = SettingsRepository(self.db)
        system_prompt = get_prompt("sheets_column_mapper_system", repo=repo)

        user_prompt = (
            f"HEADERS FOUND IN SPREADSHEET:\n{json.dumps(headers, indent=2)}\n\n"
            f"SAMPLE ROWS (Up to 3):\n{json.dumps(sample_rows[:3], indent=2)}\n\n"
            "Analyze the headers and data samples. Return the exact matching header string for each field, or null if absent."
        )

        llm = LLMFactory.create_provider(db=self.db)
        mapping, raw_resp = await llm.generate_structured(
            prompt=user_prompt,
            schema=ColumnMapping,
            system_prompt=system_prompt,
        )
        record_llm_usage(self.db, raw_resp, purpose="sheets_column_mapping")
        return mapping

    async def import_from_sheet(self, sheet_url: str, custom_mapping: Optional[ColumnMapping] = None) -> GoogleSheetsIngestionResult:
        """Main method to read, analyze, and ingest jobs or company leads from a Google Sheet."""
        csv_text = await self.fetch_csv_content(sheet_url)
        raw_reader = list(csv.reader(io.StringIO(csv_text.strip())))
        if not raw_reader:
            raise ValueError("Spreadsheet appears to be empty.")

        # Detect the real header row by inspecting first 10 rows:
        # A title/banner row usually has 1-2 non-empty columns, whereas a real data table header has >= 3 columns
        header_idx = 0
        for i, row in enumerate(raw_reader[:10]):
            non_empty_cells = [c.strip() for c in row if c and c.strip()]
            if len(non_empty_cells) >= 3:
                header_idx = i
                break
            elif len(non_empty_cells) > 0 and i == 0 and len(raw_reader) > 1:
                # Check if next row has more columns
                next_non_empty = [c.strip() for c in raw_reader[i+1] if c and c.strip()]
                if len(next_non_empty) > len(non_empty_cells):
                    continue

        headers = [c.strip() for c in raw_reader[header_idx] if c and c.strip()]
        # If headers contain empty strings or duplicates, normalize them
        full_header_row = raw_reader[header_idx]
        cleaned_headers = []
        for col_idx, col in enumerate(full_header_row):
            col_name = col.strip()
            if not col_name:
                col_name = f"Column_{col_idx+1}"
            cleaned_headers.append(col_name)

        # Parse data rows starting after header_idx
        rows = []
        for r in raw_reader[header_idx + 1:]:
            row_dict = {}
            for col_idx, col_name in enumerate(cleaned_headers):
                val = r[col_idx].strip() if col_idx < len(r) else ""
                row_dict[col_name] = val
            if any(row_dict.values()):
                rows.append(row_dict)

        if not rows:
            raise ValueError("No data rows found in the sheet.")

        # Infer mapping using LLM if not supplied
        mapping = custom_mapping
        if not mapping:
            mapping = await self.infer_column_mapping(cleaned_headers, rows[:3])

        logs: List[str] = [
            f"📥 Downloaded spreadsheet successfully ({len(rows)} data rows).",
            f"📋 Headers identified on row {header_idx + 1}: {', '.join(headers)}",
            f"🤖 AI classified data type as '{mapping.data_type}' with column mappings:",
            f"   • Company: '{mapping.company_column or 'None'}'",
            f"   • Job Title: '{mapping.title_column or 'None'}'",
            f"   • URL / Link: '{mapping.url_column or 'None'}'",
            f"   • Location: '{mapping.location_column or 'None'}'",
            f"   • Description: '{mapping.description_column or 'None'}'",
            f"   • Contact Name: '{mapping.contact_name_column or 'None'}'",
            f"   • Contact Email: '{mapping.contact_email_column or 'None'}'",
            f"   • Website: '{mapping.company_website_column or 'None'}'",
        ]

        result = GoogleSheetsIngestionResult(
            total_rows=len(rows),
            detected_type=mapping.data_type,
            headers_detected=headers,
            mapping_used=mapping.model_dump(),
            logs=logs,
        )

        for idx, row in enumerate(rows):
            row_num = idx + 2
            # Extract common values based on dynamic mapping
            company_name = (row.get(mapping.company_column or "") or "").strip()
            if not company_name and mapping.company_website_column:
                # Infer company from domain if name column missing
                web = row.get(mapping.company_website_column or "").strip()
                company_name = urlparse(web).netloc.replace("www.", "")

            if not company_name:
                company_name = "Discovered Company"

            # 1. Ingest Job if job title exists or data_type is jobs
            title = (row.get(mapping.title_column or "") or "").strip()
            job_url = (row.get(mapping.url_column or "") or "").strip()
            location = (row.get(mapping.location_column or "") or "Remote").strip()
            description = (row.get(mapping.description_column or "") or "").strip()
            salary = (row.get(mapping.salary_column or "") or "").strip()

            if title:
                canonical_url = job_url or f"{sheet_url}#row={row_num}"
                elig, is_nepal, _ = classify_geographic_eligibility(location, description[:500])

                job_create = JobCreate(
                    title=title[:250],
                    canonical_url=canonical_url[:1000],
                    application_url=job_url[:1000] if job_url else None,
                    company_name=company_name[:250],
                    employment_type="Full-time",
                    location_restrictions=location[:250],
                    geographic_eligibility=elig,
                    nepal_eligible=is_nepal,
                    salary_range=salary[:100] if salary else None,
                    description=description[:4000] if description else f"Imported from Google Sheet ({company_name})",
                    skills=[],
                    status="Active",
                )
                self.job_repo.create_or_update(job_create)
                result.jobs_imported += 1
                result.logs.append(
                    f"Row {row_num}: Added job '{title}' at {company_name} "
                    f"(Location: {location}, Nepal-eligible: {'✅ Yes' if is_nepal else '❌ No'})"
                )

            # 2. Ingest Company Contact if contact info exists
            contact_name = (row.get(mapping.contact_name_column or "") or "").strip()
            contact_email = (row.get(mapping.contact_email_column or "") or "").strip()
            contact_role = (row.get(mapping.contact_role_column or "") or "").strip()
            website = (row.get(mapping.company_website_column or "") or "").strip()

            if contact_name or contact_email or website:
                # Find or ensure company exists
                company_record = self.company_repo.get_or_create(
                    CompanyCreate(
                        name=company_name,
                        website_url=website if website else None,
                        source_name="google_sheets",
                    )
                )
                if website and not company_record.website_url:
                    company_record.website_url = website
                    self.db.commit()

                if contact_name or contact_email:
                    # Avoid duplicate contact with exact email
                    existing_emails = {c.email.lower() for c in company_record.contacts if c.email}
                    if not contact_email or contact_email.lower() not in existing_emails:
                        self.company_repo.add_contact(
                            CompanyContactCreate(
                                name=contact_name if contact_name else "Hiring Lead",
                                email=contact_email if contact_email else None,
                                role=contact_role if contact_role else "Team Member",
                                is_verified=bool(contact_email),
                            ),
                            company_id=company_record.id,
                        )
                        result.contacts_imported += 1
                        result.logs.append(
                            f"Row {row_num}: Added contact '{contact_name or 'Hiring Lead'}' "
                            f"({contact_role or 'Team Member'}) for {company_name}"
                            + (f" <{contact_email}>" if contact_email else "")
                        )
                    else:
                        result.logs.append(
                            f"Row {row_num}: Contact <{contact_email}> already exists for {company_name}, skipped duplicate."
                        )

        result.logs.append(
            f"🎉 Ingestion finished: {result.jobs_imported} jobs and {result.contacts_imported} contacts stored successfully."
        )
        return result
