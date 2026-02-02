
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend_fastapi.db.session import get_db
from backend_fastapi.services.crypto_loader import CryptoLoader
import datetime

router = APIRouter()

@router.get("/latest/{symbol}")
async def get_latest_crypto(symbol: str, db: AsyncSession = Depends(get_db)):
    """
    Get real-time crypto price.
    Always fetches fresh data from exchange (0.1s latency acceptable for Crypto).
    """
    # Note: Symbol must be URL encoded if it contains '/', but FastAPI handles it mostly if path param.
    # Better: user passes "BTC-KRW" or simple slug, we convert.
    # For now, assume client sends "BTC-KRW" and we convert to "BTC/KRW" if needed, 
    # or just use "BTC/KRW" directly (FastAPI handles '/' in path if configured, else use Query param).
    # Let's use Query param for safety if symbol has slash, OR just standard "BTC-KRW" convention.
    
    # Actually, let's assume input is "BTC-KRW" and we replace.
    real_symbol = symbol.replace("-", "/")
    
    loader = CryptoLoader(db)
    
    # Live Fetch (Hot Path)
    data = await loader.fetch_latest_price(real_symbol)
    
    if not data:
        raise HTTPException(status_code=404, detail="Crypto data not found")
        
    return {
        "symbol": data.symbol,
        "price": data.close,
        "volume": data.volume,
        "timestamp": data.timestamp,
        "source": data.source
    }
