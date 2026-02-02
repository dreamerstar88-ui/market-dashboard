
import FinanceDataReader as fdr
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from backend_fastapi.db.models import AssetPrice

class USStockLoader:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def fetch_and_save_daily(self, symbol: str, days: int = 365):
        """
        Fetches daily OHLCV from FDR and saves to DB.
        Symbol should probably be full ticker like 'NASDAQ:AAPL' or just 'AAPL'?
        FDR usually requires exchange prefix for US widely, but 'AAPL' often defaults to NASDAQ in some utils.
        We will assume the caller provides the correct FDR-compatible ticker (e.g. 'NASDAQ:AAPL').
        """
        print(f"📥 [US] Fetching {symbol} for last {days} days...")
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            # Sync call to FDR
            df = fdr.DataReader(symbol, start_date)
            if df.empty:
                print(f"⚠️  [US] No data found for {symbol}")
                return False
                
            count = 0
            for index, row in df.iterrows():
                ts = index.to_pydatetime()
                
                # Create AssetPrice entry
                price_entry = AssetPrice(
                    symbol=symbol,
                    asset_type="STOCK_US",
                    timestamp=ts,
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=row.get('Volume', 0),
                    source="FDR"
                )
                self.db.add(price_entry)
                count += 1
            
            await self.db.commit()
            print(f"✅ [US] Saved {count} rows for {symbol}")
            return True
            
        except Exception as e:
            print(f"❌ [US] Error loading {symbol}: {e}")
            await self.db.rollback()
            return False

    async def get_latest_price(self, symbol: str):
        result = await self.db.execute(
            select(AssetPrice)
            .where(AssetPrice.symbol == symbol)
            .where(AssetPrice.asset_type == "STOCK_US")
            .order_by(AssetPrice.timestamp.desc())
            .limit(1)
        )
        return result.scalars().first()
