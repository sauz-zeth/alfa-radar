"""Profile-specific selection from the RSS catalog."""
import re
from pathlib import Path

MAX_RSS_SOURCES = 40
POLICY_VERSION = "industry_sources_v1"
ROOT = Path(__file__).resolve().parent.parent
RSS_MD = ROOT / "RSS_ленты_для_новостной_аналитики_кейс_Альфа_Банка.md"
SOURCE_GROUPS = {}


def normalize_source(value):
    value = str(value or "").strip().lower()
    return value.split("/", 1)[0].split("?", 1)[0]


def rss_catalog_sources(path=RSS_MD):
    """Return normalized RSS publisher names from the Markdown catalogue."""
    if not Path(path).exists():
        return []
    link_re = re.compile(r"\[([^]]+)\]\((https?://[^)]+)\)")
    names = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        links = link_re.findall(line)
        if len(links) >= 2 and line.lstrip().startswith("|"):
            name = normalize_source(links[0][0])
            if name and name not in names:
                names.append(name)
    return names


def member_source(member):
    return normalize_source(member.get("source") or member.get("post_id", "").split("/", 1)[0])


def independent_group(member):
    # A supplied publisher group or original publisher takes priority over channel identity.
    explicit = member.get("source_group") or member.get("original_source")
    source = normalize_source(explicit) if explicit else member_source(member)
    return SOURCE_GROUPS.get(source, source)


def source_counts(members):
    sources = {member_source(m) for m in members} - {""}
    groups = {independent_group(m) for m in members} - {""}
    return sorted(sources), sorted(groups)


def choose_sources(account):
    return {"sources":[], "reason":"Подбор выполняется из каталога RSS по отрасли и профилю.",
            "basis":"Каталог RSS-лент; подбор не зависит от результатов LLM.", "policy_version":POLICY_VERSION}


def attach_sources(profile, account, configuration=None):
    entry = (configuration or {}).get("businesses", {}).get(account["uid"], choose_sources(account))
    rss_sources = rss_catalog_sources()[:MAX_RSS_SOURCES]
    sources = list(dict.fromkeys(rss_sources))
    if not isinstance(sources, list) or any(not isinstance(s,str) or not normalize_source(s) for s in sources):
        raise ValueError("sources: нужен список непустых RSS источников")
    sources = list(dict.fromkeys(normalize_source(s) for s in sources))
    if not 1 <= len(sources) <= MAX_RSS_SOURCES:
        raise ValueError(f"Для {account['uid']} требуется от 1 до {MAX_RSS_SOURCES} RSS-источников")
    selected_rss = sources
    return {**profile, "selected_sources": sources,
            "source_selection": {k: v for k, v in entry.items() if k != "sources"},
            "source_types": {"rss": len(selected_rss)},
            "selected_rss_sources": selected_rss,
            "max_sources": MAX_RSS_SOURCES,
            "max_rss_sources": MAX_RSS_SOURCES}


def filter_corpus(profile, corpus):
    """Filter publications BEFORE using aggregate labels or counting corroboration."""
    allowed = set(profile["selected_sources"])
    filtered = []
    kept = removed = 0
    for cluster in corpus["clusters"]:
        original = cluster.get("members", [])
        members = [m for m in original if member_source(m) in allowed]
        kept += len(members)
        removed += len(original)-len(members)
        if not members:
            continue
        labels = {}
        for member in members:
            # Aggregate fallback is safe only when no publications were removed.
            for label in member.get("labels", cluster.get("labels", []) if len(members)==len(original) else []):
                name = label["label"]
                labels[name] = max(labels.get(name, 0), label["score"])
        sources, groups = source_counts(members)
        filtered.append({**cluster, "members":members, "sources":sources,
                         "independent_sources":len(groups), "source_groups":groups,
                         "labels":[{"label":name,"score":score} for name,score in sorted(labels.items())]})
    available = {member_source(m) for c in corpus['clusters'] for m in c.get('members',[])}
    return {**corpus, "clusters":filtered, "source_filter":{
        "selected_sources":len(allowed), "available_selected_sources":len(allowed & available),
        "selected_sources_without_posts":sorted(allowed-available),
        "input_clusters":len(corpus['clusters']), "retained_clusters":len(filtered),
        "retained_publications":kept, "excluded_publications":removed}}
