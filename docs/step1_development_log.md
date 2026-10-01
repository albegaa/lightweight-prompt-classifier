# Step 1 Lightweight Prompt Classifier 개발 문서

## 1. 목적

본 저장소는 한국어 프롬프트 공격 탐지를 위한 경량 Binary Classifier의
학습·평가 파이프라인을 구현하기 위해 사용한다.

초기에는 KoELECTRA 기반 Selective Router의 기능 검증용 프로토타입으로 시작했으며,
현재는 KSC Step 1 본실험을 위해 다음 비교가 가능하도록 확장하였다.

- KoELECTRA Original-only
- KoELECTRA Augmented
- mDeBERTa Original-only
- mDeBERTa Augmented

본실험의 핵심 질문은 다음과 같다.

난독화 공격으로 증강한 데이터를 이용해 경량 분류기를 학습했을 때
Clean 공격 탐지 성능을 유지하면서
Obfuscated 공격에 대한 탐지 성능을 개선할 수 있는가?

---

# 2. 저장소 역할

프로젝트 내 실험 저장소 역할은 다음과 같이 분리한다.

## B-screening

담당 범위:

- T4 참조 탐지기 선정
- T6 Detector Evasion 측정
- T9a Detector Evasion × Target Delivery 교차분석

즉 난독화 기법 자체의 공격 유효성을 측정하는 스크리닝 단계 담당

## lightweight-prompt-classifier

담당 범위:

- Step 1 경량 분류기
- KoELECTRA 학습
- mDeBERTa 학습
- Original-only / Augmented 비교
- Clean / Obfuscated 평가
- 결과 표 자동 생성

즉 T9b에서 선정된 난독화 기법을 이용한
최종 경량 분류기 학습·평가 단계 담당

---

# 3. 초기 프로토타입

초기 저장소는 KoELECTRA 기반 경량 Prompt Classifier와
Selective Router 기능 검증을 위해 구현하였다.

초기 구조:

Input
→ KoELECTRA Binary Classifier
→ attack-class softmax score
→ Benign / JailGuard / Attack

Binary Label:

- 0 = Benign
- 1 = Attack

초기 구현 기능:

- KoELECTRA forward pass
- Binary classification head
- Fine-tuning
- Validation
- Accuracy / Precision / Recall / F1
- FPR / FNR
- TP / TN / FP / FN
- Inference
- Threshold Sweep
- Selective Router

초기 Demo 데이터:

Train:
- 16건
- Benign 8
- Attack 8

Validation:
- 8건
- Benign 4
- Attack 4

해당 Demo 데이터 및 결과는 코드 기능 검증용이며
최종 연구 성능으로 사용하지 않는다.

---

# 4. Step 1 본실험 방향 변경

KSC 논문은 Step 1 중심으로 구성하기로 결정하였다.

따라서 기존 프로토타입의 다음 기능을 본실험에 재사용한다.

- train.py
- evaluate.py
- Binary classifier
- 모델 저장 / 로드
- 평가 지표

반면 다음 기능은 현재 KSC Step 1 본실험에서는 핵심 범위에서 제외한다.

- Selective Router
- Threshold Sweep
- JailGuard routing
- T_low / T_high 최적화

해당 코드는 삭제하지 않고 향후 졸업논문 또는 Step 2 확장에 사용할 수 있도록 유지한다.

---

# 5. 비교 모델

## 5.1 KoELECTRA

Model:

monologg/koelectra-base-v3-discriminator

초기 classifier 프로토타입부터 사용한 한국어 모델이다.

Binary classification head를 새로 초기화한 뒤
0=Benign, 1=Attack으로 fine-tuning한다.

---

## 5.2 mDeBERTa

Model:

microsoft/mdeberta-v3-base

KoELECTRA와 비교하기 위한 다국어 baseline 모델로 사용한다.

KoELECTRA와 동일한 학습 코드를 사용하며
가능한 한 동일한 학습 설정을 유지한다.

단, tokenizer 구현 특성 때문에 mDeBERTa에서는
slow tokenizer를 사용한다.

---

# 6. 공통 학습 파이프라인

