from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)


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
        labels=[0, 1]
    ).ravel()

    accuracy = accuracy_score(y_true, y_pred)

    precision = precision_score(
        y_true,
        y_pred,
        pos_label=1,
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        pos_label=1,
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        pos_label=1,
        zero_division=0
    )

    # False Positive Rate
    # 정상 입력 중 공격으로 잘못 차단한 비율
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    # False Negative Rate
    # 실제 공격 중 정상으로 잘못 통과시킨 비율
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
        "fnr": fnr,
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
    }
