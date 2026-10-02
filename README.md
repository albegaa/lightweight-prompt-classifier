# Lightweight Prompt Classifier

졸업프로젝트 B 파트의 Step 1 경량 프롬프트 공격 분류기 개발 저장소.

본 저장소에서는 한국어 프롬프트 공격을 분류하는 경량 classifier의
학습·평가와 난독화 robustness 실험을 수행한다.

초기 개발 단계에서 구현한 Selective Router와 threshold 분석 코드도 함께 보존한다.
이 코드는 향후 팀의 최종 통합 시스템에서

    Input
      ↓
    Lightweight Classifier
      ↓
    Selective Router
      ├─ Benign
      ├─ JailGuard
      └─ Attack

구조로 연결하기 위한 prototype이다.

---

## 1. Step 1 목표

Step 1의 목적은 한국어 프롬프트 공격에 대해
경량 binary classifier의 탐지 성능을 평가하고,
난독화 데이터를 학습에 추가했을 때 robustness가 개선되는지 확인하는 것이다.

핵심 비교:

    Original-only Training
            vs
    Augmented Training

확인할 연구 질문:

1. Clean 데이터로만 학습한 classifier는 난독화 공격에서 성능이 얼마나 감소하는가?
2. 난독화 데이터를 학습에 추가하면 Obfuscated test 성능이 개선되는가?
3. 증강 학습이 Clean test 성능이나 Benign FPR에 부정적인 영향을 주는가?
4. 이러한 경향이 KoELECTRA와 mDeBERTa에서 공통적으로 나타나는가?

Binary label:

- `0` = Benign
- `1` = Attack

---

## 2. 비교 모델

### KoELECTRA

주 경량 classifier:

    monologg/koelectra-base-v3-discriminator

한국어 전용 encoder 모델이며 binary classification head를 추가하여 사용한다.

### mDeBERTa

비교 baseline:

    microsoft/mdeberta-v3-base

KoELECTRA와 동일한 binary classification task로 fine-tuning한다.

mDeBERTa는 tokenizer 호환성을 위해 slow tokenizer를 사용한다.

---

## 3. 실험 조건

총 4개의 fine-tuned classifier를 비교한다.

| Model | Training |
| --- | --- |
| KoELECTRA | Original-only |
| KoELECTRA | Augmented |
| mDeBERTa | Original-only |
| mDeBERTa | Augmented |

주 평가 세트:

- Clean test
- Obfuscated test

보조 평가 세트:

- KoreanGuardrail clean test
- KoreanGuardrail obfuscated test

KoreanGuardrail 평가는
번역 데이터의 문체적 특징에 모델이 과도하게 의존하는지 확인하기 위한
보조 분석으로 사용한다.

---

## 4. 현재 데이터 계약

원본 데이터 파일:

- `train.jsonl`
- `valid.jsonl`
- `test.jsonl`
- `kg_test.jsonl`

기본 필드:

| Field | Description |
| --- | --- |
| `id` | 각 행의 고유 ID |
| `text` | 한국어 입력 문장 |
| `label` | 0 = Benign, 1 = Attack |
| `source` | 원본 데이터셋 출처 |

난독화 및 증강 데이터에는 다음 필드가 추가된다.

| Field | Description |
| --- | --- |
| `seed_id` | variant가 파생된 원문의 `id` |
| `technique` | 난독화 기법 |
| `intensity` | 난독화 강도 |
| `changed` | 실제 문자열 변화 여부 |
| `n_changed` | 실제로 변경된 위치 수 |

원본과 variant의 관계:

    Original:
    id = xtram1_00123

    Variant:
    id = <variant unique id>
    seed_id = xtram1_00123

원본 데이터의 group ID는 `id`,
variant 데이터의 group ID는 `seed_id`로 해석한다.

분할은 증강 전에 원문 단위로 수행하며,
train / valid / test 간 동일 원문의 leakage를 허용하지 않는다.

---

## 5. T9b와 증강 학습

앞선 screening 결과를 이용한 T9b 최종 선정에서는
사전 pass 기준을 만족한 기법은 없었다.

ambiguous 보충 규칙에 따라 다음 두 조건이 선정되었다.

- `yamin_swap`, intensity `0.7`
- `symbol_insert`, intensity `0.3`

두 기법은 유효성이 확정된 pass 기법이 아니라
ambiguous 경계 사례로 선정된 조건이다.

Step 1 증강 학습에서는 이 두 조건을 사용한다.

난독화 평가에서는 특정 두 기법만 보는 것이 아니라
17종 난독화 기법의 평가셋을 사용하여 robustness를 확인한다.

---

## 6. 주요 평가 지표

Binary classifier:

- Accuracy
- Precision
- Recall
- F1
- FPR
- FNR
- TP / TN / FP / FN

주요 비교:

