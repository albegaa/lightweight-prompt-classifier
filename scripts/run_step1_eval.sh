#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ] || [ "$#" -gt 6 ]; then
    echo "Usage:"
    echo "  $0 <model_key> <training_type> <eval_name> <input_file> [gpu] [batch_size]"
    echo
    echo "model_key:"
    echo "  koelectra"
    echo "  mdeberta"
    echo
    echo "training_type:"
    echo "  original"
    echo "  augmented"
    echo
    echo "recommended eval_name:"
    echo "  clean"
    echo "  obfuscated"
    echo "  kg_clean"
    echo "  kg_obfuscated"
    echo
    echo "Example:"
    echo "  $0 koelectra original clean data/step1/test.jsonl 0 32"
    exit 1
fi

MODEL_KEY="$1"
TRAINING_TYPE="$2"
EVAL_NAME="$3"
INPUT_FILE="$4"
GPU="${5:-0}"
BATCH_SIZE="${6:-32}"

PYTHON="${PYTHON:-python}"
MAX_LENGTH="${MAX_LENGTH:-128}"

case "$MODEL_KEY" in
    koelectra)
        TOKENIZER_ARGS=()
        ;;
    mdeberta)
        TOKENIZER_ARGS=(--use-slow-tokenizer)
        ;;
    *)
        echo "Unknown model_key: $MODEL_KEY"
        echo "Use: koelectra or mdeberta"
        exit 1
        ;;
esac

case "$TRAINING_TYPE" in
    original|augmented)
        ;;
    *)
        echo "Unknown training_type: $TRAINING_TYPE"
        echo "Use: original or augmented"
        exit 1
        ;;
esac

case "$EVAL_NAME" in
    clean|obfuscated|kg_clean|kg_obfuscated)
        ;;
    *)
        echo "Unknown eval_name: $EVAL_NAME"
        echo "Use: clean, obfuscated, kg_clean, or kg_obfuscated"
        exit 1
        ;;
esac

if [ ! -f "$INPUT_FILE" ]; then
    echo "Evaluation file not found: $INPUT_FILE"
    exit 1
fi

MODEL_DIR="results/step1/${MODEL_KEY}/${TRAINING_TYPE}/best_model"
OUTPUT_DIR="results/step1/${MODEL_KEY}/${TRAINING_TYPE}/eval/${EVAL_NAME}"

if [ ! -d "$MODEL_DIR" ]; then
    echo "Fine-tuned model directory not found:"
    echo "  $MODEL_DIR"
    echo
    echo "Train the model before evaluation."
    exit 1
fi

echo "===== STEP 1 EVALUATION ====="
echo "model key       : $MODEL_KEY"
echo "training type   : $TRAINING_TYPE"
echo "evaluation      : $EVAL_NAME"
echo "model           : $MODEL_DIR"
echo "input           : $INPUT_FILE"
echo "output          : $OUTPUT_DIR"
echo "gpu             : $GPU"
echo "batch size      : $BATCH_SIZE"
echo "max length      : $MAX_LENGTH"
echo

CUDA_VISIBLE_DEVICES="$GPU" \
"$PYTHON" src/classifier/evaluate.py \
    --model "$MODEL_DIR" \
    --input "$INPUT_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --batch-size "$BATCH_SIZE" \
    --max-length "$MAX_LENGTH" \
    --fp16 \
    "${TOKENIZER_ARGS[@]}"

if [ "$EVAL_NAME" = "obfuscated" ] || \
   [ "$EVAL_NAME" = "kg_obfuscated" ]; then

    echo
    echo "===== OBFUSCATED ANALYSIS ====="

    "$PYTHON" scripts/analyze_obfuscated_eval.py \
        --predictions "$OUTPUT_DIR/predictions.csv" \
        --output-dir "$OUTPUT_DIR/analysis"
fi
