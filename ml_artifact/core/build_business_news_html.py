"""Build a standalone, offline HTML viewer for business news selections."""

from __future__ import annotations

import argparse
import json
from .news_metrics import render_metrics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_html(selection: dict, accounts: dict) -> str:
    payload = dict(selection, accounts=accounts.get("accounts", []))
    # JSON lives in a script element: escape HTML delimiters even in news text.
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    for char, escaped in (("&", r"\u0026"), ("<", r"\u003c"), (">", r"\u003e")):
        encoded = encoded.replace(char, escaped)
    template_path = Path(__file__).with_name("business_news_template.html")
    if not template_path.exists():
        template_path = Path(__file__).parent.parent / "business_news_template.html"
    template = template_path.read_text(encoding="utf-8")
    return template.replace("__METRICS_REPORT__", render_metrics(selection.get("metrics"))).replace("__BUSINESS_NEWS_DATA__", encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "outputs/business_news.json")
    parser.add_argument("--accounts", type=Path, default=ROOT / "reference_uids.json")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/business_news.html")
    args = parser.parse_args()
    selection = json.loads(args.input.read_text(encoding="utf-8"))
    accounts = json.loads(args.accounts.read_text(encoding="utf-8"))
    html = build_html(selection, accounts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Saved {len(selection['profiles'])} business feeds to {args.output}")


if __name__ == "__main__":
    main()
