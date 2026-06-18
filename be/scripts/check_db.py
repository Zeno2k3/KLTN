import asyncio
import asyncpg


async def test():
    # Tạo database kltn_db nếu chưa có
    conn = await asyncpg.connect("postgresql://postgres@127.0.0.1:5432/postgres")
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = 'kltn_db'"
    )
    if not exists:
        await conn.execute("CREATE DATABASE kltn_db")
        print("Da tao database kltn_db")
    else:
        print("Database kltn_db da ton tai")
    await conn.close()

    # Test kết nối vào kltn_db
    conn = await asyncpg.connect("postgresql://postgres@127.0.0.1:5432/kltn_db")
    print("Ket noi vao kltn_db thanh cong!")
    await conn.close()


asyncio.run(test())
