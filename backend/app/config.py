from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    supabase_url: str
    supabase_key: str  # publishable key — used for auth validation + user-scoped queries

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
