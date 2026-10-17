import argparse
import json
from pathlib import Path


def choose_tau(
    records: list[dict[str, float | bool]],
    min_recall: float = 0.9,
) -> tuple[float, float, float]:
    important = [record for record in records if record["important"]]
    if not important:
        raise ValueError("В наборе нет важных событий")
    best: tuple[float, float, float] | None = None
    for step in range(101):
        tau = step / 100
        selected = [record for record in records if float(record["prescore"]) >= tau]
        caught = [record for record in selected if record["important"]]
        recall = len(caught) / len(important)
        share = len(selected) / len(records)
        if recall >= min_recall and (best is None or share < best[2]):
            best = (tau, recall, share)
    if best is None:
        raise ValueError("Не удалось достичь требуемого recall")
    return best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--min-recall", type=float, default=0.9)
    args = parser.parse_args()

    records = [json.loads(line) for line in args.dataset.read_text().splitlines() if line]
    tau, recall, share = choose_tau(records, args.min_recall)
    print(json.dumps({"tau": tau, "recall": recall, "llm_share": share}, ensure_ascii=False))


if __name__ == "__main__":
    main()
