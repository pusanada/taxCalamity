from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Wealth Advisory & Tax Optimization Platform"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    
    # LLM Settings
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: str = "mock-key"
    LLM_MODEL: str = "qwen/qwen3-32b"
    
    # Typhoon Settings
    TYPHOON_API_KEY: Optional[str] = None
    TYPHOON_API_BASE: str = "https://api.opentyphoon.ai/v1"
    TYPHOON_MODEL: str = "typhoon-v2.1-12b-instruct"
    
    # Database & Cache Settings
    DATABASE_URL: str = "sqlite:///./wealth_advisor.db"
    REDIS_URL: str = "redis://localhost:6379"
    CHECKPOINT_DB_PATH: str = "./langgraph_checkpoints.sqlite"

    # CORS: comma-separated list of allowed frontend origins.
    # Default "*" is convenient for local dev; set explicitly in production.
    CORS_ORIGINS: str = "*"

    # When True, agents fall back to deterministic mock responses if a live LLM
    # call fails. Default False: production never serves mock data. Enable locally
    # (USE_MOCK_FALLBACK=true) to test the pipeline without hitting the LLM.
    USE_MOCK_FALLBACK: bool = False
    
    # SEC API Keys
    SEC_FUND_FACTSHEET_KEY: Optional[str] = None
    SEC_FUND_DAILY_INFO_KEY: Optional[str] = None

    VERBOSE: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
