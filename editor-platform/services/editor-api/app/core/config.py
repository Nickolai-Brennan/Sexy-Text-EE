import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/editor")
API_KEY = os.getenv("API_KEY", "dev-key")

ALLOWED_IFRAME_HOSTS = set(
    h.strip() for h in os.getenv(
        "ALLOWED_IFRAME_HOSTS",
        "youtube.com,www.youtube.com,youtu.be,player.vimeo.com",
    ).split(",") if h.strip()
)
