import os
from pydantic import BaseModel, Field

class Settings(BaseModel):
    postgres_host: str = Field(default_factory=lambda: os.getenv("POSTGRES_HOST", "postgres"))
    postgres_port: int = Field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")))
    postgres_db: str = Field(default_factory=lambda: os.getenv("POSTGRES_DB", "easpayments"))
    postgres_user: str = Field(default_factory=lambda: os.getenv("POSTGRES_USER", "easuser"))
    postgres_password: str = Field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "easpass"))

    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379/0"))

    ledger_grpc_target: str = Field(default_factory=lambda: os.getenv("LEDGER_GRPC_TARGET", "localhost:50051"))
    notify_grpc_target: str = Field(default_factory=lambda: os.getenv("NOTIFY_GRPC_TARGET", "notifications:50052"))

    api_host: str = Field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))

settings = Settings()
