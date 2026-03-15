"""Database configuration for the leaf disease application."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite database stored inside the project folder.
DATABASE_URL = "sqlite:///./leaf_disease_app.db"

# check_same_thread=False is needed for SQLite when used with FastAPI.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# SessionLocal creates database sessions when needed.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is used by SQLAlchemy models.
Base = declarative_base()
