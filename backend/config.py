import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "banner-ar-poc-dev")
    DB_URL = os.environ.get("DB_URL", "sqlite:///logs/banner_ar.db")
    DB_SCHEMA = os.environ.get("DB_SCHEMA", "banner_ar_poc")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
