
import pandas as pd
from fredapi import Fred
from sqlalchemy.ext.asyncio import AsyncSession
from backend_fastapi.core.config import settings
from backend_fastapi.db.models import AssetPrice
import asyncio
from datetime import datetime

class FredLoader:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key = settings.FRED_API_KEY
        self.fred = None
        if self.api_key:
            self.fred = Fred(api_key=self.api_key)

    async def fetch_and_save_series(self, series_id: str):
        """
        Fetches macro series (e.g. 'GDP', 'UNRATE', 'DGS10').
        """
        if not self.fred:
            print("⚠️ [Macro] FRED_API_KEY missing.")
            return False
            
        print(f"📥 [Macro] Fetching {series_id}...")
        
        try:
            # Sync call
            series = await asyncio.to_thread(self.fred.get_series, series_id)
            
            if series.empty:
                return False
                
            # Get last 5 data points for efficiency (Macro doesn't update often)
            # Actually, let's just get the latest one for the dashboard snapshot.
            # But the chart needs history. Let's start with last 30 points.
            recent_data = series.tail(30)
            
            count = 0
            for date, value in recent_data.items():
                ts = pd.to_datetime(date).to_pydatetime()
                
                price_entry = AssetPrice(
                    symbol=series_id,
                    asset_type="MACRO",
                    timestamp=ts,
                    close=value, # Macro values stored in Close
                    source="FRED"
                )
                self.db.add(price_entry)
                count += 1
            
            await self.db.commit()
            print(f"✅ [Macro] Saved {count} points for {series_id}")
            return True
            
        except Exception as e:
            print(f"❌ [Macro] Error loading {series_id}: {e}")
            await self.db.rollback()
            return False
