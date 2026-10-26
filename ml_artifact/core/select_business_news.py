"""Rank already classified news events for reference business accounts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .business_source_selection import attach_sources, filter_corpus, source_counts

ROOT = Path(__file__).resolve().parent.parent
DIRECT = "прямое"
INDIRECT = "косвенное"
IRRELEVANT = "не важно"
LEVELS = (IRRELEVANT, INDIRECT, DIRECT)
MAX_CATEGORIES = 8
DEFAULT_SOURCES = ROOT / "business_sources.json"
DEFAULT_CLUSTERS = ROOT / "outputs/cluster_explorer/clusters_78735240aa4b.json"
GENERAL = {
    "ДКП и ключевая ставка": INDIRECT,
    "Налоги и налоговое администрирование": INDIRECT,
    "Трудовое право и рынок труда": INDIRECT,
    "Господдержка и субсидии": INDIRECT,
    "Потребительский спрос и инфляция": INDIRECT,
    "Энергоресурсы и коммунальные услуги": INDIRECT,
}
INDUSTRY = {
    "41": "Строительство и недвижимость", "43": "Строительство и недвижимость",
    "46": "Розничная торговля и e-commerce", "47": "Розничная торговля и e-commerce",
    "49": "Логистика и перевозки", "52": "Логистика и перевозки",
    "55": "Туризм и гостеприимство", "56": "АПК и продовольствие",
    "79": "Туризм и гостеприимство",
    "62": "IT, телеком и ИИ", "68": "Строительство и недвижимость",
    "69": "Бухучёт, отчётность и аудит", "86": "Фарма и здравоохранение",
    "93": "Потребительский спрос и инфляция", "45": "Автомобильный рынок и автобизнес",
    "33": "Машиностроение и промышленная политика",
}
EXTRA = {
    "56": {"Потребительский спрос и инфляция": INDIRECT},
    "46": {"Логистика и перевозки": INDIRECT},
    "47": {"Реклама, медиа и продвижение": INDIRECT},
    "52": {"Таможенно-тарифное регулирование": INDIRECT},
    "62": {"Госзаказ и регулируемые закупки": INDIRECT},
    "69": {"Корпоративное право, M&A и банкротства": INDIRECT},
    "86": {"Госзаказ и регулируемые закупки": INDIRECT},
    "45": {"Лёгкая промышленность и потребительские товары": INDIRECT},
    "33": {"Машиностроение и промышленная политика": DIRECT},
}



def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_profile(account: dict, categories=None) -> dict:
    code = str(account["okved"])[:2]
    impacts = dict.fromkeys(categories or (), IRRELEVANT)
    impacts.update(GENERAL)
    impacts.update(EXTRA.get(code, {}))
    if code in INDUSTRY:
        impacts[INDUSTRY[code]] = DIRECT
    if account.get("fts"):
        impacts.update({
            "Курс рубля и валютное регулирование": DIRECT,
            "Санкции и экспортный контроль": DIRECT,
            "Таможенно-тарифное регулирование": DIRECT,
            "Геополитика и мировая экономика": INDIRECT,
        })
    if {"кредиты", "лизинг"}.intersection(account.get("products", [])):
        impacts["ДКП и ключевая ставка"] = DIRECT
    if account.get("eco_mark") in ("Рождение", "Стремительный рост"):
        impacts["Господдержка и субсидии"] = DIRECT
    impacts.pop("Реклама/мусор", None)
    # Prefer direct exposures, then industry-specific indirect factors, then general factors.
    priority = list(dict.fromkeys(([INDUSTRY[code]] if code in INDUSTRY else []) +
                                 list(EXTRA.get(code, {})) + list(GENERAL) + list(impacts)))
    active = sorted((c for c,v in impacts.items() if v != IRRELEVANT),
                    key=lambda c: (-LEVELS.index(impacts[c]), priority.index(c)))[:MAX_CATEGORIES]
    impacts = {c:(value if c in active else IRRELEVANT) for c,value in impacts.items()}
    return {"uid": account["uid"], "okved": account["okved"],
            "activity": account["okved_name"], "region": account["region"],
            "category_impacts": impacts, "max_categories": MAX_CATEGORIES}


def apply_overrides(profile: dict, overrides: dict) -> dict:
    values = overrides.get(profile["uid"], {})
    unknown = set(values) - profile["category_impacts"].keys()
    if unknown or any(value not in LEVELS for value in values.values()):
        raise ValueError(f"Некорректные категории или уровни для {profile['uid']}")
    updated = {**profile["category_impacts"], **values}
    count = sum(value != IRRELEVANT for value in updated.values())
    if count > MAX_CATEGORIES:
        raise ValueError(f"Для {profile['uid']} выбрано {count} категорий: максимум {MAX_CATEGORIES} (прямое + косвенное)")
    profile["category_impacts"] = updated
    return profile


def rank_cluster(profile: dict, cluster: dict, thresholds: dict) -> dict:
    matched = []
    spam = False
    for label in cluster.get("labels", []):
        name = label["label"]
        if name not in thresholds or label["score"] < thresholds[name]:
            continue
        if name == "Реклама/мусор":
            spam = True
            continue
        level = profile["category_impacts"].get(name, IRRELEVANT)
        if level != IRRELEVANT:
            matched.append({"label": name, "probability": label["score"],
                            "threshold": thresholds[name], "impact": level})
    matched.sort(key=lambda item: (-LEVELS.index(item["impact"]), item["label"]))
    impact = matched[0]["impact"] if matched and not spam else IRRELEVANT
    members = cluster.get("members", [])
    sources, groups = source_counts(members)
    many_sources = len(groups) > 5
    return {"event_id": cluster["event_id"], "impact": impact,
            "status": "excluded" if spam else "ignored" if impact == IRRELEVANT and not many_sources else "candidate",
            "decisive_label": matched[0]["label"] if matched else "",
            "sources": len(sources), "independent_sources": len(groups), "source_groups": groups,
            "matched_labels": matched, "members": members, "images": cluster.get("images", []),
            "date": max((m.get("date", "") for m in members), default=None),
            "headline": members[0].get("text", "").split("\n")[0][:220] if members else ""}


def select(accounts: dict, corpus: dict, thresholds: dict, overrides=None, source_configuration=None) -> dict:
    profiles = [attach_sources(apply_overrides(build_profile(a, thresholds), overrides or {}), a, source_configuration)
                for a in accounts["accounts"]]
    results = []
    for profile in profiles:
        business_corpus = filter_corpus(profile, corpus)
        candidates = [rank_cluster(profile, c, thresholds) for c in business_corpus["clusters"]]
        candidates = [c for c in candidates if c["status"] == "candidate"]
        candidates.sort(key=lambda c: (-LEVELS.index(c["impact"]), str(c["event_id"])))
        print(f"[{len(results)+1}/{len(profiles)}] {profile['uid']}: {len(candidates)} кандидатов", flush=True)
        results.append({"uid": profile["uid"], "total_matching": len(candidates), "clusters": candidates, "source_filter": business_corpus["source_filter"]})
    return {"profiles": profiles, "recommendations": results,
            "corpus": {"total_clusters": len(corpus["clusters"]),
                       "parameters": corpus.get("parameters", {})},
            "scoring": {"version": "categorical_v2", "mode": "candidates_only",
                        "selection": "max category impact; p >= classifier threshold",
                        "thresholds": thresholds}}


def main() -> None:
    from .build_business_news_html import build_html
    parser = argparse.ArgumentParser(description="Кандидаты без LLM и HTML с профилями бизнеса")
    parser.add_argument("--accounts", type=Path, default=ROOT / "reference_uids.json")
    parser.add_argument("--clusters", type=Path, default=DEFAULT_CLUSTERS)
    parser.add_argument("--metadata", type=Path, default=ROOT / "models/rubert_int4/metadata.json")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--profiles", type=Path, help="JSON: UID → категория → уровень")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/business_news.json")
    parser.add_argument("--html", type=Path)
    args = parser.parse_args()
    accounts = read_json(args.accounts)
    result = select(accounts, read_json(args.clusters), read_json(args.metadata)["thresholds"],
                    read_json(args.profiles) if args.profiles else {}, read_json(args.sources))
    result["corpus"].update(path=str(args.clusters.resolve()),
                             sha256=hashlib.sha256(args.clusters.read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html = args.html or args.output.with_suffix(".html")
    html.parent.mkdir(parents=True, exist_ok=True)
    html.write_text(build_html(result, accounts), encoding="utf-8")
    print(f"JSON: {args.output}\nHTML: {html.resolve()}", flush=True)


if __name__ == "__main__":
    main()
