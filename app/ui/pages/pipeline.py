import streamlit as st

from app.core.database import get_db
from app.repositories.outreach import OutreachRepository
from app.schemas.outreach import OutreachMessageUpdate


def render_pipeline():
    st.title("📊 Outreach Pipeline")
    st.markdown("Track and update outreach messages, follow-up dates, notes, and progress stages.")

    with get_db() as db:
        repo = OutreachRepository(db)
        status_filter = st.selectbox(
            "Filter Status",
            [
                "All",
                "Draft Generated",
                "Draft Saved",
                "Applied",
                "Follow-up required",
                "Replied",
                "Interviewing",
                "Rejected",
                "Archived",
            ],
        )

        filter_arg = None if status_filter == "All" else status_filter
        messages = repo.list_messages(status=filter_arg)

        if not messages:
            st.info("No outreach messages found in pipeline.")
            return

        for msg in messages:
            with st.expander(f"✉️ {msg.subject} — Status: `{msg.status}` (Updated: {msg.updated_at.strftime('%Y-%m-%d')})"):
                st.write(msg.body)
                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    new_status = st.selectbox(
                        "Change Status",
                        [
                            "Draft Generated",
                            "Draft Saved",
                            "Applied",
                            "Follow-up required",
                            "Replied",
                            "Interviewing",
                            "Rejected",
                            "Archived",
                        ],
                        index=[
                            "Draft Generated",
                            "Draft Saved",
                            "Applied",
                            "Follow-up required",
                            "Replied",
                            "Interviewing",
                            "Rejected",
                            "Archived",
                        ].index(msg.status) if msg.status in [
                            "Draft Generated",
                            "Draft Saved",
                            "Applied",
                            "Follow-up required",
                            "Replied",
                            "Interviewing",
                            "Rejected",
                            "Archived",
                        ] else 0,
                        key=f"status_select_{msg.id}",
                    )
                with col2:
                    notes = st.text_input("Notes", value=msg.notes or "", key=f"notes_input_{msg.id}")

                if st.button("Update Stage", key=f"btn_update_{msg.id}"):
                    repo.update(msg.id, OutreachMessageUpdate(status=new_status, notes=notes))
                    st.success("Outreach updated!")
                    st.rerun()

                st.subheader("Activity History")
                for evt in msg.events:
                    st.caption(f"• **{evt.event_type}** ({evt.created_at.strftime('%Y-%m-%d %H:%M')}): {evt.details or ''}")
