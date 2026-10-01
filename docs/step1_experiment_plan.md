# Step 1 Experiment Plan

## 1. Goal

한국어 프롬프트 공격에 대해 경량 분류기의 원문 학습과
난독화 증강 학습 성능을 비교한다.

비교 모델:

- KoELECTRA
- mDeBERTa-v3-base

학습 조건:

- Original-only
- Augmented

모든 모델은 동일한 평가 데이터를 사용한다.

---

## 2. Label

- 0 = Benign
- 1 = Attack

---

## 3. Data Contract

필수 필드:

- text
- label

권장 메타데이터:

- seed_id 또는 base_prompt_id
- category
- technique
- intensity
- changed

동일한 원본 prompt에서 생성된 variant가
train / validation / test에 나뉘지 않도록
seed_id 또는 base_prompt_id 기준으로 split한다.

---

## 4. Expected Data Layout

data/step1/

- original/
  - train.csv
  - valid.csv
  - test.csv

- augmented/
  - train.csv

- evaluation/
  - obfuscated_test.csv

### original/train.csv

원문 데이터만 포함한 학습 세트.

### original/valid.csv

모델 선택 및 validation에 사용.

### original/test.csv

Clean 성능 평가 전용.

학습 및 모델 선택에 사용하지 않는다.

### augmented/train.csv

Original train에 T9b에서 선정된 난독화 기법을 적용하여
구성한 증강 학습 세트.

### evaluation/obfuscated_test.csv

난독화 robustness 평가 전용.

학습 데이터와 독립된 원본 seed에서 생성한다.

---

## 5. Models

### KoELECTRA

Model:

monologg/koelectra-base-v3-discriminator

### mDeBERTa

Model:

microsoft/mdeberta-v3-base

mDeBERTa는 SentencePiece byte-fallback 동작 보존을 위해
slow tokenizer를 사용한다.

---

## 6. Common Training Settings

두 모델은 가능한 한 동일한 학습 설정을 사용한다.

공통 설정 후보:

- seed = 42
- learning rate = 2e-5
- weight decay = 0.01
- max length = 128
- FP16 = enabled
- model selection = validation F1

epoch와 batch size는 본 데이터 규모와
GPU 메모리를 확인한 뒤 최종 고정한다.

모델 구조상 발생하는 tokenizer 등의 구현 차이만
모델별 예외로 허용한다.

---

## 7. Experiment Matrix

1. KoELECTRA + Original-only
2. KoELECTRA + Augmented
3. mDeBERTa + Original-only
4. mDeBERTa + Augmented

모든 학습 모델은 동일한 두 평가 세트에서 평가한다.

- Clean test
- Obfuscated test

---

## 8. Metrics

기본 지표:

- Accuracy
- Precision
- Recall
- F1
- FPR
- FNR
- TP
- TN
- FP
- FN

분류기의 class-1 softmax 출력은
calibrated probability가 아니므로
P(Attack) 대신
attack-class softmax score로 표기한다.

---

## 9. Result Layout

results/step1/

- koelectra/
  - original/
  - augmented/

- mdeberta/
  - original/
  - augmented/

각 학습 결과에는 최소한 다음을 저장한다.

- best_model/
- metrics.json
- training_history.csv
- validation_results.csv

각 평가 결과에는 다음을 저장한다.

- predictions.csv
- metrics.json

---

## 10. Current Smoke-Test Status

공용 train.py와 evaluate.py에서 다음을 확인했다.

- KoELECTRA GPU 학습 성공
- KoELECTRA 독립 평가 성공
- mDeBERTa GPU 학습 성공
- mDeBERTa slow tokenizer 학습 성공
- mDeBERTa 독립 평가 성공

Demo 데이터는 파이프라인 기능 검증용이며
연구 성능으로 사용하지 않는다.

---

## 11. Current Implementation Status

완료:

- 공용 train.py
- 공용 evaluate.py
- KoELECTRA 1 epoch smoke test
- mDeBERTa 1 epoch smoke test
- P100 FP16 학습 확인
- best model 저장 및 reload 확인
- 독립 평가 결과 재현 확인

대기:

- 실제 Step 1 데이터 수신
- T9b 최종 선정 기법 반영
- Original-only 본학습
- Augmented 본학습
- Clean / Obfuscated 본평가
- 논문 표 2 작성
