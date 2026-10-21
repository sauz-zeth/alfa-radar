import logging
import math
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.constants import CounterpartyDirection
from back.db.models import BusinessProfile, Counterparty, Payment
from back.llm.factory import get_llm
from back.llm.prompts import COUNTERPARTY_SYSTEM, counterparties_prompt

logger = logging.getLogger(__name__)

TOP_COUNTERPARTIES = 25


async def _aggregate(
    session: AsyncSession, company_uid: str, direction: CounterpartyDirection
) -> list[dict[str, Any]]:
    if direction is CounterpartyDirection.SUPPLIER:
        company_column = Payment.beneficiary
        filter_column = Payment.payer
    else:
        company_column = Payment.payer
        filter_column = Payment.beneficiary

    amount = func.sum(Payment.amount).label("amount")
    payments_count = func.sum(Payment.count).label("payments_count")
    result = await session.execute(
        select(company_column, amount, payments_count)
        .where(filter_column == company_uid)
        .group_by(company_column)
        .order_by(amount.desc())
        .limit(TOP_COUNTERPARTIES)
    )
    rows = result.all()
    total = sum(float(row.amount or 0) for row in rows)
    items: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        row_amount = float(row.amount or 0)
        row_count = int(row.payments_count or 0)
        share = row_amount / total if total else 0.0
        importance = min(
            100,
            round(share * 80 + min(math.log1p(row_count) / math.log1p(1000), 1.0) * 20),
        )
        label = "Поставщик" if direction is CounterpartyDirection.SUPPLIER else "Покупатель"
        items.append(
            {
                "company_uid": str(row[0]),
                "direction": direction.value,
                "total_amount": row_amount,
                "payments_count": row_count,
                "share": round(share, 4),
                "importance": importance,
                "default_name": f"{label} {index}",
                "note": f"{share:.0%} оборота, {row_count} платежей",
            }
        )
    return items


def _merge_llm_notes(
    items: list[dict[str, Any]], llm_result: dict[str, Any]
) -> list[dict[str, Any]]:
    llm_items = llm_result.get("items")
    if not isinstance(llm_items, list):
        return items
    by_key = {(item["company_uid"], item["direction"]): item for item in items}
    for llm_item in llm_items:
        if not isinstance(llm_item, dict):
            continue
        key = (str(llm_item.get("company_uid")), str(llm_item.get("direction")))
        target = by_key.get(key)
        if target is None:
            continue
        try:
            importance = int(llm_item.get("importance", target["importance"]))
        except TypeError, ValueError:
            continue
        target["importance"] = max(0, min(100, importance))
        note = str(llm_item.get("note") or "").strip()
        if note:
            target["note"] = note[:255]
    return items


async def build_counterparties(
    session: AsyncSession, profile: BusinessProfile, use_llm: bool = True
) -> list[Counterparty]:
    existing = (
        (
            await session.execute(
                select(Counterparty)
                .where(Counterparty.profile_id == profile.id)
                .order_by(Counterparty.importance.desc())
            )
        )
        .scalars()
        .all()
    )
    if existing or not profile.company_uid:
        return list(existing)

    suppliers = await _aggregate(session, profile.company_uid, CounterpartyDirection.SUPPLIER)
    buyers = await _aggregate(session, profile.company_uid, CounterpartyDirection.BUYER)
    items = suppliers + buyers

    if use_llm and items:
        company_payload = {"uid": profile.company_uid, "business_name": profile.business_name}
        llm_input = [
            {
                "company_uid": item["company_uid"],
                "direction": item["direction"],
                "amount": item["total_amount"],
                "payments": item["payments_count"],
                "share": item["share"],
            }
            for item in items
        ]
        try:
            result = await get_llm().complete_json(
                system=COUNTERPARTY_SYSTEM,
                user=counterparties_prompt(company_payload, llm_input),
                fallback={"items": []},
            )
            items = _merge_llm_notes(items, result)
        except Exception:
            logger.exception("Counterparty LLM failed, using payment aggregates")

    counterparties = [
        Counterparty(
            profile_id=profile.id,
            company_uid=item["company_uid"],
            direction=item["direction"],
            total_amount=item["total_amount"],
            payments_count=item["payments_count"],
            share=item["share"],
            importance=item["importance"],
            default_name=item["default_name"],
            note=item["note"],
        )
        for item in items
    ]
    session.add_all(counterparties)
    await session.flush()
    counterparties.sort(key=lambda item: item.importance, reverse=True)
    return counterparties


def counterparty_context(counterparties: list[Counterparty]) -> list[dict[str, Any]]:
    return [
        {
            "name": item.display_name,
            "uid": item.company_uid,
            "direction": item.direction,
            "share": item.share,
            "importance": item.importance,
        }
        for item in counterparties[:15]
    ]
