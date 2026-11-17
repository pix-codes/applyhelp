import asyncio

import streamlit as st

from app.core.database import get_db
from app.repositories.candidate import CandidateRepository
from app.repositories.job import JobRepository
from app.services.discovery.service import DiscoveryService
from app.services.matching.matcher import JobMatcher
from app.utils.async_runner import run_async


def render_discovery():
    st.title("🌐 Company & Job Discovery")
    st.markdown("Search remote job feeds (Remotive, Arbeitnow) with rate-limiting, deduplication, and Nepal eligibility checks.")

    col1, col2 = st.columns([3, 1])
    with col1:
        source = st.selectbox(
            "Discovery Source",
            [
                "All Sources",
                "Remotive",
                "Jobicy",
                "RemoteOK",
                "RealWorkFromAnywhere",
                "WeWorkRemotely",
                "NoDesk",
                "HackerNews",
                "Arbeitnow",
            ],
            help="Select all or a specific remote/startup job source",
        )
    with col2:
        limit = st.number_input("Max Vacancies per Source", min_value=5, max_value=50, value=15)

    if st.button("🚀 Run Discovery", type="primary"):
        with st.spinner("Fetching and categorizing vacancies..."):
            with get_db() as db:
                service = DiscoveryService(db)
                src_name = None if source == "All Sources" else source
                count = run_async(service.run_discovery(source_name=src_name, limit_per_source=limit))
                st.success(f"Discovery completed! Processed and stored {count} vacancies.")
                st.rerun()

    st.divider()
    st.subheader("📋 Discovered Vacancies")

    # Ingestion Tabs: Google Sheets & File Upload
    tab_import_sheets, tab_import_file = st.tabs(["📊 Import from Google Sheets (Public URL)", "📁 Import from JSON / CSV / Manual"])

    with tab_import_sheets:
        st.markdown(
            "Paste the link to any public Google Sheet (e.g. curated remote jobs lists, company directories, hiring spreadsheets). "
            "Our AI dynamically inspects the headers and sample rows to automatically map jobs, companies, locations, URLs, and hiring contacts."
        )
        sheet_url_input = st.text_input(
            "Public Google Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/.../edit?usp=sharing",
            key="gsheet_url_input",
            help="Ensure the sheet's sharing settings are set to 'Anyone with the link can view'."
        )

        col_gs1, col_gs2 = st.columns([2, 1])
        with col_gs1:
            if st.button("🪄 Read Sheet & Import with AI", type="primary", key="btn_import_gsheet"):
                if not sheet_url_input.strip():
                    st.warning("Please provide a Google Sheets URL.")
                else:
                    with st.spinner("Fetching Google Sheet and mapping columns with AI..."):
                        from app.services.discovery.sheets import GoogleSheetsService
                        with get_db() as db_sheets:
                            try:
                                sheets_svc = GoogleSheetsService(db_sheets)
                                res = run_async(sheets_svc.import_from_sheet(sheet_url_input.strip()))
                                st.session_state["last_sheets_import_result"] = res.model_dump()
                                st.success(
                                    f"✅ Ingestion complete! Scanned {res.total_rows} rows. "
                                    f"Imported {res.jobs_imported} job vacancies and {res.contacts_imported} company contacts."
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to ingest Google Sheet: {e}")

        # Display persistent logs if an import was recently completed
        last_import = st.session_state.get("last_sheets_import_result")
        if last_import:
            st.markdown("#### 📜 Ingestion Activity Logs")
            with st.expander(f"Detailed logs for {last_import.get('total_rows', 0)} rows processed", expanded=True):
                col_m1, col_m2 = st.columns([1, 1])
                with col_m1:
                    st.markdown("**AI Column Mapping Detected:**")
                    st.json(last_import.get("mapping_used", {}))
                with col_m2:
                    st.markdown("**Ingestion Summary:**")
                    st.write(f"• **Data Type:** `{last_import.get('detected_type')}`")
                    st.write(f"• **Total Rows:** `{last_import.get('total_rows')}`")
                    st.write(f"• **Jobs Stored:** `{last_import.get('jobs_imported')}`")
                    st.write(f"• **Contacts Stored:** `{last_import.get('contacts_imported')}`")

                st.markdown("**Step-by-Step Row Processing Logs:**")
                log_text = "\n".join(last_import.get("logs", []))
                st.code(log_text, language="markdown")

    with tab_import_file:
        st.markdown(
            "If you exported jobs or have a JSON list (e.g. from HiringCafe or custom searches), "
            "upload the file or paste the JSON below to add them to your discovery pipeline."
        )
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            uploaded_file = st.file_uploader("Upload JSON or CSV file", type=["json", "csv"], key="import_jobs_file")
        with col_up2:
            pasted_json = st.text_area("Or paste raw JSON list of jobs:", height=100, placeholder='[{"title": "Backend Engineer", "company": "Acme", "url": "https://..."}]')

        if st.button("📥 Import & Score Vacancies"):
            items_to_import = []
            if uploaded_file is not None:
                try:
                    import json
                    if uploaded_file.name.endswith(".json"):
                        content = json.loads(uploaded_file.read().decode("utf-8"))
                        if isinstance(content, list):
                            items_to_import.extend(content)
                        elif isinstance(content, dict):
                            # In case it has a 'results' or 'jobs' key
                            for k in ["results", "jobs", "data", "items"]:
                                if k in content and isinstance(content[k], list):
                                    items_to_import.extend(content[k])
                                    break
                except Exception as e:
                    st.error(f"Error reading uploaded file: {e}")

            elif pasted_json.strip():
                try:
                    import json
                    parsed = json.loads(pasted_json.strip())
                    if isinstance(parsed, list):
                        items_to_import.extend(parsed)
                    elif isinstance(parsed, dict):
                        for k in ["results", "jobs", "data", "items"]:
                            if k in parsed and isinstance(parsed[k], list):
                                items_to_import.extend(parsed[k])
                                break
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")

            if items_to_import:
                from app.schemas.job import JobCreate
                from app.services.discovery.eligibility import classify_geographic_eligibility
                with get_db() as db_import:
                    import_job_repo = JobRepository(db_import)
                    imported_count = 0
                    for raw in items_to_import:
                        if not isinstance(raw, dict):
                            continue
                        title = raw.get("title") or raw.get("jobTitle") or raw.get("position") or "Software Engineer"
                        company = raw.get("company") or raw.get("companyName") or raw.get("company_name") or "Tech Company"
                        url = raw.get("url") or raw.get("apply_url") or raw.get("link") or f"https://imported-job.local/{imported_count}"
                        loc = raw.get("location") or raw.get("formatted_address") or "Remote"
                        desc = raw.get("description") or raw.get("snippet") or ""

                        elig, is_nepal, _ = classify_geographic_eligibility(str(loc), str(desc)[:500])
                        job_create = JobCreate(
                            title=str(title)[:250],
                            canonical_url=str(url),
                            application_url=str(url),
                            company_name=str(company)[:250],
                            employment_type="Full-time",
                            location_restrictions=str(loc)[:250],
                            geographic_eligibility=elig,
                            nepal_eligible=is_nepal,
                            description=str(desc)[:4000],
                            skills=[],
                            status="Active",
                        )
                        import_job_repo.create_or_update(job_create)
                        imported_count += 1
                    st.success(f"🎉 Successfully imported and matched {imported_count} vacancies into your pipeline!")
                    st.rerun()
            else:
                st.warning("Please upload a file or paste valid JSON first.")

    st.divider()

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        min_match_score = st.slider(
            "🎯 Minimum Match Score (%)",
            min_value=0,
            max_value=100,
            value=60,
            step=5,
            help="Filter jobs matching at or above this percentage against your Candidate Profile",
        )
    with filter_col2:
        date_filter = st.selectbox(
            "📅 Date Discovered",
            ["All Active", "Past 24 Hours", "Past 7 Days", "Past 30 Days"],
            index=0,
            help="Filter by discovery recency",
        )
    with filter_col3:
        nepal_only = st.checkbox("🇳🇵 Show Nepal Eligible Only", value=False)

    with get_db() as db:
        job_repo = JobRepository(db)
        cand_repo = CandidateRepository(db)
        cand_profile = cand_repo.get_or_create_default()

        jobs = job_repo.list_jobs(nepal_only=nepal_only, limit=200)

        # Date recency filtering
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if date_filter == "Past 24 Hours":
            jobs = [j for j in jobs if (now - j.date_discovered) <= timedelta(days=1)]
        elif date_filter == "Past 7 Days":
            jobs = [j for j in jobs if (now - j.date_discovered) <= timedelta(days=7)]
        elif date_filter == "Past 30 Days":
            jobs = [j for j in jobs if (now - j.date_discovered) <= timedelta(days=30)]

        # Compute match scores on the fly for any newly ingested vacancies
        for job in jobs:
            if job.match_score is None:
                score, reasons = JobMatcher.calculate_match(cand_profile, job)
                job_repo.update_match_score(job.id, score, reasons)
                job.match_score = score
                job.match_reasons = reasons

        # Filter by minimum match score
        filtered_jobs = [j for j in jobs if (j.match_score or 0.0) >= min_match_score]
        # Sort descending by date discovered and match score
        filtered_jobs.sort(key=lambda x: (x.date_discovered, x.match_score or 0.0), reverse=True)

        st.caption(f"Showing **{len(filtered_jobs)}** vacancies with match score ≥ **{min_match_score}%**")

        if not filtered_jobs:
            st.info(f"No vacancies found with match score ≥ {min_match_score}%. Try lowering the slider or adding more skills/titles in your Candidate Profile.")
        else:
            for job in filtered_jobs:
                flag = "🇳🇵 Nepal Eligible" if job.nepal_eligible else f"🌍 {job.geographic_eligibility}"
                with st.expander(f"**{job.title}** @ {job.company.name} — Match: **{job.match_score}%** ({flag})"):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**Location Restrictions:** {job.location_restrictions}")
                        st.markdown(f"**Application Link:** [{job.application_url}]({job.application_url})")
                        if job.skills:
                            st.markdown(f"**Skills:** {', '.join([s.skill_name for s in job.skills])}")
                        st.markdown("**Match Reasons:**")
                        for r in (job.match_reasons or []):
                            st.write(f"- {r}")
                    with col_b:
                        st.markdown(f"**Status:** `{job.status}`")
                        if st.button("Draft Outreach", key=f"outreach_btn_{job.id}"):
                            st.session_state["selected_job_id"] = str(job.id)
                            st.session_state["selected_company_id"] = str(job.company.id)
                            st.success("Selected for Outreach! Navigate to 'Outreach Studio' tab.")

                    with st.expander("View Full Job Description"):
                        st.write(job.description or "No description provided.")
