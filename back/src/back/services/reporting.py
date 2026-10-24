import logging
import re
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.constants import REPORTING_FORM_LABELS, ReportingForm
from back.db.models import BusinessProfile, ReportingUpload
from back.llm.factory import get_llm
from back.llm.prompts import REPORTING_SYSTEM, reporting_prompt

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 200_000


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1251", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_text_from_bytes(filename: str, raw: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)[:MAX_TEXT_CHARS]
    if lower.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook

        workbook = load_workbook(BytesIO(raw), read_only=True, data_only=True)
        lines: list[str] = []
        for sheet in workbook.worksheets:
            lines.append(f"[Лист: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                values = [str(value) for value in row if value is not None]
                if values:
                    lines.append("\t".join(values))
        return "\n".join(lines)[:MAX_TEXT_CHARS]
    return _decode(raw)[:MAX_TEXT_CHARS]


def _find_labelled_number(text: str, labels: tuple[str, ...]) -> float | None:
    for label in labels:
        pattern = rf"{label}[^\d\-]{{0,80}}(-?\d[\d\s]*(?:[.,]\d+)?)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).replace(" ", "").replace(",", ".")
            try:
                return float(value)
            except ValueError:
                continue
    return None


def fallback_extracted(form_type: ReportingForm, text: str) -> dict[str, Any]:
    period_match = re.search(r"(20\d{2})", text)
    period = period_match.group(1) if period_match else None
    if form_type is ReportingForm.INCOME:
        revenue = _find_labelled_number(text, ("выручка", "доходы"))
        profit = _find_labelled_number(text, ("чистая прибыль", "прибыль"))
        return {
            "period": period,
            "revenue": revenue,
            "cost_structure": [],
            "profit": profit,
            "debt": None,
            "interest_expense": _find_labelled_number(text, ("проценты", "процентные расходы")),
            "cash_flows": {},
            "currency_positions": [],
            "key_points": ["Извлечение выполнено без LLM: проверьте ключевые цифры вручную."],
        }
    if form_type is ReportingForm.BALANCE:
        return {
            "period": period,
            "revenue": None,
            "cost_structure": [],
            "profit": None,
            "debt": _find_labelled_number(text, ("кредиты", "займы", "заёмные средства")),
            "interest_expense": None,
            "cash_flows": {},
            "currency_positions": [],
            "key_points": ["Извлечение выполнено без LLM: проверьте ключевые цифры вручную."],
        }
    return {
        "period": period,
        "revenue": None,
        "cost_structure": [],
        "profit": None,
        "debt": None,
        "interest_expense": None,
        "cash_flows": {
            "operating": _find_labelled_number(text, ("операционная деятельность",)),
            "investing": _find_labelled_number(text, ("инвестиционная деятельность",)),
            "financing": _find_labelled_number(text, ("финансовая деятельность",)),
        },
        "currency_positions": [],
        "key_points": ["Извлечение выполнено без LLM: проверьте ключевые цифры вручную."],
    }

def _money(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} млрд ₽".replace(".0 ", " ")
    if value >= 1_000_000:
        return f"{value / 1_000_000:.0f} млн ₽"
    if value >= 1_000:
        return f"{value / 1_000:.0f} тыс ₽"
    return f"{value:,.0f} ₽".replace(",", " ")


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _md_table(headers: tuple[str, ...], rows: list[tuple[Any, ...]]) -> list[str]:
    if not rows:
        return []
    line = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    return [line, divider, *["| " + " | ".join(_cell(item) for item in row) + " |" for row in rows]]


def form_markdown(form_type: ReportingForm, filename: str, extracted: dict[str, Any]) -> str:
    """Deterministic Markdown fallback; the LLM may return a richer summary_markdown."""
    lines = [f"## {REPORTING_FORM_LABELS[form_type]}", "", f"**Файл:** {filename}"]
    period = extracted.get("period")
    if period:
        lines.append(f"**Период:** {period}")
    lines.append("")

    figures = []
    for key, label in (
        ("revenue", "Выручка"),
        ("profit", "Прибыль"),
        ("debt", "Долг"),
        ("interest_expense", "Проценты к уплате"),
    ):
        value = extracted.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            figures.append((label, _money(float(value))))
    if figures:
        lines.extend(
            ["### Ключевые цифры", "", *_md_table(("Показатель", "Значение"), figures), ""]
        )

    cash = extracted.get("cash_flows")
    if isinstance(cash, dict):
        flows = []
        for key, label in (
            ("operating", "Операционный поток"),
            ("investing", "Инвестиционный поток"),
            ("financing", "Финансовый поток"),
        ):
            value = cash.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                flows.append((label, _money(float(value))))
        if flows:
            lines.extend(
                ["### Денежные потоки", "", *_md_table(("Поток", "Сумма"), flows), ""]
            )

    costs = extracted.get("cost_structure")
    if isinstance(costs, list):
        rows = []
        for item in costs:
            if isinstance(item, dict) and item.get("name"):
                value = item.get("value")
                rows.append(
                    (
                        item["name"],
                        _money(float(value))
                        if isinstance(value, (int, float)) and not isinstance(value, bool)
                        else value,
                    )
                )
        if rows:
            lines.extend(["### Структура затрат", "", *_md_table(("Статья", "Сумма"), rows), ""])

    positions = extracted.get("currency_positions")
    if isinstance(positions, list):
        rows = []
        for item in positions:
            if isinstance(item, dict) and item.get("currency"):
                rows.append((item["currency"], item.get("amount") or "—"))
        if rows:
            lines.extend(["### Валютные позиции", "", *_md_table(("Валюта", "Сумма"), rows), ""])

    points = extracted.get("key_points")
    if isinstance(points, list):
        clean = [str(item).strip() for item in points if str(item).strip()]
        if clean:
            lines.extend(["### Что важно", "", *[f"- {item}" for item in clean], ""])

    return "\n".join(lines).strip()


def _entry_markdown(key: str, entry: dict[str, Any]) -> str:
    markdown = entry.get("markdown")
    if isinstance(markdown, str) and markdown.strip():
        return markdown.strip()
    data = entry.get("data")
    if not isinstance(data, dict):
        return ""
    try:
        form_type = ReportingForm(key)
    except ValueError:
        return ""
    markdown = form_markdown(form_type, str(entry.get("filename") or ""), data)
    entry["markdown"] = markdown
    return markdown


async def process_upload(
    session: AsyncSession,
    profile: BusinessProfile,
    form_type: ReportingForm,
    upload: UploadFile,
    use_llm: bool = True,
) -> ReportingUpload:
    raw = await upload.read()
    filename = upload.filename or f"{form_type.value}.txt"
    try:
        text = extract_text_from_bytes(filename, raw)
    except Exception:
        logger.exception("Failed to extract reporting text from %s", filename)
        text = ""

    fallback = fallback_extracted(form_type, text)
    extracted = fallback
    if use_llm and text.strip():
        try:
            extracted = await get_llm().complete_json(
                system=REPORTING_SYSTEM,
                user=reporting_prompt(form_type.value, filename, text),
                fallback=fallback,
                model=None,
            )
        except Exception:
            logger.exception("Reporting LLM failed, using fallback extraction")

    explicit_markdown = extracted.pop("summary_markdown", None)
    markdown = explicit_markdown.strip() if isinstance(explicit_markdown, str) else ""
    if not markdown:
        markdown = form_markdown(form_type, filename, extracted)

    upload_row = ReportingUpload(
        profile_id=profile.id,
        form_type=form_type.value,
        filename=filename,
        content_type=upload.content_type,
        raw_text=text[:MAX_TEXT_CHARS],
        extracted=extracted,
        status="processed",
    )
    session.add(upload_row)
    await session.flush()

    summary = dict(profile.reporting_summary or {})
    forms = dict(summary.get("forms") or {})
    forms[form_type.value] = {
        "label": REPORTING_FORM_LABELS[form_type],
        "filename": filename,
        "upload_id": str(upload_row.id),
        "data": extracted,
        "markdown": markdown,
    }
    key_points: list[str] = list(summary.get("key_points") or [])
    for point in extracted.get("key_points") or []:
        point = str(point)
        if point and point not in key_points:
            key_points.append(point)
    period = extracted.get("period") or summary.get("period")
    summary["markdown"] = "\n\n".join(
        item
        for item in (
            _entry_markdown(key, value)
            for key, value in forms.items()
            if isinstance(value, dict)
        )
        if item
    )
    summary.update(
        {
            "period": period,
            "forms": forms,
            "key_points": key_points[:20],
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    profile.reporting_summary = summary
    await session.flush()
    return upload_row


def reporting_context(profile: BusinessProfile) -> dict[str, Any]:
    summary = profile.reporting_summary or {}
    if not summary:
        return {}
    compact: dict[str, Any] = {
        "period": summary.get("period"),
        "key_points": summary.get("key_points", []),
    }
    forms = summary.get("forms") or {}
    if isinstance(forms, dict):
        compact["forms"] = {
            key: value.get("data") if isinstance(value, dict) else value
            for key, value in forms.items()
        }
    return compact
