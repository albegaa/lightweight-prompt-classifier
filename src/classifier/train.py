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
# Data Loading
# --------------------------------------------------

def load_dataframe(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Data file does not exist: {path}"
        )

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    if path.suffix.lower() == ".jsonl":
        rows = []

        with path.open(
            "r",
            encoding="utf-8",
        ) as f:
            for line in f:
                if line.strip():
                    rows.append(
                        json.loads(line)
                    )

        return pd.DataFrame(rows)

    raise ValueError(
        "Supported data formats: .csv, .jsonl"
    )


def prepare_dataframe(
    dataframe,
    text_column,
    label_column,
    max_samples=None,
):
    required_columns = {
        text_column,
        label_column,
    }

    if not required_columns.issubset(
        dataframe.columns
    ):
        raise ValueError(
            "Missing required columns. "
            f"Required: {sorted(required_columns)}, "
            f"Found: {sorted(dataframe.columns.tolist())}"
        )

    dataframe = dataframe.copy()

    dataframe = dataframe.dropna(
        subset=[
            text_column,
            label_column,
        ]
    ).reset_index(drop=True)

    dataframe[text_column] = (
        dataframe[text_column]
        .astype(str)
    )

    dataframe[label_column] = (
        dataframe[label_column]
        .astype(int)
    )

    labels = set(
        dataframe[label_column]
        .unique()
        .tolist()
    )

    if not labels.issubset({0, 1}):
        raise ValueError(
            "Labels must be 0 or 1. "
            f"Found: {sorted(labels)}"
        )

    if max_samples is not None:
        dataframe = (
            dataframe
            .head(max_samples)
            .copy()
        )

    return dataframe


# --------------------------------------------------
# Dataset
# --------------------------------------------------

class TextClassificationDataset(Dataset):

    def __init__(
        self,
        dataframe,
        tokenizer,
        text_column="text",
        label_column="label",
        max_length=128,
    ):
        self.texts = (
            dataframe[text_column]
            .astype(str)
            .tolist()
        )

        self.labels = (
            dataframe[label_column]
            .astype(int)
            .tolist()
        )

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
            for key, value
            in encoded.items()
        }

        item["labels"] = torch.tensor(
            label,
            dtype=torch.long,
        )

        return item


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def evaluate_model(
    model,
    dataloader,
    device,
):

    model.eval()

    all_labels = []
    all_predictions = []
    all_attack_scores = []

    validation_loss = 0.0

    with torch.no_grad():

        for batch in dataloader:

            labels = (
                batch["labels"]
                .to(device)
            )

            inputs = {
                key: value.to(device)
                for key, value
                in batch.items()
                if key != "labels"
            }

            outputs = model(
                **inputs,
                labels=labels,
            )

            validation_loss += (
                outputs.loss.item()
            )

            probabilities = torch.softmax(
                outputs.logits,
                dim=-1,
            )

            # This is an attack-class softmax score,
            # not a calibrated P(Attack).
            attack_scores = (
                probabilities[:, 1]
            )

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

            all_attack_scores.extend(
                attack_scores.cpu().tolist()
            )

    metrics = compute_binary_metrics(
        all_labels,
        all_predictions,
    )

    metrics["validation_loss"] = (
        validation_loss
        / len(dataloader)
    )

    return (
        metrics,
        all_labels,
        all_predictions,
        all_attack_scores,
    )


# --------------------------------------------------
# Training
# --------------------------------------------------