기존 train.py는 다음과 같은 Demo 전용 구조였다.

- KoELECTRA 모델명 고정
- CSV 경로 고정
- Demo 데이터 중심
- 최종 epoch 모델만 저장

이를 Step 1 본실험용 공용 학습 코드로 확장하였다.

현재 train.py 지원 기능:

- model name 인자 지정
- KoELECTRA / mDeBERTa 공용 사용
- CSV / JSONL 입력
- train / valid 파일 지정
- text / label column 지정
- epoch 인자화
- batch size 인자화
- learning rate 인자화
- weight decay 인자화
- max length 인자화
- random seed 고정
- FP16 지원
- smoke-test sample 제한
- epoch별 validation
- validation F1 기준 best model 저장
- best model reload
- validation prediction 저장
- training history 저장
- metrics.json 저장

기본 label:

- 0 = BENIGN
- 1 = ATTACK

---

# 7. Softmax 출력 표기

초기 프로토타입에서는 class-1 softmax 출력을
P(Attack)으로 표기하였다.

하지만 해당 값은 calibration된 probability가 아니므로
본실험 및 개발문서에서는 다음 표현을 사용한다.

attack-class softmax score

현재 validation 및 evaluation 결과에서는
해당 값을 attack_score 필드에 저장한다.

---

# 8. 재현성 설정

현재 공통 설정:

- seed = 42
- learning rate = 2e-5
- weight decay = 0.01
- max length = 128
- FP16 사용 가능
- best model = validation F1 기준

epoch와 batch size는 실제 데이터 규모 및
GPU 메모리를 확인한 뒤 최종 고정한다.

KoELECTRA와 mDeBERTa는 비교의 공정성을 위해
가능한 한 동일한 학습 조건을 사용한다.

---

# 9. mDeBERTa Tokenizer 처리

microsoft/mdeberta-v3-base를 AutoTokenizer 기본 설정으로 로드할 경우
fast tokenizer 변환 과정에서 다음 경고가 발생하였다.

SentencePiece tokenizer의 byte fallback 옵션이
fast tokenizer에서 동일하게 구현되지 않을 수 있음

본 프로젝트는 한글 난독화 문자열을 직접 처리하므로
tokenizer 차이가 결과에 영향을 줄 가능성을 줄이기 위해
mDeBERTa에서는 slow tokenizer를 사용한다.

옵션:

--use-slow-tokenizer

실제 smoke test에서 다음 tokenizer 사용을 확인하였다.

DebertaV2Tokenizer

KoELECTRA는 기존 fast tokenizer를 사용한다.

ElectraTokenizerFast

---

# 10. 서버 환경

본 smoke test는 학과 GPU 서버에서 수행하였다.

환경:

- GPU: NVIDIA Tesla P100-PCIE-16GB
- Python: 3.10.12
- PyTorch: 2.4.1+cu121
- Transformers: 4.51.3
- NumPy: 2.2.6
- Pandas: 2.3.3
- scikit-learn: 1.7.2

가상환경:

/root/project/.venv

공용 GPU 서버이므로 실행 전 반드시 GPU 사용량을 확인한다.

명령:

nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

---

# 11. KoELECTRA GPU Smoke Test

공용 train.py가 실제 GPU 환경에서 동작하는지 확인하기 위해
기존 Demo 데이터로 1 epoch smoke test를 수행하였다.

조건:

- model: monologg/koelectra-base-v3-discriminator
- train: 16건
- valid: 8건
- epoch: 1
- batch size: 4
- learning rate: 2e-5
- max length: 128
- seed: 42
- FP16
- GPU: Tesla P100

결과:

- Accuracy = 0.7500
- Precision = 1.0000
- Recall = 0.5000
- F1 = 0.6667
- FPR = 0.0000
- FNR = 0.5000
- TP = 2
- TN = 4
- FP = 0
- FN = 2

확인한 기능:

- pretrained model 다운로드
- classifier head 초기화
- GPU 이동
- FP16 forward
- backward
- optimizer step
- validation
- best model 저장
- best model reload
- metrics 저장
- prediction 저장

최종 출력:

TRAINING PIPELINE SUCCESS

