from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central app configuration. Reads from .env at project root.
    All other modules should import `settings` from here rather than
    reading os.environ directly.
    """

    database_url: str = "postgresql+psycopg2://fleetguard:fleetguard_dev_pw@localhost:5432/fleetguard_db"
    groq_api_key: str = ""  # set in .env — required for the Insight/Action agents (Day 6)
    groq_model: str = "openai/gpt-oss-120b"
    # NOTE: llama-3.3-70b-versatile (an earlier default here) was deprecated
    # by Groq on 2026-06-17. If this model also stops working later, check
    # https://console.groq.com/docs/models or GET https://api.groq.com/openai/v1/models
    # for the current list and update GROQ_MODEL in .env — no code change needed.

    # --- Auth (Microsoft SSO) ---
    azure_tenant_id: str = ""    # Directory (tenant) ID from your Azure app registration
    azure_client_id: str = ""    # Application (client) ID from your Azure app registration
    jwt_secret_key: str = "dev-only-secret-change-me"  # FleetGuard's own JWT signing key (NOT Azure's)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
