import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# The database url might look like postgresql://...
# For SQLAlchemy async, we need postgresql+asyncpg://
db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ia_amanda")

if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

# Ensure pgvector's +asyncpg string is handled if it's there
if "+asyncpg+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg+asyncpg", "+asyncpg")

engine = create_async_engine(
    db_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
