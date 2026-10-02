# Step 1 본실험 실행 Runbook

## 0. 목적

이 문서는 최종 Step 1 데이터 수신 후
KoELECTRA와 mDeBERTa 경량 classifier를 동일한 조건으로 학습하고,
Clean / Obfuscated / KoreanGuardrail 평가를 수행하기 위한
실제 실행 절차를 정리한다.

비교 조건:

- KoELECTRA Original-only
- KoELECTRA Augmented
- mDeBERTa Original-only
- mDeBERTa Augmented

Step 1의 핵심 비교는

    Original-only
        vs
    Augmented

이다.

주의:

- Demo 결과는 연구 결과로 사용하지 않는다.
- 동일 원문의 train / valid / test leakage를 허용하지 않는다.
- KoELECTRA와 mDeBERTa에는 가능한 한 동일한 학습 조건을 적용한다.
- mDeBERTa는 slow tokenizer를 사용한다.
- 난독화 평가의 주 결과는 `changed=true` 행 기준으로 본다.
- `changed=false` 행도 raw 평가 결과에는 보존한다.
- class 1 softmax 출력은 calibrated probability가 아니라
  `attack-class softmax score`이다.

---

# 1. 현재 구현 범위

학습:

- `src/classifier/train.py`
- `scripts/run_original_train.sh`
- `scripts/run_augmented_train.sh`
- `scripts/prepare_augmented_train.py`

평가:

- `src/classifier/evaluate.py`
- `scripts/run_step1_eval.sh`
- `scripts/analyze_obfuscated_eval.py`

데이터 검증:

- `scripts/validate_step1_data.py`

결과 집계:

- `scripts/make_step1_table.py`
- `scripts/make_step1_kg_summary.py`

후속 통합 prototype:

- `src/classifier/inference.py`
- `src/classifier/router.py`
- `src/classifier/threshold_sweep.py`
- `src/classifier/analyze_validation_router.py`

Router 관련 코드는 Step 1 본실험의 직접 대상은 아니며,
향후 팀 통합 저장소에서 JailGuard와 연결하기 위한 prototype으로 보존한다.

---

# 2. 실험 전에 확정할 값

본학습 시작 전에 다음을 확정한다.

- 실제 데이터 파일 경로
- EPOCHS
- BATCH_SIZE
- 사용할 GPU 번호
- 데이터 버전 또는 commit
- 증강 데이터 전달 형태 확인

증강 데이터는 다음 두 형식을 모두 지원한다.

1. variant-only
2. original + variant 합본

`prepare_augmented_train.py`가 자동으로 판별하여
최종 학습용 `prepared_train.jsonl`을 생성한다.

공통 기본 설정:

- learning rate = 2e-5
- weight decay = 0.01
- max length = 128
- seed = 42
- FP16
- best model selection = validation F1

EPOCHS와 BATCH_SIZE는 본실험 시작 전에 최종 확정한다.

---

# 3. 저장소 및 환경 확인

저장소로 이동한다.

    cd /root/project/lightweight-prompt-classifier

상태 확인:

    git status
    git branch --show-current
    git rev-parse HEAD

본실험 전에는 가능하면

    main == origin/main
    working tree clean

상태에서 시작한다.

Python 환경:

    /root/project/.venv/bin/python --version

필요하면 현재 shell에서 다음을 지정한다.

    export PYTHON=/root/project/.venv/bin/python

공용 GPU 서버의 기준 Python 패키지는
`requirements-server.txt`에 기록한다.

새 환경을 구성하는 경우:

    python -m venv /root/project/.venv
    source /root/project/.venv/bin/activate
    pip install -r requirements-server.txt

이미 구성된 공용 환경을 사용하는 경우에는
불필요하게 재설치하지 않고 다음을 확인한다.

    "$PYTHON" -m pip check

필요하면 설치된 핵심 버전도 확인한다.

    "$PYTHON" - <<'PYENV'
    import torch
    import transformers
    import sklearn
    import pandas
    import numpy

    print("torch:", torch.__version__)
    print("transformers:", transformers.__version__)
    print("scikit-learn:", sklearn.__version__)
    print("pandas:", pandas.__version__)
    print("numpy:", numpy.__version__)
    PYENV

기준 서버 환경:

