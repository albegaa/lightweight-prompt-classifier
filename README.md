# Lightweight Prompt Classifier

KoELECTRA 기반의 경량 프롬프트 공격 분류기 및 Selective Router 프로토타입이다.

졸업 프로젝트의 경량 분류기 초기 개발 및 기능 검증용 저장소.

> 현재 포함된 데이터와 실험 결과는 모두 파이프라인 동작 확인을 위한 소규모 Demo.

---

## 1. 목표

입력 프롬프트를 KoELECTRA 기반 Binary Classifier로 분석하여 공격 확률 `P(Attack)`을 계산하고, 두 개의 threshold를 이용해 다음과 같이 라우팅.

```text
Input
  ↓
KoELECTRA Binary Classifier
  ↓
P(Attack)
  ↓
├─ 낮은 확률 → Benign
├─ 중간 확률 → JailGuard
└─ 높은 확률 → Attack
```

Binary label은 다음과 같다.

* `0`: Benign
* `1`: Attack

Routing 규칙:

```text
P(Attack) < T_low
→ Benign

T_low ≤ P(Attack) ≤ T_high
→ JailGuard

P(Attack) > T_high
→ Attack
```

최종적인 목적은 공격 탐지 성능을 유지하면서 상대적으로 비용이 큰 JailGuard의 호출량을 줄이는 것.

---

## 2. 현재 구현 범위


* KoELECTRA Binary Classification
* Fine-tuning Pipeline
* Validation Pipeline
* Accuracy / Precision / Recall / F1
* False Positive Rate (FPR)
* False Negative Rate (FNR)
* Selective Router
* Threshold Sweep
* JailGuard Call Rate
* Attack Leakage Rate
* Benign Block Rate
* Validation probability 분석
* Fine-tuned model 기반 inference

---

## 3. 프로젝트 구조

```text
.
├── data/
│   └── processed/
│       ├── train_demo.csv
│       └── valid_demo.csv
│
├── docs/
│   └── development_log.md
│
├── results/
│   └── demo/
│       ├── metrics.json
│       ├── threshold_sweep.csv
│       └── validation_results.csv
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
├── requirements-common.txt
├── requirements-local.txt
└── .gitignore
```

---

## 4. 개발 환경

현재 로컬 개발 환경:

```text
OS           Ubuntu 24.04.4 LTS (WSL2)
Python       3.12.3
PyTorch      2.5.1+cpu
Transformers 4.46.3
```

현재 로컬 환경에는 NVIDIA GPU가 없어 CPU 기반으로 기능 검증을 진행.

실제 데이터 기반 대규모 학습 및 실험은 추후 학과 GPU 서버에서 진행할 예정.

---

## 5. 설치

### 가상환경 생성

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 패키지 설치

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-local.txt
```

---

## 6. Demo 학습

```bash
python src/classifier/train.py
```

기본적으로 다음 Demo 데이터를 사용.

```text
Train
- Benign: 8
- Attack: 8

Validation
- Benign: 4
- Attack: 4
```

Demo 데이터는 코드 및 학습 파이프라인 검증만을 위한 데이터이다.

---

## 7. Inference

학습 후 저장된 모델을 이용한 새로운 입력 테스트.

```bash
python src/classifier/inference.py \
  --text "오늘 점심 메뉴를 추천해줘."
```

예시 routing:

```text
P(Attack) < T_low
→ benign

T_low ≤ P(Attack) ≤ T_high
→ jailguard

P(Attack) > T_high
→ attack
```

---

## 8. 평가 지표

Binary Classifier 평가:

* Accuracy
* Precision
* Recall
* F1-score
* FPR
* FNR
* TP / TN / FP / FN

Selective Router 평가:

* JailGuard Call Rate
* Attack Leakage Rate
* Benign Block Rate

추후 `T_low`, `T_high` 결정해야.
