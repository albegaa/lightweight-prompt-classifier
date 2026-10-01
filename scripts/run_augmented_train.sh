#!/usr/bin/env bash
set -euo pipefail

MODEL_KEY="${1:-}"
GPU="${2:-}"
EPOCHS="${3:-}"
BATCH_SIZE="${4:-}"

if [[ -z "$MODEL_KEY" || -z "$GPU" || -z "$EPOCHS" || -z "$BATCH_SIZE" ]]; then
    echo "Usage:"
    echo "  bash scripts/run_augmented_train.sh <koelectra|mdeberta> <gpu> <epochs> <batch_size>"
    echo
    echo "Example:"
    echo "  bash scripts/run_augmented_train.sh koelectra 7 3 16"
    exit 1
fi

TRAIN_FILE="data/step1/augmented/train.csv"
VALID_FILE="data/step1/original/valid.csv"

if [[ ! -f "$TRAIN_FILE" ]]; then
    echo "ERROR: missing $TRAIN_FILE"
    exit 1
fi

if [[ ! -f "$VALID_FILE" ]]; then
    echo "ERROR: missing $VALID_FILE"
    exit 1
fi

COMMON_ARGS=(
    --train "$TRAIN_FILE"
    --valid "$VALID_FILE"
    --epochs "$EPOCHS"
    --batch-size "$BATCH_SIZE"
    --learning-rate 2e-5
    --weight-decay 0.01
    --max-length 128
    --seed 42
    --fp16
)

case "$MODEL_KEY" in

    koelectra)
        MODEL_NAME="monologg/koelectra-base-v3-discriminator"
        OUTPUT_DIR="results/step1/koelectra/augmented"
        EXTRA_ARGS=()
        ;;

    mdeberta)
        MODEL_NAME="microsoft/mdeberta-v3-base"
        OUTPUT_DIR="results/step1/mdeberta/augmented"
        EXTRA_ARGS=(
            --use-slow-tokenizer
        )
        ;;

    *)
        echo "ERROR: unknown model key: $MODEL_KEY"
        echo "Allowed: koelectra, mdeberta"
        exit 1
        ;;
esac

echo "========================================"
echo "Step 1 Augmented Training"
echo "========================================"
echo "model key   : $MODEL_KEY"
echo "model       : $MODEL_NAME"
echo "GPU         : $GPU"
echo "epochs      : $EPOCHS"
echo "batch size  : $BATCH_SIZE"
echo "train       : $TRAIN_FILE"
echo "valid       : $VALID_FILE"
echo "output      : $OUTPUT_DIR"
echo "========================================"

CUDA_VISIBLE_DEVICES="$GPU" \
/root/project/.venv/bin/python src/classifier/train.py \
    --model-name "$MODEL_NAME" \
    --output-dir "$OUTPUT_DIR" \
    "${COMMON_ARGS[@]}" \
    "${EXTRA_ARGS[@]}"

echo
echo "AUGMENTED TRAINING SUCCESS"
