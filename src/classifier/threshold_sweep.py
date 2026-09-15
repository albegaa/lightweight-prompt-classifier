from router import route_batch


def evaluate_router(
    y_true,
    attack_probabilities,
    t_low,
    t_high
):
    """
    Router 자체의 동작을 평가한다.

    Label:
        0 = Benign
        1 = Attack

    주의:
        JailGuard의 최종 판정 결과가 아직 없으므로
        전체 시스템 Recall/FNR은 계산하지 않는다.
    """

    routes = route_batch(
        attack_probabilities,
        t_low=t_low,
        t_high=t_high
    )

    total = len(y_true)

    benign_count = routes.count("benign")
    jailguard_count = routes.count("jailguard")
    attack_count = routes.count("attack")

    actual_attack = sum(label == 1 for label in y_true)
    actual_benign = sum(label == 0 for label in y_true)

    # 실제 공격인데 바로 benign으로 통과한 경우
    attack_leak = sum(
        label == 1 and route == "benign"
        for label, route in zip(y_true, routes)
    )

    # 실제 benign인데 바로 attack으로 차단한 경우
    benign_block = sum(
        label == 0 and route == "attack"
        for label, route in zip(y_true, routes)
    )

    return {
        "t_low": t_low,
        "t_high": t_high,

        "benign_direct_rate":
            benign_count / total,

        "jailguard_call_rate":
            jailguard_count / total,

        "attack_direct_rate":
            attack_count / total,

        "attack_leakage_rate":
            attack_leak / actual_attack
            if actual_attack > 0 else 0.0,

        "benign_block_rate":
            benign_block / actual_benign
            if actual_benign > 0 else 0.0,
    }


def sweep_thresholds(
    y_true,
    attack_probabilities,
    low_values,
    high_values
):
    results = []

    for t_low in low_values:
        for t_high in high_values:

            if t_low >= t_high:
                continue

            result = evaluate_router(
                y_true,
                attack_probabilities,
                t_low,
                t_high
            )

            results.append(result)

    return results
