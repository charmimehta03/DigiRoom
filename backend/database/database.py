import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------
# DATABASE_URL is set on the hosting platform (Postgres, e.g. Neon).
# If it is not set, we fall back to the local SQLite file so that
# running on your own laptop works exactly as before.
# ---------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./digiroom.db")

# Neon / Render / Heroku often give "postgres://..." — SQLAlchemy needs
# "postgresql+psycopg2://..."
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_size=20,
        max_overflow=40,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
    )
else:
    # Free Postgres tiers allow few connections -> keep the pool small.
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=300,      # free DBs close idle connections quickly
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
