from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str

    BOT_MODE: str = "polling"
    APP_ENV: str = "dev"

    ADMIN_IDS: List[int] = []
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "123456"

    SECRET_KEY: str = "2c92f8e77fdb4e66b1b9b2f4d988cb31"

    # إعدادات SMS Webhook
    SMS_WEBHOOK_SECRET: str
    SYP_MATCH_TOLERANCE: int = 2000  # فرق مقبول بالمبلغ (ل.س)

    # جديد: يُقرأ من .env
    SUPPORT_USERNAME: str | None = None  # بدون @

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, list):
            return [int(x) for x in v]
        return []

settings = Settings()
