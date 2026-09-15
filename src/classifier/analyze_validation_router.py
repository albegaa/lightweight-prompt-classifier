from pathlib import Path

import pandas as pd

from threshold_sweep import sweep_thresholds


INPUT_PATH = "results/demo/validation_results.csv"
OUTPUT_PATH = "results/demo/threshold_sweep.csv"


# --------------------------------------------------
# Load validation predictions
# --------------------------------------------------

df = pd.read_csv(INPUT_PATH)

required_columns = {
    "label",
    "p_attack",
}

if not required_columns.issubset(df.columns):
    raise ValueError(
        "validation_results.csv must contain "
        "label and p_attack columns."
    )


y_true = df["label"].astype(int).tolist()
attack_probabilities = (
    df["p_attack"].astype(float).tolist()
)


# --------------------------------------------------
# Probability distribution
# --------------------------------------------------

print("=== Validation Probabilities ===")

display_df = df[
    [
        "text",
        "label",
        "prediction",
        "p_attack",
    ]
].sort_values("p_attack")

print(
    display_df.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}",
    )
)


# --------------------------------------------------
# Fine-grained threshold candidates
# --------------------------------------------------

low_values = [
    0.40,
    0.42,
    0.44,
    0.46,
    0.48,
    0.50,
]

high_values = [
    0.50,
    0.52,
    0.54,
    0.56,
    0.58,
    0.60,
]


# --------------------------------------------------
# Sweep
# --------------------------------------------------

results = sweep_thresholds(
    y_true,
    attack_probabilities,
    low_values,
    high_values,
)


result_df = pd.DataFrame(results)


# --------------------------------------------------
# Sort
# --------------------------------------------------

result_df = result_df.sort_values(
    by=[
        "attack_leakage_rate",
        "benign_block_rate",
        "jailguard_call_rate",
    ],
    ascending=[
        True,
        True,
        True,
    ],
)


# --------------------------------------------------
# Print
# --------------------------------------------------

columns = [
    "t_low",
    "t_high",
    "jailguard_call_rate",
    "attack_leakage_rate",
    "benign_block_rate",
]

print("\n=== Fine-grained Router Analysis ===")

print(
    result_df[columns].to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}",
    )
)


# --------------------------------------------------
# Save
# --------------------------------------------------

Path(OUTPUT_PATH).parent.mkdir(
    parents=True,
    exist_ok=True,
)

result_df.to_csv(
    OUTPUT_PATH,
    index=False,
)

print()
print("Saved:", OUTPUT_PATH)
print("\nVALIDATION ROUTER ANALYSIS SUCCESS")
