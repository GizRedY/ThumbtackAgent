import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

load_dotenv()


class Config(BaseSettings):
    """Application configuration"""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # Google Calendar Configuration
    google_calendar_credentials_file: str = Field(
        default="credentials.json", 
        env="GOOGLE_CALENDAR_CREDENTIALS_FILE"
    )
    google_calendar_id: str = Field(default="primary", env="GOOGLE_CALENDAR_ID")
    
    # Thumbtack Configuration
    thumbtack_email: Optional[str] = Field(None, env="THUMBTACK_EMAIL")
    thumbtack_password: Optional[str] = Field(None, env="THUMBTACK_PASSWORD")
    thumbtack_api_key: Optional[str] = Field(None, env="THUMBTACK_API_KEY")
    
    # Application Configuration
    check_interval_minutes: int = Field(default=5, env="CHECK_INTERVAL_MINUTES")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    timezone: str = Field(default="America/New_York", env="TIMEZONE")
    
    # Business Configuration
    business_name: str = Field(default="Your Business", env="BUSINESS_NAME")
    service_type: str = Field(default="Photography", env="SERVICE_TYPE")
    base_price: float = Field(default=150.0, env="BASE_PRICE")
    price_range_min: float = Field(default=100.0, env="PRICE_RANGE_MIN")
    price_range_max: float = Field(default=500.0, env="PRICE_RANGE_MAX")
    
    class Config:
        env_file = ".env"


config = Config()