- Python 3.10.12
- PyTorch 2.4.1+cu121
- Transformers 4.51.3
- scikit-learn 1.7.2
- Pandas 2.3.3
- NumPy 2.2.6

---

# 4. GPU 확인

공용 GPU 서버이므로 학습 직전에 반드시 확인한다.

    nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

과거에 비어 있던 GPU 번호를 그대로 사용하지 않는다.

사용할 GPU를 정한 뒤 예:

    GPU=0

P100에서는 BF16이 아니라 FP16을 사용한다.

---

# 5. 데이터 경로 설정

실제 전달된 파일 경로에 맞게 아래 값을 수정한다.

예시:

    TRAIN_FILE="/path/to/train.jsonl"
    VALID_FILE="/path/to/valid.jsonl"
    TEST_FILE="/path/to/test.jsonl"

    KG_TEST_FILE="/path/to/kg_test.jsonl"

    AUGMENTED_INPUT="/path/to/augmented_train.jsonl"

    OBFUSCATED_TEST_FILE="/path/to/obfuscated_test.jsonl"
    OBFUSCATED_KG_FILE="/path/to/obfuscated_kg_test.jsonl"

실제 파일 확인:

    ls -lh \
      "$TRAIN_FILE" \
      "$VALID_FILE" \
      "$TEST_FILE" \
      "$KG_TEST_FILE" \
      "$AUGMENTED_INPUT" \
      "$OBFUSCATED_TEST_FILE" \
      "$OBFUSCATED_KG_FILE"

파일명이 다르더라도
스크립트를 수정하지 말고 경로 변수만 변경한다.

---

# 6. 데이터 계약

원본 데이터:

- `train`
- `valid`
- `test`
- `kg_test`

필수 필드:

- `id`
- `text`
- `label`
- `source`

label:

- `0` = Benign
- `1` = Attack

variant 데이터 추가 필드:

- `seed_id`
- `technique`
- `intensity`
- `changed`
- `n_changed`

원본 source group:

    id

variant source group:

    seed_id

예:

    original.id = xtram1_00123

    variant.seed_id = xtram1_00123

---

# 7. 데이터 전체 검증

본학습 전에 반드시 실행한다.

    "$PYTHON" scripts/validate_step1_data.py \
      --train "$TRAIN_FILE" \
      --valid "$VALID_FILE" \
      --test "$TEST_FILE" \
      --kg-test "$KG_TEST_FILE" \
      --augmented-train "$AUGMENTED_INPUT" \
      --obfuscated-test "$OBFUSCATED_TEST_FILE" \
      --obfuscated-kg-test "$OBFUSCATED_KG_FILE"

정상 종료:

    VALIDATION PASSED

주요 검사:

- 필수 필드
- null
- 빈 문자열
- label 0/1
- ID 중복
- 동일 text의 conflicting label
- exact-text leakage
- source-group leakage
- `seed_id`가 적절한 원본에 존재하는지
- variant label이 원문 label과 일치하는지
- variant source가 원문 source와 일치하는지
- augmented variant의 `changed=false` 존재 여부

허용되는 source group overlap:

    train
      ↔ augmented_train

    test
      ↔ obfuscated_test

    kg_test
      ↔ obfuscated_kg_test

나머지 train / valid / held-out 평가 간 group overlap은 허용하지 않는다.

---

# 8. 데이터 규모 및 label 분포 확인

실제 데이터의 행 수와 label 분포를 확인한다.

    "$PYTHON" - <<PY
    import pandas as pd

    files = {
        "train": "$TRAIN_FILE",
        "valid": "$VALID_FILE",
        "test": "$TEST_FILE",
        "kg_test": "$KG_TEST_FILE",
        "augmented_input": "$AUGMENTED_INPUT",
        "obfuscated_test": "$OBFUSCATED_TEST_FILE",
        "obfuscated_kg": "$OBFUSCATED_KG_FILE",
    }

    def load(path):
        if path.endswith(".jsonl"):
            return pd.read_json(path, lines=True)
        return pd.read_csv(path)

    for name, path in files.items():
        df = load(path)

        print()
        print("=====", name, "=====")
        print("rows:", len(df))

        if "label" in df.columns:
            print(
                "labels:",
                df["label"]
                .value_counts(dropna=False)
                .sort_index()
                .to_dict()
            )

        if "changed" in df.columns:
            print(
                "changed:",
                df["changed"]
                .value_counts(dropna=False)
                .to_dict()
            )

        if "technique" in df.columns:
            print(
                "techniques:",
                df["technique"]
                .nunique(dropna=True)
            )
    PY

