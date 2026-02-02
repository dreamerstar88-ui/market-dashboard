from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend_fastapi.db.session import get_db
from backend_fastapi.services.kr_loader import KRStockLoader
import FinanceDataReader as fdr
import asyncio

router = APIRouter()
kr_loader = KRStockLoader()

@router.get("/latest/{symbol}")
async def get_latest_stock(symbol: str, db: AsyncSession = Depends(get_db)):
    # Simple pass-through for now, optimized later
    data = await kr_loader.fetch_and_save(symbol, db)
    if not data:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return data

@router.get("/history/{symbol}")
async def get_stock_history(symbol: str, days: int = 365):
    # Direct FDR call for history (optimized)
    try:
        df = await asyncio.to_thread(fdr.DataReader, symbol)
        if df.empty:
            return []
            
        # Limit to last N days
        df = df.iloc[-days:]
        df = df.dropna()
        
        # Convert to list of dicts for JSON
        history = []
        for index, row in df.iterrows():
            history.append({
                "time": index.strftime("%Y-%m-%d"),
                "open": row['Open'],
                "high": row['High'],
                "low": row['Low'],
                "close": row['Close'],
                "volume": row['Volume']
            })
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
