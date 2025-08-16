import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///db.sqlite3"
    
    # Telegram
    BOT_TOKEN: str = ""
    WEBAPP_URL: str = "https://frontend-delta-sandy-58.vercel.app"
    BACKEND_URL: str = "http://localhost:8000"
    
    # Google Apps Script
    GOOGLE_APPS_SCRIPT_URL: str = "https://script.google.com/macros/s/AKfycbx6Tl9msvSJFsYqr2ZSpZa0We5-pf_q5q0vr5g33tPU8huEX3Lrys97E0brARF8ahnJ/exec"
    
    # Admin IDs (comma-separated string from env)
    ADMIN_IDS: List[int] = []
    
    # CORS - для GitHub Codespaces разрешаем все домены
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # App settings
    MAX_STOCKS_PER_USER: int = 5
    FREE_HOOKAH_TITLE: str = "Бесплатный кальян"
    PAID_HOOKAH_TITLE: str = "Платный кальян"
    
    # WebApp settings
    WEBAPP_DOMAIN: str = "frontend-delta-sandy-58.vercel.app"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse admin IDs from comma-separated string
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            try:
                self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
            except ValueError:
                print("Warning: Invalid ADMIN_IDS format. Expected comma-separated integers.")
                self.ADMIN_IDS = []
        
        # Auto-detect backend URL for GitHub Codespaces
        if "github.dev" in os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", ""):
            self.BACKEND_URL = f"https://{os.getenv('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN')}"
        elif "CODESPACE_NAME" in os.environ:
            self.BACKEND_URL = f"https://{os.getenv('CODESPACE_NAME')}-{os.getenv('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', '8000.app.github.dev')}"


# Global settings instance
settings = Settings()
