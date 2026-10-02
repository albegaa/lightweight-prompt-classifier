# Step 1 Lightweight Prompt Classifier 개발 문서

> **문서 읽는 법**
>
> 이 문서는 Step 1 개발 과정을 시간순으로 보존하는 개발 기록이다.
> 앞쪽 절의 "현재 상태", "남은 결정" 등은 작성 당시의 상태를 나타내며
> 이후 개발 과정에서 변경된 내용은 문서 마지막의 최신 상태 절에서 갱신한다.
>
> 현재 실행 절차는 `docs/step1_runbook.md`,
> 현재 실험 설계는 `docs/step1_experiment_plan.md`,
> 저장소의 현재 역할은 `README.md`를 기준으로 한다.

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

---

# 34. 2026-10-02 Step 1 구조 재정리 및 본실험 파이프라인 확정

## 34.1 저장소 역할 재정의

프로젝트 저장소의 역할을 다음과 같이 정리하였다.

### lightweight-prompt-classifier

B 파트 개인 Step 1 개발 저장소.

담당 범위:

- 경량 classifier 개발
- KoELECTRA / mDeBERTa fine-tuning
- Original-only / Augmented 비교
- Clean / Obfuscated robustness 평가
- KoreanGuardrail 보조 평가
- 초기 Selective Router prototype 보존

본 저장소의 classifier가 안정화된 이후
최종 통합에 필요한 검증된 구성요소만
별도의 팀 통합 저장소로 이관한다.

### B-screening

B 파트 개인 연구 및 실험 기록 저장소.

주요 기록:

- T4 Reference Detector
- T6 Detector Evasion
- T9a Effective Attack
- T9b 결과 연결
- Step 1 주요 실험 결정 및 해석

active classifier code의 기준 저장소로 사용하지 않는다.

### 향후 팀 통합 저장소

A/B/C가 공동 작업할 최종 시스템 저장소.

목표 구조:

    Input
      ↓
    Lightweight Classifier
      ↓
    Selective Router
      ↓
    JailGuard
      ↓
    Target LLM

각 개인 저장소 전체를 복사하는 것이 아니라
최종 pipeline에 필요한 검증된 코드만 이관한다.

동일한 active code를 개인 저장소와
팀 통합 저장소에서 동시에 수정하지 않는 것을 원칙으로 한다.

---

## 34.2 최종 데이터 계약 반영

원본 데이터:

- train
- valid
- test
- kg_test

기본 필드:

- `id`
- `text`
- `label`
- `source`

variant 데이터 추가 필드:

- `seed_id`
- `technique`
- `intensity`
- `changed`
- `n_changed`

source group은 다음과 같이 해석한다.

    Original row
    → id

    Variant row
    → seed_id

즉,

    original.id == variant.seed_id

관계를 이용해 원본과 variant를 연결한다.

---

## 34.3 T9b 결과 반영

T9b 사전 pass 기준을 만족한 기법은 0종이었다.

ambiguous fallback 규칙에 따라
Step 1 증강 조건으로 다음 두 cell을 선정하였다.

- `yamin_swap`, intensity `0.7`
- `symbol_insert`, intensity `0.3`

두 조건은 효과가 입증된 pass 기법이 아니라
ambiguous 경계 사례이다.

따라서 논문 및 결과 해석에서도
"유효한 공격 기법을 발견했다"는 식으로 표현하지 않는다.

---

## 34.4 데이터 validator 개편

`scripts/validate_step1_data.py`를
최종 데이터 계약에 맞게 개편하였다.

지원 데이터:

- train
- valid
- test
- kg_test
- augmented_train
- obfuscated_test
- obfuscated_kg_test

주요 검사:

- 필수 필드
- null / empty
- label 0/1
- ID 중복
- conflicting label
- exact-text leakage
- source-group leakage
- variant `seed_id`의 parent 존재 여부
- variant label 일치 여부
- variant source 일치 여부
- augmented variant의 `changed=false` 금지

허용 overlap:

    train ↔ augmented_train
    test ↔ obfuscated_test
    kg_test ↔ obfuscated_kg_test

Synthetic test 결과:

1. 정상 구조 → `VALIDATION PASSED`
2. augmented `changed=false` → 의도대로 실패
3. train / test source-group leakage → 의도대로 실패

---