이 결과를 실험 기록에 남긴다.

---

# 9. T9b 증강 조건 확인

Step 1 증강 학습 조건:

- `yamin_swap`, intensity `0.7`
- `symbol_insert`, intensity `0.3`

두 조건은 T9b에서 pass 판정을 받은 기법이 아니라
ambiguous fallback을 통해 선정된 경계 사례이다.

따라서 논문에서도

    유효한 기법이 확인되었다

라고 표현하지 않는다.

실제 augmented input이 이 조건과 일치하는지 확인한다.

예:

    "$PYTHON" - <<PY
    import pandas as pd

    path = "$AUGMENTED_INPUT"

    if path.endswith(".jsonl"):
        df = pd.read_json(path, lines=True)
    else:
        df = pd.read_csv(path)

    if "seed_id" in df.columns:
        variants = df[df["seed_id"].notna()].copy()
    else:
        variants = df.copy()

    print(
        variants[
            ["technique", "intensity"]
        ]
        .value_counts()
        .sort_index()
    )
    PY

예상 조건 외 variant가 들어 있으면
바로 학습하지 않고 데이터 담당자와 먼저 확인한다.

---

# 10. 학습 설정 확정

예:

    GPU=0
    EPOCHS=3
    BATCH_SIZE=16

환경변수 지정:

    export BATCH_SIZE="$BATCH_SIZE"

learning rate 등은 script 기본값을 사용한다.

필요할 경우 다음 환경변수로 명시 가능하다.

    export LEARNING_RATE=2e-5
    export WEIGHT_DECAY=0.01
    export MAX_LENGTH=128
    export SEED=42

KoELECTRA와 mDeBERTa의 비교 조건은
임의로 다르게 변경하지 않는다.

---

# 11. KoELECTRA Original-only 학습

실행:

    scripts/run_original_train.sh \
      koelectra \
      "$TRAIN_FILE" \
      "$VALID_FILE" \
      "$GPU" \
      "$EPOCHS"

저장 위치:

    results/step1/koelectra/original/

best model:

    results/step1/koelectra/original/best_model/

---

# 12. mDeBERTa Original-only 학습

실행:

    scripts/run_original_train.sh \
      mdeberta \
      "$TRAIN_FILE" \
      "$VALID_FILE" \
      "$GPU" \
      "$EPOCHS"

저장 위치:

    results/step1/mdeberta/original/

mDeBERTa는 script 내부에서 slow tokenizer를 사용한다.

---

# 13. KoELECTRA Augmented 학습

실행:

    scripts/run_augmented_train.sh \
      koelectra \
      "$TRAIN_FILE" \
      "$AUGMENTED_INPUT" \
      "$VALID_FILE" \
      "$GPU" \
      "$EPOCHS"

내부 흐름:

    original train
          +
    augmented input
          ↓
    prepare_augmented_train.py
          ↓
    prepared_train.jsonl
          ↓
    validate_step1_data.py
          ↓
    train.py

표준화된 학습 파일:

    results/step1/koelectra/augmented/prepared_train.jsonl

모델:

    results/step1/koelectra/augmented/best_model/

---

# 14. mDeBERTa Augmented 학습

실행:

    scripts/run_augmented_train.sh \
      mdeberta \
      "$TRAIN_FILE" \
      "$AUGMENTED_INPUT" \
      "$VALID_FILE" \
      "$GPU" \
      "$EPOCHS"

표준화된 학습 파일:

    results/step1/mdeberta/augmented/prepared_train.jsonl

모델:

    results/step1/mdeberta/augmented/best_model/

---

# 15. 학습 결과 확인

네 개의 best model이 존재해야 한다.

    find results/step1 \
      -type d \
      -name best_model \
      | sort

예상:

    results/step1/koelectra/original/best_model
    results/step1/koelectra/augmented/best_model
    results/step1/mdeberta/original/best_model
    results/step1/mdeberta/augmented/best_model

