from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Email configuration
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str = "Spaceborn"

    # App settings
    SITE_URL: str = "https://yourdomain.com"

    class Config:
        env_file = ".env"


settings = Settings()
