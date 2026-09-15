from evaluate import compute_binary_metrics


# --------------------------------------------------
# Label
# 0 = Benign
# 1 = Attack
# --------------------------------------------------

y_true = [
    0, 0, 0, 0,
    1, 1, 1, 1
]

y_pred = [
    0, 0, 1, 0,
    1, 1, 0, 1
]


metrics = compute_binary_metrics(
    y_true,
    y_pred
)


print("=== Confusion Matrix ===")
print("TP:", metrics["tp"])
print("TN:", metrics["tn"])
print("FP:", metrics["fp"])
print("FN:", metrics["fn"])

print("\n=== Classification Metrics ===")

for key in [
    "accuracy",
    "precision",
    "recall",
    "f1",
    "fpr",
    "fnr"
]:
    print(f"{key:10s}: {metrics[key]:.4f}")

print("\nMETRIC TEST SUCCESS")
