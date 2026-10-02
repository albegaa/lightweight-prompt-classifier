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


def load_json(path):
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


def load_changed_only(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            "Missing KG obfuscated analysis file: "
            f"{path}"
        )

    df = pd.read_csv(path)

    if "scope" not in df.columns:
        raise ValueError(
            f"'scope' column missing: {path}"
        )

    selected = df.loc[
        df["scope"] == "changed_only"
    ]

    if len(selected) != 1:
        raise ValueError(
            "Expected exactly one changed_only row "
            f"in {path}, found {len(selected)}"
        )

    return selected.iloc[0]


def pct(value):
    return float(value) * 100.0


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate the Step 1 KoreanGuardrail "
            "supplementary evaluation summary."
        )
    )

    parser.add_argument(
        "--results-root",
        default="results/step1",
    )

    parser.add_argument(
        "--output",
        default="results/step1/kg_summary.csv",
    )

    args = parser.parse_args()

    root = Path(
        args.results_root
    )

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
            / "kg_clean"
            / "metrics.json"
        )

        obfuscated_path = (
            base
            / "kg_obfuscated"
            / "analysis"
            / "obfuscated_overall.csv"
        )

        clean = load_json(
            clean_path
        )

        obfuscated = load_changed_only(
            obfuscated_path
        )

        row = {
            "model": model_name,
            "training": training_type,

            "kg_clean_n": int(
                clean["n"]
            ),

            "kg_clean_accuracy": pct(
                clean["accuracy"]
            ),

            "kg_clean_precision": pct(
                clean["precision"]
            ),

            "kg_clean_recall": pct(
                clean["recall"]
            ),

            "kg_clean_f1": pct(
                clean["f1"]
            ),

            "kg_clean_fpr": pct(
                clean["fpr"]
            ),

            "kg_clean_fnr": pct(
                clean["fnr"]
            ),

            "kg_obfuscated_total_rows": int(
                obfuscated["total_rows"]
            ),

            "kg_obfuscated_changed_rows": int(
                obfuscated["changed_rows"]
            ),

            "kg_obfuscated_application_rate": pct(
                obfuscated["application_rate"]
            ),

            "kg_obfuscated_n": int(
                obfuscated["n"]
            ),

            "kg_obfuscated_accuracy": pct(
                obfuscated["accuracy"]
            ),

            "kg_obfuscated_precision": pct(
                obfuscated["precision"]
            ),

            "kg_obfuscated_recall": pct(
                obfuscated["recall"]
            ),

            "kg_obfuscated_f1": pct(
                obfuscated["f1"]
            ),

            "kg_obfuscated_fpr": pct(
                obfuscated["fpr"]
            ),

            "kg_obfuscated_fnr": pct(
                obfuscated["fnr"]
            ),
        }

        row["kg_f1_drop_pp"] = (
            row["kg_clean_f1"]
            - row["kg_obfuscated_f1"]
        )

        row["kg_recall_drop_pp"] = (
            row["kg_clean_recall"]
            - row["kg_obfuscated_recall"]
        )

        rows.append(
            row
        )

    df = pd.DataFrame(
        rows
    )

    output = Path(
        args.output
    )

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
        "kg_clean_recall",
        "kg_clean_f1",
        "kg_clean_fpr",
        "kg_obfuscated_application_rate",
        "kg_obfuscated_recall",
        "kg_obfuscated_f1",
        "kg_obfuscated_fpr",
        "kg_f1_drop_pp",
        "kg_recall_drop_pp",
    ]

    print(
        "===== STEP 1 KOREANGUARDRAIL SUMMARY ====="
    )

    print(
        "KG obfuscated metrics:"
        " changed=true rows only"
    )

    print()

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
