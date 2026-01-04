from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration"""
    
    # API
    API_TITLE: str = "AI Code Review Assistant"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Claude API
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    
    # Database
    DATABASE_URL: str = "sqlite:///./patent_ai.db"
    
    # Security
    SECRET_KEY: str = "secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10
    
    # GitHub (optional)
    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()