from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, engine
# Remove the direct import of User, it's loaded via Base from db_models
# from app.models.user import User
# Import other models if needed for specific logic here, otherwise Base.metadata.create_all is enough
# from app.models import Trade, Algorithm, Position, Signal

def init_db():
    print(f"--- Using database at: {engine.url} ---") # Added print for confirmation
    # Create all tables defined in Base's metadata
    Base.metadata.create_all(bind=engine)
    print("Database initialized and tables created.")

if __name__ == "__main__":
    # Potentially add logic to check if DB exists or needs reset
    init_db() 