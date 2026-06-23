from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Wealth Advisory & Tax Optimization Platform"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    
    # LLM Settings
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: str = "mock-key"
    LLM_MODEL: str = "qwen-2.5-32b"
    
    # Typhoon Settings
    TYPHOON_API_KEY: Optional[str] = None
    TYPHOON_API_BASE: str = "https://api.opentyphoon.ai/v1"
    TYPHOON_MODEL: str = "typhoon-v1.5-instruct"
    
    # Database & Cache Settings
    DATABASE_URL: str = "sqlite:///./wealth_advisor.db"
    REDIS_URL: str = "redis://localhost:6379"
    
    VERBOSE: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
