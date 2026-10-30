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

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
