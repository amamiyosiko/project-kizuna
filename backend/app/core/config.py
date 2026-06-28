from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Amazon CS AI"
    ENV: str = "development"
    DATABASE_URL: str
    JWT_SECRET_KEY: str
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
