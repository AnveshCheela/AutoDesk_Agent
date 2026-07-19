import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY: str = os.getenv("GROK_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./data/tickets.db")
    MAX_AGENT_STEPS: int = 5
    TOP_K_RESULTS: int = 3

settings = Settings()
