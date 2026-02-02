
import ccxt
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from backend_fastapi.db.models import AssetPrice

class CryptoLoader:
    def __init__(self, db: AsyncSession):
        self.db = db
        # Initialize exchange in sync mode as per test findings
        self.exchange = ccxt.upbit({
            'enableRateLimit': True,
            'timeout': 10000,
        })

    async def fetch_latest_price(self, symbol: str):
        """
        Fetches REAL-TIME current price.
        Symbol example: 'BTC/KRW'
        """
        try:
            # Run sync CCXT call in a separate thread to avoid blocking async loop
            ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
            
            if not ticker:
                return False

            price = ticker['last']
            ts = datetime.utcnow() # Universal time for DB
            
            # Save to DB (Hot Cache style)
            price_entry = AssetPrice(
                symbol=symbol,
                asset_type="CRYPTO",
                timestamp=ts,
                open=ticker.get('open'),
                high=ticker.get('high'),
                low=ticker.get('low'),
                close=price,
                volume=ticker.get('baseVolume'), # 24h volume
                source="Upbit"
            )
            self.db.add(price_entry)
            await self.db.commit()
            
            # print(f"✅ [Crypto] Fetched {symbol}: {price}")
            return price_entry
            
        except Exception as e:
            print(f"❌ [Crypto] Error loading {symbol}: {e}")
            return None

    async def get_latest_price_from_db(self, symbol: str):
        result = await self.db.execute(
            select(AssetPrice)
            .where(AssetPrice.symbol == symbol)
            .where(AssetPrice.asset_type == "CRYPTO")
            .order_by(AssetPrice.timestamp.desc())
            .limit(1)
        )
        return result.scalars().first()
