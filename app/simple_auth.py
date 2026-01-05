"""
Simple Authentication + Rate Limiting

Checks two things:
1. API key matches the secret in .env
2. Client IP hasn't exceeded rate limit
"""
from fastapi import Request, HTTPException
from datetime import datetime
from collections import defaultdict
from app.config import settings

# In-memory storage for rate limiting
# Format: {client_ip: [timestamp1, timestamp2, ...]}
request_history = defaultdict(list)


def check_auth_and_rate_limit(request: Request):
    """
    Validate API key and enforce rate limits
    
    Raises:
        HTTPException: 401 if invalid API key, 429 if rate limit exceeded
    """
    
    # ===== Authentication Check =====
    # Get API key from header
    api_key = request.headers.get("x-api-key", "")
    
    # Verify against secret (if configured)
    if settings.API_SECRET:  # Only check if API_SECRET is set
        if api_key != settings.API_SECRET:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key. Add 'x-api-key' header with correct value."
            )
    
    # ===== Rate Limit Check =====
    # Get client IP address
    client_ip = request.client.host if request.client else "unknown"
    
    # Get request history for this IP
    now = datetime.now()
    history = request_history[client_ip]
    
    # Clean up requests older than 1 hour
    history[:] = [
        timestamp for timestamp in history 
        if (now - timestamp).total_seconds() < 3600
    ]
    
    # Check if limit exceeded
    if len(history) >= settings.RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.RATE_LIMIT_PER_HOUR} requests per hour"
        )
    
    # Record this request
    history.append(now)
