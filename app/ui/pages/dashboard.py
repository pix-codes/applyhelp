import streamlit as st
from sqlalchemy import func

from app.core.database import get_db
from app.models import Company, Job, LLMUsage, OutreachMessage


def render_dashboard():
    st.title("🎯 Job Discovery & Outreach Assistant")
    st.markdown("Track companies, remote engineering vacancies, Nepal eligibility, and personalized outreach.")

    with get_db() as db:
        comp_count = db.query(func.count(Company.id)).scalar() or 0
        job_count = db.query(func.count(Job.id)).scalar() or 0
        nepal_count = db.query(func.count(Job.id)).filter(Job.nepal_eligible.is_(True)).scalar() or 0
        outreach_count = db.query(func.count(OutreachMessage.id)).scalar() or 0
        tokens_count = db.query(func.sum(LLMUsage.total_tokens)).scalar() or 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Companies", comp_count)
    col2.metric("Discovered Jobs", job_count)
    col3.metric("🇳🇵 Nepal Eligible", nepal_count)
    col4.metric("Outreach Messages", outreach_count)
    col5.metric("LLM Tokens Used", f"{tokens_count:,}")

    st.divider()

    st.subheader("⚡ Quick Discovery Actions")
    st.info("Head over to the **Company & Job Discovery** tab to run respectful crawlers across Remotive and Arbeitnow feeds.")

    st.subheader("📬 Outreach Pipeline Highlights")
    with get_db() as db:
        recent_outreach = (
            db.query(OutreachMessage)
            .order_by(OutreachMessage.updated_at.desc())
            .limit(5)
            .all()
        )
        if not recent_outreach:
            st.write("No outreach messages created yet. Browse jobs and start in the **Outreach Studio**.")
        else:
            for o in recent_outreach:
                with st.expander(f"{o.subject} - Status: {o.status}"):
                    st.write(o.body)
                    st.caption(f"Last updated: {o.updated_at.strftime('%Y-%m-%d %H:%M')}")
