from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
    # Encryption (for API keys)
    ENCRYPTION_KEY: str
    
    # S3 (note images)
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    S3_BUCKET_NAME: str
    
    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # Billing
    PADDLE_API_KEY: str
    TAP_API_KEY: str
    
    # AI
    ANTHROPIC_API_KEY: str
    
    # Email
    SENDGRID_API_KEY: str
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
