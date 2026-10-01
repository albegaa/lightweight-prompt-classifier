#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd


def load_data(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    if path.suffix.lower() == ".jsonl":
        return pd.read_json(path, lines=True)

    raise ValueError(
        f"Unsupported format: {path.suffix}. "
        "Use .csv or .jsonl"
    )


def check_basic(
    name,
    df,
    text_column,
    label_column,
):
    errors = []
    warnings = []

    print(f"\n===== {name} =====")
    print("rows:", len(df))
    print("columns:", list(df.columns))

    required = {
        text_column,
        label_column,
    }

    missing = required - set(df.columns)

    if missing:
        errors.append(
            f"{name}: missing columns {sorted(missing)}"
        )
        return errors, warnings

    null_text = df[text_column].isna().sum()
    null_label = df[label_column].isna().sum()

    print("null text:", int(null_text))
    print("null label:", int(null_label))

    if null_text > 0:
        errors.append(
            f"{name}: {null_text} null texts"
        )

    if null_label > 0:
        errors.append(
            f"{name}: {null_label} null labels"
        )

    labels = set(
        pd.to_numeric(
            df[label_column],
            errors="coerce",
        )
        .dropna()
        .astype(int)
        .tolist()
    )

    print(
        "label counts:",
        df[label_column]
        .value_counts(dropna=False)
        .sort_index()
        .to_dict(),
    )

    if not labels.issubset({0, 1}):
        errors.append(
            f"{name}: invalid labels {sorted(labels)}"
        )

    empty_text = (
        df[text_column]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    print("empty text:", int(empty_text))

    if empty_text > 0:
        errors.append(
            f"{name}: {empty_text} empty texts"
        )

    duplicate_texts = (
        df[text_column]
        .astype(str)
        .duplicated()
        .sum()
    )

    print(
        "duplicate texts within split:",
        int(duplicate_texts),
    )

    if duplicate_texts > 0:
        warnings.append(
            f"{name}: {duplicate_texts} duplicate texts "
            "within the same split"
        )

    # Same text with conflicting labels
    conflict = (
        df.groupby(text_column)[label_column]
        .nunique()
    )

    conflict_count = int(
        (conflict > 1).sum()
    )

    print(
        "conflicting-label texts:",
        conflict_count,
    )

    if conflict_count > 0:
        errors.append(
            f"{name}: {conflict_count} texts have "
            "conflicting labels"
        )

    return errors, warnings


def find_group_column(
    datasets,
    requested,
):
    if requested:
        missing = [
            name
            for name, df in datasets.items()
            if requested not in df.columns
        ]

        if missing:
            print(
                "\nWARNING: requested group column "
                f"'{requested}' missing from: "
                + ", ".join(missing)
            )
            return None

        return requested

    candidates = [
        "base_prompt_id",
        "seed_id",
    ]

    for column in candidates:
        if all(
            column in df.columns
            for df in datasets.values()
        ):
            return column

    return None


def overlap_count(
    df_a,
    df_b,
    column,
):
    a = set(
        df_a[column]
        .dropna()
        .astype(str)
    )

    b = set(
        df_b[column]
        .dropna()
        .astype(str)
    )

    return len(a & b)


def text_overlap_count(
    df_a,
    df_b,
    text_column,
):
    a = set(
        df_a[text_column]
        .dropna()
        .astype(str)
    )

    b = set(
        df_b[text_column]
        .dropna()
        .astype(str)
    )

    return len(a & b)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--train",
        required=True,
    )

    parser.add_argument(
        "--valid",
        required=True,
    )

    parser.add_argument(
        "--test",
        default=None,
    )

    parser.add_argument(
        "--augmented-train",
        default=None,
    )

    parser.add_argument(
        "--obfuscated-test",
        default=None,
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
        "--group-column",
        default=None,
        help=(
            "Base prompt grouping column. "
            "If omitted, auto-detects "
            "base_prompt_id or seed_id."
        ),
    )

    args = parser.parse_args()

    file_args = {
        "train": args.train,
        "valid": args.valid,
        "test": args.test,
        "augmented_train": args.augmented_train,
        "obfuscated_test": args.obfuscated_test,
    }

    datasets = {}

    for name, path in file_args.items():
        if path:
            datasets[name] = load_data(path)

    errors = []
    warnings = []

    print("===== STEP 1 DATA VALIDATION =====")

    for name, df in datasets.items():
        e, w = check_basic(
            name,
            df,
            args.text_column,
            args.label_column,
        )

        errors.extend(e)
        warnings.extend(w)

    # --------------------------------------------------
    # Exact-text leakage
    # --------------------------------------------------

    print("\n===== EXACT TEXT LEAKAGE =====")

    forbidden_text_pairs = [
        ("train", "valid"),
        ("train", "test"),
        ("valid", "test"),
        ("augmented_train", "valid"),
        ("augmented_train", "test"),
        ("train", "obfuscated_test"),
        ("augmented_train", "obfuscated_test"),
        ("valid", "obfuscated_test"),
    ]

    for left, right in forbidden_text_pairs:

        if (
            left not in datasets
            or right not in datasets
        ):
            continue

        n = text_overlap_count(
            datasets[left],
            datasets[right],
            args.text_column,
        )

        print(
            f"{left} <-> {right}: {n}"
        )

        if n > 0:
            errors.append(
                f"Exact-text leakage: "
                f"{left} <-> {right} = {n}"
            )

    # test <-> obfuscated_test overlap is not treated
    # as an error because they may share the same
    # held-out base prompts by design.

    # --------------------------------------------------
    # Base-prompt / seed leakage
    # --------------------------------------------------

    group_column = find_group_column(
        datasets,
        args.group_column,
    )

    print("\n===== GROUP LEAKAGE =====")

    if group_column is None:
        print(
            "Group column not available."
        )
        print(
            "WARNING: base-prompt leakage "
            "could not be checked."
        )

        warnings.append(
            "No common base_prompt_id/seed_id; "
            "group leakage was not checked."
        )

    else:
        print(
            "group column:",
            group_column,
        )

        # train and augmented_train are intentionally
        # allowed to share base prompts.
        #
        # test and obfuscated_test are also intentionally
        # allowed to share held-out base prompts.

        forbidden_group_pairs = [
            ("train", "valid"),
            ("train", "test"),
            ("train", "obfuscated_test"),
            ("augmented_train", "valid"),
            ("augmented_train", "test"),
            ("augmented_train", "obfuscated_test"),
            ("valid", "test"),
            ("valid", "obfuscated_test"),
        ]

        for left, right in forbidden_group_pairs:

            if (
                left not in datasets
                or right not in datasets
            ):
                continue

            n = overlap_count(
                datasets[left],
                datasets[right],
                group_column,
            )

            print(
                f"{left} <-> {right}: {n}"
            )

            if n > 0:
                errors.append(
                    f"Group leakage ({group_column}): "
                    f"{left} <-> {right} = {n}"
                )

        if (
            "test" in datasets
            and "obfuscated_test" in datasets
        ):
            n = overlap_count(
                datasets["test"],
                datasets["obfuscated_test"],
                group_column,
            )

            print(
                "test <-> obfuscated_test "
                f"(allowed): {n}"
            )

    # --------------------------------------------------
    # Final
    # --------------------------------------------------

    print("\n===== WARNINGS =====")

    if warnings:
        for item in warnings:
            print("WARNING:", item)
    else:
        print("none")

    print("\n===== ERRORS =====")

    if errors:
        for item in errors:
            print("ERROR:", item)

        print(
            f"\nVALIDATION FAILED "
            f"({len(errors)} error(s))"
        )

        sys.exit(1)

    print("none")
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
