# Step 1 보조 통계 (`scripts/step1_stats.py`)

기존 평가 출력(`predictions.csv`)을 읽기만 하고, 기존 출력에 없는 **신뢰구간과 조건 간 차이**를
`results/stats/` 아래에 추가로 만든다. 학습·평가 코드와 기존 결과는 수정하지 않는다.
추가 패키지 없이 `requirements-server.txt`의 pandas / numpy만 쓴다.

## 사용법

```bash
python scripts/step1_stats.py \
    --clean-input data/step1/test.jsonl \
    --obfuscated-input data/step1/obfuscated_test.jsonl \
    [--kg-clean-input ... --kg-obfuscated-input ...]
```

| 인자 | 기본값 | 설명 |
| --- | --- | --- |
| `--results-root` | `results/step1` | `<model>/<original\|augmented>/eval/<eval_name>/predictions.csv` 구조 |
| `--clean-input`, `--obfuscated-input` | (필수) | `evaluate.py`에 넣었던 평가 입력 파일 |
| `--kg-clean-input`, `--kg-obfuscated-input` | 없음 | 둘 다 주면 `kg_clean`, `kg_obfuscated`도 같은 방식으로 처리 |
| `--models`, `--trainings` | `koelectra,mdeberta` / `original,augmented` | |
| `--train-techniques` | `yamin_swap:0.7,symbol_insert:0.3` | 증강 학습에 쓴 기법:강도 |
| `--n-boot`, `--seed` | `2000`, `20261002` | 부트스트랩 반복 수, 시드 |
| `--output-dir` | `results/stats` | |
| `--skip-crosscheck` | 꺼짐 | 기존 `metrics.json` / `obfuscated_overall.csv`와의 대조를 건너뜀 |

## 입력 검증 (맞지 않으면 목록을 보여주고 멈춤)

- `predictions.csv`의 `id`와 평가 입력 파일의 `id`를 대조해 **빠진 행 / 중복 id / 여분 행**을 확인한다
  (입력 파일은 `evaluate.py`와 같이 `text`·`label` 결측 행을 뺀 뒤 비교).
- 같은 id의 `label`(난독화 평가는 `seed_id`, `technique`, `intensity`, `changed`도)이 입력과 다르면 멈춘다.
- 난독화 행의 `seed_id`가 clean 평가에 없거나 변형의 `label`이 원문과 다르면 멈춘다.
- 기존 `metrics.json`(전체 행)과 `analysis/obfuscated_overall.csv`(`changed_only`)의 confusion count가
  다시 계산한 값과 다르면 멈춘다.

## 지표 정의

- `evaluate.py` / `analyze_obfuscated_eval.py`와 같다: label 1 = Attack, `confusion_matrix(labels=[0,1])`,
  `zero_division=0`, 분모가 0이면 0.0. FPR = FP/(FP+TN).
- clean은 전체 행, obfuscated는 `changed=true` 행. `changed` 정규화 규칙도 기존 코드와 같다.
- 원문 행은 `seed_id = id`로 취급한다 (clean 평가 및 `seed_id`가 비어 있는 행).
- **Recall, FPR (구간 방식이 평가 종류에 따라 다름):**
  - `clean`, `kg_clean`(원문 1문장 = 1행): **Wilson 95% 구간**(z=1.96).
  - `obfuscated`, `kg_obfuscated`(원문 1개에서 변형 여러 행): **seed_id 클러스터 부트스트랩**이 기본 구간이다.
    Recall은 공격 행 중 예측 1의 비율, FPR은 정상 행 중 예측 1의 비율이며, 해당 label의 `seed_id`를
    복원추출해(반복 2000, 시드 고정) 백분위 95% 구간을 구한다. 같은 원문에서 나온 변형은 서로 독립이 아니므로
    (원문이 어려우면 변형 여러 개가 함께 틀림) 행을 독립으로 보는 Wilson을 쓰면 구간이 실제보다 좁아진다.
    그래서 변형 여러 개가 한 원문을 이루는 평가에서는 원문(seed)을 표본 단위로 삼는다.
    Wilson 값은 비교용으로 `*_wilson_lo/hi` 열에만 남기고, 논문용 markdown 표에는 기본 구간만 표시한다.
  - 기법 분해·source별(난독화)·정상 문장 난독화 오탐률도 같은 규칙(난독화는 클러스터 부트스트랩)이다.
    clean 쪽 값은 Wilson이다. `ci_method` 열에 어떤 방식인지 기록한다.
- **F1, Precision:** 모든 평가에서 `seed_id` 단위 클러스터 부트스트랩(반복 2000, 시드 고정, 백분위 95% 구간).
  clean은 클러스터가 1행이라 일반 부트스트랩과 같다.
- **Original vs Augmented:** 같은 모델·같은 `eval_name`의 두 `predictions.csv`를 `id`로 결합하고,
  같은 `seed_id` 클러스터 재표본으로 Δ(Augmented − Original)의 Recall·FPR·F1 구간을 구한다.
- **원문 vs 변형:** clean의 `id`와 obfuscated의 `seed_id`로 짝을 지어(원문 1 : 변형 다),
  원문에서 맞힌(예측 1) 공격 중 변형 후에도 맞힌 비율을 구한다. 구간은 seed 클러스터 부트스트랩.
- **기법 분해:** `trained_technique_same_intensity`(학습 기법·같은 강도),
  `trained_technique_other_intensity`(학습 기법·다른 강도), `other_techniques`(나머지).
- **정상 문장 난독화 오탐률:** `label=0` & `changed=true`의 FPR(전체와 기법별), clean FPR과 나란히.

## 출력 (`results/stats/`)

`condition_metrics.csv`, `paired_original_vs_augmented.csv`, `paired_original_vs_variant.csv`,
`technique_groups.csv`, `source_metrics.csv`, `benign_obfuscation_fpr.csv`,
`step1_stats_tables.md`(논문용 표: % 소수 첫째 자리, 괄호에 기본 95% 구간만 표시), `run_info.json`(시드, 입력·예측 파일 sha256 등).
csv의 `*_ci_lo/hi`가 기본 구간, `*_wilson_lo/hi`는 참고용 Wilson 구간이다.

## 테스트

```bash
python tests/test_step1_stats.py      # 또는 pytest tests/
```

가짜 데이터를 만들고 작은 BERT로 **`evaluate.py`와 `analyze_obfuscated_eval.py`를 실제로 실행**해
`predictions.csv`를 만든 뒤, 점추정이 기존 `metrics.json`·analysis csv·sklearn과 같은지, `changed` 정규화가
기존 함수와 같은 동작인지, 행이 빠지거나 중복·여분이 있으면 멈추는지 확인한다.
(`torch`/`transformers`가 없으면 `evaluate.py`를 쓰는 테스트는 건너뛴다.)
