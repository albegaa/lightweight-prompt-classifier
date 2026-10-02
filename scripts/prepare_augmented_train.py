#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import pandas as pd


def load_data(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".jsonl":
        return pd.read_json(path, lines=True)

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    raise ValueError(
        f"Unsupported format: {path.suffix}. "
        "Use .jsonl or .csv"
    )


def has_seed_id(df):
    if "seed_id" not in df.columns:
        return pd.Series(
            False,
            index=df.index,
            dtype=bool,
        )

    return (
        df["seed_id"].notna()
        & df["seed_id"]
        .astype(str)
        .str.strip()
        .ne("")
    )


def verify_base_rows(
    original,
    candidate_base,
):
    original_ids = set(
        original["id"].astype(str)
    )

    candidate_ids = set(
        candidate_base["id"].astype(str)
    )

    missing = original_ids - candidate_ids
    extra = candidate_ids - original_ids

    if missing:
        raise ValueError(
            "Combined augmented file is missing "
            f"{len(missing)} original train row(s)."
        )

    if extra:
        raise ValueError(
            "Combined augmented file contains "
            f"{len(extra)} unexpected base row(s)."
        )

    left = (
        original[
            ["id", "text", "label", "source"]
        ]
        .copy()
    )

    right = (
        candidate_base[
            ["id", "text", "label", "source"]
        ]
        .copy()
    )

    left["id"] = left["id"].astype(str)
    right["id"] = right["id"].astype(str)

    merged = left.merge(
        right,
        on="id",
        suffixes=("_original", "_candidate"),
    )

    for column in [
        "text",
        "label",
        "source",
    ]:
        mismatch = (
            merged[f"{column}_original"]
            .astype(str)
            != merged[f"{column}_candidate"]
            .astype(str)
        )

        n = int(mismatch.sum())

        if n > 0:
            raise ValueError(
                f"{n} original row(s) have "
                f"mismatched '{column}' values "
                "inside the augmented file."
            )


def verify_variants(
    original,
    variants,
):
    if len(variants) == 0:
        raise ValueError(
            "No augmented variant rows found."
        )

    required = {
        "id",
        "text",
        "label",
        "source",
        "seed_id",
        "technique",
        "intensity",
        "changed",
        "n_changed",
    }

    missing = required - set(
        variants.columns
    )

    if missing:
        raise ValueError(
            "Variant rows are missing columns: "
            f"{sorted(missing)}"
        )

    original_ids = set(
        original["id"].astype(str)
    )

    seed_ids = set(
        variants["seed_id"]
        .astype(str)
    )

    unknown = seed_ids - original_ids

    if unknown:
        raise ValueError(
            f"{len(unknown)} seed_id value(s) "
            "do not exist in original train."
        )

    changed_false = int(
        variants["changed"]
        .eq(False)
        .sum()
    )

    if changed_false:
        raise ValueError(
            f"{changed_false} variant row(s) "
            "have changed=false."
        )

    duplicate_variant_ids = int(
        variants["id"]
        .astype(str)
        .duplicated()
        .sum()
    )

    if duplicate_variant_ids:
        raise ValueError(
            f"{duplicate_variant_ids} duplicate "
            "variant id(s) found."
        )

    overlap = (
        set(original["id"].astype(str))
        & set(variants["id"].astype(str))
    )

    if overlap:
        raise ValueError(
            f"{len(overlap)} variant id(s) collide "
            "with original train ids."
        )


def write_jsonl(df, path):
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    records = df.to_dict(
        orient="records"
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        for row in records:
            clean = {}

            for key, value in row.items():
                if pd.isna(value):
                    clean[key] = None
                    continue

                if key == "changed":
                    if isinstance(value, bool):
                        clean[key] = value
                    elif value in (0, 0.0, 1, 1.0):
                        clean[key] = bool(value)
                    else:
                        raise ValueError(
                            f"Invalid changed value: {value!r}"
                        )
                elif key == "n_changed":
                    numeric = float(value)
                    if not numeric.is_integer():
                        raise ValueError(
                            f"Invalid n_changed value: {value!r}"
                        )
                    clean[key] = int(numeric)
                elif key == "intensity":
                    clean[key] = round(float(value), 10)
                else:
                    clean[key] = value

            f.write(
                json.dumps(
                    clean,
                    ensure_ascii=False,
                )
                + "\n"
            )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a standardized combined "
            "Step 1 augmented training JSONL."
        )
    )

    parser.add_argument(
        "--original-train",
        required=True,
    )

    parser.add_argument(
        "--augmented-input",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    original = load_data(
        args.original_train
    )

    augmented = load_data(
        args.augmented_input
    )

    required_base = {
        "id",
        "text",
        "label",
        "source",
    }

    for name, df in [
        ("original train", original),
        ("augmented input", augmented),
    ]:
        missing = (
            required_base
            - set(df.columns)
        )

        if missing:
            raise ValueError(
                f"{name} is missing columns: "
                f"{sorted(missing)}"
            )

    variant_mask = has_seed_id(
        augmented
    )

    variants = (
        augmented.loc[variant_mask]
        .copy()
    )

    base_rows = (
        augmented.loc[~variant_mask]
        .copy()
    )

    print(
        "original train rows:",
        len(original),
    )

    print(
        "augmented input rows:",
        len(augmented),
    )

    print(
        "detected base rows:",
        len(base_rows),
    )

    print(
        "detected variant rows:",
        len(variants),
    )

    verify_variants(
        original,
        variants,
    )

    if len(base_rows) == 0:
        mode = "variant-only"

        combined = pd.concat(
            [
                original,
                variants,
            ],
            ignore_index=True,
            sort=False,
        )

    else:
        mode = "combined"

        verify_base_rows(
            original,
            base_rows,
        )

        combined = augmented.copy()

    duplicate_ids = int(
        combined["id"]
        .astype(str)
        .duplicated()
        .sum()
    )

    if duplicate_ids:
        raise ValueError(
            f"Combined training data contains "
            f"{duplicate_ids} duplicate id(s)."
        )

    print("input mode:", mode)
    print(
        "final training rows:",
        len(combined),
    )

    print(
        "final label counts:",
        combined["label"]
        .value_counts()
        .sort_index()
        .to_dict(),
    )

    write_jsonl(
        combined,
        args.output,
    )

    print(
        "saved:",
        args.output,
    )


if __name__ == "__main__":
    main()
