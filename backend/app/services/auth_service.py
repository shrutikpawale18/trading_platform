from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Algorithm, AlgorithmType
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        
        user = self.db.query(User).filter(User.email == email).first()
        if user is None:
            raise credentials_exception
        return user

    def create_user(self, email: str, password: str) -> User:
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        hashed_password = self.get_password_hash(password)
        user_id = str(uuid.uuid4())
        db_user = User(
            id=user_id,
            email=email,
            hashed_password=hashed_password,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(db_user)
        # Don't commit yet, need to add algorithm first in the same transaction

        # Create a default Algorithm for the new user
        default_algo = Algorithm(
            user_id=user_id,
            symbol="SPY", # Example default symbol
            type=AlgorithmType.MOVING_AVERAGE_CROSSOVER,
            parameters={"short_window": 20, "long_window": 50}, # Example parameters
            is_active=True
        )
        self.db.add(default_algo)

        try:
            self.db.commit() # Commit both user and algorithm
            self.db.refresh(db_user)
            # Optionally refresh the algo too if needed later
            # self.db.refresh(default_algo) 
        except Exception as e:
            self.db.rollback() # Rollback if commit fails
            print(f"!!! Error during user/algo creation commit: {e!r}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to create user and default algorithm."
            )
        
        print(f"--- User {email} created with ID {user_id} and default algorithm ---")
        return db_user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user 