from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .config import get_settings

settings = get_settings()

# create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# create async session maker
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """
    Dependency per ottenere una sessione del database.
    Da utilizzare nelle route FastAPI.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# function to initialize database
async def init_db():
    from .models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) 