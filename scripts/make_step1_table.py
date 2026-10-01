#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import pandas as pd


EXPERIMENTS = [
    ("KoELECTRA", "Original", "koelectra", "original"),
    ("KoELECTRA", "Augmented", "koelectra", "augmented"),
    ("mDeBERTa", "Original", "mdeberta", "original"),
    ("mDeBERTa", "Augmented", "mdeberta", "augmented"),
]


def load_metrics(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Missing metrics file: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def pct(value):
    return float(value) * 100.0


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--results-root",
        default="results/step1",
    )

    parser.add_argument(
        "--output",
        default="results/step1/table2_summary.csv",
    )

    args = parser.parse_args()

    root = Path(args.results_root)

    rows = []

    for (
        model_name,
        training_type,
        model_key,
        training_key,
    ) in EXPERIMENTS:

        base = (
            root
            / model_key
            / training_key
            / "eval"
        )

        clean_path = (
            base
            / "clean"
            / "metrics.json"
        )

        obfuscated_path = (
            base
            / "obfuscated"
            / "metrics.json"
        )

        clean = load_metrics(
            clean_path
        )

        obfuscated = load_metrics(
            obfuscated_path
        )

        row = {
            "model": model_name,
            "training": training_type,

            "clean_n": clean["n"],
            "clean_accuracy": pct(
                clean["accuracy"]
            ),
            "clean_precision": pct(
                clean["precision"]
            ),
            "clean_recall": pct(
                clean["recall"]
            ),
            "clean_f1": pct(
                clean["f1"]
            ),
            "clean_fpr": pct(
                clean["fpr"]
            ),
            "clean_fnr": pct(
                clean["fnr"]
            ),

            "obfuscated_n": obfuscated["n"],
            "obfuscated_accuracy": pct(
                obfuscated["accuracy"]
            ),
            "obfuscated_precision": pct(
                obfuscated["precision"]
            ),
            "obfuscated_recall": pct(
                obfuscated["recall"]
            ),
            "obfuscated_f1": pct(
                obfuscated["f1"]
            ),
            "obfuscated_fpr": pct(
                obfuscated["fpr"]
            ),
            "obfuscated_fnr": pct(
                obfuscated["fnr"]
            ),
        }

        row["f1_drop_pp"] = (
            row["clean_f1"]
            - row["obfuscated_f1"]
        )

        row["recall_drop_pp"] = (
            row["clean_recall"]
            - row["obfuscated_recall"]
        )

        rows.append(row)

    df = pd.DataFrame(rows)

    output = Path(args.output)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output,
        index=False,
        encoding="utf-8-sig",
        float_format="%.2f",
    )

    display_columns = [
        "model",
        "training",
        "clean_accuracy",
        "clean_recall",
        "clean_f1",
        "clean_fpr",
        "obfuscated_accuracy",
        "obfuscated_recall",
        "obfuscated_f1",
        "obfuscated_fpr",
        "f1_drop_pp",
    ]

    print("===== STEP 1 TABLE 2 =====")

    print(
        df[display_columns]
        .round(2)
        .to_string(index=False)
    )

    print()
    print("Saved:")
    print(output)


if __name__ == "__main__":
    main()
