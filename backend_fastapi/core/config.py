import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "InsightStream"
    API_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite+aiosqlite:///./dashboard.db"

settings = Settings()
