"""
Configuration settings for Tesumi System v2.0
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # App info
    APP_NAME: str = "Tesumi System v2.0 - API版かなた"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Database
    DATABASE_URL: Optional[str] = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "tesumi_db"
    DB_USER: str = "tesumi"
    DB_PASSWORD: str = "tesumi_password"
    
    # Vector database settings
    VECTOR_DIMENSION: int = 384  # Sentence-BERT embedding dimension
    
    # Claude API
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-haiku-20240307"
    CLAUDE_MAX_TOKENS: int = 4096
    
    # Memory settings
    MAX_MEMORY_NODES: int = 10000
    MEMORY_DECAY_FACTOR: float = 0.95
    EMOTION_DIMENSION: int = 2  # Valence-Arousal
    
    # GNN settings
    GNN_HIDDEN_DIM: int = 128
    GNN_NUM_LAYERS: int = 3
    GNN_DROPOUT: float = 0.1
    
    # Embedding model
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @property
    def database_url(self) -> str:
        """Construct database URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
