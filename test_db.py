"""Quick Supabase connection test."""
import asyncio
from sqlalchemy import text
from app.database import engine

async def test():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"[OK] Supabase connected! Test query returned: {result.scalar()}")

            # Check if tables exist
            tables = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
            ))
            table_list = [row[0] for row in tables.all()]
            if table_list:
                print(f"[TABLES] Found: {', '.join(table_list)}")
            else:
                print("[WARN] No tables found -- run supabase_schema.sql in Supabase SQL Editor first!")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

asyncio.run(test())
