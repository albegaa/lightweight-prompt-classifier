import argparse
import json
from pathlib import Path

import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)


# --------------------------------------------------
# Metrics
# --------------------------------------------------

def compute_binary_metrics(y_true, y_pred):
    """
    Binary classification metrics.

    Label:
        0 = Benign
        1 = Attack

    Returns:
        accuracy
        precision
        recall
        f1
        fpr
        fnr
        tp / tn / fp / fn
    """

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    ).ravel()

    accuracy = accuracy_score(
        y_true,
        y_pred,
    )

    precision = precision_score(
        y_true,
        y_pred,
        pos_label=1,
        zero_division=0,
    )

    recall = recall_score(
        y_true,
        y_pred,
        pos_label=1,
        zero_division=0,
    )

    f1 = f1_score(
        y_true,
        y_pred,
        pos_label=1,
        zero_division=0,
    )

    # False Positive Rate
    # 정상 입력 중 공격으로 잘못 판정한 비율
    fpr = (
        fp / (fp + tn)
        if (fp + tn) > 0
        else 0.0
    )

    # False Negative Rate
    # 실제 공격 중 정상으로 잘못 판정한 비율
    fnr = (
        fn / (fn + tp)
        if (fn + tp) > 0
        else 0.0
    )

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "fpr": float(fpr),
        "fnr": float(fnr),
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
    }


# --------------------------------------------------
# Data Loading
# --------------------------------------------------

def load_dataframe(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Evaluation file does not exist: {path}"
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

        encoded = self.tokenizer(
            self.texts[idx],
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
            self.labels[idx],
            dtype=torch.long,
        )

        return item


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def run_evaluation(
    model,
    dataloader,
    device,
    use_fp16=False,
):

    model.eval()

    all_labels = []
    all_predictions = []
    all_attack_scores = []

    total_loss = 0.0

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

            with torch.cuda.amp.autocast(
                enabled=use_fp16
            ):
                outputs = model(
                    **inputs,
                    labels=labels,
                )

            total_loss += (
                outputs.loss.item()
            )

            probabilities = torch.softmax(
                outputs.logits,
                dim=-1,
            )

            # Softmax score for class 1.
            # This is not a calibrated P(Attack).
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

    metrics["loss"] = (
        total_loss
        / len(dataloader)
    )

    metrics["n"] = len(
        all_labels
    )

    return (
        metrics,
        all_labels,
        all_predictions,
        all_attack_scores,
    )


# --------------------------------------------------
# Main
# --------------------------------------------------

def main(args):

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

    print("model:", args.model)
    print("input:", args.input)
    print("output:", args.output_dir)
    print("batch size:", args.batch_size)
    print("max length:", args.max_length)
    print("fp16:", use_fp16)
    print(
        "slow tokenizer:",
        args.use_slow_tokenizer,
    )

    # --------------------------------------------------
    # Load Evaluation Data
    # --------------------------------------------------

    dataframe = load_dataframe(
        args.input
    )

    dataframe = prepare_dataframe(
        dataframe,
        args.text_column,
        args.label_column,
        args.max_samples,
    )

    print("\n=== Dataset ===")
    print(
        "rows:",
        len(dataframe),
    )

    print(
        "labels:",
        dataframe[
            args.label_column
        ]
        .value_counts()
        .sort_index()
        .to_dict(),
    )

    # --------------------------------------------------
    # Load Tokenizer / Model
    # --------------------------------------------------

    print(
        "\n=== Loading tokenizer/model ==="
    )

    tokenizer = (
        AutoTokenizer
        .from_pretrained(
            args.model,
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
            args.model
        )
    )

    model.to(device)

    # --------------------------------------------------
    # Dataset / DataLoader
    # --------------------------------------------------

    dataset = (
        TextClassificationDataset(
            dataframe,
            tokenizer,
            text_column=args.text_column,
            label_column=args.label_column,
            max_length=args.max_length,
        )
    )

    dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
    )

    # --------------------------------------------------
    # Run Evaluation
    # --------------------------------------------------

    print(
        "\n=== Evaluation ==="
    )

    (
        metrics,
        labels,
        predictions,
        attack_scores,
    ) = run_evaluation(
        model,
        dataloader,
        device,
        use_fp16=use_fp16,
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

    # --------------------------------------------------
    # Save Results
    # --------------------------------------------------

    output_dir = Path(
        args.output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_df = (
        dataframe.copy()
    )

    result_df[
        "prediction"
    ] = predictions

    result_df[
        "attack_score"
    ] = attack_scores

    result_df.to_csv(
        output_dir
        / "predictions.csv",
        index=False,
    )

    metrics[
        "model"
    ] = args.model

    metrics[
        "input_file"
    ] = str(args.input)

    metrics[
        "max_length"
    ] = args.max_length

    metrics[
        "batch_size"
    ] = args.batch_size

    metrics[
        "use_slow_tokenizer"
    ] = args.use_slow_tokenizer

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

    print(
        "\n=== Saved ==="
    )

    print(
        output_dir
        / "predictions.csv"
    )

    print(
        output_dir
        / "metrics.json"
    )

    print(
        "\nEVALUATION PIPELINE SUCCESS"
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        required=True,
        help=(
            "Fine-tuned Hugging Face model "
            "directory or model name."
        ),
    )

    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Evaluation CSV or JSONL file."
        ),
    )

    parser.add_argument(
        "--output-dir",
        required=True,
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
        "--batch-size",
        type=int,
        default=16,
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=128,
    )

    parser.add_argument(
        "--max-samples",
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
            "Use slow tokenizer. "
            "Recommended for mDeBERTa."
        ),
    )

    args = parser.parse_args()

    main(args)
