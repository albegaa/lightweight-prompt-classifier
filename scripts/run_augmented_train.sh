#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ] || [ "$#" -gt 6 ]; then
    echo "Usage:"
    echo "  $0 <model_key> <original_train> <augmented_input> <valid_file> [gpu] [epochs]"
    echo
    echo "model_key:"
    echo "  koelectra"
    echo "  mdeberta"
    echo
    echo "Example:"
    echo "  $0 koelectra \\"
    echo "    data/step1/train.jsonl \\"
    echo "    data/step1/augmented_train.jsonl \\"
    echo "    data/step1/valid.jsonl \\"
    echo "    0 3"
    exit 1
fi

MODEL_KEY="$1"
ORIGINAL_TRAIN="$2"
AUGMENTED_INPUT="$3"
VALID_FILE="$4"
GPU="${5:-0}"
EPOCHS="${6:-3}"

PYTHON="${PYTHON:-python}"

BATCH_SIZE="${BATCH_SIZE:-16}"
LEARNING_RATE="${LEARNING_RATE:-2e-5}"
WEIGHT_DECAY="${WEIGHT_DECAY:-0.01}"
MAX_LENGTH="${MAX_LENGTH:-128}"
SEED="${SEED:-42}"

case "$MODEL_KEY" in
    koelectra)
        MODEL_NAME="monologg/koelectra-base-v3-discriminator"
        OUTPUT_DIR="results/step1/koelectra/augmented"
        TOKENIZER_ARGS=()
        ;;
    mdeberta)
        MODEL_NAME="microsoft/mdeberta-v3-base"
        OUTPUT_DIR="results/step1/mdeberta/augmented"
        TOKENIZER_ARGS=(--use-slow-tokenizer)
        ;;
    *)
        echo "Unknown model_key: $MODEL_KEY"
        echo "Use: koelectra or mdeberta"
        exit 1
        ;;
esac

for FILE in \
    "$ORIGINAL_TRAIN" \
    "$AUGMENTED_INPUT" \
    "$VALID_FILE"
do
    if [ ! -f "$FILE" ]; then
        echo "Data file not found: $FILE"
        exit 1
    fi
done

mkdir -p "$OUTPUT_DIR"

PREPARED_TRAIN="$OUTPUT_DIR/prepared_train.jsonl"

echo "===== STEP 1 AUGMENTED TRAINING ====="
echo "model key       : $MODEL_KEY"
echo "model           : $MODEL_NAME"
echo "original train  : $ORIGINAL_TRAIN"
echo "augmented input : $AUGMENTED_INPUT"
echo "valid           : $VALID_FILE"
echo "prepared train  : $PREPARED_TRAIN"
echo "output          : $OUTPUT_DIR"
echo "gpu             : $GPU"
echo "epochs          : $EPOCHS"
echo "batch size      : $BATCH_SIZE"
echo "learning rate   : $LEARNING_RATE"
echo "weight decay    : $WEIGHT_DECAY"
echo "max length      : $MAX_LENGTH"
echo "seed            : $SEED"
echo

echo "===== PREPARE AUGMENTED TRAIN ====="

"$PYTHON" scripts/prepare_augmented_train.py \
    --original-train "$ORIGINAL_TRAIN" \
    --augmented-input "$AUGMENTED_INPUT" \
    --output "$PREPARED_TRAIN"

echo
echo "===== VALIDATE AUGMENTED TRAIN ====="

"$PYTHON" scripts/validate_step1_data.py \
    --train "$ORIGINAL_TRAIN" \
    --valid "$VALID_FILE" \
    --augmented-train "$PREPARED_TRAIN"

echo
echo "===== START TRAINING ====="

CUDA_VISIBLE_DEVICES="$GPU" \
"$PYTHON" src/classifier/train.py \
    --model-name "$MODEL_NAME" \
    --train "$PREPARED_TRAIN" \
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
