from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Amazon CS AI"
    ENV: str = "development"
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    CONFIG_ENCRYPTION_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    AI_PROVIDER: str = "openai"  # auto / openai / gemini / rule
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    AWS_REGION: str = "ap-northeast-1"
    S3_BUCKET_NAME: str | None = None
    S3_UPLOAD_EXPIRES_SECONDS: int = 900

    AMAZON_LWA_CLIENT_ID: str | None = None
    AMAZON_LWA_CLIENT_SECRET: str | None = None
    AMAZON_REFRESH_TOKEN: str | None = None
    AMAZON_MARKETPLACE_ID: str | None = None
    AMAZON_REGION: str = "jp"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
