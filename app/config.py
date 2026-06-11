from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration for local, Render, and AWS Lambda deployments."""

    # API
    API_TITLE: str = "Patent AI Translation Platform"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    LLM_PROVIDER: str = "gemini"

    # LLM providers
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./patent_review.db"

    # Chroma vector index
    CHROMA_DB_DIR: str = "./aws_chroma_db"
    CHROMA_COLLECTION_NAME: str = "patent_translations_aws"
    VECTOR_EMBEDDING_DIM: int = 384
    ENABLE_VECTOR_RAG: bool = True

    # Security
    SECRET_KEY: str = "secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_SECRET: str = ""

    # Guardrails
    RATE_LIMIT_PER_HOUR: int = 5
    RATE_LIMIT_PER_MINUTE: int = 10
    MAX_INPUT_CHARS: int = 3000
    DAILY_COST_LIMIT_USD: float = 1.0
    DISABLE_CLAUDE: bool = True
    PERSIST_TRANSLATIONS: bool = False

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # GitHub (optional legacy fields)
    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        if not self.ALLOWED_ORIGINS or self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
