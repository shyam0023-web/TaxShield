import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from urllib.parse import quote_plus

# The password contains an @ symbol, which conflicts with the URL formatting
password = quote_plus("Abhishek9544995068@")
url = f"postgresql+asyncpg://postgres:{password}@db.pueihaqjbthiajnyxnrt.supabase.co:5432/postgres"

async def test_conn():
    print(f"Trying to connect to: postgresql+asyncpg://postgres:***@db.pueihaqjbthiajnyxnrt.supabase.co:5432/postgres")
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            print("SUCCESS! Successfully connected to Supabase PostgreSQL.")
    except Exception as e:
        print(f"FAILED to connect: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_conn())