학습 결과 파일도 확인한다.

    find results/step1 \
      -maxdepth 5 \
      -type f \
      \( -name 'metrics.json' \
      -o -name 'training_history.csv' \
      -o -name 'validation_results.csv' \) \
      | sort

---

# 16. 평가 종류

각 학습 조건에 대해 네 평가를 수행한다.

1. `clean`
2. `obfuscated`
3. `kg_clean`
4. `kg_obfuscated`

총 평가 실행 수:

    4개 학습 조건 × 4개 평가 = 16회

평가 script:

    scripts/run_step1_eval.sh

형식:

    scripts/run_step1_eval.sh \
      MODEL_KEY \
      TRAINING_TYPE \
      EVAL_NAME \
      INPUT_FILE \
      GPU \
      BATCH_SIZE

---

# 17. KoELECTRA Original 평가

Clean:

    scripts/run_step1_eval.sh \
      koelectra original clean \
      "$TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

Obfuscated:

    scripts/run_step1_eval.sh \
      koelectra original obfuscated \
      "$OBFUSCATED_TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

KG Clean:

    scripts/run_step1_eval.sh \
      koelectra original kg_clean \
      "$KG_TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

KG Obfuscated:

    scripts/run_step1_eval.sh \
      koelectra original kg_obfuscated \
      "$OBFUSCATED_KG_FILE" \
      "$GPU" "$BATCH_SIZE"

---

# 18. KoELECTRA Augmented 평가

    scripts/run_step1_eval.sh \
      koelectra augmented clean \
      "$TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

    scripts/run_step1_eval.sh \
      koelectra augmented obfuscated \
      "$OBFUSCATED_TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

    scripts/run_step1_eval.sh \
      koelectra augmented kg_clean \
      "$KG_TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

    scripts/run_step1_eval.sh \
      koelectra augmented kg_obfuscated \
      "$OBFUSCATED_KG_FILE" \
      "$GPU" "$BATCH_SIZE"

---

# 19. mDeBERTa Original 평가

    scripts/run_step1_eval.sh \
      mdeberta original clean \
      "$TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

    scripts/run_step1_eval.sh \
      mdeberta original obfuscated \
      "$OBFUSCATED_TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

    scripts/run_step1_eval.sh \
      mdeberta original kg_clean \
      "$KG_TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

    scripts/run_step1_eval.sh \
      mdeberta original kg_obfuscated \
      "$OBFUSCATED_KG_FILE" \
      "$GPU" "$BATCH_SIZE"

---

# 20. mDeBERTa Augmented 평가

    scripts/run_step1_eval.sh \
      mdeberta augmented clean \
      "$TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

    scripts/run_step1_eval.sh \
      mdeberta augmented obfuscated \
      "$OBFUSCATED_TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

    scripts/run_step1_eval.sh \
      mdeberta augmented kg_clean \
      "$KG_TEST_FILE" \
      "$GPU" "$BATCH_SIZE"

    scripts/run_step1_eval.sh \
      mdeberta augmented kg_obfuscated \
      "$OBFUSCATED_KG_FILE" \
      "$GPU" "$BATCH_SIZE"

---

# 21. Obfuscated 평가의 자동 후처리

`eval_name`이

- `obfuscated`
- `kg_obfuscated`

인 경우 `run_step1_eval.sh`가 자동으로

    scripts/analyze_obfuscated_eval.py

를 실행한다.

평가 출력:

    metrics.json
    predictions.csv

난독화 분석 출력:

    analysis/
    ├── obfuscated_overall.csv
    ├── obfuscated_by_technique.csv
    └── obfuscated_by_cell.csv

`metrics.json`:

    모든 입력 행 기준 raw 평가

`obfuscated_overall.csv`:

    all_rows
    changed_only

주 난독화 성능:

    changed_only

추가 기록:

    application_rate

---

# 22. 난독화 평가 기준

`changed=false`:

- raw 결과에는 유지
- application rate 계산에 사용
- 실제 난독화 성능의 주 지표에서는 제외

`changed=true`:

- 실제 문자열 변화가 발생한 행
- 난독화 robustness의 주 평가 대상

따라서 논문 및 메인 결과표에서는
Obfuscated F1 / Recall 등을 `changed=true` 기준으로 보고한다.

