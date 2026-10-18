import argparse
import json
from pathlib import Path


def choose_threshold(
    pairs: list[dict[str, float | bool]],
    min_recall: float = 0.95,
) -> tuple[float, float]:
    continuations = [pair for pair in pairs if pair["continuation"]]
    if not continuations:
        raise ValueError("В наборе нет пар-продолжений")
    candidates = sorted({float(pair["similarity"]) for pair in pairs}, reverse=True)
    best = (candidates[-1], 0.0)
    for threshold in candidates:
        selected = [pair for pair in pairs if float(pair["similarity"]) >= threshold]
        caught = [pair for pair in selected if pair["continuation"]]
        recall = len(caught) / len(continuations)
        if recall >= min_recall:
            best = (threshold, recall)
            break
    return best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs", type=Path)
    parser.add_argument("--min-recall", type=float, default=0.95)
    args = parser.parse_args()

    pairs = [json.loads(line) for line in args.pairs.read_text().splitlines() if line]
    threshold, recall = choose_threshold(pairs, args.min_recall)
    print(json.dumps({"theta_ch": threshold, "recall": recall}, ensure_ascii=False))


if __name__ == "__main__":
    main()