def main(args):

    set_seed(args.seed)

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    use_fp16 = (
        args.fp16
        and device.type == "cuda"
    )

    print("=== Configuration ===")
    print("device:", device)

    if device.type == "cuda":
        print(
            "gpu:",
            torch.cuda.get_device_name(0),
        )

    print("model:", args.model_name)
    print("train:", args.train)
    print("valid:", args.valid)
    print("output:", args.output_dir)
    print("epochs:", args.epochs)
    print("batch size:", args.batch_size)
    print("learning rate:", args.learning_rate)
    print("weight decay:", args.weight_decay)
    print("max length:", args.max_length)
    print("seed:", args.seed)
    print("fp16:", use_fp16)

    # --------------------------------------------------
    # Load Data
    # --------------------------------------------------

    train_df = load_dataframe(
        args.train
    )

    valid_df = load_dataframe(
        args.valid
    )

    train_df = prepare_dataframe(
        train_df,
        args.text_column,
        args.label_column,
        args.max_train_samples,
    )

    valid_df = prepare_dataframe(
        valid_df,
        args.text_column,
        args.label_column,
        args.max_valid_samples,
    )

    print("\n=== Dataset ===")

    print(
        "train size:",
        len(train_df),
    )

    print(
        "train labels:",
        train_df[
            args.label_column
        ]
        .value_counts()
        .sort_index()
        .to_dict(),
    )

    print(
        "valid size:",
        len(valid_df),
    )

    print(
        "valid labels:",
        valid_df[
            args.label_column
        ]
        .value_counts()
        .sort_index()
        .to_dict(),
    )

    # --------------------------------------------------
    # Tokenizer / Model
    # --------------------------------------------------

    print(
        "\n=== Loading tokenizer/model ==="
    )

    tokenizer = (
        AutoTokenizer
        .from_pretrained(
            args.model_name,
            use_fast=not args.use_slow_tokenizer,
        )
    )

    print(
        "tokenizer:",
        tokenizer.__class__.__name__,
    )

    model = (
        AutoModelForSequenceClassification
        .from_pretrained(
            args.model_name,
            num_labels=2,
            id2label={
                0: "BENIGN",
                1: "ATTACK",
            },
            label2id={
                "BENIGN": 0,
                "ATTACK": 1,
            },
        )
    )

    model.to(device)

    # --------------------------------------------------
    # Dataset / DataLoader
    # --------------------------------------------------

    train_dataset = (
        TextClassificationDataset(
            train_df,
            tokenizer,
            text_column=args.text_column,
            label_column=args.label_column,
            max_length=args.max_length,
        )
    )

    valid_dataset = (
        TextClassificationDataset(
            valid_df,
            tokenizer,
            text_column=args.text_column,
            label_column=args.label_column,
            max_length=args.max_length,
        )
    )

    generator = torch.Generator()
    generator.manual_seed(
        args.seed
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        generator=generator,
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
        weight_decay=args.weight_decay,
    )

    scaler = torch.cuda.amp.GradScaler(
        enabled=use_fp16
    )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    output_dir = Path(
        args.output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    best_model_dir = (
        output_dir / "best_model"
    )

    best_f1 = -1.0
    best_epoch = None

    history = []

    # --------------------------------------------------
    # Training
    # --------------------------------------------------

    print("\n=== Training ===")

    for epoch in range(
        args.epochs
    ):

        model.train()

        total_loss = 0.0

        for batch in train_loader:

            optimizer.zero_grad()

            labels = (
                batch["labels"]
                .to(device)
            )

            inputs = {
                key: value.to(device)
                for key, value
                in batch.items()
                if key != "labels"
            }

            with torch.cuda.amp.autocast(
                enabled=use_fp16
            ):
                outputs = model(
                    **inputs,
                    labels=labels,
                )

                loss = outputs.loss

            scaler.scale(
                loss
            ).backward()

            scaler.step(
                optimizer
            )

            scaler.update()

            total_loss += (
                loss.item()
            )

        average_loss = (
            total_loss
            / len(train_loader)
        )

        # ----------------------------------------------
        # Validation after each epoch
        # ----------------------------------------------

        (
            metrics,
            labels,
            predictions,
            attack_scores,
        ) = evaluate_model(
            model,
            valid_loader,
            device,
        )

        current_f1 = float(
            metrics["f1"]
        )

        epoch_result = {
            "epoch": epoch + 1,
            "train_loss": (
                average_loss
            ),
            **metrics,
        }

        history.append(
            epoch_result
        )

        print()
        print(
            f"Epoch "
            f"{epoch + 1}/"
            f"{args.epochs}"
        )

        print(
            f"train loss      : "
            f"{average_loss:.4f}"
        )

        for key, value in (
            metrics.items()
        ):
            if isinstance(
                value,
                float,
            ):
                print(
                    f"{key:16s}: "
                    f"{value:.4f}"
                )
            else:
                print(
                    f"{key:16s}: "
                    f"{value}"
                )

        # ----------------------------------------------
        # Save best model by validation F1
        # ----------------------------------------------

        if current_f1 > best_f1:

            best_f1 = (
                current_f1
            )

            best_epoch = (
                epoch + 1
            )

            model.save_pretrained(
                best_model_dir
            )

            tokenizer.save_pretrained(
                best_model_dir
            )

            print(
                "-> best model updated "
                f"(F1={best_f1:.4f})"
            )

    # --------------------------------------------------
    # Reload Best Model
    # --------------------------------------------------

    print(
        "\n=== Reload Best Model ==="
    )

    print(
        "best epoch:",
        best_epoch,
    )

    print(
        "best validation F1:",
        f"{best_f1:.4f}",
    )

    model = (
        AutoModelForSequenceClassification
        .from_pretrained(
            best_model_dir
        )
    )

    model.to(device)

    # --------------------------------------------------
    # Final Validation
    # --------------------------------------------------

    print(
        "\n=== Final Validation ==="
    )

    (
        final_metrics,
        labels,
        predictions,
        attack_scores,
    ) = evaluate_model(
        model,
        valid_loader,
        device,
    )

    for key, value in (
        final_metrics.items()
    ):

        if isinstance(
            value,
            float,
        ):
            print(
                f"{key:16s}: "
                f"{value:.4f}"
            )
        else:
            print(
                f"{key:16s}: "
                f"{value}"
            )

    # --------------------------------------------------
    # Save Results
    # --------------------------------------------------

    result_df = (
        valid_df.copy()
    )

    result_df[
        "prediction"
    ] = predictions

    result_df[
        "attack_score"
    ] = attack_scores

    result_df.to_csv(
        output_dir
        / "validation_results.csv",
        index=False,
    )

    final_metrics[
        "best_epoch"
    ] = best_epoch

    final_metrics[
        "best_validation_f1"
    ] = best_f1

    final_metrics[
        "model_name"
    ] = args.model_name

    final_metrics[
        "seed"
    ] = args.seed

    final_metrics[
        "max_length"
    ] = args.max_length

    final_metrics[
        "batch_size"
    ] = args.batch_size

    final_metrics[
        "learning_rate"
    ] = args.learning_rate

    with open(
        output_dir
        / "metrics.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            final_metrics,
            f,
            ensure_ascii=False,
            indent=2,
        )

    pd.DataFrame(
        history
    ).to_csv(
        output_dir
        / "training_history.csv",
        index=False,
    )

    print("\n=== Saved ===")

    print(
        output_dir
        / "validation_results.csv"
    )

    print(
        output_dir
        / "metrics.json"
    )

    print(
        output_dir
        / "training_history.csv"
    )

    print(
        best_model_dir
    )

    print(
        "\nTRAINING PIPELINE SUCCESS"
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model-name",
        default=(
            "monologg/"
            "koelectra-base-v3-discriminator"
        ),
    )

    parser.add_argument(
        "--train",
        default=(
            "data/processed/"
            "train_demo.csv"
        ),
    )

    parser.add_argument(
        "--valid",
        default=(
            "data/processed/"
            "valid_demo.csv"
        ),
    )

    parser.add_argument(
        "--output-dir",
        default="results/demo",
    )

    parser.add_argument(
        "--text-column",
        default="text",
    )

    parser.add_argument(
        "--label-column",
        default="label",
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
        "--weight-decay",
        type=float,
        default=0.01,
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

    parser.add_argument(
        "--max-train-samples",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--max-valid-samples",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--fp16",
        action="store_true",
    )

    parser.add_argument(
        "--use-slow-tokenizer",
        action="store_true",
        help=(
            "Use the model's slow tokenizer. "
            "Recommended for mDeBERTa to preserve "
            "SentencePiece byte-fallback behavior."
        ),
    )

    args = parser.parse_args()

    main(args)
