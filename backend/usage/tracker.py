import logging
from decimal import Decimal
from typing import Optional

from psycopg_pool import AsyncConnectionPool

from .pricing import calculate_cost

logger = logging.getLogger("canvas2code.usage")


USAGE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    node_type TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd DECIMAL(10, 6) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_logs_provider_created
    ON usage_logs(provider, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created
    ON usage_logs(created_at);
"""


class UsageTracker:
    def __init__(self):
        self._pool: Optional[AsyncConnectionPool] = None

    def bind_pool(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def setup_schema(self):
        if self._pool is None:
            return
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(USAGE_TABLE_DDL)

    async def log_usage(
        self,
        provider: str,
        model: str,
        node_type: str,
        usage_dict: dict,
        thread_id: str,
    ):
        if self._pool is None:
            return
        try:
            input_tokens = int(usage_dict.get("input_tokens", 0) or 0)
            output_tokens = int(usage_dict.get("output_tokens", 0) or 0)
            cost = calculate_cost(provider, model, input_tokens, output_tokens)

            async with self._pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO usage_logs (
                            thread_id, provider, model, node_type,
                            input_tokens, output_tokens, estimated_cost_usd
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            thread_id or "",
                            provider,
                            model,
                            node_type,
                            input_tokens,
                            output_tokens,
                            cost,
                        ),
                    )
        except Exception:
            logger.exception("Failed to log usage for %s/%s", provider, model)

    async def get_monthly_spend(self, provider: str) -> Decimal:
        if self._pool is None:
            return Decimal("0")
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT COALESCE(SUM(estimated_cost_usd), 0)
                        FROM usage_logs
                        WHERE provider = %s
                          AND created_at >= date_trunc('month', NOW())
                        """,
                        (provider,),
                    )
                    row = await cur.fetchone()
                    return Decimal(row[0]) if row else Decimal("0")
        except Exception:
            logger.exception("Failed to get monthly spend for %s", provider)
            return Decimal("0")

    async def get_daily_total(self) -> Decimal:
        if self._pool is None:
            return Decimal("0")
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT COALESCE(SUM(estimated_cost_usd), 0)
                        FROM usage_logs
                        WHERE created_at >= date_trunc('day', NOW())
                        """
                    )
                    row = await cur.fetchone()
                    return Decimal(row[0]) if row else Decimal("0")
        except Exception:
            logger.exception("Failed to get daily total")
            return Decimal("0")

    async def get_daily_call_count(self) -> int:
        if self._pool is None:
            return 0
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM usage_logs
                        WHERE created_at >= date_trunc('day', NOW())
                        """
                    )
                    row = await cur.fetchone()
                    return int(row[0]) if row else 0
        except Exception:
            logger.exception("Failed to get daily call count")
            return 0

    async def get_recent_generations(self, limit: int = 10) -> list[dict]:
        if self._pool is None:
            return []
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT thread_id,
                               MAX(created_at) AS last_at,
                               SUM(estimated_cost_usd) AS total_cost,
                               COUNT(*) AS calls
                        FROM usage_logs
                        GROUP BY thread_id
                        ORDER BY last_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                    rows = await cur.fetchall()
                    return [
                        {
                            "thread_id": r[0],
                            "last_at": r[1].isoformat() if r[1] else None,
                            "total_cost_usd": float(r[2]) if r[2] is not None else 0.0,
                            "calls": int(r[3]) if r[3] is not None else 0,
                        }
                        for r in rows
                    ]
        except Exception:
            logger.exception("Failed to get recent generations")
            return []


tracker = UsageTracker()
