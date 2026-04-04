import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os

url='postgresql+asyncpg://postgres.zhrvyvacmmecmpqkfooa:ABHI954499%40a@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres'
engine=create_async_engine(url)

async def test():
    conn = await engine.connect()
    print('asyncpg pooler connected!')
    await conn.close()
    await engine.dispose()

asyncio.run(test())
