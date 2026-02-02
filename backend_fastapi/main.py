from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend_fastapi.core.config import settings
from backend_fastapi.api.v1.api import api_router
from backend_fastapi.db.session import engine, Base
import asyncio

# Database Init
async def init_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_tables()
    print("🚀 Backend Started & DB Initialized")
    yield
    print("🛑 Backend Stopped")

app = FastAPI(title="InsightStream Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow Streamlit (localhost)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)

@app.get("/health")
def health_check():
    return {"status": "ok", "latency": "zero"}
