import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///uam.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "artifacts")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "my-secret-key-for-uam")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
    USE_MINIO: bool = os.getenv("USE_MINIO", "false").lower() == "true"
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:8080")
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_HOSTS: str = os.getenv("ALLOWED_HOSTS", "*")

    # Supabase Auth configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    USE_SUPABASE_AUTH: bool = os.getenv("USE_SUPABASE_AUTH", "false").lower() == "true"

    # Rate limiting configuration
    RATE_LIMIT_REGISTER: str = os.getenv("RATE_LIMIT_REGISTER", "10/minute")
    RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "15/minute")
    RATE_LIMIT_GENERAL: str = os.getenv("RATE_LIMIT_GENERAL", "100/minute")

    def validate_production(self) -> None:
        """Fail fast on missing required environment variables in production."""
        if self.ENVIRONMENT != "production":
            return

        required = {
            "DATABASE_URL": self.DATABASE_URL,
            "REDIS_URL": self.REDIS_URL,
            "SECRET_KEY": self.SECRET_KEY,
        }

        missing = [k for k, v in required.items() if not v or v in ("", "changeme", "your-super-secret-key-change-this-in-production")]
        if missing:
            raise RuntimeError(
                f"Missing or insecure required environment variables in production: {', '.join(missing)}"
            )

        # Warn about insecure defaults
        if self.SECRET_KEY == "my-secret-key-for-uam":
            raise RuntimeError("SECRET_KEY must be changed from the default value in production")

        if self.ALLOWED_HOSTS == "*":
            raise RuntimeError("ALLOWED_HOSTS must be set to specific hosts in production (not '*')")

        # Supabase Auth validation
        if self.USE_SUPABASE_AUTH:
            supabase_required = {
                "SUPABASE_URL": self.SUPABASE_URL,
                "SUPABASE_ANON_KEY": self.SUPABASE_ANON_KEY,
                "SUPABASE_SERVICE_ROLE_KEY": self.SUPABASE_SERVICE_ROLE_KEY,
                "SUPABASE_JWT_SECRET": self.SUPABASE_JWT_SECRET,
            }
            supabase_missing = [k for k, v in supabase_required.items() if not v]
            if supabase_missing:
                raise RuntimeError(
                    f"Missing Supabase Auth environment variables: {', '.join(supabase_missing)}"
                )


settings = Settings()

# Validate on import in production
settings.validate_production()
