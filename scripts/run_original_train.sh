#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ] || [ "$#" -gt 5 ]; then
    echo "Usage:"
    echo "  $0 <model_key> <train_file> <valid_file> [gpu] [epochs]"
    echo
    echo "model_key:"
    echo "  koelectra"
    echo "  mdeberta"
    echo
    echo "Example:"
    echo "  $0 koelectra data/step1/train.jsonl data/step1/valid.jsonl 0 3"
    exit 1
fi

MODEL_KEY="$1"
TRAIN_FILE="$2"
VALID_FILE="$3"
GPU="${4:-0}"
EPOCHS="${5:-3}"

PYTHON="${PYTHON:-python}"

BATCH_SIZE="${BATCH_SIZE:-16}"
LEARNING_RATE="${LEARNING_RATE:-2e-5}"
WEIGHT_DECAY="${WEIGHT_DECAY:-0.01}"
MAX_LENGTH="${MAX_LENGTH:-128}"
SEED="${SEED:-42}"

case "$MODEL_KEY" in
    koelectra)
        MODEL_NAME="monologg/koelectra-base-v3-discriminator"
        OUTPUT_DIR="results/step1/koelectra/original"
        TOKENIZER_ARGS=()
        ;;
    mdeberta)
        MODEL_NAME="microsoft/mdeberta-v3-base"
        OUTPUT_DIR="results/step1/mdeberta/original"
        TOKENIZER_ARGS=(--use-slow-tokenizer)
        ;;
    *)
        echo "Unknown model_key: $MODEL_KEY"
        echo "Use: koelectra or mdeberta"
        exit 1
        ;;
esac

if [ ! -f "$TRAIN_FILE" ]; then
    echo "Train file not found: $TRAIN_FILE"
    exit 1
fi

if [ ! -f "$VALID_FILE" ]; then
    echo "Validation file not found: $VALID_FILE"
    exit 1
fi

echo "===== STEP 1 ORIGINAL TRAINING ====="
echo "model key       : $MODEL_KEY"
echo "model           : $MODEL_NAME"
echo "train           : $TRAIN_FILE"
echo "valid           : $VALID_FILE"
echo "output          : $OUTPUT_DIR"
echo "gpu             : $GPU"
echo "epochs          : $EPOCHS"
echo "batch size      : $BATCH_SIZE"
echo "learning rate   : $LEARNING_RATE"
echo "weight decay    : $WEIGHT_DECAY"
echo "max length      : $MAX_LENGTH"
echo "seed            : $SEED"
echo

CUDA_VISIBLE_DEVICES="$GPU" \
"$PYTHON" src/classifier/train.py \
    --model-name "$MODEL_NAME" \
    --train "$TRAIN_FILE" \
    --valid "$VALID_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --epochs "$EPOCHS" \
    --batch-size "$BATCH_SIZE" \
    --learning-rate "$LEARNING_RATE" \
    --weight-decay "$WEIGHT_DECAY" \
    --max-length "$MAX_LENGTH" \
    --seed "$SEED" \
    --fp16 \
    "${TOKENIZER_ARGS[@]}"
