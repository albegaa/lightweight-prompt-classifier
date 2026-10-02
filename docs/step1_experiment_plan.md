# Step 1 Lightweight Classifier 실험 계획

## 1. 목적

본 실험은 한국어 프롬프트 공격에 대해
경량 binary classifier의 탐지 성능을 평가하고,
한국어 난독화 데이터를 학습에 추가했을 때
난독화 robustness가 개선되는지 확인하는 것을 목적으로 한다.

Step 1은 앞선 screening 결과와 연결된다.

    T4 Reference Detector
            ↓
    T6 Detector Evasion
            ↓
    T7 Target Delivery
            ↓
    T9a Effective Attack
            ↓
    T8 Readability
            ↓
    T9b Technique Selection
            ↓
    Step 1 Lightweight Classifier

Step 1에서는 T9b 결과를 증강 학습에 활용하되,
난독화 평가에서는 17종 기법 전체에 대한 성능을 확인한다.

---

## 2. 핵심 연구 질문

다음 네 질문을 중심으로 평가한다.

1. Clean 데이터만으로 학습한 경량 classifier는
   난독화 공격에서 어느 정도 성능 저하를 보이는가?

2. 난독화 데이터를 학습에 추가하면
   Obfuscated test에서 Attack Recall과 F1이 개선되는가?

3. 난독화 증강 학습이
   Clean test 성능 또는 Benign FPR에 부정적인 영향을 주는가?

4. 이러한 변화가
   KoELECTRA와 mDeBERTa에서 공통적으로 나타나는가?

실제 결과가 나오기 전에는
augmentation의 효과를 전제로 결론을 내리지 않는다.

---

## 3. Binary Classification Task

Label:

- `0` = Benign
- `1` = Attack

classifier의 class 1 softmax 출력은

    attack-class softmax score

로 표현한다.

이 값은 calibration된 확률이 아니므로
`P(Attack)`으로 해석하지 않는다.

---

## 4. 비교 모델

### 4.1 KoELECTRA

사용 모델:

    monologg/koelectra-base-v3-discriminator

한국어 전용 encoder 모델이며
Step 1의 주 경량 classifier로 사용한다.

Binary classification head를 추가하여
Benign / Attack을 분류한다.

### 4.2 mDeBERTa

사용 모델:

    microsoft/mdeberta-v3-base

KoELECTRA와 비교하기 위한 다국어 baseline이다.

동일한 binary classification task로 fine-tuning한다.

mDeBERTa는 tokenizer 호환성을 위해
slow tokenizer를 사용한다.

---

## 5. 학습 조건

각 모델에서 두 가지 학습 조건을 비교한다.

### 5.1 Original-only

원문 학습 데이터만 사용한다.

    Original Train
          +
    Original Validation

### 5.2 Augmented

원문 학습 데이터와
T9b에서 선정된 난독화 variant를 이용한다.

개념적 구성:

    Original Train
          +
    Selected Obfuscated Variants
          +
    Original Validation

Original-only와 Augmented는
동일한 validation set을 사용한다.

이를 통해 model selection 조건을 동일하게 유지한다.

단, 전달되는 증강 학습 파일이

- 원문과 variant가 합쳐진 완성본인지
- variant만 포함한 파일인지

는 최종 데이터 전달 및 데이터 카드 확인 후 확정한다.

코드에서는 이 구성을 명시적으로 확인한 뒤 학습한다.

---

## 6. 최종 실험 행렬

총 4개의 fine-tuned classifier를 비교한다.

| Model | Training |
| --- | --- |
| KoELECTRA | Original-only |
| KoELECTRA | Augmented |
| mDeBERTa | Original-only |
| mDeBERTa | Augmented |

각 모델은 동일한 평가 데이터에서 비교한다.

메인 평가:

- Clean test
- Obfuscated test

보조 평가:

- KoreanGuardrail clean test
- KoreanGuardrail obfuscated test

---

## 7. 원본 데이터 계약

원본 파일:

- `train.jsonl`
- `valid.jsonl`
- `test.jsonl`
- `kg_test.jsonl`

기본 필드:

| Field | 의미 |
| --- | --- |
| `id` | 각 행의 고유 ID |
| `text` | 한국어 입력 문장 |
| `label` | 0 = Benign, 1 = Attack |
| `source` | 출처 데이터셋 |

목표 최종 데이터 규모:

- Attack 약 3,000건
- Benign 약 3,000건
- Attack : Benign = 1 : 1

원본 데이터 후보는 다음과 같다.

