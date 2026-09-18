from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    bot_token: str = Field(default="", alias="BOT_TOKEN")
    tg_user_id: Optional[int] = Field(default=None, alias="TG_USER_ID")

    tg_api_id: str = Field(default="", alias="TG_API_ID")
    tg_api_hash: str = Field(default="", alias="TG_API_HASH")

    kai_group: str = Field(default="5108", alias="KAI_GROUP")
    kai_subgroup: int = Field(default=2, alias="KAI_SUBGROUP")
    kai_api_url: str = Field(default="https://kai.ru/web/studentu/raspisanie1", alias="KAI_API_URL")

    tg_api_base_url: Optional[str] = Field(default=None, alias="TG_API_BASE_URL")

    database_url: str = Field(default="sqlite+aiosqlite:///kai_assistant.db", alias="DATABASE_URL")

    bb_login: str = Field(default="", alias="BB_LOGIN")
    bb_password: str = Field(default="", alias="BB_PASSWORD")
    bb_url: str = Field(default="https://bb.kai.ru", alias="BB_URL")

    web_host: str = Field(default="0.0.0.0", alias="WEB_HOST")
    web_port: int = Field(default=8000, alias="WEB_PORT")
    enable_tunnel: bool = Field(default=True, alias="ENABLE_TUNNEL")

    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.6-flash", alias="GEMINI_MODEL")

    app_auth_token: str = Field(default="", alias="APP_AUTH_TOKEN")

    sync_fresh_threshold_minutes: int = Field(default=15, alias="SYNC_FRESH_THRESHOLD_MINUTES")
    sync_recent_threshold_minutes: int = Field(default=60, alias="SYNC_RECENT_THRESHOLD_MINUTES")

    @field_validator("tg_user_id", mode="before")
    @classmethod
    def parse_optional_int(cls, v):
        if isinstance(v, str):
            v_clean = v.strip()
            if not v_clean:
                return None
            return int(v_clean)
        return v

    @field_validator("tg_api_base_url", mode="before")
    @classmethod
    def parse_optional_str(cls, v):
        if isinstance(v, str):
            v_clean = v.strip()
            if not v_clean:
                return None
            return v_clean.rstrip("/")
        return v



settings = Settings()
