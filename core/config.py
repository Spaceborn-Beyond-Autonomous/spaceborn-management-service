from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Get project root directory (parent of core/)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "Spaceborn Management Service"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Convert DATABASE_URL to asyncpg format for SQLAlchemy"""
        db_url = self.DATABASE_URL
        
        # Replace protocol
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        
        # Convert sslmode to ssl for asyncpg
        parsed = urlparse(db_url)
        if parsed.query:
            params = parse_qs(parsed.query)
            
            # Remove sslmode and channel_binding (not supported by asyncpg)
            if 'sslmode' in params:
                params.pop('sslmode')
                params['ssl'] = ['require']  # asyncpg uses ssl=true
            if 'channel_binding' in params:
                params.pop('channel_binding')
            
            # Rebuild query string
            new_query = urlencode(params, doseq=True)
            db_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
        
        return db_url
    
    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    @property
    def origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