## 34.5 Augmented 학습 입력 표준화

`scripts/prepare_augmented_train.py`를 추가하였다.

목적:

A가 전달하는 augmented 파일 형식이

1. variant-only
2. original + variant 합본

중 어느 형태이더라도
동일한 Step 1 학습 pipeline을 사용할 수 있도록 한다.

variant-only 입력:

    original train
        +
    variants
        ↓
    prepared_train.jsonl

combined 입력:

    original + variants
        ↓
    원본 completeness 검증
        ↓
    prepared_train.jsonl

검사:

- variant seed가 original train에 존재하는지
- `changed=false`가 없는지
- variant ID 충돌 여부
- 합본 원문이 original train과 동일한지

Synthetic test에서
variant-only와 combined 입력을 모두 검증하였다.

---

## 34.6 학습 실행 script 개편

### Original-only

`scripts/run_original_train.sh`

입력:

- model key
- train file
- valid file
- GPU
- epochs

CSV 고정 경로를 제거하고
실제 JSONL 파일 경로를 인자로 받도록 변경하였다.

지원 모델:

- KoELECTRA
- mDeBERTa

### Augmented

`scripts/run_augmented_train.sh`

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

Original-only와 동일한 validation set을 사용한다.

---

## 34.7 평가 pipeline 확장

`scripts/run_step1_eval.sh`를
임의 평가 파일을 받을 수 있는 구조로 변경하였다.

지원 평가:

- `clean`
- `obfuscated`
- `kg_clean`
- `kg_obfuscated`

따라서 네 학습 조건에 대해

    4 training conditions
        ×
    4 evaluation sets
        =
    16 evaluations

을 동일한 script로 수행할 수 있다.

---

## 34.8 평가 metadata 보존 확인

`src/classifier/evaluate.py`는
입력 DataFrame을 복사한 뒤

- `prediction`
- `attack_score`

를 추가하여 `predictions.csv`를 저장한다.

따라서 난독화 평가 입력에 존재하는

- `id`
- `seed_id`
- `source`
- `technique`
- `intensity`
- `changed`
- `n_changed`

metadata가 결과 파일에도 그대로 보존된다.

`attack_score`는 calibrated probability가 아니라
class 1의 softmax score이다.

---

## 34.9 난독화 평가 후처리 추가

`scripts/analyze_obfuscated_eval.py`를 추가하였다.

출력:

- `obfuscated_overall.csv`
- `obfuscated_by_technique.csv`
- `obfuscated_by_cell.csv`

분석:

### all_rows

변형 시도 전체 행 기준 raw 평가.

### changed_only

실제로 문자열이 변경된
`changed=true` 행만을 사용한 평가.

### application_rate

    changed=true rows
    -----------------
       total rows

난독화 robustness의 주 결과는
`changed_only`를 사용한다.

단, all_rows 결과도 raw artifact로 보존한다.

추가 분석:

- technique별
- technique × intensity별

Synthetic predictions를 이용한 자동 assertion test에서

    ALL ASSERTIONS PASSED

를 확인하였다.

---

## 34.10 Main Step 1 결과표 변경

`scripts/make_step1_table.py`를 수정하였다.

Clean 결과:

    eval/clean/metrics.json

Obfuscated 결과:

    eval/obfuscated/analysis/obfuscated_overall.csv
    scope = changed_only

즉 메인 난독화 결과에는
실제 변형된 행만 사용한다.

추가 기록:

- total obfuscated rows
- changed rows
- application rate
- F1 Drop
- Recall Drop

Synthetic result test에서
`all_rows`에 의도적으로 F1 99%를 입력하고
`changed_only`에는 다른 값을 입력하였다.

최종 table이 `changed_only` 값을 읽는 것을 확인하였고,

    ALL TABLE ASSERTIONS PASSED

를 확인하였다.

---

## 34.11 KoreanGuardrail 보조 평가 추가

`scripts/make_step1_kg_summary.py`를 추가하였다.

Clean:

    eval/kg_clean/metrics.json

Obfuscated:

    eval/kg_obfuscated/analysis/obfuscated_overall.csv
    scope = changed_only

출력:

    results/step1/kg_summary.csv

목적:

번역 데이터의 문체적 특징에 classifier가
과도하게 의존하는지 보조적으로 확인한다.

