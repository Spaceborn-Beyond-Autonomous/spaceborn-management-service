from pydantic import BaseModel
from functools import lru_cache
import os


class Settings(BaseModel):
    PROJECT_NAME: str = "Spaceborn Management Service"
    API_V1_STR: str = "/api/v1"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Get database URI, converting to asyncpg format"""
        db_url = os.getenv("DATABASE_URL", "")
        
        if db_url:
            # Convert postgresql:// to postgresql+asyncpg://
            if db_url.startswith("postgresql://"):
                return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgres://"):
                return db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            return db_url
        
        # Default for local development if DATABASE_URL not set
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/orgdb"

    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "CHANGE_ME")
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
