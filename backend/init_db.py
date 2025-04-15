import os
import sys
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine
from app.models.db_models import Base

def init_database():
    # Create database directory if it doesn't exist
    db_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(db_dir, exist_ok=True)

    # Create SQLite database
    engine = create_engine('sqlite:///./trading.db')
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Run migrations
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database() 