단, 전체 행 결과도 raw artifact로 보존한다.

---

# 23. 평가 결과 개수 확인

4개 모델 조건 × 4개 평가이므로
정상적으로 완료되면 `metrics.json`은 16개가 생성된다.

확인:

    find results/step1 \
      -path '*/eval/*/metrics.json' \
      -type f \
      | sort

개수:

    find results/step1 \
      -path '*/eval/*/metrics.json' \
      -type f \
      | wc -l

예상:

    16

난독화 분석 디렉터리 확인:

    find results/step1 \
      -path '*/eval/*/analysis/obfuscated_overall.csv' \
      -type f \
      | sort

예상:

    8

이유:

    4개 학습 조건
        ×
    obfuscated / kg_obfuscated

---

# 24. 메인 Step 1 결과표 생성

실행:

    "$PYTHON" scripts/make_step1_table.py

출력:

    results/step1/table2_summary.csv

Clean:

    eval/clean/metrics.json

Obfuscated:

    eval/obfuscated/analysis/obfuscated_overall.csv
    scope = changed_only

포함 주요 지표:

- Clean Accuracy
- Clean Precision
- Clean Recall
- Clean F1
- Clean FPR
- Clean FNR
- Obfuscated application rate
- Obfuscated Accuracy
- Obfuscated Precision
- Obfuscated Recall
- Obfuscated F1
- Obfuscated FPR
- Obfuscated FNR
- F1 Drop
- Recall Drop

Drop:

    Clean - Obfuscated

단위:

    percentage point

단, Obfuscated 성능은 `changed=true` variant 집합 기준이므로
이 값은 동일 샘플의 paired 전후 차이를 의미하지 않는다.

논문에서는

    Clean 대비 changed-only 난독화 평가셋에서 관찰된 성능 차이

로 해석한다.

---

# 25. KoreanGuardrail 보조 결과 생성

실행:

    "$PYTHON" scripts/make_step1_kg_summary.py

출력:

    results/step1/kg_summary.csv

KG Clean:

    eval/kg_clean/metrics.json

KG Obfuscated:

    eval/kg_obfuscated/analysis/obfuscated_overall.csv
    scope = changed_only

KoreanGuardrail 평가는
번역 문체에 대한 과도한 의존 가능성을 확인하기 위한
보조 평가이다.

KSC 지면이 부족할 경우
메인 표에는 포함하지 않고 졸업논문 보조 실험으로 사용할 수 있다.

---

# 26. 최종 결과 확인

메인:

    cat results/step1/table2_summary.csv

KG:

    cat results/step1/kg_summary.csv

또는:

    "$PYTHON" - <<'PY'
    import pandas as pd

    print("===== MAIN =====")
    print(
        pd.read_csv(
            "results/step1/table2_summary.csv"
        ).to_string(index=False)
    )

    print()
    print("===== KOREANGUARDRAIL =====")
    print(
        pd.read_csv(
            "results/step1/kg_summary.csv"
        ).to_string(index=False)
    )
    PY

---

# 27. 결과 해석 순서

단순히 가장 높은 점수를 고르는 것이 아니라
Original-only 대비 Augmented 변화 중심으로 해석한다.

확인 순서:

1. Original-only Clean 성능
2. Original-only Obfuscated 성능 저하
3. Augmented 학습 후 Obfuscated Recall / F1 변화
4. Augmented 학습 후 Clean 성능 변화
5. Benign FPR 변화
6. F1 Drop / Recall Drop 변화
7. KoELECTRA와 mDeBERTa에서 동일 경향이 나타나는지
8. KG 보조 평가에서도 유사한 경향이 나타나는지

augmentation 효과는
실제 수치를 확인한 뒤 판단한다.

---

# 28. technique별 분석

난독화 평가 결과에서 필요하면 다음을 사용한다.

기법별:

    */eval/obfuscated/analysis/obfuscated_by_technique.csv

기법 × 강도별:

    */eval/obfuscated/analysis/obfuscated_by_cell.csv

KG에서도 동일한 구조로 저장된다.

해석 시 각 cell의 표본 수를 함께 확인한다.

표본 수가 적은 조건을
과도하게 일반화하지 않는다.

---

# 29. Kanana Safeguard와의 관계

