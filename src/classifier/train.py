import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)

from evaluate import compute_binary_metrics


MODEL_NAME = "monologg/koelectra-base-v3-discriminator"


# --------------------------------------------------
# Reproducibility
# --------------------------------------------------

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# --------------------------------------------------
# Dataset
# --------------------------------------------------

class TextClassificationDataset(Dataset):
    def __init__(
        self,
        dataframe,
        tokenizer,
        max_length=128,
    ):
        self.texts = dataframe["text"].astype(str).tolist()
        self.labels = dataframe["label"].astype(int).tolist()
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]

        encoded = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        item = {
            key: value.squeeze(0)
            for key, value in encoded.items()
        }

        item["labels"] = torch.tensor(
            label,
            dtype=torch.long,
        )

        return item


# --------------------------------------------------
# Validation
# --------------------------------------------------

def evaluate_model(
    model,
    dataloader,
    device,
):
    model.eval()

    all_labels = []
    all_predictions = []
    all_probabilities = []
    validation_loss = 0.0

    with torch.no_grad():

        for batch in dataloader:

            labels = batch["labels"].to(device)

            inputs = {
                key: value.to(device)
                for key, value in batch.items()
                if key != "labels"
            }

            outputs = model(
                **inputs,
                labels=labels,
            )

            validation_loss += outputs.loss.item()

            probabilities = torch.softmax(
                outputs.logits,
                dim=-1,
            )

            attack_probabilities = probabilities[:, 1]

            predictions = torch.argmax(
                probabilities,
                dim=-1,
            )

            all_labels.extend(
                labels.cpu().tolist()
            )

            all_predictions.extend(
                predictions.cpu().tolist()
            )

            all_probabilities.extend(
                attack_probabilities.cpu().tolist()
            )

    metrics = compute_binary_metrics(
        all_labels,
        all_predictions,
    )

    metrics["validation_loss"] = (
        validation_loss / len(dataloader)
    )

    return (
        metrics,
        all_labels,
        all_predictions,
        all_probabilities,
    )


# --------------------------------------------------
# Main
# --------------------------------------------------

def main(args):

    set_seed(args.seed)

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print("=== Configuration ===")
    print("device:", device)
    print("model:", MODEL_NAME)
    print("train:", args.train)
    print("valid:", args.valid)
    print("epochs:", args.epochs)
    print("batch size:", args.batch_size)
    print("learning rate:", args.learning_rate)
    print("max length:", args.max_length)

    # --------------------------------------------------
    # Load CSV
    # --------------------------------------------------

    train_df = pd.read_csv(args.train)
    valid_df = pd.read_csv(args.valid)

    required_columns = {"text", "label"}

    if not required_columns.issubset(train_df.columns):
        raise ValueError(
            "Train CSV must contain text and label columns."
        )

    if not required_columns.issubset(valid_df.columns):
        raise ValueError(
            "Validation CSV must contain text and label columns."
        )

    if not set(train_df["label"].unique()).issubset({0, 1}):
        raise ValueError(
            "Train labels must be 0 or 1."
        )

    if not set(valid_df["label"].unique()).issubset({0, 1}):
        raise ValueError(
            "Validation labels must be 0 or 1."
        )

    print("\n=== Dataset ===")
    print("train size:", len(train_df))
    print("valid size:", len(valid_df))

    # --------------------------------------------------
    # Tokenizer / Model
    # --------------------------------------------------

    print("\n=== Loading tokenizer/model ===")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
    )

    model.to(device)

    # --------------------------------------------------
    # Dataset / DataLoader
    # --------------------------------------------------

    train_dataset = TextClassificationDataset(
        train_df,
        tokenizer,
        max_length=args.max_length,
    )

    valid_dataset = TextClassificationDataset(
        valid_df,
        tokenizer,
        max_length=args.max_length,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
    )

    valid_loader = DataLoader(
        valid_dataset,
        batch_size=args.batch_size,
        shuffle=False,
    )

    # --------------------------------------------------
    # Optimizer
    # --------------------------------------------------

    optimizer = AdamW(
        model.parameters(),
        lr=args.learning_rate,
    )

    # --------------------------------------------------
    # Training
    # --------------------------------------------------

    print("\n=== Training ===")

    for epoch in range(args.epochs):

        model.train()

        total_loss = 0.0

        for batch in train_loader:

            optimizer.zero_grad()

            labels = batch["labels"].to(device)

            inputs = {
                key: value.to(device)
                for key, value in batch.items()
                if key != "labels"
            }

            outputs = model(
                **inputs,
                labels=labels,
            )

            loss = outputs.loss

            loss.backward()

            optimizer.step()

            total_loss += loss.item()

        average_loss = (
            total_loss / len(train_loader)
        )

        print(
            f"Epoch "
            f"{epoch + 1}/{args.epochs} "
            f"- train loss: "
            f"{average_loss:.4f}"
        )

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    print("\n=== Validation ===")

    (
        metrics,
        labels,
        predictions,
        attack_probabilities,
    ) = evaluate_model(
        model,
        valid_loader,
        device,
    )

    for key, value in metrics.items():

        if isinstance(value, float):
            print(
                f"{key:16s}: {value:.4f}"
            )
        else:
            print(
                f"{key:16s}: {value}"
            )

    # --------------------------------------------------
    # Save Results
    # --------------------------------------------------

    output_dir = Path(args.output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_df = valid_df.copy()

    result_df["prediction"] = predictions
    result_df["p_attack"] = attack_probabilities

    result_df.to_csv(
        output_dir / "validation_results.csv",
        index=False,
    )

    with open(
        output_dir / "metrics.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metrics,
            f,
            ensure_ascii=False,
            indent=2,
        )

    model.save_pretrained(
        output_dir / "model"
    )

    tokenizer.save_pretrained(
        output_dir / "model"
    )

    print("\n=== Saved ===")
    print(
        output_dir / "validation_results.csv"
    )
    print(
        output_dir / "metrics.json"
    )
    print(
        output_dir / "model"
    )

    print("\nTRAINING PIPELINE SUCCESS")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--train",
        default="data/processed/train_demo.csv",
    )

    parser.add_argument(
        "--valid",
        default="data/processed/valid_demo.csv",
    )

    parser.add_argument(
        "--output-dir",
        default="results/demo",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-5,
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=128,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    main(args)
