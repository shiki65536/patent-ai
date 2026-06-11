"""
Simple Authentication + Rate Limiting + Demo Cost Guardrails.

This is intentionally lightweight because the AWS demo runs on Lambda container.
For a public production app, move rate/cost accounting to DynamoDB or API Gateway usage plans.
"""
from collections import defaultdict
from datetime import date, datetime

from fastapi import HTTPException, Request

from app.config import settings

request_history = defaultdict(list)
_daily_usage = {
    "date": str(date.today()),
    "estimated_cost_usd": 0.0,
}


def check_auth_and_rate_limit(request: Request):
    api_key = request.headers.get("x-api-key", "")

    if settings.API_SECRET and api_key != settings.API_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Add 'x-api-key' header with correct value.",
        )

    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now()
    history = request_history[client_ip]

    history[:] = [
        timestamp for timestamp in history
        if (now - timestamp).total_seconds() < 3600
    ]

    if len(history) >= settings.RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.RATE_LIMIT_PER_HOUR} requests per hour",
        )

    history.append(now)


def validate_translation_input(text: str):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Japanese text is required")

    if len(text) > settings.MAX_INPUT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Input too long. Max {settings.MAX_INPUT_CHARS} characters.",
        )


def assert_provider_allowed(provider: str):
    if provider == "claude" and settings.DISABLE_CLAUDE:
        raise HTTPException(
            status_code=403,
            detail="Claude is disabled for this public demo. Set DISABLE_CLAUDE=false to enable it.",
        )


def check_daily_cost_limit(next_cost_usd: float):
    today = str(date.today())
    if _daily_usage["date"] != today:
        _daily_usage["date"] = today
        _daily_usage["estimated_cost_usd"] = 0.0

    if _daily_usage["estimated_cost_usd"] + next_cost_usd > settings.DAILY_COST_LIMIT_USD:
        raise HTTPException(
            status_code=429,
            detail=f"Daily demo cost limit reached: ${settings.DAILY_COST_LIMIT_USD}",
        )


def record_estimated_cost(cost_usd: float):
    today = str(date.today())
    if _daily_usage["date"] != today:
        _daily_usage["date"] = today
        _daily_usage["estimated_cost_usd"] = 0.0

    _daily_usage["estimated_cost_usd"] += cost_usd


def get_cost_usage():
    return dict(_daily_usage)
