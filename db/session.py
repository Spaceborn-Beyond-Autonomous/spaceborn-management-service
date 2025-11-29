from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    # 1. Checks connection health before using it (Crucial for Neon where connections might drop)
    pool_pre_ping=True, 
    
    # 2. Recycle connections every 5 minutes. 
    # Neon idle-timeouts connections after 5 mins. This prevents using a stale/closed connection.
    pool_recycle=300, 
    
    # 3. Connection Pool Sizing
    pool_size=10,
    max_overflow=20,

    # 4. Neon Specific Args
    connect_args={
        "ssl": "require",  # Neon requires SSL
        "server_settings": {
            "jit": "off"   # Optimization: Disables JIT compilation which can slow down simple queries
        }
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session