"""JWT token generation and verification for Fortress Director API."""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
SECRET_KEY = os.getenv(
    "FORTRESS_JWT_SECRET", "dev-secret-key-change-in-production-12345678"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("FORTRESS_JWT_EXPIRE_MIN", "1440"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    session_id: str, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token for a session.

    Args:
        session_id: Unique session identifier
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta
    to_encode: Dict[str, Any] = {
        "sub": session_id,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Session ID if valid, None if invalid

    Raises:
        JWTError: If token is malformed or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        session_id: str = payload.get("sub")
        if session_id is None:
            return None
        return session_id
    except JWTError:
        return None


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token without verification.

    Args:
        token: JWT token string

    Returns:
        Token payload if decodable, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)