Attack:

- `Lakera/gandalf_ignore_instructions`
- `xTRam1/safe-guard-prompt-injection`의 attack 행

Benign:

- `xTRam1/safe-guard-prompt-injection`의 benign 행
- `KoAlpaca-RealQA`
- `Anthropic/hh-rlhf` helpful-base
- `awesome-chatgpt-prompts`

초기 후보였던 `deepset/prompt-injections`는
최종 원본 구성에서 제외한다.

제외 이유:

- role assignment 또는 번역 요청까지 공격으로 분류하는 등
  다른 데이터와 label 기준이 충돌함
- 전체 규모에서 차지하는 비중이 작음

`xTRam1`의 benign 행도 정상 데이터에 포함한다.

이는 Attack과 Benign의 출처가 완전히 분리될 경우
모델이 공격 특성 대신 출처별 문체 차이를
shortcut으로 학습할 가능성을 줄이기 위함이다.

원본 데이터 정리 시 다음 규칙을 적용한다.

- 원본 데이터셋이 제공하는 train / test split은 그대로 사용하지 않음
- 전체 데이터를 합친 뒤 중복 및 label conflict를 제거
- 영어 원문 기준 300자 이하의 단일 짧은 프롬프트를 사용
- 이후 우리 기준으로 train / valid / test를 다시 분할
- 증강 전에 원문 단위로 split

300자 상한은 번역 전 영어 원문을 선별하기 위한 기준이다.

번역된 최종 한국어 `text`에
다시 300자 상한을 적용한다는 의미는 아니다.

Step 1 classifier의 입력 길이는

    max_length = 128

로 유지한다.

300자 상한을 선택한 이유는
번역과 난독화 이후 token 수 증가를 고려할 때
문장 뒷부분이 128 token 이후 잘릴 가능성을 줄이기 위함이다.

KoELECTRA와 mDeBERTa 모두 현재 tokenizer 설정에서

    truncation_side = right

임을 확인하였다.

따라서 128 token을 초과하면
입력의 뒤쪽이 잘린다.

최종 데이터 수신 후에는
문자 수만 확인하는 것이 아니라
실제 KoELECTRA / mDeBERTa tokenizer를 이용하여
128 token 초과 비율을 별도로 측정한다.

장문의 DAN류 jailbreak 및
긴 문서 내부에 삽입된 indirect injection은
이번 Step 1의 직접적인 연구 범위에서 제외하며,
연구의 한계 및 향후 과제로 기록한다.

학습 / 검증 / 평가 분할:

    8 : 1 : 1

분할 시 다음 원칙을 사용한다.

- split별 Attack : Benign 비율을 동일하게 유지
- 고정 random seed 사용
- 동일 원문이 train / valid / test에 동시에 들어가지 않음
- augmentation은 train split 이후에만 수행

Benign 데이터는 단순 무작위 추출하지 않고
Attack 데이터의 길이 분포를 기준으로
길이 구간별로 대응되도록 샘플링한다.

이를 통해 입력 길이 자체가
Benign / Attack을 구분하는 shortcut으로 사용되는 가능성을 줄인다.

번역이 필요한 원본 데이터의 최종 번역 범위,
번역 도구 및 출처별 최종 비율은
최종 데이터 카드와 실제 생성 결과를 기준으로 기록한다.

---

## 8. 변형 데이터 계약

난독화 평가 및 증강 데이터에는
기본 필드에 다음 metadata가 추가된다.

| Field | 의미 |
| --- | --- |
| `seed_id` | variant가 파생된 원문의 `id` |
| `technique` | 난독화 기법 |
| `intensity` | 난독화 강도 |
| `changed` | 변형 결과가 원문과 실제로 다른지 여부 |
| `n_changed` | 실제 변경된 위치 수 |

각 variant는 새로운 `id`를 갖는다.

예:

    Original
    id = xtram1_00123

    Variant
    id = <unique variant id>
    seed_id = xtram1_00123

원문과 variant의 연결은
`id ↔ seed_id` 관계로 확인한다.

---

## 9. changed 처리 원칙

### 난독화 평가 데이터

`changed=false` 행도 파일에는 유지한다.

이는 다음 목적으로 사용한다.

- 기법 적용률 확인
- 실제 변형 여부 검산
- 전체 raw 평가 결과 보존

난독화 robustness의 주 성능은

    changed=true

행을 기준으로 계산한다.

