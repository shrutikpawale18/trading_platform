from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# Remove unused column/type imports if models are removed
# from sqlalchemy import Column, String, Float, DateTime, Enum, Boolean, ForeignKey
# from sqlalchemy.dialects.sqlite import JSON
import os
from dotenv import load_dotenv
from pathlib import Path
# Import the single source of truth for Base
from app.models.db_models import Base

load_dotenv()

# Define the base directory of the backend app directory
APP_DIR = Path(__file__).resolve().parent
# Go up one level to get the backend directory
BACKEND_DIR = APP_DIR.parent

# Construct the absolute path to the database file within the backend directory
DEFAULT_DB_PATH = BACKEND_DIR / "trading.db"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

print(f"--- Using database at: {SQLALCHEMY_DATABASE_URL} ---")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} # Keep check_same_thread for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Remove Base definition - it's imported now
# Base = declarative_base()

# Remove redundant model definitions
# class Algorithm(Base): ...
# class Position(Base): ...
# class Trade(Base): ...
# class Signal(Base): ...

def get_db():
    print("--- Entering get_db ---")
    db = SessionLocal()
    print("--- SessionLocal() created db object ---")
    try:
        print("--- Yielding db from get_db ---")
        yield db
        print("--- Returned from yield in get_db ---")
    except Exception as e:
        print(f"!!! Exception in get_db try block: {e}")
        raise # Re-raise the exception
    finally:
        print("--- Closing db in get_db finally block ---")
        db.close()
        print("--- db closed in get_db finally block ---")

# Remove init_db from here, it belongs in its own script (e.g., app/init_db.py)
# def init_db():
#     Base.metadata.create_all(bind=engine) 