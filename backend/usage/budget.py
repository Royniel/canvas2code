import logging
import os
from decimal import Decimal
from typing import Optional

from .tracker import tracker

logger = logging.getLogger("canvas2code.budget")


# Monthly per-provider budget in USD. None = unlimited (free tier).
# Adjust these as monthly billing reality demands.
BUDGET_LIMITS: dict[str, Optional[Decimal]] = {
    "gemini": Decimal("10"),
    "groq": None,  # free tier — no monthly limit, tokens still tracked
    "openrouter": Decimal("5"),
    "judge": Decimal("10"),  # judge uses gemini-2.5-flash
}

# Hard daily cap across ALL providers — safety net against runaway loops.
# Override with the DAILY_BUDGET_USD env var.
DAILY_CAP = Decimal(os.environ.get("DAILY_BUDGET_USD", "2"))


async def check_budget(provider: str) -> bool:
    """Returns True if the provider can be used; False if any limit is hit.

    Two checks, in order:
    1. Global daily cap (DAILY_CAP) — refuses ALL providers if today's total spend
       is at or above the cap.
    2. Per-provider monthly limit (BUDGET_LIMITS[provider]) — refuses just that
       provider if its month-to-date spend is at or above its limit.

    Providers with `None` in BUDGET_LIMITS bypass check #2 (free tier).
    """
    daily = await tracker.get_daily_total()
    if daily >= DAILY_CAP:
        logger.warning(
            "Daily budget cap reached: $%s >= $%s; refusing %s",
            daily,
            DAILY_CAP,
            provider,
        )
        return False

    limit = BUDGET_LIMITS.get(provider)
    if limit is None:
        return True

    monthly = await tracker.get_monthly_spend(provider)
    if monthly >= limit:
        logger.warning(
            "Monthly budget for %s reached: $%s >= $%s",
            provider,
            monthly,
            limit,
        )
        return False
    return True
