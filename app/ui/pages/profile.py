import asyncio

import streamlit as st

from app.core.database import get_db
from app.repositories.candidate import CandidateRepository
from app.schemas.candidate import (
    CandidateExperienceCreate,
    CandidateProfileUpdate,
    CandidateProjectCreate,
)
from app.services.resume.parser import ResumeParserService


def render_candidate_profile():
    st.title("👤 Candidate Profile")
    st.markdown("Your candidate profile serves as the **single source of truth** for matching and personalized outreach generation.")

    with get_db() as db:
        repo = CandidateRepository(db)
        profile = repo.get_or_create_default()

        # ------------------------------------------------------------------
        # Resume PDF Upload Section
        # ------------------------------------------------------------------
        with st.expander("📄 Auto-Fill Profile from Resume (PDF Upload)", expanded=True):
            st.markdown(
                "Upload your existing resume in **PDF** format. "
                "PyMuPDF extracts the content and the LLM structures your skills, work history, projects, and titles automatically."
            )
            uploaded_pdf = st.file_uploader("Upload Resume PDF", type=["pdf"], key="resume_pdf_uploader")
            if uploaded_pdf is not None:
                if st.button("🚀 Parse & Populate Profile", type="primary"):
                    with st.spinner("Extracting text via PyMuPDF and structuring profile with LLM..."):
                        try:
                            pdf_bytes = uploaded_pdf.read()
                            parsed = asyncio.run(ResumeParserService.parse_and_update_profile(pdf_bytes, db))
                            st.success(f"🎉 Successfully parsed resume for **{parsed.full_name}**! Profile has been updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to parse resume: {e}")

        st.divider()

        with st.form("profile_form"):
            st.subheader("Personal Information")
            name = st.text_input("Full Name", value=profile.full_name)
            email = st.text_input("Email", value=profile.email)
            location = st.text_input("Location", value=profile.location)
            summary = st.text_area("Professional Summary", value=profile.professional_summary or "", height=100)

            st.subheader("Technical Skills & Roles")
            skills_raw = st.text_input(
                "Technical Skills (comma-separated)",
                value=", ".join(profile.technical_skills or []),
            )
            titles_raw = st.text_input(
                "Preferred Job Titles (comma-separated)",
                value=", ".join(profile.preferred_job_titles or []),
            )

            st.subheader("Preferences & Links")
            remote_pref = st.text_input("Remote Work Preferences", value=profile.remote_work_preferences)
            github = st.text_input("GitHub URL", value=profile.github_url or "")
            linkedin = st.text_input("LinkedIn URL", value=profile.linkedin_url or "")
            portfolio = st.text_input("Portfolio URL", value=profile.portfolio_url or "")

            submitted = st.form_submit_button("Save Profile")
            if submitted:
                skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
                titles_list = [t.strip() for t in titles_raw.split(",") if t.strip()]
                repo.update_profile(
                    profile.id,
                    CandidateProfileUpdate(
                        full_name=name,
                        email=email,
                        location=location,
                        professional_summary=summary,
                        technical_skills=skills_list,
                        preferred_job_titles=titles_list,
                        remote_work_preferences=remote_pref,
                        github_url=github,
                        linkedin_url=linkedin,
                        portfolio_url=portfolio,
                    ),
                )
                st.success("Candidate Profile successfully updated!")
                st.rerun()

        st.divider()
        st.subheader("💼 Work Experience")
        for exp in profile.experiences:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{exp.title}** at **{exp.company}** ({exp.start_date or ''} - {exp.end_date or 'Present'})")
                st.write(exp.description or "")
                if exp.technologies:
                    st.caption(f"Tech: {', '.join(exp.technologies)}")
            with col2:
                if st.button("Delete", key=f"del_exp_{exp.id}"):
                    repo.delete_experience(exp.id)
                    st.rerun()

        with st.expander("➕ Add Work Experience"), st.form("add_exp_form"):
            exp_title = st.text_input("Job Title")
            exp_comp = st.text_input("Company Name")
            exp_dates = st.text_input("Dates (e.g. 2022 - Present)")
            exp_desc = st.text_area("Responsibilities & Achievements")
            exp_tech = st.text_input("Technologies (comma-separated)")
            if st.form_submit_button("Add Experience"):
                if exp_title and exp_comp:
                    techs = [t.strip() for t in exp_tech.split(",") if t.strip()]
                    repo.add_experience(
                        profile.id,
                        CandidateExperienceCreate(
                            title=exp_title,
                            company=exp_comp,
                            start_date=exp_dates,
                            description=exp_desc,
                            technologies=techs,
                        ),
                    )
                    st.success("Experience added!")
                    st.rerun()

        st.divider()
        st.subheader("🚀 Featured Projects")
        for proj in profile.projects:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{proj.name}** - [Link]({proj.url or proj.github_url or '#'})")
                st.write(proj.description or "")
                if proj.technologies:
                    st.caption(f"Tech: {', '.join(proj.technologies)}")
            with col2:
                if st.button("Delete", key=f"del_proj_{proj.id}"):
                    repo.delete_project(proj.id)
                    st.rerun()

        with st.expander("➕ Add Featured Project"), st.form("add_proj_form"):
            proj_name = st.text_input("Project Name")
            proj_desc = st.text_area("Project Description")
            proj_url = st.text_input("Project / Demo URL")
            proj_github = st.text_input("GitHub URL")
            proj_tech = st.text_input("Technologies (comma-separated)")
            if st.form_submit_button("Add Project"):
                if proj_name:
                    techs = [t.strip() for t in proj_tech.split(",") if t.strip()]
                    repo.add_project(
                        profile.id,
                        CandidateProjectCreate(
                            name=proj_name,
                            description=proj_desc,
                            url=proj_url,
                            github_url=proj_github,
                            technologies=techs,
                        ),
                    )
                    st.success("Project added!")
                    st.rerun()
