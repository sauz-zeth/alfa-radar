import argparse
import json
from pathlib import Path
from typing import Any


def best_threshold(records: list[dict[str, Any]], category: str) -> tuple[float, float]:
    thresholds = sorted(
        {0.0, 1.0} | {float(record["scores"].get(category, 0.0)) for record in records}
    )
    best = (0.5, -1.0)
    for threshold in thresholds:
        tp = fp = fn = 0
        for record in records:
            predicted = float(record["scores"].get(category, 0.0)) >= threshold
            actual = category in record["labels"]
            tp += int(predicted and actual)
            fp += int(predicted and not actual)
            fn += int(actual and not predicted)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        if f1 > best[1]:
            best = (threshold, f1)
    return best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("category_thresholds.json"))
    parser.add_argument("--categories", nargs="*")
    args = parser.parse_args()

    records = [json.loads(line) for line in args.dataset.read_text().splitlines() if line]
    categories = args.categories or sorted(
        {category for record in records for category in record["labels"]}
    )
    result = {}
    for category in categories:
        threshold, f1 = best_threshold(records, category)
        result[category] = {"threshold": threshold, "f1": f1}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