주의:

본 결과는 16/8건의 Demo 데이터에서 얻은 기능 검증 결과이며
연구 성능으로 사용하지 않는다.

---

# 12. mDeBERTa GPU Smoke Test

동일한 train.py에서 model name만 변경하여
mDeBERTa가 정상 동작하는지 확인하였다.

조건:

- model: microsoft/mdeberta-v3-base
- train: 16건
- valid: 8건
- epoch: 1
- batch size: 4
- learning rate: 2e-5
- max length: 128
- seed: 42
- FP16
- slow tokenizer 사용

Tokenizer:

DebertaV2Tokenizer

결과:

- Accuracy = 0.5000
- Precision = 0.0000
- Recall = 0.0000
- F1 = 0.0000
- FPR = 0.0000
- FNR = 1.0000
- TP = 0
- TN = 4
- FP = 0
- FN = 4

최종 출력:

TRAINING PIPELINE SUCCESS

해당 성능 역시 Demo 데이터 기능 검증 결과이므로
실제 모델 성능 비교에 사용하지 않는다.

중요한 확인 사항은
KoELECTRA와 mDeBERTa가 동일한 train.py에서
정상적으로 학습된다는 점이다.

---

# 13. 공용 평가 파이프라인

기존 evaluate.py는 compute_binary_metrics 함수만 제공하였다.

Step 1 본실험을 위해 저장된 fine-tuned 모델을
독립적으로 평가할 수 있도록 확장하였다.

지원 기능:

- 저장 모델 경로 입력
- CSV / JSONL 평가 데이터
- text / label column 선택
- KoELECTRA / mDeBERTa 공용
- FP16 evaluation
- slow tokenizer 옵션
- Accuracy
- Precision
- Recall
- F1
- FPR
- FNR
- TP / TN / FP / FN
- attack-class softmax score
- predictions.csv 저장
- metrics.json 저장

---

# 14. KoELECTRA 독립 평가 재현

KoELECTRA smoke training에서 저장한 best_model을
새로운 evaluate.py에서 다시 불러와
동일한 validation 8건을 평가하였다.

독립 평가 결과:

- Accuracy = 0.7500
- Precision = 1.0000
- Recall = 0.5000
- F1 = 0.6667
- TP = 2
- TN = 4
- FP = 0
- FN = 2

학습 직후 validation 결과와 동일하였다.

최종 출력:

EVALUATION PIPELINE SUCCESS

따라서 저장 모델 → 독립 evaluation 과정이 정상 동작함을 확인하였다.

---

# 15. mDeBERTa 독립 평가 재현

mDeBERTa smoke training에서 저장한 best_model을
evaluate.py에서 다시 평가하였다.

slow tokenizer 사용:

DebertaV2Tokenizer

결과:

- Accuracy = 0.5000
- Precision = 0.0000
- Recall = 0.0000
- F1 = 0.0000
- TP = 0
- TN = 4
- FP = 0
- FN = 4

학습 직후 분류 결과와 동일하였다.

학습 직후 validation loss와 독립 FP16 evaluation loss 사이에는
미세한 차이가 있었지만 prediction 및 분류 지표는 동일하였다.

최종 출력:

EVALUATION PIPELINE SUCCESS

---

# 16. 본실험 데이터 구조

예상 데이터 구조:

data/step1/

original/
- train.csv
- valid.csv
- test.csv

augmented/
- train.csv

evaluation/
- obfuscated_test.csv

필수 필드:

- text
- label

권장 메타데이터:

- seed_id 또는 base_prompt_id
- category
- technique
- intensity
- changed

label:

- 0 = Benign
- 1 = Attack

---

# 17. 데이터 누수 방지

동일한 원본 prompt에서 생성된 variant가
Train / Validation / Test에 분리되어 포함될 경우
난독화 robustness 평가가 과대평가될 수 있다.

따라서 split은 원본 prompt 단위로 수행해야 한다.

우선 사용 후보:

- base_prompt_id
- seed_id

이를 자동 검사하기 위해 다음 스크립트를 구현하였다.

scripts/validate_step1_data.py

검사 항목:

