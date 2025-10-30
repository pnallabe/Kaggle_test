"""
Configuration settings for the API
"""

import os
from typing import List

class Settings:
    """Application settings from environment variables"""
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # GCP
    PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    REGION: str = os.getenv("GCP_REGION", "us-central1")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/ai_analyst"
    )
    
    # Redis / Memorystore
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # BigQuery
    BQ_ANALYTICS_DATASET: str = os.getenv("BQ_ANALYTICS_DATASET", "analytics")
    BQ_AUDIT_DATASET: str = os.getenv("BQ_AUDIT_DATASET", "audit")
    
    # GCS
    GCS_ARTIFACTS_BUCKET: str = os.getenv("GCS_ARTIFACTS_BUCKET", "")
    GCS_BACKEND_BUCKET: str = os.getenv("GCS_BACKEND_BUCKET", "")
    
    # Authentication
    IDENTITY_PLATFORM_API_KEY: str = os.getenv("IDENTITY_PLATFORM_API_KEY", "")
    JWT_ALGORITHM: str = "RS256"
    JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8080"
    ).split(",")
    
    # Pub/Sub
    PUBSUB_JOB_TOPIC: str = os.getenv("PUBSUB_JOB_TOPIC", "ai-data-analyst-jobs")
    
    # Security
    SECRET_MANAGER_PROJECT: str = os.getenv("SECRET_MANAGER_PROJECT", PROJECT_ID)
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "1000"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "3600"))  # 1 hour

settings = Settings()
