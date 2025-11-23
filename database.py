from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_db_url, normalize_db_url, settings

# ASSUMPTION: Using sync engine for now; can be swapped to async engine when persistence is added.
DATABASE_URL = normalize_db_url(get_db_url(settings))

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
