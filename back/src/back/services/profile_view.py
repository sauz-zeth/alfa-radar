from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back.core.categories import CATEGORIES
from back.db.models import BusinessCategory, BusinessProfile, Counterparty
from back.schemas.onboarding import CategoryOut, CounterpartyOut
from back.schemas.profile import CategoryGroupOut, NotificationTriggerOut, ProfileStatsOut


async def categories_out(session: AsyncSession, profile: BusinessProfile) -> list[CategoryOut]:
    rows = (
        (
            await session.execute(
                select(BusinessCategory)
                .options(selectinload(BusinessCategory.category))
                .where(BusinessCategory.profile_id == profile.id)
                .order_by(BusinessCategory.weight.desc(), BusinessCategory.category_id)
            )
        )
        .scalars()
        .all()
    )
    return [
        CategoryOut(
            category_id=row.category_id,
            slug=row.category.slug,
            name=row.category.name,
            short_name=row.category.short_name,
            group=row.category.group,
            description=row.category.description,
            example=row.category.example,
            channels=list(row.category.channels or []),
            weight=row.weight,
            rationale=row.rationale,
            is_manual=row.is_manual,
        )
        for row in rows
        if row.category is not None
    ]


async def counterparties_out(
    session: AsyncSession, profile: BusinessProfile
) -> list[CounterpartyOut]:
    rows = (
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
    return [CounterpartyOut.model_validate(row) for row in rows]


DEFAULT_TRIGGERS: tuple[dict[str, str], ...] = (
    {
        "key": "metal_duties",
        "label": "Пошлины и квоты на металлы",
        "channel": "Сразу, push-уведомление",
    },
    {
        "key": "key_rate",
        "label": "Ключевая ставка ±1 п.п.",
        "channel": "Сразу",
    },
    {
        "key": "counterparty_sanctions",
        "label": "Санкции против контрагентов",
        "channel": "Сразу, push и почта",
    },
    {
        "key": "usd_move",
        "label": "Курс USD ±5% за неделю",
        "channel": "В сводке",
    },
)


def _money(value: float | None) -> str:
    if value is None:
        return "нет данных"
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.0f} млрд ₽"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.0f} млн ₽"
    return f"{value:,.0f} ₽".replace(",", " ")


def profile_stats(profile: BusinessProfile) -> ProfileStatsOut:
    company = profile.company
    products: list[str] = []
    if company is not None:
        for enabled, label in (
            (company.cl_product_rko_mark, "РКО"),
            (company.cl_product_loa_mark, "Кредиты"),
            (company.cl_product_gar_mark, "Гарантии"),
            (company.cl_product_lea_mark, "Лизинг"),
            (company.cl_product_dep_mark, "Депозиты"),
            (company.cl_product_zpp_mark, "Зарплатный проект"),
            (company.factoring_mark, "Факторинг"),
        ):
            if enabled:
                products.append(label)
    return ProfileStatsOut(
        industry=company.main_okved_name if company else None,
        city=company.city if company else None,
        region=company.region if company else None,
        revenue=company.revenue if company else None,
        revenue_label=_money(company.revenue if company else None),
        revenue_segment=company.revenue_segment if company else None,
        employees=company.amount_workers_fns_gradation if company else None,
        age=company.company_age_years_gradation if company else None,
        foreign_trade_country=company.fts_country_name if company else None,
        products=products,
        tags=list(profile.tags or []),
    )


def grouped_categories(
    categories: list[CategoryOut],
) -> list[CategoryGroupOut]:
    by_id = {item.category_id: item for item in categories}
    groups = [
        (
            "direct",
            "Прямое влияние",
            "Категории, которые прямо влияют на выручку или затраты",
            0.8,
            1.0,
        ),
        ("indirect", "Косвенное", "Заметное влияние через контрагентов и отрасль", 0.45, 0.8),
        ("background", "Фоновое", "Влияет на общий деловой контекст", 0.01, 0.45),
        ("none", "Не влияют", "Прямой связи с показателями компании нет", 0.0, 0.0),
    ]
    result: list[CategoryGroupOut] = []
    for key, name, description, low, high in groups:
        if key == "none":
            items = [
                by_id.get(category.id)
                or CategoryOut(
                    category_id=category.id,
                    slug=category.slug,
                    name=category.name,
                    short_name=category.short_name,
                    group=category.group,
                    description=category.description,
                    example=category.example,
                    channels=list(category.channels),
                    weight=0.0,
                    rationale="Прямой связи с показателями компании нет.",
                    is_manual=False,
                )
                for category in CATEGORIES
                if category.id not in by_id or by_id[category.id].weight <= 0
            ]
        elif key == "direct":
            items = [item for item in categories if item.weight >= low]
        elif key == "indirect":
            items = [item for item in categories if low <= item.weight < high]
        else:
            items = [item for item in categories if low <= item.weight < high]
        result.append(
            CategoryGroupOut(
                key=key,
                name=name,
                description=description,
                weight_min=low,
                weight_max=high,
                items=items,
            )
        )
    return result


def notification_triggers(profile: BusinessProfile) -> list[NotificationTriggerOut]:
    stored = profile.notifications or {}
    enabled_map = stored.get("triggers") if isinstance(stored, dict) else {}
    if not isinstance(enabled_map, dict):
        enabled_map = {}
    return [
        NotificationTriggerOut(
            key=item["key"],
            label=item["label"],
            channel=item["channel"],
            enabled=bool(enabled_map.get(item["key"], True)),
        )
        for item in DEFAULT_TRIGGERS
    ]
