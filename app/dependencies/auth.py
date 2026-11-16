from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session as DbSession
from app.db.session import get_db
from app.db.models import User
from app.config import settings
from app.schemas.auth import TokenData
import httpx
import time

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Cache for Supabase JWKS
_supabase_jwks_cache = {"keys": None, "fetched_at": 0}


async def _fetch_supabase_jwks() -> dict:
    """Fetch Supabase JWKS with caching (5 minute TTL)."""
    now = time.time()
    if _supabase_jwks_cache["keys"] and (now - _supabase_jwks_cache["fetched_at"]) < 300:
        return _supabase_jwks_cache["keys"]

    jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _supabase_jwks_cache["keys"] = resp.json()
        _supabase_jwks_cache["fetched_at"] = now
        return _supabase_jwks_cache["keys"]


def _verify_supabase_jwt(token: str) -> TokenData:
    """Verify a Supabase JWT using the service role secret or JWKS."""
    try:
        # First try decoding with the JWT secret (symmetric HS256)
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        email = payload.get("email") or payload.get("sub")
        if not email:
            raise JWTError("No email/sub in token")
        return TokenData(email=str(email))
    except JWTError:
        pass

    # Fallback: try JWKS endpoint (asymmetric RS256)
    try:
        import asyncio
        jwks = asyncio.get_event_loop().run_until_complete(_fetch_supabase_jwks())
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise JWTError("No matching key in JWKS")
        payload = jwt.decode(
            token,
            key,
            algorithms=[unverified.get("alg", "RS256")],
            options={"verify_aud": False},
        )
        email = payload.get("email") or payload.get("sub")
        if not email:
            raise JWTError("No email/sub in token")
        return TokenData(email=str(email))
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Supabase credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _verify_custom_jwt(token: str) -> TokenData:
    """Verify a custom UAM JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        return TokenData(email=email)
    except JWTError:
        raise credentials_exception


def get_current_user(token: str = Depends(oauth2_scheme), db: DbSession = Depends(get_db)):
    if settings.USE_SUPABASE_AUTH:
        token_data = _verify_supabase_jwt(token)
    else:
        token_data = _verify_custom_jwt(token)

    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Enforce Row-Level Security (RLS) policies on PostgreSQL connection
    if db.bind.dialect.name == "postgresql":
        import sqlalchemy as sa
        try:
            db.execute(sa.text("SET LOCAL app.current_user_id = :user_id;"), {"user_id": str(user.id)})
            db.execute(sa.text("SET LOCAL app.user_role = :role;"), {"role": str(user.role)})
        except Exception:
            pass

    return user
