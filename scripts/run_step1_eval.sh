#!/usr/bin/env bash
set -euo pipefail

MODEL_KEY="${1:-}"
TRAINING_TYPE="${2:-}"
GPU="${3:-}"
BATCH_SIZE="${4:-}"

if [[ -z "$MODEL_KEY" || -z "$TRAINING_TYPE" || -z "$GPU" || -z "$BATCH_SIZE" ]]; then
    echo "Usage:"
    echo "  bash scripts/run_step1_eval.sh <koelectra|mdeberta> <original|augmented> <gpu> <batch_size>"
    echo
    echo "Examples:"
    echo "  bash scripts/run_step1_eval.sh koelectra original 7 16"
    echo "  bash scripts/run_step1_eval.sh koelectra augmented 7 16"
    exit 1
fi

if [[ "$TRAINING_TYPE" != "original" && "$TRAINING_TYPE" != "augmented" ]]; then
    echo "ERROR: unknown training type: $TRAINING_TYPE"
    echo "Allowed: original, augmented"
    exit 1
fi

CLEAN_TEST="data/step1/original/test.csv"
OBFUSCATED_TEST="data/step1/evaluation/obfuscated_test.csv"

if [[ ! -f "$CLEAN_TEST" ]]; then
    echo "ERROR: missing $CLEAN_TEST"
    exit 1
fi

if [[ ! -f "$OBFUSCATED_TEST" ]]; then
    echo "ERROR: missing $OBFUSCATED_TEST"
    exit 1
fi

case "$MODEL_KEY" in

    koelectra)
        MODEL_ROOT="results/step1/koelectra"
        EXTRA_ARGS=()
        ;;

    mdeberta)
        MODEL_ROOT="results/step1/mdeberta"
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

MODEL_DIR="$MODEL_ROOT/$TRAINING_TYPE/best_model"

if [[ ! -d "$MODEL_DIR" ]]; then
    echo "ERROR: trained model not found:"
    echo "  $MODEL_DIR"
    exit 1
fi

OUTPUT_ROOT="$MODEL_ROOT/$TRAINING_TYPE/eval"

COMMON_ARGS=(
    --model "$MODEL_DIR"
    --batch-size "$BATCH_SIZE"
    --max-length 128
    --fp16
)

echo "========================================"
echo "Step 1 Evaluation"
echo "========================================"
echo "model key      : $MODEL_KEY"
echo "training type  : $TRAINING_TYPE"
echo "model          : $MODEL_DIR"
echo "GPU            : $GPU"
echo "batch size     : $BATCH_SIZE"
echo "clean test     : $CLEAN_TEST"
echo "obfuscated test: $OBFUSCATED_TEST"
echo "output         : $OUTPUT_ROOT"
echo "========================================"

echo
echo "===== CLEAN TEST ====="

CUDA_VISIBLE_DEVICES="$GPU" \
/root/project/.venv/bin/python src/classifier/evaluate.py \
    "${COMMON_ARGS[@]}" \
    --input "$CLEAN_TEST" \
    --output-dir "$OUTPUT_ROOT/clean" \
    "${EXTRA_ARGS[@]}"

echo
echo "===== OBFUSCATED TEST ====="

CUDA_VISIBLE_DEVICES="$GPU" \
/root/project/.venv/bin/python src/classifier/evaluate.py \
    "${COMMON_ARGS[@]}" \
    --input "$OBFUSCATED_TEST" \
    --output-dir "$OUTPUT_ROOT/obfuscated" \
    "${EXTRA_ARGS[@]}"

echo
echo "========================================"
echo "STEP 1 EVALUATION SUCCESS"
echo "========================================"
echo "clean:"
echo "  $OUTPUT_ROOT/clean/metrics.json"
echo
echo "obfuscated:"
echo "  $OUTPUT_ROOT/obfuscated/metrics.json"
