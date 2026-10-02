#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd


BASE_COLUMNS = {
    "id",
    "text",
    "label",
    "source",
}

VARIANT_COLUMNS = {
    "seed_id",
    "technique",
    "intensity",
    "changed",
    "n_changed",
}


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


def nonempty_string_mask(series):
    return (
        series.notna()
        & series.astype(str).str.strip().ne("")
    )


def variant_mask(df):
    if "seed_id" not in df.columns:
        return pd.Series(
            False,
            index=df.index,
            dtype=bool,
        )

    return nonempty_string_mask(df["seed_id"])


def group_ids(df):
    if "id" not in df.columns:
        return pd.Series(
            index=df.index,
            dtype="object",
        )

    groups = df["id"].astype(str).copy()

    mask = variant_mask(df)

    if mask.any():
        groups.loc[mask] = (
            df.loc[mask, "seed_id"]
            .astype(str)
        )

    return groups


def check_basic(name, df):
    errors = []
    warnings = []

    print(f"\n===== {name} =====")
    print("rows:", len(df))
    print("columns:", list(df.columns))

    missing = BASE_COLUMNS - set(df.columns)

    if missing:
        errors.append(
            f"{name}: missing base columns "
            f"{sorted(missing)}"
        )
        return errors, warnings

    for column in BASE_COLUMNS:
        null_count = int(df[column].isna().sum())

        print(
            f"null {column}:",
            null_count,
        )

        if null_count > 0:
            errors.append(
                f"{name}: {null_count} null "
                f"values in '{column}'"
            )

    empty_text = int(
        df["text"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    empty_id = int(
        df["id"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    empty_source = int(
        df["source"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    print("empty text:", empty_text)
    print("empty id:", empty_id)
    print("empty source:", empty_source)

    if empty_text:
        errors.append(
            f"{name}: {empty_text} empty texts"
        )

    if empty_id:
        errors.append(
            f"{name}: {empty_id} empty ids"
        )

    if empty_source:
        errors.append(
            f"{name}: {empty_source} empty sources"
        )

    numeric_labels = pd.to_numeric(
        df["label"],
        errors="coerce",
    )

    non_numeric_mask = (
        df["label"].notna()
        & numeric_labels.isna()
    )

    invalid_numeric = int(
        non_numeric_mask.sum()
    )

    if invalid_numeric > 0:
        errors.append(
            f"{name}: {invalid_numeric} "
            "non-numeric labels"
        )

    invalid_value_mask = (
        numeric_labels.notna()
        & ~numeric_labels.isin([0, 1])
    )

    invalid_values = sorted(
        numeric_labels.loc[
            invalid_value_mask
        ]
        .unique()
        .tolist()
    )

    labels = set(
        numeric_labels
        .dropna()
        .tolist()
    )

    print(
        "label counts:",
        df["label"]
        .value_counts(dropna=False)
        .sort_index()
        .to_dict(),
    )

    if invalid_values:
        errors.append(
            f"{name}: invalid labels "
            f"{invalid_values}"
        )

    duplicate_ids = int(
        df["id"]
        .astype(str)
        .duplicated()
        .sum()
    )

    print(
        "duplicate ids:",
        duplicate_ids,
    )

    if duplicate_ids > 0:
        errors.append(
            f"{name}: {duplicate_ids} "
            "duplicate ids"
        )

    duplicate_texts = int(
        df["text"]
        .astype(str)
        .duplicated()
        .sum()
    )

    print(
        "duplicate texts within dataset:",
        duplicate_texts,
    )

    if duplicate_texts > 0:
        warnings.append(
            f"{name}: {duplicate_texts} "
            "duplicate texts within dataset"
        )

    conflict = (
        df.groupby("text")["label"]
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
            f"{name}: {conflict_count} texts "
            "have conflicting labels"
        )

    return errors, warnings


def check_variant_schema(
    name,
    df,
    require_variant=False,
    augmented=False,
):
    errors = []
    warnings = []

    mask = variant_mask(df)
    n_variant = int(mask.sum())

    print(
        f"{name} variant rows:",
        n_variant,
    )

    if require_variant and n_variant != len(df):
        errors.append(
            f"{name}: expected every row to have "
            f"seed_id, but {len(df) - n_variant} "
            "rows do not"
        )

    if n_variant == 0:
        if require_variant:
            missing = (
                VARIANT_COLUMNS
                - set(df.columns)
            )

            if missing:
                errors.append(
                    f"{name}: missing variant columns "
                    f"{sorted(missing)}"
                )

        return errors, warnings

    missing = (
        VARIANT_COLUMNS
        - set(df.columns)
    )

    if missing:
        errors.append(
            f"{name}: variant rows exist but "
            f"variant columns are missing: "
            f"{sorted(missing)}"
        )
        return errors, warnings

    variants = df.loc[mask]

    for column in VARIANT_COLUMNS:
        null_count = int(
            variants[column]
            .isna()
            .sum()
        )

        if null_count > 0:
            errors.append(
                f"{name}: {null_count} variant rows "
                f"have null '{column}'"
            )

    empty_technique = int(
        variants["technique"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    if empty_technique > 0:
        errors.append(
            f"{name}: {empty_technique} variant rows "
            "have empty technique"
        )

    intensity_numeric = pd.to_numeric(
        variants["intensity"],
        errors="coerce",
    )

    invalid_intensity = int(
        intensity_numeric.isna().sum()
    )

    if invalid_intensity > 0:
        errors.append(
            f"{name}: {invalid_intensity} variant rows "
            "have invalid intensity"
        )

    n_changed_numeric = pd.to_numeric(
        variants["n_changed"],
        errors="coerce",
    )

    invalid_n_changed = int(
        n_changed_numeric.isna().sum()
    )

    if invalid_n_changed > 0:
        errors.append(
            f"{name}: {invalid_n_changed} variant rows "
            "have invalid n_changed"
        )

    negative_n_changed = int(
        (n_changed_numeric.dropna() < 0).sum()
    )

    if negative_n_changed > 0:
        errors.append(
            f"{name}: {negative_n_changed} variant rows "
            "have negative n_changed"
        )

    changed_counts = (
        variants["changed"]
        .value_counts(dropna=False)
        .to_dict()
    )

    print(
        f"{name} changed counts:",
        changed_counts,
    )

    if augmented:
        changed_false = int(
            variants["changed"]
            .eq(False)
            .sum()
        )

        if changed_false > 0:
            errors.append(
                f"{name}: {changed_false} augmented "
                "variant rows have changed=false"
            )

    return errors, warnings


def text_overlap_count(df_a, df_b):
    a = set(
        df_a["text"]
        .dropna()
        .astype(str)
    )

    b = set(
        df_b["text"]
        .dropna()
        .astype(str)
    )

    return len(a & b)


def group_overlap_count(df_a, df_b):
    a = set(
        group_ids(df_a)
        .dropna()
        .astype(str)
    )

    b = set(
        group_ids(df_b)
        .dropna()
        .astype(str)
    )

    return len(a & b)


def check_parent_relation(
    child_name,
    child_df,
    parent_name,
    parent_df,
):
    errors = []
    warnings = []

    mask = variant_mask(child_df)

    if not mask.any():
        print(
            f"{child_name} -> {parent_name}: "
            "no variant rows"
        )
        return errors, warnings

    variants = child_df.loc[mask].copy()

    parent_ids = set(
        parent_df["id"]
        .dropna()
        .astype(str)
    )

    child_seeds = set(
        variants["seed_id"]
        .dropna()
        .astype(str)
    )

    unknown = sorted(
        child_seeds - parent_ids
    )

    print(
        f"{child_name} -> {parent_name} "
        f"unique seeds:",
        len(child_seeds),
    )

    print(
        f"{child_name} -> {parent_name} "
        f"unknown seeds:",
        len(unknown),
    )

    if unknown:
        errors.append(
            f"{child_name}: {len(unknown)} seed_id "
            f"values are not present in "
            f"{parent_name}.id"
        )

    parent_meta = (
        parent_df[
            ["id", "label", "source"]
        ]
        .copy()
    )

    parent_meta["id"] = (
        parent_meta["id"]
        .astype(str)
    )

    variants["seed_id"] = (
        variants["seed_id"]
        .astype(str)
    )

    merged = variants.merge(
        parent_meta,
        left_on="seed_id",
        right_on="id",
        how="inner",
        suffixes=("_variant", "_parent"),
    )

    if len(merged) > 0:
        label_mismatch = int(
            (
                merged["label_variant"]
                .astype(int)
                != merged["label_parent"]
                .astype(int)
            ).sum()
        )

        source_mismatch = int(
            (
                merged["source_variant"]
                .astype(str)
                != merged["source_parent"]
                .astype(str)
            ).sum()
        )

        print(
            f"{child_name} label mismatch:",
            label_mismatch,
        )

        print(
            f"{child_name} source mismatch:",
            source_mismatch,
        )

        if label_mismatch > 0:
            errors.append(
                f"{child_name}: {label_mismatch} "
                "variant rows have labels that differ "
                f"from {parent_name}"
            )

        if source_mismatch > 0:
            errors.append(
                f"{child_name}: {source_mismatch} "
                "variant rows have source values that "
                f"differ from {parent_name}"
            )

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Validate Step 1 original, augmented, "
            "obfuscated, and KoreanGuardrail datasets."
        )
    )

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
        "--kg-test",
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
        "--obfuscated-kg-test",
        default=None,
    )

    args = parser.parse_args()

    file_args = {
        "train": args.train,
        "valid": args.valid,
        "test": args.test,
        "kg_test": args.kg_test,
        "augmented_train": args.augmented_train,
        "obfuscated_test": args.obfuscated_test,
        "obfuscated_kg_test": (
            args.obfuscated_kg_test
        ),
    }

    datasets = {}

    for name, path in file_args.items():
        if path:
            datasets[name] = load_data(path)

    errors = []
    warnings = []

    print(
        "===== STEP 1 DATA VALIDATION ====="
    )

    # --------------------------------------------------
    # Basic schema
    # --------------------------------------------------

    for name, df in datasets.items():
        e, w = check_basic(
            name,
            df,
        )

        errors.extend(e)
        warnings.extend(w)

    # --------------------------------------------------
    # Variant schema
    # --------------------------------------------------

    print(
        "\n===== VARIANT SCHEMA ====="
    )

    variant_rules = {
        "augmented_train": {
            "require_variant": False,
            "augmented": True,
        },
        "obfuscated_test": {
            "require_variant": True,
            "augmented": False,
        },
        "obfuscated_kg_test": {
            "require_variant": True,
            "augmented": False,
        },
    }

    for name, rule in variant_rules.items():
        if name not in datasets:
            continue

        e, w = check_variant_schema(
            name,
            datasets[name],
            **rule,
        )

        errors.extend(e)
        warnings.extend(w)

    # --------------------------------------------------
    # Parent / variant relation
    # --------------------------------------------------

    print(
        "\n===== PARENT / VARIANT RELATION ====="
    )

    parent_pairs = [
        (
            "augmented_train",
            "train",
        ),
        (
            "obfuscated_test",
            "test",
        ),
        (
            "obfuscated_kg_test",
            "kg_test",
        ),
    ]

    for child_name, parent_name in parent_pairs:
        if (
            child_name not in datasets
            or parent_name not in datasets
        ):
            continue

        e, w = check_parent_relation(
            child_name,
            datasets[child_name],
            parent_name,
            datasets[parent_name],
        )

        errors.extend(e)
        warnings.extend(w)

    # --------------------------------------------------
    # Exact-text leakage
    # --------------------------------------------------

    print(
        "\n===== EXACT TEXT LEAKAGE ====="
    )

    forbidden_text_pairs = [
        ("train", "valid"),
        ("train", "test"),
        ("train", "kg_test"),
        ("valid", "test"),
        ("valid", "kg_test"),
        ("test", "kg_test"),

        ("train", "obfuscated_test"),
        ("train", "obfuscated_kg_test"),
        ("valid", "obfuscated_test"),
        ("valid", "obfuscated_kg_test"),

        ("augmented_train", "valid"),
        ("augmented_train", "test"),
        ("augmented_train", "kg_test"),
        ("augmented_train", "obfuscated_test"),
        ("augmented_train", "obfuscated_kg_test"),

        ("test", "obfuscated_kg_test"),
        ("kg_test", "obfuscated_test"),
        ("obfuscated_test", "obfuscated_kg_test"),
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
        )

        print(
            f"{left} <-> {right}: {n}"
        )

        if n > 0:
            errors.append(
                "Exact-text leakage: "
                f"{left} <-> {right} = {n}"
            )

    # Intentional overlap:
    # train <-> augmented_train
    # test <-> obfuscated_test
    # kg_test <-> obfuscated_kg_test

    # --------------------------------------------------
    # Source-group leakage
    # --------------------------------------------------

    print(
        "\n===== SOURCE GROUP LEAKAGE ====="
    )

    forbidden_group_pairs = [
        ("train", "valid"),
        ("train", "test"),
        ("train", "kg_test"),

        ("valid", "test"),
        ("valid", "kg_test"),
        ("test", "kg_test"),

        ("train", "obfuscated_test"),
        ("train", "obfuscated_kg_test"),
        ("valid", "obfuscated_test"),
        ("valid", "obfuscated_kg_test"),

        ("augmented_train", "valid"),
        ("augmented_train", "test"),
        ("augmented_train", "kg_test"),
        ("augmented_train", "obfuscated_test"),
        ("augmented_train", "obfuscated_kg_test"),

        ("test", "obfuscated_kg_test"),
        ("kg_test", "obfuscated_test"),
        ("obfuscated_test", "obfuscated_kg_test"),
    ]

    for left, right in forbidden_group_pairs:
        if (
            left not in datasets
            or right not in datasets
        ):
            continue

        n = group_overlap_count(
            datasets[left],
            datasets[right],
        )

        print(
            f"{left} <-> {right}: {n}"
        )

        if n > 0:
            errors.append(
                "Source-group leakage: "
                f"{left} <-> {right} = {n}"
            )

    allowed_group_pairs = [
        ("train", "augmented_train"),
        ("test", "obfuscated_test"),
        ("kg_test", "obfuscated_kg_test"),
    ]

    print(
        "\n===== EXPECTED / ALLOWED GROUP OVERLAP ====="
    )

    for left, right in allowed_group_pairs:
        if (
            left not in datasets
            or right not in datasets
        ):
            continue

        n = group_overlap_count(
            datasets[left],
            datasets[right],
        )

        print(
            f"{left} <-> {right} "
            f"(allowed): {n}"
        )

    # --------------------------------------------------
    # Final
    # --------------------------------------------------

    print(
        "\n===== WARNINGS ====="
    )

    if warnings:
        for item in warnings:
            print(
                "WARNING:",
                item,
            )
    else:
        print("none")

    print(
        "\n===== ERRORS ====="
    )

    if errors:
        for item in errors:
            print(
                "ERROR:",
                item,
            )

        print(
            f"\nVALIDATION FAILED "
            f"({len(errors)} error(s))"
        )

        sys.exit(1)

    print("none")
    print(
        "\nVALIDATION PASSED"
    )


if __name__ == "__main__":
    main()
