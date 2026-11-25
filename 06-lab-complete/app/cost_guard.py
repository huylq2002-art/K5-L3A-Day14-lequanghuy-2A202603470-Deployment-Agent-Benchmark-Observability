"""Ngân sách chung của agent, cộng dồn theo kỳ UTC trong Redis."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from .config import settings
from .redis_client import r

# Giá USD / 1K tokens (tham khảo gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _budget_period(now: datetime) -> tuple[str, datetime, float]:
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if settings.daily_budget_usd is not None:
        return (
            f"agent:cost:day:{now.date()}",
            midnight + timedelta(days=1),
            settings.daily_budget_usd,
        )

    first_of_month = midnight.replace(day=1)
    next_month = (first_of_month + timedelta(days=32)).replace(day=1)
    return (
        f"agent:cost:month:{now:%Y-%m}",
        next_month,
        settings.monthly_budget_usd,
    )


def check_budget() -> None:
    key, _, budget = _budget_period(datetime.now(timezone.utc))
    spent = float(r.get(key) or 0)
    if spent >= budget:
        raise HTTPException(status_code=402, detail="LLM budget exhausted")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    key, expires_at, _ = _budget_period(datetime.now(timezone.utc))
    cost = (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000
    with r.pipeline() as pipe:
        pipe.incrbyfloat(key, cost)
        pipe.expireat(key, expires_at)
        pipe.execute()
    return cost
