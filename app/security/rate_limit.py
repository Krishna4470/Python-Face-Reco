from fastapi import Request, HTTPException, status
import time
from collections import defaultdict
from app.config import settings

# Store timestamps of requests per IP
# Format: { "ip_address": [timestamp1, timestamp2, ...] }
_rate_limit_data = defaultdict(list)

def get_client_ip(request: Request) -> str:
    """Extract client IP, respecting proxies"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def check_rate_limit(request: Request):
    """
    FastAPI dependency to limit requests to LIVENESS_MAX_ATTEMPTS_PER_MINUTE.
    Cleans up old timestamps automatically.
    """
    ip = get_client_ip(request)
    now = time.time()
    
    # Get current timestamps for this IP
    timestamps = _rate_limit_data[ip]
    
    # Remove timestamps older than 60 seconds
    timestamps = [t for t in timestamps if now - t < 60]
    
    if len(timestamps) >= settings.LIVENESS_MAX_ATTEMPTS_PER_MINUTE:
        # Too many requests
        _rate_limit_data[ip] = timestamps # Update dict with cleaned list
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )
        
    # Add current request
    timestamps.append(now)
    _rate_limit_data[ip] = timestamps
    return True