- text / label column 존재
- null
- empty text
- binary label
- split 내부 duplicate text
- conflicting label
- split 간 exact text leakage
- base_prompt_id / seed_id 기준 leakage

Demo 데이터에는 group ID가 없어
group leakage 검사는 수행되지 않았으며
해당 사실을 warning으로 출력하였다.

Demo smoke 결과:

ALL CHECKS PASSED

실제 Step 1 데이터에서는 group ID 검사를 통과한 뒤에만
본학습을 수행한다.

---

# 18. Original-only 학습 실행 스크립트

파일:

scripts/run_original_train.sh

사용 형식:

bash scripts/run_original_train.sh \
  <koelectra|mdeberta> \
  <gpu> \
  <epochs> \
  <batch_size>

예:

bash scripts/run_original_train.sh koelectra 7 3 16

mDeBERTa 예:

bash scripts/run_original_train.sh mdeberta 7 3 16

기능:

- 모델 선택
- GPU 선택
- epoch / batch size 전달
- 공통 learning rate 적용
- 공통 weight decay 적용
- FP16 적용
- mDeBERTa slow tokenizer 자동 적용
- 결과 경로 자동 지정

결과 위치:

results/step1/koelectra/original/

results/step1/mdeberta/original/

---

# 19. Augmented 학습 실행 스크립트

파일:

scripts/run_augmented_train.sh

증강 학습 데이터:

data/step1/augmented/train.csv

Validation:

data/step1/original/valid.csv

Original-only 모델과 Augmented 모델 모두
동일한 validation set을 사용한다.

사용 형식:

bash scripts/run_augmented_train.sh \
  <koelectra|mdeberta> \
  <gpu> \
  <epochs> \
  <batch_size>

결과 위치:

results/step1/koelectra/augmented/

results/step1/mdeberta/augmented/

---

# 20. Clean / Obfuscated 평가 스크립트

파일:

scripts/run_step1_eval.sh

각 모델은 다음 두 평가 세트에서 평가한다.

Clean:

data/step1/original/test.csv

Obfuscated:

data/step1/evaluation/obfuscated_test.csv

사용 형식:

bash scripts/run_step1_eval.sh \
  <koelectra|mdeberta> \
  <original|augmented> \
  <gpu> \
  <batch_size>

예:

bash scripts/run_step1_eval.sh \
  koelectra \
  original \
  7 \
  16

한 번 실행하면 다음 두 평가를 연속 수행한다.

- Clean test
- Obfuscated test

결과:

eval/clean/metrics.json
eval/clean/predictions.csv

eval/obfuscated/metrics.json
eval/obfuscated/predictions.csv

---

# 21. 본실험 비교 행렬

최종 비교 모델은 총 4개이다.

| Model | Training |
| --- | --- |
| KoELECTRA | Original-only |
| KoELECTRA | Augmented |
| mDeBERTa | Original-only |
| mDeBERTa | Augmented |

각 모델은 동일한 두 평가 세트에서 평가한다.

- Clean
- Obfuscated

따라서 총 classifier evaluation 결과는 다음과 같다.

4 models
×
2 evaluation sets
=
8 metrics.json

---

# 22. 평가 지표

본실험에서는 다음 지표를 저장한다.

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

특히 논문에서는 다음을 중심으로 비교할 예정이다.

- Clean Recall
- Clean F1
- Clean FPR
- Obfuscated Recall
- Obfuscated F1
- Obfuscated FPR
- Clean 대비 Obfuscated 성능 감소폭

---

# 23. 표 2 자동 생성

파일:

scripts/make_step1_table.py

목적:

4개 classifier의 Clean / Obfuscated 결과를 자동 집계하여
논문 표 2 작성을 위한 CSV를 생성한다.

입력:

각 모델의 eval/clean/metrics.json
각 모델의 eval/obfuscated/metrics.json

출력:

results/step1/table2_summary.csv

집계 대상:

- KoELECTRA Original
- KoELECTRA Augmented
- mDeBERTa Original
- mDeBERTa Augmented

포함 항목:

