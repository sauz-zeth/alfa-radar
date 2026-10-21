"""Import the hackathon CSV files.

The script auto-detects the file type by its header and can be pointed at a
directory or at individual CSV files:

    uv run python scripts/import_csv.py "/tmp/alfadata/Данные для участников"
    uv run python scripts/import_csv.py df_Uid_data_hack.csv df_Uid_payment_hack.csv
    uv run python scripts/import_csv.py path/to/file.csv --limit 5000 --skip-payments

Supported files:
    df_Uid_data_hack.csv      -> companies
    df_Uid_payment_hack.csv   -> payments
    df_Fid_Uid_link_hack.csv  -> person_company_links

Companies and person-company links are idempotent (upsert). Payments have no
natural key, so they are skipped if the table already has rows; use
--replace-payments to reload them.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import asyncpg

from back.config import get_settings

try:
    from scripts.seed import COMPANY_COLUMNS, as_float, company_record
except ImportError:  # running as `python scripts/import_csv.py`
    from seed import COMPANY_COLUMNS, as_float, company_record  # type: ignore[no-redef]


def delimiter_for(path: Path) -> str:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = handle.readline()
    return ";" if header.count(";") >= header.count(",") else ","


def detect_kind(path: Path) -> str:
    delimiter = delimiter_for(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        headers = set(next(reader))
    if {"SYNTHETIC_U", "MAINOKVED_CODE"} <= headers:
        return "companies"
    if {"BENEFICIARY", "PAYER", "PAY_AMT", "PAY_CNT"} <= headers:
        return "payments"
    if {"SYNTHETIC_F", "CITY_NAME", "RC_NAME", "SYNTHETIC_U"} <= headers:
        return "person_links"
    raise SystemExit(f"Неизвестный формат CSV: {path} (заголовки: {sorted(headers)})")


def resolve_inputs(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            files.extend(sorted(path.glob("*.csv")))
        elif path.is_file():
            files.append(path)
        else:
            raise SystemExit(f"Путь не найден: {path}")
    if not files:
        for candidate in (
            get_settings().data_dir,
            Path("/tmp/alfadata/Данные для участников"),
            Path("/tmp/alfadata"),
        ):
            if candidate.is_dir():
                nested = candidate / "Данные для участников"
                target = nested if nested.is_dir() else candidate
                files.extend(sorted(target.glob("*.csv")))
                if files:
                    break
    if not files:
        raise SystemExit("Не найдено ни одного CSV. Передайте файлы/каталог аргументом.")
    return files


def iter_companies(path: Path, limit: int) -> list[tuple[Any, ...]]:
    delimiter = delimiter_for(path)
    records: list[tuple[Any, ...]] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for index, row in enumerate(reader, start=1):
            if limit and index > limit:
                break
            uid = (row.get("SYNTHETIC_U") or "").strip()
            if not uid or uid in seen:
                continue
            seen.add(uid)
            records.append(company_record(row))
    return records


def iter_payments(path: Path) -> Iterator[tuple[str, str, float, int]]:
    delimiter = delimiter_for(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            amount = as_float(row.get("PAY_AMT"))
            if not row.get("PAYER") or not row.get("BENEFICIARY") or amount is None:
                continue
            yield (
                row["PAYER"].strip(),
                row["BENEFICIARY"].strip(),
                amount,
                int(as_float(row.get("PAY_CNT")) or 0),
            )


def iter_person_links(path: Path) -> list[tuple[str, str, str | None, str | None]]:
    delimiter = delimiter_for(path)
    records: list[tuple[str, str, str | None, str | None]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            person = (row.get("SYNTHETIC_F") or "").strip()
            company = (row.get("SYNTHETIC_U") or "").strip()
            if not person or not company:
                continue
            records.append(
                (
                    person,
                    company,
                    row.get("CITY_NAME") or None,
                    row.get("RC_NAME") or None,
                )
            )
    return records


async def import_companies(conn: asyncpg.Connection, path: Path, limit: int) -> None:
    records = iter_companies(path, limit)
    if not records:
        print(f"companies: {path.name} — нет строк")
        return
    columns = ", ".join(COMPANY_COLUMNS)
    updates = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in COMPANY_COLUMNS if column != "uid"
    )
    await conn.execute("DROP TABLE IF EXISTS _companies_stage")
    await conn.execute("CREATE TEMP TABLE _companies_stage (LIKE companies)")
    batch_size = 10_000
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        await conn.copy_records_to_table("_companies_stage", records=batch, columns=COMPANY_COLUMNS)
        await conn.execute(
            f"""
            INSERT INTO companies ({columns})
            SELECT {columns} FROM _companies_stage
            ON CONFLICT (uid) DO UPDATE SET {updates}
            """
        )
        await conn.execute("TRUNCATE _companies_stage")
    print(f"companies: {len(records)} (upsert)")


async def import_payments(conn: asyncpg.Connection, path: Path, replace: bool) -> None:
    count = await conn.fetchval("SELECT count(*) FROM payments")
    if count and not replace:
        print(
            f"payments: в таблице уже {count} строк, пропускаю {path.name} "
            "(используйте --replace-payments)"
        )
        return
    if replace:
        await conn.execute("TRUNCATE TABLE payments RESTART IDENTITY")
    total = 0
    batch: list[tuple[str, str, float, int]] = []
    for record in iter_payments(path):
        batch.append(record)
        if len(batch) >= 50_000:
            await conn.copy_records_to_table(
                "payments",
                records=batch,
                columns=["payer", "beneficiary", "amount", "count"],
            )
            total += len(batch)
            batch = []
            print(f"payments: {total}...", end="\r")
    if batch:
        await conn.copy_records_to_table(
            "payments",
            records=batch,
            columns=["payer", "beneficiary", "amount", "count"],
        )
        total += len(batch)
    print(f"payments: {total}          ")


async def import_person_links(conn: asyncpg.Connection, path: Path, replace: bool) -> None:
    if replace:
        await conn.execute("TRUNCATE TABLE person_company_links RESTART IDENTITY")
    records = iter_person_links(path)
    if not records:
        print(f"person_company_links: {path.name} — нет строк")
        return
    await conn.executemany(
        """
        INSERT INTO person_company_links (synthetic_f, synthetic_u, city_name, rc_name)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (synthetic_f, synthetic_u) DO UPDATE SET
            city_name = EXCLUDED.city_name,
            rc_name = EXCLUDED.rc_name
        """,
        records,
    )
    print(f"person_company_links: {len(records)} (upsert)")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Импорт CSV хакатона в Postgres")
    parser.add_argument(
        "inputs",
        nargs="*",
        help="CSV-файлы или каталоги. Без аргументов ищет /tmp/alfadata или DATA_DIR.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Лимит компаний, 0 = все")
    parser.add_argument("--skip-payments", action="store_true")
    parser.add_argument("--skip-person-links", action="store_true")
    parser.add_argument(
        "--replace-payments",
        action="store_true",
        help="Очистить payments перед загрузкой",
    )
    parser.add_argument(
        "--replace-person-links",
        action="store_true",
        help="Очистить person_company_links перед загрузкой",
    )
    args = parser.parse_args()

    files = resolve_inputs(args.inputs)
    kinds = [(path, detect_kind(path)) for path in files]
    print("Найдено:")
    for path, kind in kinds:
        print(f"  {kind:16} {path}")

    settings = get_settings()
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        for path, kind in kinds:
            if kind == "companies":
                await import_companies(conn, path, args.limit)
            elif kind == "payments" and not args.skip_payments:
                await import_payments(conn, path, args.replace_payments)
            elif kind == "person_links" and not args.skip_person_links:
                await import_person_links(conn, path, args.replace_person_links)
    finally:
        await conn.close()
    print("import: done")


if __name__ == "__main__":
    asyncio.run(main())
