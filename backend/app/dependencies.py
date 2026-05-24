"""
FastAPI dependencies:
  - get_current_user   — validates JWT, returns Supabase user object
  - get_db_client      — returns a user-scoped Supabase client
  - check_rate_limit   — in-memory sliding-window rate limiter (5 entries/hour)
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException
from supabase import Client

from app.database import get_supabase_admin, get_user_client

# Initialised once at startup — used only for auth.get_user()
_admin = get_supabase_admin()

# In-memory rate-limit state: { user_id: [timestamp, ...] }
_entry_timestamps: dict[str, list[datetime]] = defaultdict(list)


def _extract_token(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    return authorization.split(" ", 1)[1]


async def get_current_user(authorization: str = Header(...)):
    """Validate the Supabase JWT and return the authenticated user object."""
    token = _extract_token(authorization)
    try:
        result = _admin.auth.get_user(token)
        if not result.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return result.user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_db_client(authorization: str = Header(...)) -> Client:
    """Return a user-scoped Supabase client (respects RLS)."""
    token = _extract_token(authorization)
    return get_user_client(token)


def check_rate_limit(user_id: str) -> None:
    """Sliding-window rate limit: max 5 entry submissions per user per hour."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=1)
    _entry_timestamps[user_id] = [
        t for t in _entry_timestamps[user_id] if t > window_start
    ]
    if len(_entry_timestamps[user_id]) >= 5:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: maximum 5 entries per hour",
        )
    _entry_timestamps[user_id].append(now)
