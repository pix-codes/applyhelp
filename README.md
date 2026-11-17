# ApplyHelp - AI-Powered Job Discovery & Personalized Outreach Assistant

A production-conscious personal job-search assistant designed to discover remote engineering opportunities, evaluate geographic and candidate suitability (with first-class support for Nepal eligibility), respectfully research companies, generate grounded cold outreach, and export drafts to Gmail or `.eml`.

---

## 🌟 Key Features

1. **Candidate Profile as Source of Truth & PDF Resume Parser**:
   - Upload any resume PDF using fast, accurate PyMuPDF text extraction.
   - LLM automatically structures personal details, technical skills, work history, target roles, and featured projects into PostgreSQL.
   - Edit and fine-tune parsed details directly through Streamlit.

2. **Respectful Discovery & Nepal Eligibility Verification**:
   - Automated ingestion across 8 verified public feeds and platforms:
     - **Real Work From Anywhere** (Curated, 100% location-independent global remote roles)
     - **We Work Remotely** (Programming, backend, and developer feed)
     - **NoDesk** (Global remote startups & scaleups)
     - **Jobicy API** (Worldwide remote engineering vacancies with salary ranges)
     - **Remote OK API** (Global tech and startup positions)
     - **Y Combinator / Hacker News** ("Ask HN: Who is hiring?" startup threads via Algolia/Firebase API)
     - **Remotive API** (Developer & remote software jobs)
     - **Arbeitnow API** (Remote-friendly engineering teams)
   - Structured geographic categorization: Worldwide, Nepal-eligible, Country-specific, Region-specific, Unknown, Excluded.
   - **Never classifies unknown eligibility as Worldwide**.
   - Respectful crawling with per-domain rate-limiting, jitter, caching, and backoff.

3. **Deterministic & Contextual Matching**:
   - Computes transparent compatibility scores based on skill overlap, title alignment, and geographic permissions.
   - Provides clear match explanations without LLM hallucination.

4. **Public Company Research**:
   - Scrapes official company landing pages respectfully.
   - Analyzes product focus and engineering challenges.
   - Defends against prompt injections from untrusted website content.

5. **AI-Powered Grounded Outreach Studio**:
   - Tailored email generator for Founders, Engineering Managers, Recruiters, and Follow-ups.
   - No robotic buzzwords or fabricated familiarity.
   - Live editing, versioning, and pipeline status tracking.

6. **Secure Gmail Draft Integration & EML Fallback**:
   - Uses Google's official REST API with minimal scope: `https://www.googleapis.com/auth/gmail.compose`.
   - Never requests mailbox reading permissions.
   - Never sends emails automatically.
   - OAuth refresh tokens are encrypted at rest with Fernet.
   - One-click `.eml` export fallback when Gmail is not connected.

7. **Flexible LLM Provider Layer**:
   - Groq (ChatGroq)
   - Mistral (ChatMistralAI)
   - Google Gemini via direct REST API (no Google GenAI SDK)
   - OpenAI & OpenAI-compatible providers (vLLM, Ollama, DeepSeek, OpenRouter)
   - Optional Cloudflare AI Gateway routing.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.12+
- `uv` (Fast Python package manager)
- PostgreSQL (running locally or in Docker at `localhost:5432`)

### 1. Environment Setup
Create a `.env` file from the provided example:
```bash
cp .env.example .env
```
Ensure `DATABASE_URL` points to your PostgreSQL database:
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/apply_help
APP_SECRET_KEY=BEbXP8jmgz4cTxIWH2_iQxi_g8HsQ2ZcTv3bAR9I8F4=
```

### 2. Run Database Migrations
```bash
uv run alembic upgrade head
```

### 3. Launch Streamlit Application
```bash
uv run streamlit run app/main.py
```
Open your browser at `http://localhost:8501`.

---

## 📖 Google OAuth & Gmail Setup
For a complete walkthrough on generating your Google Client ID, enabling the Gmail API, and connecting Gmail drafts, refer to the [Google OAuth Setup Guide](docs/GMAIL_SETUP_GUIDE.md) or open the **📖 Google OAuth Setup Guide** tab directly in the Streamlit Settings page.

---

## 🧪 Testing and Quality
Run the automated test suite:
```bash
uv run pytest
```

Run code formatting and linting:
```bash
uv run ruff check .
```

---

## 🐳 Docker Deployment
Build and run the container:
```bash
docker compose up --build
```
The container runs as an unprivileged user (`appuser`) with healthchecks enabled and connects to your host's existing PostgreSQL service.
