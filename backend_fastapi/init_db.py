
import asyncio
from backend_fastapi.db.session import engine
from backend_fastapi.db.models import Base

async def init_models():
    async with engine.begin() as conn:
        print("🛠️  Creating Tables...")
        await conn.run_sync(Base.metadata.drop_all) # Clean slate for dev
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables Created!")

if __name__ == "__main__":
    asyncio.run(init_models())