- Clean Recall / F1 / FPR
- Obfuscated Recall / F1 / FPR
- F1 Drop
- Recall Drop

class 1의 softmax 출력은

    attack-class softmax score

로 표현한다.

이 값은 calibration된 공격 확률이 아니므로
`P(Attack)`으로 해석하지 않는다.

---

## 7. Selective Router Prototype

초기 개발 단계에서 classifier score를 기반으로
세 구간으로 분기하는 Selective Router를 구현하였다.

개념적 구조:

    attack score < T_low
    → Benign

    T_low <= attack score <= T_high
    → JailGuard

    attack score > T_high
    → Attack

관련 코드:

- `src/classifier/router.py`
- `src/classifier/threshold_sweep.py`
- `src/classifier/analyze_validation_router.py`
- `src/classifier/inference.py`

관련 테스트:

- `src/classifier/test_router.py`
- `src/classifier/test_threshold_sweep.py`

현재 Router threshold는 최종값이 아니다.

Step 1 본실험에서 학습된 classifier의 validation score를 확보한 뒤
필요할 경우 threshold를 다시 분석한다.

최종 JailGuard 통합은 별도의 팀 통합 저장소에서 수행할 예정이다.

---

## 8. 프로젝트 구조

    lightweight-prompt-classifier/
    ├── README.md
    │
    ├── data/
    │   └── processed/
    │       ├── train_demo.csv
    │       └── valid_demo.csv
    │
    ├── docs/
    │   ├── development_log.md
    │   ├── step1_development_log.md
    │   ├── step1_experiment_plan.md
    │   ├── step1_runbook.md
    │   └── images/
    │
    ├── src/
    │   └── classifier/
    │       ├── train.py
    │       ├── evaluate.py
    │       ├── inference.py
    │       ├── router.py
    │       ├── threshold_sweep.py
    │       ├── analyze_validation_router.py
    │       └── test_*.py
    │
    ├── scripts/
    │   ├── validate_step1_data.py
    │   ├── prepare_augmented_train.py
    │   ├── run_original_train.sh
    │   ├── run_augmented_train.sh
    │   ├── run_step1_eval.sh
    │   ├── analyze_obfuscated_eval.py
    │   ├── make_step1_table.py
    │   └── make_step1_kg_summary.py
    │
    ├── results/
    │   └── demo/
    │
    ├── requirements-common.txt
    ├── requirements-local.txt
    ├── requirements-server.txt
    └── .gitignore

Demo 데이터와 Demo 결과는
기능 검증 기록을 보존하기 위한 것이며 최종 연구 성능으로 사용하지 않는다.

---

## 9. 실행 환경

공용 GPU 서버 기준 환경:

- Ubuntu
- Python 3.10.12
- PyTorch 2.4.1+cu121
- Transformers 4.51.3
- NumPy 2.2.6
- Pandas 2.3.3
- scikit-learn 1.7.2
- NVIDIA Tesla P100-PCIE-16GB

P100에서는 BF16이 아니라 FP16을 사용한다.

### 환경 설치

공용 GPU 서버:

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-server.txt

로컬 CPU 환경:

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-local.txt

공통 Python 패키지는 `requirements-common.txt`에서 관리하며,
PyTorch는 실행 환경에 따라 별도의 requirements 파일에서 설치한다.

- `requirements-server.txt`: 공용 GPU 서버 / CUDA 12.1
- `requirements-local.txt`: 로컬 CPU 환경

공용 GPU이므로 실제 학습 전 사용 가능한 GPU를 다시 확인한다.

    nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

---

## 10. 현재 구현 상태

완료:

- KoELECTRA binary classifier
- mDeBERTa binary classifier
- CSV / JSONL 데이터 로딩
- 공용 fine-tuning pipeline
- validation pipeline
- validation F1 기반 best model 저장
- 독립 evaluation pipeline
- KoELECTRA GPU smoke test
- mDeBERTa GPU smoke test
- Original-only 실행 script
- Augmented 실행 script
- 데이터 validation script
- `seed_id` 기반 원문-variant 검증
- Clean / Obfuscated 평가 script
- `kg_test` 평가 지원
- 17종 난독화 평가 지원
- Augmented training input 표준화
- changed-only 난독화 후처리
- technique / intensity별 난독화 분석
- Table 2 generator
- KoreanGuardrail supplementary summary
- Selective Router prototype
- Threshold Sweep prototype
- 저장 모델 기반 inference

현재 진행:

- 최종 실험 데이터 수령 및 검증
- Step 1 본실험
- 실험 결과 정리 및 논문 반영

---

## 11. 문서

초기 classifier 및 Router 개발 기록:

    docs/development_log.md

Step 1 개발 기록:

    docs/step1_development_log.md

Step 1 실험 설계:

    docs/step1_experiment_plan.md

Step 1 실행 절차:

    docs/step1_runbook.md

