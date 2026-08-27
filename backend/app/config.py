from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    APP_NAME: str = "OCRA - Meeting-to-Jira Engineering Execution Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ocra.db"
    
    # LLM Settings
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEFAULT_LLM_MODEL: str = "gemini-2.5-flash"
    
    # Jira Cloud OAuth 2.0 (3LO) Settings
    JIRA_CLIENT_ID: Optional[str] = None
    JIRA_CLIENT_SECRET: Optional[str] = None
    JIRA_REDIRECT_URI: str = "http://localhost:8000/api/integrations/jira/callback"
    JIRA_CLOUD_ID: Optional[str] = None
    JIRA_SITE_URL: Optional[str] = None
    
    # GitHub Issues Connector
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_DEFAULT_REPO: Optional[str] = None  # "owner/repo"
    GITHUB_API_BASE: str = "https://api.github.com"

    # Google Calendar Connector (OAuth2 / 3LO — same pattern as Jira)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/integrations/calendar/callback"
    GOOGLE_OAUTH_ACCESS_TOKEN: Optional[str] = None
    GOOGLE_CALENDAR_ID: str = "primary"
    GOOGLE_CALENDAR_API_BASE: str = "https://www.googleapis.com/calendar/v3"

    # Adapter Mode
    USE_MOCK_JIRA: bool = True
    USE_MOCK_GITHUB: bool = True
    USE_MOCK_CALENDAR: bool = True
    
    # Policy Defaults
    DEFAULT_PROJECT_KEY: str = "PAY"
    AUTO_EXECUTE_ENABLED: bool = True
    MIN_CONFIDENCE_THRESHOLD: float = 0.80
    KILL_SWITCH_ACTIVE: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"]


settings = Settings()
