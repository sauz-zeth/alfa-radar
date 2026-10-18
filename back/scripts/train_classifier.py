import argparse
import json
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)


class MultiLabelDataset(Dataset[dict[str, torch.Tensor]]):
    def __init__(
        self,
        records: list[dict[str, Any]],
        tokenizer: AutoTokenizer,
        labels: list[str],
    ) -> None:
        self._records = records
        self._tokenizer = tokenizer
        self._labels = labels

    def __len__(self) -> int:
        return len(self._records)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        record = self._records[index]
        encoded = self._tokenizer(
            record["text"],
            truncation=True,
            max_length=512,
        )
        target = torch.zeros(len(self._labels), dtype=torch.float)
        for label in record["labels"]:
            if label in self._labels:
                target[self._labels.index(label)] = 1.0
        encoded["labels"] = target
        return dict(encoded)


def load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--model", default="ai-forever/ruBert-base")
    parser.add_argument("--output", type=Path, default=Path("models/category-classifier"))
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--val-share", type=float, default=0.1)
    args = parser.parse_args()

    records = load_records(args.dataset)
    labels = sorted({label for record in records for label in record["labels"]})
    split = max(1, int(len(records) * args.val_share))
    train_records = records[split:]
    val_records = records[:split]

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=len(labels),
        problem_type="multi_label_classification",
        id2label=dict(enumerate(labels)),
        label2id={label: index for index, label in enumerate(labels)},
    )
    training_args = TrainingArguments(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        report_to=[],
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=MultiLabelDataset(train_records, tokenizer, labels),
        eval_dataset=MultiLabelDataset(val_records, tokenizer, labels),
        data_collator=DataCollatorWithPadding(tokenizer),
    )
    trainer.train()
    trainer.save_model(str(args.output))
    tokenizer.save_pretrained(str(args.output))
    (args.output / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