따라서 `changed=false` 행은
application rate 계산 및 raw artifact에는 포함하지만,
메인 Obfuscated Recall / F1 / FPR 계산에서는 제외한다.

### 증강 학습 데이터

`changed=false` variant는
원문과 동일하므로 증강 데이터에서 제외한다.

validator에서도 증강 데이터에
`changed=false`가 포함되어 있는지 확인한다.

---

## 10. T9b와 증강 학습

T9b 사전 pass 조건:

- Evasion Rate >= 30%
- Delivery Retention >= 70%
- Readability pass

최종 결과:

- Pass 기법: 0종
- Ambiguous 기법: 2종
- Fail 기법: 15종

사전 ambiguous 보충 규칙에 따라
다음 두 조건이 Step 1 증강 후보로 선정되었다.

| Technique | Intensity | Effective Attack | 판정 |
| --- | ---: | ---: | --- |
| `yamin_swap` | 0.7 | 7/44 (15.9%) | Ambiguous |
| `symbol_insert` | 0.3 | 6/44 (13.6%) | Ambiguous |

두 조건은 pass 기법이 아니라
ambiguous 경계 사례이다.

따라서 Step 1 결과에서도
“유효성이 입증된 난독화 기법”으로 표현하지 않는다.

---

## 11. 난독화 평가

난독화 평가셋은
Clean test의 held-out 원문에 17종 변형을 적용한 결과를 사용한다.

목적은 증강에 사용한 두 기법만 평가하는 것이 아니라,
classifier가 다양한 한국어 난독화에 대해
어느 정도 robustness를 보이는지 확인하는 것이다.

주 분석:

- 전체 Obfuscated 성능
- Original-only vs Augmented 비교

데이터와 지면이 허용하면 추가로 확인:

- technique별 Recall
- intensity별 Recall
- technique별 FNR
- changed=true 기준 결과

기법별 결과는 표본 수를 함께 확인하여 해석한다.

---

## 12. KoreanGuardrail 보조 평가

`kg_test.jsonl`은
번역이 아닌 방식으로 만든 한국어 보조 평가셋이다.

구성:

- KoreanGuardrail 시드 249건
- screening에 사용한 70건 제외
- 최종 179건
- A1 / A2 → label 1
- Benign → label 0

목적:

학습 및 메인 평가 데이터에 번역 데이터가 포함되는 조건에서
classifier가 공격 특성보다 번역 문체에 과도하게 의존하는지
보조적으로 확인한다.

주의:

KoreanGuardrail 역시
Claude 생성 후 검수된 AI 생성 데이터이다.

따라서 논문에서는

    번역이 아닌 방식으로 만든 한국어 평가셋

으로 표현한다.

기법별 표본 수가 작기 때문에
기본 보고는 다음 두 조건의 전체 평균을 중심으로 한다.

- KG Clean
- KG Obfuscated

KSC 지면이 부족하면
해당 결과는 졸업논문 보조 실험으로 사용할 수 있다.

---

## 13. Leakage 원칙

가장 중요한 기준은
동일 원문 group이 학습과 held-out 평가에 동시에 포함되지 않는 것이다.

여기서 `source` 컬럼은
원본 데이터셋 출처를 의미하며,
leakage 판단을 위한 group ID와는 구분한다.

원본 행의 group ID:

    id

variant 행의 group ID:

    seed_id

허용:

    Original train
        ↔
    Augmented train variants

동일 학습 원문에서 생성된 variant이므로 허용한다.

허용:

    Clean test
        ↔
    Obfuscated test variants

동일 held-out 평가 원문의
원문 / variant 관계이므로 허용한다.

허용:

    KG clean
        ↔
    KG obfuscated variants

동일 보조 평가 원문의 관계이므로 허용한다.

금지:

    Train group
        ↔
    Validation group

    Train group
        ↔
    Test group

    Train group
        ↔
    KG evaluation group

또한 원본 데이터를 새로 분할하기 전에
출처 내부 및 출처 간 exact duplicate를 제거한다.

split 및 variant 관계는
`id`와 `seed_id`를 이용해 검증한다.

---

## 14. 공통 학습 설정

현재 구현된 기본값:

- learning rate = 2e-5
- weight decay = 0.01
- max length = 128
- seed = 42
- FP16
- best model selection = validation F1

본실험 전 최종 결정:

- epochs
- batch size

KoELECTRA와 mDeBERTa는
비교 가능성을 위해 가능한 한 동일한 학습 조건을 사용한다.

GPU OOM 등 모델별 기술적 제약이 발생하면
임의로 조건을 변경하지 않고 변경 이유를 기록한다.

