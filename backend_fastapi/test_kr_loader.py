
import asyncio
from backend_fastapi.db.session import AsyncSessionLocal
from backend_fastapi.services.kr_loader import KRStockLoader

async def main():
    session = AsyncSessionLocal()
    try:
        loader = KRStockLoader(session)
        print("🧪 Testing KR Stock Pipeline...")
        
        # 1. Load Data
        symbol = "005930" # Samsung Electronics
        await loader.fetch_and_save_daily(symbol, days=10)
        
        # 2. Verify Data
        latest = await loader.get_latest_price(symbol)
        if latest:
            print(f"🎉 Verification Success! Latest Price from DB: {latest.close} KRW at {latest.timestamp}")
        else:
            print("❌ Verification Failed: No data found in DB.")
            
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
