from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any

from sqlalchemy import text

from app.core.database_pool import db_pool

CENT = Decimal("0.01")


async def _fetch_all(query: str, **params):
    if not db_pool.session_factory:
        await db_pool.initialize()
    async with await db_pool.get_session() as session:
        result = await session.execute(text(query), params)
        return result.fetchall()


async def _fetch_one(query: str, **params):
    return (await _fetch_all(query, **params))[0]


async def list_properties(tenant_id: str):
    rows = await _fetch_all(
        "SELECT id, name, timezone FROM properties WHERE tenant_id = :tenant_id ORDER BY id",
        tenant_id=tenant_id,
    )
    return [{"id": r.id, "name": r.name, "timezone": r.timezone} for r in rows]


async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Decimal:
    """
    Revenue for a calendar month, bucketed in the property's own timezone.
    A check-in at 23:30 UTC on Feb 29 is a March booking for a Paris property.
    """
    start_date = datetime(year, month, 1)
    end_date = datetime(year + (month == 12), month % 12 + 1, 1)

    row = await _fetch_one(
        """
        SELECT COALESCE(SUM(r.total_amount), 0) AS total
        FROM reservations r
        JOIN properties p ON p.id = r.property_id AND p.tenant_id = r.tenant_id
        WHERE r.property_id = :property_id
          AND r.tenant_id = :tenant_id
          AND (r.check_in_date AT TIME ZONE p.timezone) >= :start_date
          AND (r.check_in_date AT TIME ZONE p.timezone) < :end_date
        """,
        property_id=property_id, tenant_id=tenant_id, start_date=start_date, end_date=end_date,
    )
    return Decimal(row.total).quantize(CENT, rounding=ROUND_HALF_UP)


async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Sums reservations at full stored precision and rounds to cents exactly once.
    Raises on database failure instead of returning placeholder figures.
    """
    row = await _fetch_one(
        """
        SELECT COALESCE(SUM(total_amount), 0) AS total_revenue, COUNT(*) AS reservation_count
        FROM reservations
        WHERE property_id = :property_id AND tenant_id = :tenant_id
        """,
        property_id=property_id, tenant_id=tenant_id,
    )
    total = Decimal(row.total_revenue).quantize(CENT, rounding=ROUND_HALF_UP)
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": str(total),
        "currency": "USD",
        "count": row.reservation_count,
    }
