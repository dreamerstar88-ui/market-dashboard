
import asyncio
from backend_fastapi.db.session import AsyncSessionLocal
from backend_fastapi.services.us_loader import USStockLoader
from backend_fastapi.services.crypto_loader import CryptoLoader

async def test_us(session):
    print("\n🇺🇸 Testing US Loader...")
    loader = USStockLoader(session)
    # NASDAQ:AAPL is the safe bet for FDR
    symbol = "NASDAQ:AAPL" 
    await loader.fetch_and_save_daily(symbol, days=5)
    
    latest = await loader.get_latest_price(symbol)
    if latest:
        print(f"✅ US Success: {latest.symbol} = ${latest.close}")
    else:
        print("❌ US Failed")

async def test_crypto(session):
    print("\n₿ Testing Crypto Loader...")
    loader = CryptoLoader(session)
    symbol = "BTC/KRW"
    
    # Fetch live
    await loader.fetch_latest_price(symbol)
    
    # Read back
    latest = await loader.get_latest_price_from_db(symbol)
    if latest:
        print(f"✅ Crypto Success: {latest.symbol} = {latest.close} KRW")
    else:
        print("❌ Crypto Failed")

async def main():
    session = AsyncSessionLocal()
    try:
        await test_us(session)
        await test_crypto(session)
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
