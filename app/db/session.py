import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql"):
    parsed = urllib.parse.urlparse(db_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    query_params.pop("pgbouncer", None)
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    db_url = urllib.parse.urlunparse(parsed._replace(query=new_query))

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Production-ready connection pool settings
engine_kwargs = {"pool_pre_ping": True, "connect_args": connect_args}
if db_url.startswith("postgresql"):
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),  # 30 min
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
    })

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