Synthetic KG result test에서

    ALL KG ASSERTIONS PASSED

를 확인하였다.

KG 결과는 보조 평가이며
KSC 지면이 부족한 경우 졸업논문 중심으로 사용할 수 있다.

---

## 34.12 Runbook 및 실험 계획 최신화

다음 문서를 현재 pipeline에 맞게 갱신하였다.

- `README.md`
- `docs/step1_experiment_plan.md`
- `docs/step1_runbook.md`

주요 반영 내용:

- 저장소 역할 재정의
- JSONL 데이터 계약
- T9b 최종 선정 조건
- `id ↔ seed_id` 관계
- KG 평가
- `changed=true` 주 평가 기준
- 현재 학습 / 평가 script interface
- Main / KG summary 생성 절차
- 향후 팀 통합 저장소 계획

---

## 34.13 현재 Step 1 코드 상태

현재 구현 완료:

- KoELECTRA training
- mDeBERTa training
- CSV / JSONL loader
- validation F1 best model selection
- Original-only training script
- Augmented training script
- variant-only / combined augmentation normalization
- 최종 데이터 validator
- clean evaluation
- obfuscated evaluation
- KG clean evaluation
- KG obfuscated evaluation
- metadata-preserving predictions
- changed-only analysis
- technique analysis
- technique × intensity analysis
- Main Step 1 table generator
- KG supplementary summary generator
- Selective Router prototype
- threshold sweep prototype

Synthetic test 완료:

- validator 정상 case
- changed=false rejection
- source-group leakage rejection
- variant-only augmentation
- combined augmentation
- obfuscated metrics
- main table
- KG summary

---

## 34.14 현재 남은 작업

아직 실제 연구 성능은 측정하지 않았다.

남은 작업:

1. 최종 Step 1 데이터 수신
2. 실제 파일 schema 검증
3. 실제 데이터 규모 / label 분포 기록
4. T9b 두 증강 조건 포함 여부 확인
5. epochs 확정
6. batch size 확정
7. KoELECTRA Original 학습
8. mDeBERTa Original 학습
9. KoELECTRA Augmented 학습
10. mDeBERTa Augmented 학습
11. Clean / Obfuscated 평가
12. KG 보조 평가
13. `table2_summary.csv` 생성
14. `kg_summary.csv` 생성
15. 실제 결과 검산
16. B-screening에 최종 실험 결정 및 결과 기록
17. 논문 실험 설정 및 결과 작성

현재 단계에서는
augmentation의 성능 개선 여부에 대한 결론을 내리지 않는다.

---

## 34.15 다음 통합 단계

Step 1 본실험이 안정화되면
본 저장소 전체를 새 팀 저장소로 복사하지 않는다.

통합에 필요한 검증된 구성요소만 선정한다.

예상 B 파트 이관 대상:

- trained lightweight classifier
- classifier inference
- attack-class softmax score 출력
- 필요한 Router logic
- 필요한 threshold configuration

이후 별도 팀 저장소에서
A/B/C 구성요소를 연결하여 최종 pipeline을 구성한다.

현재 Step 1 개발 단계에서는
팀 통합 저장소를 아직 active source로 사용하지 않는다.

---

## 34.16 Step 1 본실험 전 최종 사전 점검

실제 Step 1 데이터 수신 전에
현재 학습·평가 pipeline이 본실험에 사용할 수 있는 상태인지
추가 검증을 수행하였다.

### 데이터 validator 재검증

`validate_step1_data.py`에 대해 synthetic test를 다시 수행하였다.

확인 결과:

- 정상 데이터 → `VALIDATION PASSED`
- augmented variant의 `changed=false` → 정상 rejection
- train / test source-group leakage → 정상 rejection
- `label=0.5` → 정상 rejection

따라서 binary label 계약과
원문 단위 leakage 검사가 의도대로 동작함을 확인하였다.

### Augmented training input 준비 검증

`prepare_augmented_train.py`에 대해
두 입력 형태를 모두 검증하였다.

지원 형태:

1. variant-only
2. original + variant combined

두 입력 방식 모두 동일한 최종 학습 JSONL을 생성하는 것을 확인하였다.

또한 pandas 결합 과정에서 variant metadata가

    intensity = 0.7000000000000001
    changed = 1.0
    n_changed = 1.0

과 같이 저장될 수 있는 문제를 확인하였다.

