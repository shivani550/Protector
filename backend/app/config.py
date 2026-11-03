import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENV: str = "development"
    PORT: int = 8000
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    DEMO_MODE: bool = True
    SEED_ON_BOOT: bool = False
    WATCH_INBOX: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///./protector.db"
    STORAGE_DIR: str = "./storage"

    DATA_KEY: str = "dt8sO-HwBy8OB8XtO9l6oLEM4tvwJnhNl-4M8grfRCE="
    JWT_SECRET: str = "42b2ade9a941186b6a9546a3c3377af29de90054133eadab3b1ae939f9edcb31"
    INSURER_API_KEY: str = "ins_28dee668e81a5f79275b5fce509c4e72"
    DEMO_PASSWORD: str = "DemoPass123!"

    LLM_PROVIDER: str = "mock"
    LLM_MODEL_FAST: str = "claude-3-haiku-20240307"
    LLM_MODEL_REASONING: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ALLOW_VISION_LLM: bool = False

    DELIVERY_MODE: str = "mock"
    WHATSAPP_PROVIDER: str = "mock"
    EMAIL_PROVIDER: str = "mock"

    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"

    META_WA_TOKEN: Optional[str] = None
    META_WA_PHONE_NUMBER_ID: Optional[str] = None
    META_WA_VERIFY_TOKEN: Optional[str] = None
    WHATSAPP_META_TEMPLATE_NAME: str = "hello_world"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_APP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "claims@demo.test"
    EMAIL_FROM_NAME: str = "Protector Health Desk"

    HELPLINE: str = "1800-123-4567"
    SENDER_NAME: str = "Protector Care Team"
    DEMO_PHONE_E164: str = "+919876543210"
    DEMO_EMAIL: str = "test@demo.test"

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 8
    LINK_TTL_HOURS: int = 72


settings = Settings()
