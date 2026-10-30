import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "BitFortress"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+psycopg2://postgres@127.0.0.1:5433/satoshiguard"
    )
    
    # JWT Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "satoshiguard_ultra_secure_jwt_secret_token_production_guard_9281")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Bitcoin Core Regtest RPC
    BITCOIN_RPC_HOST: str = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1")
    BITCOIN_RPC_PORT: int = int(os.getenv("BITCOIN_RPC_PORT", "18443"))
    BITCOIN_RPC_USER: str = os.getenv("BITCOIN_RPC_USER", "satoshiguard")
    BITCOIN_RPC_PASSWORD: str = os.getenv("BITCOIN_RPC_PASSWORD", "guardvaultpassword123")
    BITCOIN_WALLET_NAME: str = os.getenv("BITCOIN_WALLET_NAME", "satoshiguard_treasury")
    
    # Regtest block explorer / mock network options
    NETWORK: str = "regtest"

    # Environment mode: "development" | "production" | "testing"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    def validate_production_configuration(self):
        """
        Enforces strict security constraints when running in production:
        Rejects insecure fallback secrets and default development credentials.
        """
        if self.ENVIRONMENT.lower() == "production":
            insecure_secret_patterns = [
                "satoshiguard_ultra_secure_jwt",
                "default",
                "secret",
                "password",
                "changeme",
                "bitfortress"
            ]
            if any(p in self.SECRET_KEY.lower() for p in insecure_secret_patterns) or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "FATAL SECURITY VIOLATION: Production mode requires a strong, random SECRET_KEY (min 32 chars) supplied via environment variable."
                )
            if self.BITCOIN_RPC_PASSWORD in ["guardvaultpassword123", "password", "123456", "admin"]:
                raise ValueError(
                    "FATAL SECURITY VIOLATION: Production mode requires a secure non-default BITCOIN_RPC_PASSWORD."
                )

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
settings.validate_production_configuration()