이에 JSONL 저장 시 다음 타입을 보존하도록 수정하였다.

- `intensity` → float
- `changed` → boolean
- `n_changed` → integer

수정 후 두 입력 방식 모두

    intensity = 0.7
    changed = true
    n_changed = 1

형태로 동일하게 저장됨을 확인하였다.

관련 commit:

    5f26042 fix: preserve augmented metadata types

### 난독화 평가 후처리 검증

`analyze_obfuscated_eval.py`에 synthetic prediction을 입력하여
다음 계산을 직접 검산하였다.

- all rows metrics
- changed-only metrics
- application rate
- technique별 metrics
- technique × intensity별 metrics
- TP / TN / FP / FN
- Recall / F1 / FPR / FNR

계산 결과가 기대값과 일치함을 확인하였다.

난독화 성능의 주 결과는 계속해서

    changed=true

행을 기준으로 사용한다.

### Main Step 1 결과표 검증

`make_step1_table.py`에 대해
4개 실험 조건의 synthetic 결과를 생성하여 검증하였다.

대상:

- KoELECTRA Original
- KoELECTRA Augmented
- mDeBERTa Original
- mDeBERTa Augmented

확인 항목:

- Clean metrics
- Obfuscated changed-only metrics
- application rate
- F1 difference
- Recall difference

모든 계산이 기대값과 일치하였다.

단, Clean과 Obfuscated changed-only는
완전히 동일한 표본의 paired 비교가 아니므로
논문에서는 단순 인과적 성능 감소량으로 표현하지 않는다.

### KoreanGuardrail summary 검증

`make_step1_kg_summary.py`도
synthetic KG 결과를 이용하여 검증하였다.

확인 항목:

- KG Clean
- KG Obfuscated changed-only
- application rate
- F1 difference
- Recall difference

출력 결과가 기대값과 일치함을 확인하였다.

### GPU model smoke test

공용 GPU 서버의 NVIDIA Tesla P100-PCIE-16GB에서
실제 모델 학습 step이 가능한지 확인하였다.

KoELECTRA:

    monologg/koelectra-base-v3-discriminator

확인:

- tokenizer load
- model load
- CUDA 이동
- FP16 forward
- loss 계산
- backward
- optimizer step

결과:

    KoELECTRA SMOKE TEST PASSED

mDeBERTa:

    microsoft/mdeberta-v3-base

slow tokenizer를 사용하여 동일하게 검증하였다.

확인:

- tokenizer load
- model load
- CUDA 이동
- FP16 forward
- loss 계산
- backward
- optimizer step

결과:

    mDeBERTa SMOKE TEST PASSED

두 모델 모두 본학습 실행이 가능한 상태임을 확인하였다.

### 실행 환경 재현성 정리

현재 본실험 기준 서버 환경:

- Python 3.10.12
- PyTorch 2.4.1+cu121
- Transformers 4.51.3
- scikit-learn 1.7.2
- Pandas 2.3.3
- NumPy 2.2.6
- sentencepiece 0.2.2
- protobuf 7.36.2
- NVIDIA Tesla P100-PCIE-16GB

환경 파일을 다음과 같이 분리하였다.

- `requirements-common.txt`
- `requirements-local.txt`
- `requirements-server.txt`

`requirements-server.txt`에 대해
`pip install --dry-run` 및 `pip check`를 수행하였고
현재 공용 GPU 환경과 충돌이 없음을 확인하였다.

관련 commit:

    84438ea docs: document reproducible Step 1 environments

### 현재 상태

본실험 전 코드 사전 점검은 완료하였다.

현재 남은 주요 작업은 실제 최종 데이터를 수신한 뒤

1. 전체 데이터 validator 실행
2. 데이터 규모 및 label 분포 기록
3. T9b 증강 조건 확인
4. EPOCHS / BATCH_SIZE 확정
5. KoELECTRA / mDeBERTa Original 학습
6. KoELECTRA / mDeBERTa Augmented 학습
7. Clean / Obfuscated 평가
8. KoreanGuardrail 보조 평가
9. Main / KG 결과 생성
10. 실제 결과 검산 및 논문 반영

순서로 진행하는 것이다.

실제 연구 성능에 대한 결론은
최종 데이터 기반 본실험 결과가 나온 뒤 작성한다.
