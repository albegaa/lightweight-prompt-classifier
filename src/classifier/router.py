def route_probability(
    p_attack,
    t_low=0.3,
    t_high=0.7
):
    """
    Attack probability를 이용해 입력을 routing한다.

    Parameters
    ----------
    p_attack : float
        모델이 출력한 Attack class의 확률

    t_low : float
        Benign으로 직접 통과시키는 최대 threshold

    t_high : float
        Attack으로 직접 차단하는 최소 threshold

    Returns
    -------
    str
        "benign"
        "jailguard"
        "attack"
    """

    if not 0.0 <= p_attack <= 1.0:
        raise ValueError(
            "p_attack must be between 0 and 1."
        )

    if not 0.0 <= t_low < t_high <= 1.0:
        raise ValueError(
            "Thresholds must satisfy "
            "0 <= t_low < t_high <= 1."
        )

    if p_attack < t_low:
        return "benign"

    elif p_attack > t_high:
        return "attack"

    else:
        return "jailguard"


def route_batch(
    probabilities,
    t_low=0.3,
    t_high=0.7
):
    """
    여러 Attack probability를 한번에 routing한다.
    """

    return [
        route_probability(
            p,
            t_low=t_low,
            t_high=t_high
        )
        for p in probabilities
    ]
