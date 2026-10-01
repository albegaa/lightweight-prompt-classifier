# Step 1 본실험 실행 Runbook

## 0. 목적

이 문서는 Step 1 본실험에서 실제 데이터 수신 후
KoELECTRA와 mDeBERTa를 동일한 조건으로 학습하고,
Clean / Obfuscated 평가 결과를 생성하기 위한 실행 절차를 정리한다.

비교 조건:

- KoELECTRA Original-only
- KoELECTRA Augmented
- mDeBERTa Original-only
- mDeBERTa Augmented

최종적으로 동일한 평가 세트에서 네 조건을 비교한다.

주의:

- Demo 데이터 결과는 연구 결과로 사용하지 않는다.
- 동일 원본 prompt의 variant가 train / valid / test에 나뉘면 안 된다.
- 두 모델의 epoch, batch size, learning rate 등 주요 학습 조건은 동일하게 사용한다.
- mDeBERTa는 SentencePiece byte-fallback 보존을 위해 slow tokenizer를 사용한다.

---

# 1. 현재 구현 상태

완료된 코드:

- src/classifier/train.py
- src/classifier/evaluate.py
- scripts/validate_step1_data.py
- scripts/run_original_train.sh
- scripts/run_augmented_train.sh
- scripts/run_step1_eval.sh
- scripts/make_step1_table.py

Smoke Test 완료:

- KoELECTRA GPU 학습
- KoELECTRA 독립 평가
- mDeBERTa GPU 학습
- mDeBERTa slow tokenizer 학습
- mDeBERTa 독립 평가
- P100 FP16 동작
- best model 저장 및 재로드
- 표 2 결과 집계

---

# 2. 본실험 전 확정할 값

본학습 시작 전에 팀에서 반드시 다음을 확정한다.

- EPOCHS
- BATCH_SIZE
- 원문 데이터 파일명
- 증강 데이터 파일명
- group ID 필드명
- T9b 최종 선정 난독화 기법

현재 공통 학습 설정:

- learning rate = 2e-5
- weight decay = 0.01
- max length = 128
- seed = 42
- FP16 사용
- best model 기준 = validation F1

EPOCHS와 BATCH_SIZE는 최종 데이터 규모 및 GPU 상황 확인 후 확정한다.

예시:

EPOCHS=3
BATCH_SIZE=16

위 값은 예시이며 최종값이 아니다.

---

# 3. 예상 데이터 구조

데이터는 다음 구조로 배치한다.

data/step1/

- original/
  - train.csv
  - valid.csv
  - test.csv

- augmented/
  - train.csv

- evaluation/
  - obfuscated_test.csv

각 데이터는 최소 다음 필드를 포함한다.

- text
- label

label:

- 0 = Benign
- 1 = Attack

가능하면 다음 메타데이터도 유지한다.

- seed_id 또는 base_prompt_id
- category
- technique
- intensity
- changed

---

# 4. 저장소 최신화

본실험 전에 저장소 상태를 확인한다.

실행:

cd /root/project/lightweight-prompt-classifier
git status
git pull origin main

정상 상태:

- main == origin/main
- working tree clean

---

# 5. GPU 확인

학습 및 평가 실행 직전에 반드시 GPU 상태를 다시 확인한다.

실행:

nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

공용 GPU 서버이므로 과거에 비어 있던 GPU 번호를 그대로 사용하지 않는다.

사용 가능한 GPU 번호를 확인한 후 이후 명령의 GPU 인자로 전달한다.

---

# 6. 데이터 파일 확인

실제 데이터 전달 후 다음을 확인한다.

실행:

find data/step1 -maxdepth 3 -type f -print | sort

예상 파일:

data/step1/original/train.csv
data/step1/original/valid.csv
data/step1/original/test.csv
data/step1/augmented/train.csv
data/step1/evaluation/obfuscated_test.csv

---

# 7. 데이터 검증