Kanana Safeguard:

    kakaocorp/kanana-safeguard-prompt-2.1b

는 T4/T6에서 사용한 external reference detector이다.

Step 1에서 fine-tuning하는 모델:

- KoELECTRA
- mDeBERTa

와 동일한 조건의 학습 모델이 아니다.

따라서 `make_step1_table.py`에서는
다음 네 조건만 집계한다.

- KoELECTRA Original
- KoELECTRA Augmented
- mDeBERTa Original
- mDeBERTa Augmented

Kanana 결과는 필요할 경우
별도 reference baseline으로 제시한다.

---

# 30. Git 및 결과 파일 주의

fine-tuned model은 GitHub에 올리지 않는다.

특히:

- `best_model/`
- `*.safetensors`
- large checkpoints

실제 데이터 역시 공개 정책을 확인한다.

`predictions.csv`에는 원문 text가 포함되므로
공개 저장소에 commit하기 전에 반드시 확인한다.

특히 라이선스가 불명확하거나
내부 실험 전용 데이터는 재배포하지 않는다.

작은 집계 결과:

- `metrics.json`
- summary CSV
- analysis CSV

도 최종 공개 범위를 확인한 뒤 commit한다.

---

# 31. 실험마다 기록할 정보

각 학습 실행마다 다음을 기록한다.

- 실행 날짜
- Git commit
- 모델명
- 데이터 버전
- train / valid / test 크기
- KG test 크기
- label 분포
- augmented input 형식
- 사용 난독화 조건
- GPU
- epoch
- batch size
- learning rate
- weight decay
- max length
- seed
- best epoch
- validation F1
- Clean 결과
- Obfuscated changed-only 결과
- application rate
- KG 결과
- 오류 및 수정사항

현재 commit:

    git rev-parse HEAD

GPU:

    nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

---

# 32. 오류 발생 시 원칙

공통 실험 조건을 임의로 바꾸지 않는다.

오류 발생 시:

1. 오류 메시지 저장
2. 데이터 문제인지 모델 구현 문제인지 구분
3. 최소한의 수정만 수행
4. 수정 이유 기록
5. 두 모델 비교 조건에 영향이 있는지 확인
6. 코드 수정 시 Git commit 남김
7. 필요한 실험만 다시 실행

mDeBERTa slow tokenizer와 같은 차이는
모델 호환성을 위한 구현 차이로 기록한다.

GPU OOM으로 batch size를 변경해야 하는 경우
비교 조건에 영향을 주므로 반드시 기록하고
가능하면 두 모델의 effective condition을 맞춘다.

---

# 33. Step 1 완료 조건

다음을 모두 만족하면
Step 1 본실험 실행 완료로 본다.

- 최종 데이터 수신
- 데이터 validator 통과
- 데이터 규모 및 label 분포 기록
- 증강 조건 확인
- KoELECTRA Original 학습
- KoELECTRA Augmented 학습
- mDeBERTa Original 학습
- mDeBERTa Augmented 학습
- best model 4개 확인
- Clean 평가 4회
- Obfuscated 평가 4회
- KG Clean 평가 4회
- KG Obfuscated 평가 4회
- metrics.json 16개 확인
- 난독화 analysis 8개 확인
- `table2_summary.csv` 생성
- `kg_summary.csv` 생성
- 결과 수치 검산
- 실험 설정 기록
- 결과 해석 작성

---

# 34. 전체 실행 순서 요약

1. 저장소 상태 확인
2. Python / requirements 환경 확인
3. GPU 확인
4. 데이터 경로 변수 설정
5. 전체 데이터 validator 실행
6. 데이터 규모 / label 분포 확인
7. T9b 증강 조건 확인
8. EPOCHS / BATCH_SIZE 확정
9. KoELECTRA Original 학습
10. mDeBERTa Original 학습
11. KoELECTRA Augmented 학습
12. mDeBERTa Augmented 학습
13. best model 4개 확인
14. 네 학습 조건 × 네 평가 = 16회 실행
15. Obfuscated 자동 changed-only 분석 확인
16. `make_step1_table.py`
17. `make_step1_kg_summary.py`
18. Main / KG 결과 검산
19. technique별 결과 필요 시 확인
20. 실험 설정 및 결과 기록
21. 논문 결과 작성

