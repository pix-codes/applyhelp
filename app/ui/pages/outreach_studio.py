import asyncio
import uuid

import streamlit as st

from app.core.database import get_db
from app.repositories.candidate import CandidateRepository
from app.repositories.company import CompanyRepository
from app.repositories.outreach import OutreachRepository
from app.schemas.outreach import OutreachMessageCreate, OutreachMessageUpdate
from app.services.gmail.client import GmailClient
from app.services.gmail.eml_export import export_as_eml
from app.services.outreach.generator import OutreachGenerator
from app.services.outreach.templates import TEMPLATES
from app.services.research.service import CompanyResearchService


def render_outreach_studio():
    st.title("✍️ Outreach Studio")
    st.markdown("Ground personalized cold outreach in verified candidate experience and company facts.")

    with get_db() as db:
        cand_repo = CandidateRepository(db)
        comp_repo = CompanyRepository(db)
        outreach_repo = OutreachRepository(db)

        profile = cand_repo.get_or_create_default()
        companies = comp_repo.list_companies(limit=100)

        if not companies:
            st.warning("No companies found yet. Please run discovery first.")
            return

        # Select Company & Job
        comp_names = {c.name: c.id for c in companies}
        default_comp_name = list(comp_names.keys())[0]

        # Check session state for pre-selection
        preselected_cid = st.session_state.get("selected_company_id")
        if preselected_cid:
            for name, cid in comp_names.items():
                if str(cid) == preselected_cid:
                    default_comp_name = name
                    break

        selected_comp_name = st.selectbox("Select Target Company", list(comp_names.keys()), index=list(comp_names.keys()).index(default_comp_name))
        company_id = comp_names[selected_comp_name]
        company = comp_repo.get_by_id(company_id)

        # Company Research Section
        col_r1, col_r2 = st.columns([3, 1])
        with col_r1:
            st.subheader(f"🏢 {company.name}")
            comp_url_val = st.text_input(
                "Company Official Website URL",
                value=company.website_url or f"https://{company.name.lower().replace(' ', '')}.com",
                key=f"comp_url_input_{company.id}",
                help="Website analyzed for engineering challenges, product focus, and tech stack",
            )
            if comp_url_val != company.website_url:
                company.website_url = comp_url_val
                db.commit()

            if company.research:
                st.markdown(f"**Product:** {company.research.product_summary}")
                st.markdown(f"**Engineering Focus:** {company.research.engineering_challenges}")
                if company.research.engineering_stack:
                    st.caption(f"Known Stack: {', '.join(company.research.engineering_stack)}")
            else:
                st.warning("⚠️ No research collected yet for this company. Click **'🔍 Research Company'** to analyze their website and generate grounded talking points.")

        with col_r2:
            st.write("")
            st.write("")
            if st.button("🔍 Research Company", type="primary", key=f"res_btn_{company.id}"):
                with st.spinner("Analyzing public company website and tech stack..."):
                    research_svc = CompanyResearchService(db)
                    res = asyncio.run(research_svc.research_company(company.id))
                    if res:
                        st.success("Company research completed!")
                        st.rerun()
                    else:
                        st.error("Could not fetch company website. Check the URL and try again.")

        st.divider()

        # Outreach Generation Form
        template_name = st.selectbox("Outreach Template", list(TEMPLATES.keys()))
        st.caption(TEMPLATES[template_name]["description"])

        # Optional Job association
        jobs_for_comp = [j for j in company.jobs]
        job_options = {"None (General Cold Outreach)": None}
        for j in jobs_for_comp:
            job_options[j.title] = j

        selected_job_title = st.selectbox("Associate with Open Vacancy", list(job_options.keys()))
        selected_job = job_options[selected_job_title]

        # Reset or update recipient email when company or contact changes
        company_changed = st.session_state.get("_last_selected_company_id") != str(company.id)
        if company_changed:
            st.session_state["_last_selected_company_id"] = str(company.id)
            # Find first available contact email for this company if any
            first_contact_with_email = next((c for c in company.contacts if c.email), None)
            if first_contact_with_email:
                st.session_state["draft_recipient_email"] = first_contact_with_email.email
            else:
                st.session_state["draft_recipient_email"] = ""

        # Optional Target Recipient / Contact
        contacts_for_comp = [c for c in company.contacts]
        contact_options = {"None (General Hiring / Engineering Team)": None}
        default_contact_idx = 0
        for idx_c, c in enumerate(contacts_for_comp):
            contact_label = f"{c.name} ({c.role})" if c.role else c.name
            if c.email:
                contact_label += f" - {c.email}"
            contact_options[contact_label] = c
            # Pre-select first contact with an email
            if c.email and default_contact_idx == 0:
                default_contact_idx = idx_c + 1

        selected_contact_label = st.selectbox(
            "Target Recipient / Contact (Optional)",
            list(contact_options.keys()),
            index=default_contact_idx,
            key=f"contact_select_{company.id}",
        )
        selected_contact = contact_options[selected_contact_label]

        # If a specific contact was selected from dropdown, update recipient email
        if selected_contact and selected_contact.email:
            st.session_state["draft_recipient_email"] = selected_contact.email

        # Recipient email input (auto-populated from company/contact, with manual override)
        recipient_email_input = st.text_input(
            "Recipient 'To' Email Address",
            value=st.session_state.get("draft_recipient_email", ""),
            placeholder="e.g. founder@company.com or engineering@company.com",
            help="Automatically populated from company contacts if available. This email address will be placed in the 'To' field of your Gmail draft or exported .EML file.",
            key=f"draft_to_email_input_{company.id}"
        )
        st.session_state["draft_recipient_email"] = recipient_email_input

        if st.button("🪄 Generate Personalized Email Draft", type="primary"):
            with st.spinner("Generating draft and conducting cross-model anti-slop review..."):
                gen = OutreachGenerator(db)
                result = asyncio.run(gen.generate_email(
                    candidate=profile,
                    company=company,
                    template_type=template_name,
                    job=selected_job,
                    contact=selected_contact,
                ))
                st.session_state["draft_subject"] = result.subject
                st.session_state["draft_body"] = result.body
                st.session_state["talking_points"] = result.talking_points
                st.session_state["draft_reviewed_by"] = result.reviewed_by
                if result.reviewed_by and not result.reviewed_by.startswith("Unreviewed"):
                    st.success(f"Draft generated and polished by reviewer: {result.reviewed_by} to eliminate AI slop!")
                elif result.reviewed_by and result.reviewed_by.startswith("Unreviewed"):
                    st.warning(f"Draft generated, but reviewer cross-check could not complete: {result.reviewed_by}")
                else:
                    st.success("Draft generated successfully! (Tip: configure a second LLM provider in Settings for automatic cross-model anti-slop review)")

        # Review & Edit Draft
        if "draft_subject" in st.session_state:
            st.subheader("📝 Review & Edit Outreach Email")
            rev_info = st.session_state.get("draft_reviewed_by")
            if rev_info:
                if rev_info.startswith("Unreviewed"):
                    st.warning(f"⚠️ **Anti-Slop Protection**: {rev_info}")
                else:
                    st.caption(f"🛡️ **Anti-Slop Protection**: Reviewed and vetted by `{rev_info}`")

            for tp in st.session_state.get("talking_points", []):
                st.info(f"💡 Grounded talking point: {tp}")

            final_recipient = st.text_input(
                "To (Recipient Email)",
                value=st.session_state.get("draft_recipient_email", ""),
                placeholder="recipient@example.com",
                key="final_to_email",
            )
            edited_subject = st.text_input("Subject Line", value=st.session_state["draft_subject"])
            edited_body = st.text_area("Email Body", value=st.session_state["draft_body"], height=250)

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                if st.button("💾 Save to Outreach Pipeline"):
                    msg = outreach_repo.create(OutreachMessageCreate(
                        company_id=company.id,
                        job_id=selected_job.id if selected_job else None,
                        contact_id=selected_contact.id if selected_contact else None,
                        template_type=template_name,
                        subject=edited_subject,
                        body=edited_body,
                        status="Draft Generated",
                    ))
                    st.session_state["current_saved_msg_id"] = str(msg.id)
                    st.success(f"Saved to pipeline with ID: {msg.id}")

            with col_b:
                gmail = GmailClient(db)
                if gmail.is_connected():
                    if st.button("📮 Save as Gmail Draft"):
                        try:
                            draft_id = asyncio.run(gmail.create_draft(
                                subject=edited_subject,
                                body=edited_body,
                                to_email=final_recipient.strip() if final_recipient.strip() else None,
                            ))
                            # update message if saved
                            saved_id = st.session_state.get("current_saved_msg_id")
                            if saved_id:
                                outreach_repo.update(uuid.UUID(saved_id), OutreachMessageUpdate(
                                    status="Draft Saved",
                                    gmail_draft_id=draft_id
                                ))
                            st.success(f"Draft saved in your Gmail account! (ID: {draft_id})")
                        except Exception as e:
                            st.error(f"Gmail draft error: {e}")
                else:
                    st.button("📮 Save as Gmail Draft", disabled=True, help="Connect Gmail in Settings to enable direct draft creation")

            with col_c:
                eml_bytes = export_as_eml(
                    subject=edited_subject,
                    body=edited_body,
                    from_email=profile.email,
                    to_email=final_recipient.strip() if final_recipient.strip() else None,
                )
                st.download_button(
                    label="📥 Export as .EML File",
                    data=eml_bytes,
                    file_name="outreach_draft.eml",
                    mime="message/rfc822",
                )
