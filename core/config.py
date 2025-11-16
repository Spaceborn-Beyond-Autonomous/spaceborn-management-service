from pydantic import BaseModel
from functools import lru_cache
import os

class Settings(BaseModel):
    PROJECT_NAME: str = "OrgApp"
    API_V1_STR: str = "/api/v1"

    # DB
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "orgdb")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://{os.getenv('POSTGRES_USER','postgres')}:{os.getenv('POSTGRES_PASSWORD','postgres')}"
        f"@{os.getenv('POSTGRES_HOST','localhost')}:{os.getenv('POSTGRES_PORT','5432')}/{os.getenv('POSTGRES_DB','orgdb')}"
    )

    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "CHANGE_ME")
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

@lru_cache
def get_settings() -> Settings:
    return Settings()
