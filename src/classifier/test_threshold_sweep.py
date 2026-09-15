from threshold_sweep import sweep_thresholds


# --------------------------------------------------
# 0 = Benign
# 1 = Attack
# --------------------------------------------------

y_true = [
    0, 0, 0, 0, 0,
    1, 1, 1, 1, 1
]


# 학습된 모델이 출력했다고 가정한 P(Attack)
attack_probabilities = [
    0.05,   # benign
    0.10,   # benign
    0.25,   # benign
    0.45,   # benign - ambiguous
    0.85,   # benign - 위험한 오탐

    0.15,   # attack - 위험한 미탐
    0.40,   # attack - ambiguous
    0.65,   # attack
    0.80,   # attack
    0.95    # attack
]


low_values = [
    0.1,
    0.2,
    0.3,
    0.4
]

high_values = [
    0.6,
    0.7,
    0.8,
    0.9
]


results = sweep_thresholds(
    y_true,
    attack_probabilities,
    low_values,
    high_values
)


print(
    f"{'T_LOW':>6} "
    f"{'T_HIGH':>6} "
    f"{'JG_RATE':>8} "
    f"{'LEAK':>8} "
    f"{'BLOCK':>8}"
)

print("-" * 44)


for r in results:

    print(
        f"{r['t_low']:>6.2f} "
        f"{r['t_high']:>6.2f} "
        f"{r['jailguard_call_rate']:>8.2f} "
        f"{r['attack_leakage_rate']:>8.2f} "
        f"{r['benign_block_rate']:>8.2f}"
    )


print("\nTHRESHOLD SWEEP TEST SUCCESS")
