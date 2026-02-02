from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from backend_fastapi.db.session import Base
from datetime import datetime

class AssetPrice(Base):
    __tablename__ = "asset_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True) # e.g. "005930", "AAPL"
    price = Column(Float)
    change = Column(Float) # Change amount
    change_percent = Column(Float) # %
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String) # "FDR", "YF", "CCXT"
    
    __table_args__ = (Index('idx_symbol_timestamp', 'symbol', 'timestamp'),)