학습 전에 반드시 데이터 검증 스크립트를 실행한다.

실행:

/root/project/.venv/bin/python \
  scripts/validate_step1_data.py \
  --train data/step1/original/train.csv \
  --valid data/step1/original/valid.csv \
  --test data/step1/original/test.csv \
  --augmented-train data/step1/augmented/train.csv \
  --obfuscated-test data/step1/evaluation/obfuscated_test.csv

검사 항목:

- text / label 필드 존재
- null 여부
- 빈 문장 여부
- label이 0/1인지
- 동일 split 내부 중복
- 동일 문장에 상충 label 존재 여부
- split 간 exact text leakage
- seed_id / base_prompt_id 기준 group leakage

최종적으로 다음이 출력되어야 한다.

ALL CHECKS PASSED

Group column이 자동 탐지되지 않으면
실제 데이터의 group ID 필드를 확인한 뒤 명시적으로 지정한다.

예:

--group-column seed_id

또는

--group-column base_prompt_id

Group leakage 검사를 수행하지 않은 상태로 본학습을 시작하지 않는다.

---

# 8. 데이터 규모 확인

검증 후 각 데이터의 행 수와 label 분포를 확인한다.

실행 예:

/root/project/.venv/bin/python - <<'PY'
import pandas as pd

files = {
    "train": "data/step1/original/train.csv",
    "valid": "data/step1/original/valid.csv",
    "test": "data/step1/original/test.csv",
    "augmented": "data/step1/augmented/train.csv",
    "obfuscated_test": "data/step1/evaluation/obfuscated_test.csv",
}

for name, path in files.items():
    df = pd.read_csv(path)

    print()
    print("=====", name, "=====")
    print("rows:", len(df))

    if "label" in df.columns:
        print(
            "labels:",
            df["label"]
            .value_counts()
            .sort_index()
            .to_dict()
        )
PY

이 결과를 실험 기록에 남긴다.

---

# 9. 학습 설정 확정

KoELECTRA와 mDeBERTa에 동일한 설정을 적용한다.

예:

EPOCHS=3
BATCH_SIZE=16

최종 확정 후 팀원 모두 같은 값을 사용한다.

모델별 오류 해결을 위한 tokenizer 구현 차이 등은 허용하지만
epoch, batch size, learning rate 등의 비교 조건은 임의로 다르게 변경하지 않는다.

---

# 10. KoELECTRA Original-only 학습

GPU 번호, epoch, batch size를 인자로 전달한다.

형식:

bash scripts/run_original_train.sh \
  koelectra \
  GPU \
  EPOCHS \
  BATCH_SIZE

예:

bash scripts/run_original_train.sh \
  koelectra \
  7 \
  3 \
  16

저장 위치:

results/step1/koelectra/original/

주요 결과:

- best_model/
- metrics.json
- training_history.csv
- validation_results.csv

학습 종료 시 다음 문구를 확인한다.

ORIGINAL TRAINING SUCCESS

---

# 11. mDeBERTa Original-only 학습

동일한 epoch와 batch size를 사용한다.

형식:

bash scripts/run_original_train.sh \
  mdeberta \
  GPU \
  EPOCHS \
  BATCH_SIZE

예:

bash scripts/run_original_train.sh \
  mdeberta \
  7 \
  3 \
  16

mDeBERTa는 내부적으로 slow tokenizer 옵션을 사용한다.

저장 위치:

results/step1/mdeberta/original/

---

# 12. KoELECTRA Augmented 학습

Original-only와 동일한 validation set을 사용한다.

형식:

bash scripts/run_augmented_train.sh \
  koelectra \
  GPU \
  EPOCHS \
  BATCH_SIZE

예:

bash scripts/run_augmented_train.sh \
  koelectra \
  7 \
  3 \
  16

저장 위치:

results/step1/koelectra/augmented/

---

# 13. mDeBERTa Augmented 학습

형식:

bash scripts/run_augmented_train.sh \
  mdeberta \
  GPU \
  EPOCHS \
  BATCH_SIZE

예:

bash scripts/run_augmented_train.sh \
  mdeberta \
  7 \
  3 \
  16

저장 위치:

results/step1/mdeberta/augmented/

---

# 14. 학습 결과 기본 확인

네 모델 학습 후 다음 디렉터리가 존재하는지 확인한다.

실행:

find results/step1 -maxdepth 4 -type f \
  \( -name 'metrics.json' \
  -o -name 'training_history.csv' \
  -o -name 'validation_results.csv' \) \
  | sort

각 조건에서 best_model도 존재해야 한다.

확인:

find results/step1 -type d -name best_model | sort

예상:

results/step1/koelectra/original/best_model
results/step1/koelectra/augmented/best_model
results/step1/mdeberta/original/best_model
results/step1/mdeberta/augmented/best_model

---

# 15. Clean / Obfuscated 평가

각 학습 모델을 동일한 두 평가 세트에서 평가한다.

평가 세트:

- Clean: data/step1/original/test.csv
- Obfuscated: data/step1/evaluation/obfuscated_test.csv

평가 결과는 학습 조건별 eval 디렉터리에 저장된다.

---

# 16. KoELECTRA Original 평가

형식:

bash scripts/run_step1_eval.sh \
  koelectra \
  original \
  GPU \
  BATCH_SIZE

예:

bash scripts/run_step1_eval.sh \
  koelectra \
  original \
  7 \
  16

생성:

results/step1/koelectra/original/eval/clean/metrics.json
results/step1/koelectra/original/eval/obfuscated/metrics.json

---

# 17. KoELECTRA Augmented 평가

실행 예:

bash scripts/run_step1_eval.sh \
  koelectra \
  augmented \
  7 \
  16

---

# 18. mDeBERTa Original 평가

실행 예:

bash scripts/run_step1_eval.sh \
  mdeberta \
  original \
  7 \
  16

---

# 19. mDeBERTa Augmented 평가

실행 예:

bash scripts/run_step1_eval.sh \
  mdeberta \
  augmented \
  7 \
  16

---

# 20. 평가 결과 확인

총 8개의 metrics.json이 생성되어야 한다.

4개 학습 조건 × 2개 평가 세트 = 8개

실행:

find results/step1 \
  -path '*/eval/*/metrics.json' \
  -type f \
  | sort

개수 확인:

find results/step1 \
  -path '*/eval/*/metrics.json' \
  -type f \
  | wc -l

예상:

8

---

# 21. 표 2 자동 생성

모든 평가가 끝난 뒤 실행한다.

실행:

/root/project/.venv/bin/python \
  scripts/make_step1_table.py

출력:

results/step1/table2_summary.csv

포함 지표:

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

F1 Drop과 Recall Drop은 percentage point 단위이다.

---

# 22. 표 2 확인

실행:

cat results/step1/table2_summary.csv

또는:

/root/project/.venv/bin/python - <<'PY'
import pandas as pd

df = pd.read_csv(
    "results/step1/table2_summary.csv"
)

print(
    df.to_string(
        index=False
    )
)
PY

비교 대상:

- KoELECTRA Original
- KoELECTRA Augmented
- mDeBERTa Original
- mDeBERTa Augmented

---

# 23. 결과 해석 시 확인할 항목

논문 4.3에서는 단순히 최고 점수만 보는 것이 아니라
Original-only와 Augmented의 변화를 중심으로 해석한다.

주요 비교:

1. Clean 성능 변화
2. Obfuscated 성능 변화
3. Attack Recall 변화
4. Benign FPR 변화
5. Clean 대비 Obfuscated 성능 감소폭 변화

예시 해석 구조:

- 원문 학습 모델의 Clean 성능
- 난독화 입력에서의 성능 저하
- 난독화 증강 후 Obfuscated 성능 변화
- 증강이 Clean 성능에 미친 영향
- KoELECTRA와 mDeBERTa에서 같은 경향이 나타나는지 여부

