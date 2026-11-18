# Settings loaded from environment variables using pydantic-settings
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # LLM configuration
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    # Prompt limits
    PROMPT_MAX_CHARS: int = 24000
    LLM_RATE_LIMIT_WAIT_MAX_SECONDS: int = 20
    # Input limits
    MAX_INPUT_CHARS: int = 200000
    MAX_ANALYSIS_LINES: int = 300
    TOP_PATTERNS: int = 15
    CONTEXT_LINES: int = 5
    RAW_MODE_MAX_CHARS: int = 24000
    # Rate limiting per IP
    RATE_LIMIT_PER_10MIN: int = 10
    # History (DynamoDB) settings
    ENABLE_HISTORY: bool = False
    DYNAMODB_TABLE: str = "log_analyses"
    DYNAMODB_ENDPOINT_URL: str = ""
    APP_AWS_REGION: str = "ap-south-1"
    APP_AWS_ACCESS_KEY_ID: str = ""
    APP_AWS_SECRET_ACCESS_KEY: str = ""
    # LangSmith tracing
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "log-analyzer"
    # CORS origins for dev
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instantiate a single settings object for the app
settings = Settings()
