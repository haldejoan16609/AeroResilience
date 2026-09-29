"""
AeroResilience — Database Setup
Supports both Supabase (PostgreSQL via asyncpg) and local SQLite (aiosqlite).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Engine configuration differs between SQLite and PostgreSQL
engine_kwargs = {"echo": False}

if settings.USE_SUPABASE:
    # PostgreSQL (Supabase) — connection pooling settings
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    })
    print("[DB] Database: Supabase (PostgreSQL)")
else:
    print("[DB] Database: Local SQLite")

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables (only for SQLite — Supabase uses the SQL schema file)."""
    if not settings.USE_SUPABASE:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[OK] SQLite tables created")
    else:
        print("[OK] Connected to Supabase -- tables managed via SQL schema")


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
