import os
from typing import Optional
from dotenv import load_dotenv

# Пробуем импортировать BaseSettings из разных мест (совместимость с разными версиями)
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    try:
        from pydantic import BaseSettings, Field
    except ImportError:
        print("❌ Не удалось импортировать BaseSettings. Устанавливаю pydantic-settings...")
        import subprocess
        import sys

        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pydantic-settings'])
        from pydantic_settings import BaseSettings
        from pydantic import Field

load_dotenv()


class Config(BaseSettings):
    """Application configuration"""

    # OpenAI Configuration
    openai_api_key: str = Field(default="", description="OpenAI API key")

    # Google Calendar Configuration
    google_calendar_credentials_file: str = Field(
        default="credentials.json",
        description="Path to Google Calendar credentials file"
    )
    google_calendar_id: str = Field(default="primary", description="Google Calendar ID")

    # Thumbtack Configuration
    thumbtack_email: Optional[str] = Field(default=None, description="Thumbtack email")
    thumbtack_password: Optional[str] = Field(default=None, description="Thumbtack password")
    thumbtack_api_key: Optional[str] = Field(default=None, description="Thumbtack API key")

    # Application Configuration
    check_interval_minutes: int = Field(default=5, description="Check interval in minutes")
    log_level: str = Field(default="INFO", description="Logging level")
    timezone: str = Field(default="America/New_York", description="Timezone")

    # Business Configuration
    business_name: str = Field(default="Your Business", description="Business name")
    service_type: str = Field(default="Photography", description="Service type")
    base_price: float = Field(default=150.0, description="Base price")
    price_range_min: float = Field(default=100.0, description="Minimum price")
    price_range_max: float = Field(default=500.0, description="Maximum price")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Загружаем из переменных окружения если не заданы
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

        if not self.thumbtack_email:
            self.thumbtack_email = os.getenv("THUMBTACK_EMAIL")

        if not self.thumbtack_password:
            self.thumbtack_password = os.getenv("THUMBTACK_PASSWORD")


# Создаём экземпляр конфигурации
try:
    config = Config()
    print("✅ Конфигурация загружена успешно")
except Exception as e:
    print(f"⚠️ Проблема с загрузкой конфигурации: {e}")
    # Создаём базовую конфигурацию
    config = Config(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        business_name=os.getenv("BUSINESS_NAME", "Your Business"),
        service_type=os.getenv("SERVICE_TYPE", "Photography"),
        base_price=float(os.getenv("BASE_PRICE", "150")),
        price_range_min=float(os.getenv("PRICE_RANGE_MIN", "100")),
        price_range_max=float(os.getenv("PRICE_RANGE_MAX", "500"))
    )