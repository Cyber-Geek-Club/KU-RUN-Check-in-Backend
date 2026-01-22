from datetime import datetime, timedelta, timezone
import os
import logging
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET", "change_me_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    # Debug logging
    logger.info(f"[TOKEN] Created access_token:")
    logger.info(f"  - User ID (sub): {data.get('sub')}")
    logger.info(f"  - Now (UTC): {now.isoformat()}")
    logger.info(f"  - Expires (UTC): {expire.isoformat()}")
    logger.info(f"  - Expires in: {expires_minutes} minutes")
    logger.info(f"  - Token prefix: {token[:50]}...")
    
    return token


def create_refresh_token(data: dict, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS):
    """
    Create a refresh token with longer expiry.
    Includes 'type': 'refresh' claim to distinguish from access tokens.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"[TOKEN] Verified access_token successfully:")
        logger.info(f"  - User ID (sub): {payload.get('sub')}")
        logger.info(f"  - Exp claim: {payload.get('exp')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning(f"[TOKEN] Token EXPIRED! Token prefix: {token[:30]}...")
        return None
    except JWTError as e:
        logger.warning(f"[TOKEN] Token verification failed: {e}. Token prefix: {token[:30]}...")
        return None


def verify_refresh_token(token: str):
    """
    Verify a refresh token and ensure it has the 'type': 'refresh' claim.
    Returns the payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Ensure this is a refresh token
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None