- Clean Accuracy
- Clean Precision
- Clean Recall
- Clean F1
- Clean FPR
- Clean FNR
- Obfuscated Accuracy
- Obfuscated Precision
- Obfuscated Recall
- Obfuscated F1
- Obfuscated FPR
- Obfuscated FNR
- F1 Drop
- Recall Drop

percentage point 값은 소수 둘째 자리까지 저장한다.

---

# 24. 표 2 생성 Smoke Test

실제 본실험 결과가 아직 없으므로
/tmp에 가상의 metrics.json을 생성하여
end-to-end 집계 기능을 검증하였다.

가상 입력:

Clean F1 = 89.50
Obfuscated F1 = 73.80

출력:

F1 Drop = 15.70 pp

CSV에서도 다음과 같이 정상 저장됨을 확인하였다.

15.70

기존 floating point 표현:

15.700000000000003

문제는 float_format 설정으로 수정하였다.

최종:

PY_COMPILE SUCCESS

표 생성 성공

CSV 저장 성공

---

# 25. 실험 실행 Runbook

파일:

docs/step1_runbook.md

실제 데이터 전달 후 다음 전체 절차를 따라갈 수 있도록
본실험 실행 순서를 별도 문서로 작성하였다.

주요 내용:

- Git 최신화
- GPU 확인
- 데이터 구조 확인
- 데이터 leakage 검사
- 데이터 규모 확인
- 학습 설정 확정
- Original-only 학습
- Augmented 학습
- Clean 평가
- Obfuscated 평가
- 결과 파일 검산
- 표 2 자동 생성
- 논문 결과 해석

현재 문서는 생성된 상태이며
Git commit 여부는 별도 확인이 필요하다.

---

# 26. Git Ignore 정책

Fine-tuned model은 GitHub에 업로드하지 않는다.

현재 주요 ignore 대상:

- *.pt
- *.pth
- *.bin
- *.safetensors
- results/smoke/
- results/**/model/
- results/**/best_model/

Smoke test 모델은 수백 MB에서 1GB 이상이므로
Git 저장소에는 포함하지 않는다.

또한 실제 predictions.csv에는 원본 prompt가 포함될 수 있으므로
본실험 결과 공개 전 반드시 내용과 공개 범위를 확인한다.

---

# 27. 주요 Git Commit

현재 Step 1 본실험 준비 과정의 주요 commit은 다음과 같다.

## 0968401

feat: generalize classifier training pipeline

내용:

- 기존 KoELECTRA Demo train.py 확장
- model-name 인자화
- CSV / JSONL 지원
- KoELECTRA / mDeBERTa 공용화
- FP16
- epoch별 validation
- best F1 model 저장
- training history 저장

---

## d9f1d98

feat: add reusable classifier evaluation pipeline

내용:

- 독립 evaluation pipeline 구현
- 저장된 모델 평가
- Clean / Obfuscated 공용 평가 기반
- predictions.csv
- metrics.json
- attack-class softmax score 저장

---

## c50feeb

docs: add Step 1 experiment plan

내용:

- Step 1 실험 구조
- 데이터 계약
- 비교 모델
- 공통 학습 설정
- 결과 구조
- smoke-test 상태 기록

---

## 6065970

feat: add Step 1 training and data validation scripts

내용:

- Original-only 학습 실행 script
- Step 1 데이터 leakage 검사
- label / duplicate / group split 검사

---

## 20217c3

feat: add augmented training and Step 1 evaluation scripts

내용:

- Augmented 학습 script
- Clean / Obfuscated 공용 evaluation script

---

## 355b821

feat: add Step 1 result table generator

내용:

- 4 classifier 결과 자동 집계
- Clean / Obfuscated 비교
- F1 / Recall drop 자동 계산
- table2_summary.csv 생성

---

# 28. 현재 Repository 구조

주요 구조:

lightweight-prompt-classifier/

data/
- processed/
  - train_demo.csv
  - valid_demo.csv

docs/
- development_log.md
- step1_experiment_plan.md
- step1_runbook.md
- images/

src/
- classifier/
  - train.py
  - evaluate.py
  - inference.py
  - router.py
  - threshold_sweep.py
  - analyze_validation_router.py
  - test_metrics.py
  - test_model.py
  - test_router.py
  - test_threshold_sweep.py
  - test_train_step.py

