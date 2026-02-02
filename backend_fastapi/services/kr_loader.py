import FinanceDataReader as fdr
from sqlalchemy.ext.asyncio import AsyncSession
from backend_fastapi.db.models import AssetPrice
from sqlalchemy import select
from datetime import datetime
import asyncio

class KRStockLoader:
    async def fetch_and_save(self, symbol: str, db: AsyncSession):
        # 1. Check DB first (Cache Layer)
        # For simplicity, we just fetch latest for now to verify logic
        try:
            # FDR fetch (Sync) -> Async wrapper
            df = await asyncio.to_thread(fdr.DataReader, symbol)
            if df.empty:
                return None
                
            latest = df.iloc[-1]
            price = float(latest['Close'])
            
            # Save to DB (optional for MVP, but good for history)
            return {"symbol": symbol, "price": price, "timestamp": datetime.now()}
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
