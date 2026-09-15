from router import route_probability, route_batch


T_LOW = 0.3
T_HIGH = 0.7


test_probabilities = [
    0.05,
    0.20,
    0.30,
    0.50,
    0.70,
    0.80,
    0.95
]


print("=== Router Test ===")
print("T_low :", T_LOW)
print("T_high:", T_HIGH)
print()


for p in test_probabilities:
    route = route_probability(
        p,
        t_low=T_LOW,
        t_high=T_HIGH
    )

    print(
        f"P(Attack)={p:.2f}"
        f" -> {route}"
    )


print("\n=== Batch Router ===")

routes = route_batch(
    test_probabilities,
    t_low=T_LOW,
    t_high=T_HIGH
)

print(routes)

print("\nROUTER TEST SUCCESS")