---

## 15. 평가 지표

저장 지표:

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

주요 비교 지표:

- Clean Recall
- Clean F1
- Clean FPR
- Obfuscated Recall
- Obfuscated F1
- Obfuscated FPR

Obfuscated 주 성능은
`changed=true` variant 기준으로 계산한다.

추가 변화량:

    F1 Drop
    = Clean F1 - Obfuscated F1

    Recall Drop
    = Clean Recall - Obfuscated Recall

Drop은 percentage point 단위로 보고한다.

단, Clean 평가셋과
`changed=true` Obfuscated variant 집합은
완전히 동일한 표본의 paired 전후 비교가 아니다.

따라서 Drop은

    Clean 대비 changed-only 난독화 평가셋에서
    관찰된 성능 차이

로 해석하며,
동일 샘플에 대한 직접적인 인과적 감소량으로 표현하지 않는다.

---

## 16. 결과 해석 원칙

결과에서는 단순 최고 점수보다
Original-only 대비 Augmented의 변화를 중심으로 본다.

확인 항목:

1. Original-only Clean 성능
2. Original-only Obfuscated 성능 저하
3. Augmented 학습 후 Obfuscated Recall / F1 변화
4. Augmented 학습 후 Clean 성능 변화
5. Benign FPR 변화
6. KoELECTRA / mDeBERTa 경향 비교
7. 필요 시 KG Clean / Obfuscated 결과

augmentation의 효과는
실제 본실험 결과를 확인한 후 판단한다.

---

## 17. Kanana Safeguard와의 관계

Kanana Safeguard는
Step 1에서 fine-tuning하는 모델이 아니다.

참조 탐지기:

    kakaocorp/kanana-safeguard-prompt-2.1b

T4/T6에서 사용한 외부 reference detector이며,
KoELECTRA / mDeBERTa와 동일한 학습 조건의 비교 모델로 해석하지 않는다.

필요한 경우 동일 최종 test set에서
reference baseline으로 별도 평가할 수 있다.

---

## 18. Selective Router와의 관계

Step 1의 직접적인 실험 대상은
Binary Classifier의 학습 및 robustness이다.

본 저장소에는 이후 시스템 연결을 고려하여
Selective Router prototype도 보존한다.

Step 1 본실험이 완료되고
실제 validation attack score가 확보되면
필요한 경우 `T_low`, `T_high`를 다시 분석한다.

최종적으로 검증된 B 파트 구성요소는
별도의 팀 통합 저장소에서 JailGuard와 연결한다.

---

## 19. 현재 구현 상태

완료:

- KoELECTRA 학습 pipeline
- mDeBERTa 학습 pipeline
- CSV / JSONL loader
- 공용 evaluation pipeline
- KoELECTRA GPU smoke test
- mDeBERTa GPU smoke test
- data validation script
- `id ↔ seed_id` group validation
- `changed` validation
- Original-only 실행 script
- Augmented 실행 script
- Augmented training input 표준화
- Clean / Obfuscated 평가 script
- `kg_test` 평가 지원
- 17종 난독화 평가 지원
- changed-only 난독화 분석
- technique / intensity별 분석
- Table 2 generator
- KoreanGuardrail supplementary summary
- Selective Router prototype
- Threshold Sweep prototype
- GPU 서버 실행환경 requirements 정리
- Step 1 Runbook 정리

본실험 대기:

- 최종 데이터 수신
- 실제 데이터 validator 통과
- 실제 데이터 규모 / label / source / 길이 분포 확인
- 최종 augmented input 확인
- epochs 확정
- batch size 확정
- KoELECTRA Original / Augmented
- mDeBERTa Original / Augmented
- 최종 Clean / Obfuscated 평가
- KG 보조 평가
- 최종 결과표 생성
- 실제 결과 검산 및 논문 반영

---

## 20. 저장소 역할

본 저장소는
B 파트의 Step 1 경량 분류기 개발 및 실험 저장소이다.

여기에는 다음을 보존한다.

- classifier 개발 과정
- Step 1 학습 및 평가
- 실험 설계
- 실행 절차
- 초기 Router prototype

B 파트의 screening 과정과 분석 기록은
별도의 `B-screening` 저장소에서 관리한다.

Step 1 결과가 안정된 이후에는
A/B/C의 검증된 최종 구성요소를 별도 팀 통합 저장소로 이관하여
JailGuard까지 포함한 전체 pipeline을 구성한다.
