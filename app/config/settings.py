from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/apply_help",
        alias="DATABASE_URL",
    )

    # Security
    app_secret_key: str = Field(
        default="BEbXP8jmgz4cTxIWH2_iQxi_g8HsQ2ZcTv3bAR9I8F4=",
        alias="APP_SECRET_KEY",
    )

    # LLM Providers
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    mistral_api_key: str | None = Field(default=None, alias="MISTRAL_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    nvidia_api_key: str | None = Field(default=None, alias="NVIDIA_API_KEY")
    nvidia_model: str | None = Field(default="minimaxai/minimax-m3.1-flash", alias="NVIDIA_MODEL")

    # Cloudflare AI Gateway
    cloudflare_gateway_url: str | None = Field(
        default=None, alias="CLOUDFLARE_GATEWAY_URL"
    )
    cloudflare_api_key: str | None = Field(
        default=None, alias="CLOUDFLARE_API_KEY"
    )

    # LLM Defaults
    default_llm_provider: str = Field(default="groq", alias="DEFAULT_LLM_PROVIDER")
    default_llm_model: str = Field(
        default="llama-3.3-70b-versatile", alias="DEFAULT_LLM_MODEL"
    )
    finetuner_llm_provider: str | None = Field(default=None, alias="FINETUNER_LLM_PROVIDER")
    finetuner_llm_model: str | None = Field(default=None, alias="FINETUNER_LLM_MODEL")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_timeout: int = Field(default=45, alias="LLM_TIMEOUT")

    # Crawling & Respectful Scraping
    crawl_user_agent: str = Field(
        default="ApplyHelpBot/1.0 (+https://github.com/parakram/apply-help; personal-job-discovery)",
        alias="CRAWL_USER_AGENT",
    )
    crawl_default_delay: float = Field(default=3.0, alias="CRAWL_DEFAULT_DELAY")
    crawl_max_concurrent_global: int = Field(
        default=2, alias="CRAWL_MAX_CONCURRENT_GLOBAL"
    )
    crawl_max_concurrent_per_domain: int = Field(
        default=1, alias="CRAWL_MAX_CONCURRENT_PER_DOMAIN"
    )

    # Gmail OAuth 2.0 (Optional)
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(
        default=None, alias="GOOGLE_CLIENT_SECRET"
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8501", alias="GOOGLE_REDIRECT_URI"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
