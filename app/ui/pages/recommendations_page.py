import json
import streamlit as st

from app.services.recommendation_service import get_recommendations


def render_recommendations():
    """Streamlit page for AI‑powered skill and CV recommendations.
    Users paste a candidate profile JSON and job‑market data JSON.
    Personal identifiers are redacted before the LLM call.
    """
    st.set_page_config(page_title="Candidate Recommendations", layout="wide")

    st.title("🤖 AI‑Powered Skill & CV Recommendations")

    st.subheader("Candidate Profile (JSON)")
    profile_json = st.text_area("Paste candidate profile JSON", height=200)

    st.subheader("Job Market Data (JSON)")
    market_json = st.text_area("Paste job market data JSON", height=200)

    if st.button("Generate Recommendations"):
        try:
            profile = json.loads(profile_json)
            market = json.loads(market_json)
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
            st.stop()
        with st.spinner("Contacting AI model…"):
            try:
                result = get_recommendations(profile, market)
            except Exception as exc:
                st.error(f"Error generating recommendations: {exc}")
                st.stop()
        st.subheader("Suggested Skills to Learn")
        st.markdown(result.get("skills", ""))
        st.subheader("CV Enhancement")
        st.markdown(result.get("cv", ""))