실제 결과가 나온 뒤 수치에 근거해서 작성한다.

---

# 24. Kanana Safeguard 관련

Kanana Safeguard는 Step 1 경량 분류기와 별도의 참조 탐지기이다.

현재 make_step1_table.py는 다음 네 조건을 자동 집계한다.

- KoELECTRA Original
- KoELECTRA Augmented
- mDeBERTa Original
- mDeBERTa Augmented

Kanana 결과는 별도 참조 평가 결과에서 가져와
최종 논문 표 구성 단계에서 추가한다.

Kanana와 경량 분류기의 학습 조건을 동일한 모델 학습 실험으로 해석하지 않는다.

---

# 25. Git / 결과 파일 주의

Fine-tuned model 파일은 GitHub에 올리지 않는다.

현재 best_model 및 safetensors 계열 파일은 gitignore 대상이다.

실제 데이터에도 원문 prompt가 포함될 수 있으므로
data/step1 파일을 GitHub에 올리기 전에 팀 정책을 확인한다.

predictions.csv에도 원문 text가 포함되므로
공개 저장소에 commit하기 전에 반드시 내용을 확인한다.

metrics.json, summary CSV 등 작은 집계 결과도
최종 공개 범위를 정한 뒤 commit한다.

---

# 26. 본실험 중 기록할 정보

각 학습 실행마다 다음 정보를 기록한다.

- 실행 날짜
- Git commit
- 모델명
- 데이터 버전
- train / valid / test 크기
- label 분포
- 사용 난독화 기법
- GPU
- epoch
- batch size
- learning rate
- max length
- seed
- best epoch
- validation F1
- Clean 평가 결과
- Obfuscated 평가 결과

Git commit 확인:

git rev-parse HEAD

GPU 확인:

nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

---

# 27. 오류 발생 시 원칙

공통 학습 조건은 임의로 변경하지 않는다.

특정 모델에서만 오류가 발생하면:

1. 오류 메시지 저장
2. 모델별 구현 차이인지 확인
3. 최소한의 예외 처리만 적용
4. 다른 모델의 실험 조건에는 영향을 주지 않음
5. 수정 사항을 Git commit으로 남김

mDeBERTa tokenizer와 같은 모델 구조상 차이는
실험 설정 차이가 아니라 구현 호환성 차이로 기록한다.

---

# 28. 최종 완료 조건

다음 조건을 모두 만족하면 Step 1 본실험 완료로 본다.

- 데이터 누수 검사 통과
- KoELECTRA Original 학습 완료
- KoELECTRA Augmented 학습 완료
- mDeBERTa Original 학습 완료
- mDeBERTa Augmented 학습 완료
- 4개 모델 Clean 평가 완료
- 4개 모델 Obfuscated 평가 완료
- metrics.json 8개 확인
- table2_summary.csv 생성
- 표 2 수치 검산
- 논문 4.1 Step 1 설정 작성
- 논문 4.3 표 2 + 결과 해석 작성

---

# 29. 전체 실행 순서 요약

1. Git 최신화
2. GPU 확인
3. 데이터 배치
4. validate_step1_data.py 실행
5. 데이터 규모 / label 분포 확인
6. epoch / batch size 최종 확정
7. KoELECTRA Original 학습
8. mDeBERTa Original 학습
9. KoELECTRA Augmented 학습
10. mDeBERTa Augmented 학습
11. KoELECTRA Original 평가
12. KoELECTRA Augmented 평가
13. mDeBERTa Original 평가
14. mDeBERTa Augmented 평가
15. metrics.json 8개 확인
16. make_step1_table.py 실행
17. table2_summary.csv 검산
18. 논문 표 2 작성
19. 4.3 결과 해석 작성
20. 실험 설정 및 결과 기록
