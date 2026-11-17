import asyncio

import streamlit as st

from app.config.settings import get_settings
from app.core.database import get_db
from app.repositories.settings_repo import SettingsRepository
from app.services.gmail.client import GmailClient
from app.services.llm.prompts import (
    DEFAULT_PROMPTS,
    PROMPT_METADATA,
    optimize_prompt_with_ai,
)
from app.utils.async_runner import run_async


def render_settings():
    st.title("⚙️ System Settings & Integrations")
    settings = get_settings()

    with get_db() as db:
        repo = SettingsRepository(db)

        # Tab layout for clean organization
        tab_llm, tab_prompts, tab_gmail, tab_guide = st.tabs([
            "🤖 LLM Providers",
            "💬 System Prompts",
            "📬 Gmail Integration",
            "📖 Google OAuth Setup Guide",
        ])

        with tab_llm:
            st.subheader("🤖 LLM Provider Configuration")
            st.markdown(
                "Configure your LLM API keys and model names directly here. "
                "Keys saved here are **encrypted at rest** in your local PostgreSQL database and override `.env` defaults."
            )

            current_provider = repo.get("default_llm_provider", settings.default_llm_provider) or "groq"
            providers_list = ["groq", "mistral", "gemini", "openai", "nvidia"]
            default_index = providers_list.index(current_provider) if current_provider in providers_list else 0
            selected_provider = st.selectbox(
                "Active Default LLM Provider",
                providers_list,
                index=default_index,
                help="The active provider used for parsing resumes, researching companies, and generating outreach.",
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Groq (Llama 3 / Mixtral)")
                groq_key = st.text_input(
                    "Groq API Key",
                    value=repo.get("groq_api_key", settings.groq_api_key) or "",
                    type="password",
                    help="Free, ultra-fast inference via console.groq.com",
                )
                groq_model = st.text_input(
                    "Groq Model",
                    value=repo.get("groq_model", "llama-3.3-70b-versatile") or "llama-3.3-70b-versatile",
                    help="e.g. llama-3.3-70b-versatile, llama-3.1-8b-instant",
                )

                st.markdown("#### Mistral AI")
                mistral_key = st.text_input(
                    "Mistral API Key",
                    value=repo.get("mistral_api_key", settings.mistral_api_key) or "",
                    type="password",
                    help="Mistral AI API key from console.mistral.ai",
                )
                mistral_model = st.text_input(
                    "Mistral Model",
                    value=repo.get("mistral_model", "mistral-large-latest") or "mistral-large-latest",
                    help="e.g. mistral-large-latest, mistral-small-latest, codestral-latest, open-mistral-nemo",
                )

                st.markdown("#### Cloudflare AI Gateway (Optional)")
                cf_gateway = st.text_input(
                    "Cloudflare AI Gateway Base URL",
                    value=repo.get("cloudflare_gateway_url", settings.cloudflare_gateway_url) or "",
                    placeholder="https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}",
                    help="Optional Cloudflare AI Gateway universal endpoint",
                )
                cf_api_key = st.text_input(
                    "Cloudflare API Key / Token",
                    value=repo.get("cloudflare_api_key", settings.cloudflare_api_key) or "",
                    type="password",
                    help="Cloudflare API token if your gateway requires authentication",
                )

            with col2:
                st.markdown("#### Google Gemini REST")
                gemini_key = st.text_input(
                    "Google Gemini API Key",
                    value=repo.get("gemini_api_key", settings.gemini_api_key) or "",
                    type="password",
                    help="Direct Google AI Studio REST key from aistudio.google.com (No SDK used)",
                )
                gemini_model = st.text_input(
                    "Gemini Model",
                    value=repo.get("gemini_model", "gemini-1.5-flash") or "gemini-1.5-flash",
                    help="e.g. gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash",
                )

                st.markdown("#### OpenAI / OpenAI-Compatible")
                openai_key = st.text_input(
                    "OpenAI / Compatible API Key",
                    value=repo.get("openai_api_key", settings.openai_api_key) or "",
                    type="password",
                    help="API key for OpenAI, DeepSeek, Together, OpenRouter, etc.",
                )
                openai_model = st.text_input(
                    "OpenAI / Compatible Model",
                    value=repo.get("openai_model", "gpt-4o-mini") or "gpt-4o-mini",
                    help="e.g. gpt-4o-mini, deepseek-chat, llama3-70b-8192",
                )
                openai_base = st.text_input(
                    "OpenAI-Compatible Base URL (Optional)",
                    value=repo.get("openai_base_url", settings.openai_base_url) or "",
                    placeholder="https://api.openai.com/v1, https://api.deepseek.com/v1, etc.",
                )

                st.markdown("#### NVIDIA API Catalog")
                nvidia_key = st.text_input(
                    "NVIDIA API Key",
                    value=repo.get("nvidia_api_key", settings.nvidia_api_key) or "",
                    type="password",
                    help="API key from build.nvidia.com (e.g. nvapi-...)",
                )
                nvidia_model = st.text_input(
                    "NVIDIA Model",
                    value=repo.get("nvidia_model", settings.nvidia_model) or "minimaxai/minimax-m3.1-flash",
                    help="e.g. minimaxai/minimax-m3.1-flash, meta/llama-3.3-70b-instruct, mistralai/mistral-large-2-instruct",
                )

            if st.button("💾 Save LLM Settings", type="primary"):
                repo.set("default_llm_provider", selected_provider, encrypt=False)
                repo.set("groq_api_key", groq_key, encrypt=True)
                repo.set("groq_model", groq_model, encrypt=False)
                repo.set("mistral_api_key", mistral_key, encrypt=True)
                repo.set("mistral_model", mistral_model, encrypt=False)
                repo.set("gemini_api_key", gemini_key, encrypt=True)
                repo.set("gemini_model", gemini_model, encrypt=False)
                repo.set("openai_api_key", openai_key, encrypt=True)
                repo.set("openai_model", openai_model, encrypt=False)
                repo.set("openai_base_url", openai_base, encrypt=False)
                repo.set("nvidia_api_key", nvidia_key, encrypt=True)
                repo.set("nvidia_model", nvidia_model, encrypt=False)
                repo.set("cloudflare_gateway_url", cf_gateway, encrypt=False)
                repo.set("cloudflare_api_key", cf_api_key, encrypt=True)
                st.success("✅ LLM provider keys, models, and Cloudflare credentials saved successfully (encrypted at rest)!")

        with tab_prompts:
            st.subheader("💬 System Prompts Configuration")
            st.markdown(
                "Customize and fine-tune the system prompts used across ApplyHelp. "
                "Any modifications here will override the default hardcoded prompts and persist directly in your local settings."
            )

            # Dedicated Finetuner Provider & Model Configuration
            with st.expander("🛠️ AI Prompt Finetuner Model Settings", expanded=False):
                st.markdown("Select which LLM provider and model should be tasked with reviewing and fine-tuning your prompts.")
                col_ft1, col_ft2 = st.columns(2)
                with col_ft1:
                    cur_ft_prov = repo.get("finetuner_llm_provider", settings.finetuner_llm_provider) or "Same as Active Default"
                    ft_options = ["Same as Active Default", "groq", "mistral", "gemini", "openai", "nvidia"]
                    ft_index = ft_options.index(cur_ft_prov) if cur_ft_prov in ft_options else 0
                    selected_ft_prov = st.selectbox(
                        "Finetuner LLM Provider",
                        ft_options,
                        index=ft_index,
                        key="finetuner_prov_select",
                        help="Choose which provider performs prompt optimization.",
                    )
                with col_ft2:
                    cur_ft_mod = repo.get("finetuner_llm_model", settings.finetuner_llm_model) or ""
                    selected_ft_mod = st.text_input(
                        "Finetuner Model Name (Optional Override)",
                        value=cur_ft_mod,
                        placeholder="e.g. llama-3.3-70b-versatile, gpt-4o, minimaxai/minimax-m3.1-flash",
                        key="finetuner_mod_input",
                        help="Leave blank to use the provider's default configured model.",
                    )

                if st.button("💾 Save Finetuner Settings", key="btn_save_ft_settings"):
                    val_to_save = None if selected_ft_prov == "Same as Active Default" else selected_ft_prov
                    repo.set("finetuner_llm_provider", val_to_save, encrypt=False)
                    repo.set("finetuner_llm_model", selected_ft_mod.strip() if selected_ft_mod.strip() else None, encrypt=False)
                    st.success("✅ Finetuner model settings saved successfully!")
                    st.rerun()

            st.divider()

            prompt_inputs = {}
            for p_key, meta in PROMPT_METADATA.items():
                st.markdown(f"#### {meta['title']}")
                st.caption(meta["description"])
                saved_prompt = repo.get(f"prompt_{p_key}")
                default_prompt = DEFAULT_PROMPTS.get(p_key, "")

                # Check if an AI-optimized prompt was staged in session_state for this key
                staged_key = f"staged_prompt_{p_key}"
                current_text = st.session_state.get(staged_key, saved_prompt if saved_prompt is not None else default_prompt)

                prompt_inputs[p_key] = st.text_area(
                    label=f"Prompt: {meta['title']}",
                    value=current_text,
                    height=180,
                    key=f"prompt_input_{p_key}",
                    label_visibility="collapsed",
                )

                # AI Prompt Fine-tuning Expander
                with st.expander(f"✨ Fine-tune '{meta['title']}' with AI"):
                    col_ai_inst, col_ai_btn = st.columns([3, 1])
                    with col_ai_inst:
                        refine_instruction = st.text_input(
                            "What should be improved or changed?",
                            placeholder="e.g. 'Make it more concise', 'Be harsher on corporate buzzwords', 'Require explicit salary parsing'",
                            key=f"refine_input_{p_key}",
                        )
                    with col_ai_btn:
                        st.write("")
                        st.write("")
                        if st.button("🪄 Optimize with AI", key=f"btn_optimize_{p_key}"):
                            with st.spinner("AI is optimizing and refining your prompt..."):
                                try:
                                    refined = run_async(
                                        optimize_prompt_with_ai(
                                            prompt_key=p_key,
                                            current_prompt=prompt_inputs[p_key],
                                            user_guidance=refine_instruction,
                                            db=db,
                                        )
                                    )
                                    st.session_state[staged_key] = refined
                                    st.success("Prompt optimized! Review the updated text above and click 'Save Custom Prompts' to persist.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Optimization failed: {e}")

                st.divider()

            col_p1, col_p2 = st.columns([1, 1])
            with col_p1:
                if st.button("💾 Save Custom Prompts", type="primary"):
                    for p_key, p_val in prompt_inputs.items():
                        repo.set(f"prompt_{p_key}", p_val, encrypt=False)
                    st.success("✅ Custom system prompts saved successfully!")
                    st.rerun()

            with col_p2:
                if st.button("🔄 Reset All Prompts to Defaults"):
                    for p_key in PROMPT_METADATA.keys():
                        repo.delete(f"prompt_{p_key}")
                    st.info("Reset prompts to defaults.")
                    st.rerun()

        with tab_gmail:
            st.subheader("📬 Gmail OAuth 2.0 Credentials")
            st.markdown(
                "Save your Google OAuth 2.0 Client ID and Secret to enable saving generated emails directly as drafts in your Gmail account. "
                "Tokens are **encrypted at rest** and only request the minimal `gmail.compose` scope."
            )

            g_client_id = st.text_input(
                "Google Client ID",
                value=repo.get("google_client_id", settings.google_client_id) or "",
                placeholder="xxxxxxxxxxxx-xxxxxxxxxxxxxxxx.apps.googleusercontent.com",
            )
            g_client_secret = st.text_input(
                "Google Client Secret",
                value=repo.get("google_client_secret", settings.google_client_secret) or "",
                type="password",
            )
            g_redirect_uri = st.text_input(
                "Google OAuth Redirect URI",
                value=repo.get("google_redirect_uri", settings.google_redirect_uri) or "http://localhost:8501",
            )

            if st.button("💾 Save Google OAuth Credentials"):
                repo.set("google_client_id", g_client_id, encrypt=False)
                repo.set("google_client_secret", g_client_secret, encrypt=True)
                repo.set("google_redirect_uri", g_redirect_uri, encrypt=False)
                st.success("Google OAuth credentials saved!")
                st.rerun()

            st.divider()
            gmail = GmailClient(db)

            # Automatically detect OAuth code from URL query parameters if returning from Google
            query_params = st.query_params
            if "code" in query_params and not gmail.is_connected():
                returned_code = query_params["code"]
                st.info("🔄 Detected OAuth authorization code from Google redirect! Connecting...")
                success = run_async(gmail.exchange_code_for_tokens(returned_code.strip()))
                if success:
                    st.success("🎉 Successfully connected Gmail!")
                    # Clean up URL parameters so it doesn't re-trigger
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("Authentication failed with the code from Google. Try clicking the authorization link again.")

            if gmail.is_connected():
                st.success("🟢 Gmail is connected! Your drafts will be created directly in your Gmail drafts folder.")
                if st.button("Disconnect / Revoke Access"):
                    gmail.revoke_connection()
                    st.success("Gmail disconnected.")
                    st.rerun()
            else:
                st.info("Gmail is not currently connected.")
                if gmail.client_id and gmail.client_secret:
                    try:
                        auth_url = gmail.get_authorization_url()
                        st.markdown(f"👉 **[Click here to authorize Gmail with Google]({auth_url})**")
                        st.caption("When Google redirects back to `http://localhost:8501`, ApplyHelp will automatically detect the code and connect.")

                        st.write("Or if you are using an external browser window, paste the code below:")
                        auth_code = st.text_input("Authorization Code (or full callback URL):")
                        if st.button("Complete Connection") and auth_code:
                            raw = auth_code.strip()
                            # If user pasted the whole URL like http://localhost:8501/?code=4/0A... extract the code
                            if "code=" in raw:
                                import urllib.parse
                                parsed = urllib.parse.urlparse(raw)
                                code_val = urllib.parse.parse_qs(parsed.query).get("code", [raw])[0]
                            else:
                                code_val = raw

                            success = run_async(gmail.exchange_code_for_tokens(code_val))
                            if success:
                                st.success("Successfully connected Gmail!")
                                st.rerun()
                            else:
                                st.error("Failed to authenticate with the provided code. Ensure the Redirect URI in Google Cloud matches `http://localhost:8501` exactly.")
                    except Exception as e:
                        st.error(f"Error initializing OAuth: {e}")
                else:
                    st.warning("Please enter and save your Google Client ID and Secret above to generate the authorization link.")

        with tab_guide:
            st.subheader("📖 Step-by-Step Google OAuth & Gmail API Setup Guide")
            st.markdown("""
### 1. Create a Project in Google Cloud Console
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `ApplyHelp-Outreach`) or select an existing one.

---

### 2. Enable the Gmail API
1. In the sidebar, navigate to **APIs & Services** > **Library**.
2. Search for **Gmail API**.
3. Click on **Gmail API** and click **Enable**.

---

### 3. Configure OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. Select User Type: **External** (for personal Google accounts) and click **Create**.
3. Fill in the required fields:
   - **App name**: `ApplyHelp`
   - **User support email**: Your Gmail address
   - **Developer contact information**: Your Gmail address
4. Click **Save and Continue**.
5. Under **Scopes**, click **Add or Remove Scopes**:
   - Filter/search for `https://www.googleapis.com/auth/gmail.compose`
   - Check the box for `.../auth/gmail.compose` (Compose and save drafts)
   - Click **Update** and then **Save and Continue**.
6. Under **Test Users**:
   - Click **Add Users**.
   - Add your own personal Gmail address (this allows you to authorize without submitting for public verification).
   - Click **Save and Continue**.

---

### 4. Create OAuth 2.0 Credentials
1. Go to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** at the top > **OAuth client ID**.
3. Application type: Select **Web application**.
4. Name: `ApplyHelp Web Client`.
5. Under **Authorized redirect URIs**:
   - Click **Add URI**.
   - Enter `http://localhost:8501` (or your configured custom port/URL).
6. Click **Create**.
7. Google will show you your **Client ID** and **Client Secret**.

---

### 5. Connect in ApplyHelp
1. Switch to the **📬 Gmail Integration** tab above.
2. Paste the **Client ID** and **Client Secret**.
3. Verify that the redirect URI is `http://localhost:8501`.
4. Click **Save Google OAuth Credentials**.
5. Click the generated **Authorize Gmail with Google** link.
6. Log in with your test user Google account. If you see an *"unverified app"* warning, click **Advanced** > **Go to ApplyHelp (unsafe)**.
7. Approve the draft composition permission.
8. When redirected back to `http://localhost:8501/?code=4/0A...`, copy the code after `code=` in your browser address bar.
9. Paste it into the **Authorization Code** box in ApplyHelp and click **Complete Connection**.
            """)
