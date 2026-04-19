import asyncio
import asyncpg
import sys

async def main():
    try:
        conn = await asyncpg.connect('postgresql://autoflow:autoflow@127.0.0.1:5432/autoflow')
        print("SUCCESS 1: autoflow:autoflow")
        await conn.close()
        return
    except Exception as e:
        print(f"FAIL 1: {e}")

    try:
        conn = await asyncpg.connect('postgresql://autoflow:password@127.0.0.1:5432/autoflow')
        print("SUCCESS 2: autoflow:password")
        await conn.close()
        return
    except Exception as e:
        print(f"FAIL 2: {e}")

    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@127.0.0.1:5432/autoflow')
        print("SUCCESS 3: postgres:postgres")
        await conn.close()
        return
    except Exception as e:
        print(f"FAIL 3: {e}")

asyncio.run(main())
