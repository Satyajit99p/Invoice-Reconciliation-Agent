"""
Configuration management for the chat interface.
Uses environment variables with sensible defaults.
"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000"

    # Application
    APP_NAME: str = "Invoice Chat Interface"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # File Upload
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    ALLOWED_FILE_TYPES: List[str] = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.ms-excel",  # .xls
        "text/csv",  # .csv
        "application/pdf",  # .pdf
    ]
    ALLOWED_FILE_EXTENSIONS: List[str] = [".xlsx", ".xls", ".csv", ".pdf"]
    
    # Session Management
    SESSION_TIMEOUT_HOURS: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    SESSION_CLEANUP_INTERVAL: int = int(os.getenv("SESSION_CLEANUP_INTERVAL", "3600"))  # 1 hour
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_DEFAULT_MODEL: str = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    
    # External Model APIs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "") 
    
    # Model Configuration
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "llama3.2")
    ENABLE_CLOUD_MODELS: bool = os.getenv("ENABLE_CLOUD_MODELS", "false").lower() == "true"
    MODEL_FALLBACK_ENABLED: bool = os.getenv("MODEL_FALLBACK_ENABLED", "true").lower() == "true"
    
    # Supabase (inherited from existing setup)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Database connection settings (if using direct PostgreSQL)
    SUPABASE_DB_HOST: str = os.getenv("SUPABASE_DB_HOST", "")
    SUPABASE_DB_PORT: str = os.getenv("SUPABASE_DB_PORT", "5432")
    SUPABASE_DB_NAME: str = os.getenv("SUPABASE_DB_NAME", "")
    SUPABASE_DB_USER: str = os.getenv("SUPABASE_DB_USER", "")
    SUPABASE_DB_PASSWORD: str = os.getenv("SUPABASE_DB_PASSWORD", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT.lower() in ["development", "dev", "local"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() in ["production", "prod"]
    
    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.SUPABASE_URL and self.SUPABASE_KEY)
    
    @property
    def ollama_configured(self) -> bool:
        """Check if Ollama is configured."""
        return bool(self.OLLAMA_BASE_URL)
    
    @property
    def openai_configured(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.OPENAI_API_KEY)
    
    @property
    def anthropic_configured(self) -> bool:
        """Check if Anthropic is configured."""
        return bool(self.ANTHROPIC_API_KEY)
    
    class Config:
        # Look for .env file in the parent directory (project root)
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
        case_sensitive = True
        extra = 'ignore'

# Global settings instance
settings = Settings()


def get_upload_path(session_id: str, filename: str) -> str:
    """Generate upload path for a file."""
    import os
    upload_dir = os.path.join(settings.UPLOAD_DIR, session_id)
    os.makedirs(upload_dir, exist_ok=True)
    return os.path.join(upload_dir, filename)


def get_available_models() -> dict:
    """Get list of available models based on configuration."""
    models = {
        "ollama": [],
        "openai": [],
        "anthropic": []
    }
    
    # Ollama models (check what's available)
    if settings.ollama_configured:
        try:
            import ollama
            ollama_models = ollama.list()
            models["ollama"] = [model["name"] for model in ollama_models.get("models", [])]
        except Exception:
            models["ollama"] = [settings.OLLAMA_DEFAULT_MODEL]  # Fallback
    
    # OpenAI models
    if settings.openai_configured:
        models["openai"] = ["gpt-5.5 "]
    
    # Anthropic models  
    if settings.anthropic_configured:
        models["anthropic"] = ["claude-haiku-4-5", " claude-sonnet-4-5 ", " claude-sonnet-4-6"]
    
    return models