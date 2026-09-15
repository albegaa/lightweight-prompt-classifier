import argparse

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)

from router import route_probability


def load_model(model_path):
    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    tokenizer = AutoTokenizer.from_pretrained(
        model_path
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        model_path
    )

    model.to(device)
    model.eval()

    return tokenizer, model, device


def predict(
    text,
    tokenizer,
    model,
    device,
    max_length=128,
):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():
        outputs = model(**inputs)

    probabilities = torch.softmax(
        outputs.logits,
        dim=-1,
    )[0]

    p_benign = probabilities[0].item()
    p_attack = probabilities[1].item()

    prediction = int(
        torch.argmax(probabilities).item()
    )

    return {
        "prediction": prediction,
        "p_benign": p_benign,
        "p_attack": p_attack,
    }


def main(args):
    tokenizer, model, device = load_model(
        args.model_path
    )

    result = predict(
        args.text,
        tokenizer,
        model,
        device,
        max_length=args.max_length,
    )

    route = route_probability(
        result["p_attack"],
        t_low=args.t_low,
        t_high=args.t_high,
    )

    print("=== Inference ===")
    print("device:", device)
    print("text:", args.text)

    print()
    print("prediction:", result["prediction"])
    print(
        "P(Benign):",
        f"{result['p_benign']:.4f}"
    )
    print(
        "P(Attack):",
        f"{result['p_attack']:.4f}"
    )

    print()
    print("T_low:", args.t_low)
    print("T_high:", args.t_high)
    print("route:", route)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model-path",
        default="results/demo/model",
    )

    parser.add_argument(
        "--text",
        required=True,
    )

    parser.add_argument(
        "--t-low",
        type=float,
        default=0.44,
    )

    parser.add_argument(
        "--t-high",
        type=float,
        default=0.50,
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=128,
    )

    args = parser.parse_args()

    main(args)
