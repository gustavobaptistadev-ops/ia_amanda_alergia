import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Core API
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = "" # Fallback to FRONTEND_URL if empty
    PUBLIC_API_URL: str = "http://localhost:8000"
    
    # Database (Supabase / Postgres)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: str = ""
    POSTGRES_DB: str = ""
    DATABASE_URL: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # JWT / Security
    JWT_SECRET_KEY: str = ""
    INTERNAL_API_KEY: str = ""
    WEBHOOK_SECRET: str = ""
    ENCRYPTION_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"
    INITIAL_ADMIN_PASSWORD: str = ""
    ADMIN_USERNAME: str = "admin"

    # Evolution API
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_GLOBAL_KEY: str = ""
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE_NAME: str = "ia_amanda"

    # Google Calendar
    GOOGLE_CALENDAR_ID: str = "primary"
    GOOGLE_CREDENTIALS_JSON: str = ""

    # Langfuse (Observability)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Langflow (Reviewer Agent API)
    LANGFLOW_API_URL: str = ""
    LANGFLOW_API_KEY: str = ""
    LANGFLOW_FLOW_ID: str = ""
    LANGFLOW_TWEAKS: str = "{}" # JSON string with specific tweaks for the flow
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def get_cors_origins(self) -> list[str]:
        origins_str = self.CORS_ORIGINS or self.FRONTEND_URL
        return [o.strip() for o in origins_str.split(",") if o.strip()]

    @property
    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_HOST and self.POSTGRES_DB:
            return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return ""

settings = Settings()