scripts/
- validate_step1_data.py
- run_original_train.sh
- run_augmented_train.sh
- run_step1_eval.sh
- make_step1_table.py

results/
- demo/
- smoke/

---

# 29. 현재 완료 상태

완료:

- 초기 KoELECTRA classifier prototype
- Binary classification pipeline
- Validation metrics
- Router prototype
- Threshold Sweep prototype
- KoELECTRA / mDeBERTa 공용 train.py
- KoELECTRA GPU smoke training
- mDeBERTa GPU smoke training
- mDeBERTa slow tokenizer 처리
- 공용 evaluate.py
- KoELECTRA 독립 평가 재현
- mDeBERTa 독립 평가 재현
- Step 1 데이터 validation script
- Original-only 실행 script
- Augmented 실행 script
- Clean / Obfuscated evaluation script
- 표 2 자동 집계 script
- Step 1 experiment plan
- Step 1 runbook

---

# 30. 본실험 전 남은 결정

아직 확정되지 않은 항목:

- 실제 Step 1 train 데이터
- 실제 valid 데이터
- 실제 clean test 데이터
- 실제 obfuscated test 데이터
- group ID 필드명
- T9b 최종 선정 난독화 기법
- augmented train 구성
- epoch 수
- batch size

해당 값은 데이터 전달 및 T9b 완료 후 최종 확정한다.

---

# 31. 이후 본실험 순서

실제 데이터 도착 후 다음 순서로 진행한다.

1. 데이터 파일 배치
2. validate_step1_data.py
3. split leakage 확인
4. label / 데이터 규모 확인
5. epoch / batch size 확정
6. KoELECTRA Original 학습
7. mDeBERTa Original 학습
8. KoELECTRA Augmented 학습
9. mDeBERTa Augmented 학습
10. 4개 모델 Clean 평가
11. 4개 모델 Obfuscated 평가
12. metrics.json 8개 확인
13. make_step1_table.py
14. table2_summary.csv 검산
15. 논문 표 2 작성
16. 4.1 Step 1 실험 설정 작성
17. 4.3 증강 학습 결과 작성

---

# 32. 논문 연결

## 3.3 증강 학습

담당:

채원

작성 내용:

- classifier 모델
- Original-only 학습
- Augmented 학습
- T9b 선정 난독화 기법 사용
- 동일 validation set
- 학습 데이터 구성

---

## 4.1 실험 설정

Step 1 담당:

채원

작성 내용:

- KoELECTRA
- mDeBERTa
- binary labels
- learning rate
- epoch
- batch size
- max length
- random seed
- FP16
- validation F1 기준 best model
- 평가 지표

---

## 4.3 증강 학습 결과

담당:

채원

핵심:

- 표 2
- Original vs Augmented
- Clean vs Obfuscated
- Attack Recall 변화
- F1 변화
- Benign FPR 변화
- robustness 개선 여부
- Clean 성능 trade-off 여부

실제 수치가 나온 뒤 결과에 근거해 해석한다.

---

# 33. 현재 결론

현재 lightweight-prompt-classifier는
초기 KoELECTRA 기능 검증용 프로토타입에서
Step 1 본실험을 실행할 수 있는 공용 학습·평가 파이프라인으로 확장되었다.

현재 확인된 범위:

- KoELECTRA 학습 가능
- mDeBERTa 학습 가능
- 두 모델 공용 train.py 사용 가능
- 두 모델 공용 evaluate.py 사용 가능
- P100 FP16 실행 가능
- 모델별 tokenizer 차이 처리 완료
- 데이터 leakage 자동 검사 가능
- Original / Augmented 학습 자동화
- Clean / Obfuscated 평가 자동화
- 표 2 결과 자동 집계 가능

현재 실제 연구 성능에 대한 결론은 내리지 않는다.

Smoke Test에 사용한 Demo 데이터는 코드 기능 검증용이며,
최종 연구 결과는 실제 Step 1 데이터로 수행하는 본실험 이후 작성한다.
