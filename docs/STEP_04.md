# 4단계: 전체·경계 영역의 Dice 직접 계산

상태: **사용자 코드 작성·테스트 실행 대기**. 지금은 아래 함수 하나만 작성합니다.

## 작성 위치와 프로젝트에서의 역할

파일: `src/pathology_edge/learner_metrics.py`

함수: `dice_score(prediction, target, region=None)`

예측 마스크와 정답 마스크가 얼마나 겹치는지 픽셀 단위로 계산합니다.
`region`으로 같은 함수의 평가 범위를 전체 이미지 또는 경계 영역으로 제한할 수 있습니다.
핵의 개수나 NMS 후보 수를 계산하는 함수가 아닙니다. 기존 실험의 `metrics.binary_metrics`는 그대로 유지하고 독립 검산용으로 작성합니다.

## 입출력 계약

| 인수 | 의미·조건 |
|---|---|
| `prediction`, `target` | 같은 모양의 2차원 NumPy 배열 `(H,W)`. 두 축 모두 크기가1 이상. dtype은 bool 또는 정수·실수이며 값은0/1만 허용 |
| `region` | `None`이면 모든 픽셀. 지정하면 입력과 같은 모양의 bool NumPy 배열이며 True인 픽셀만 평가. 적어도 하나의 True 필요 |
| 반환 | `[0,1]` 범위의 Python `float`. 값이 높을수록 선택 영역의 foreground 겹침이 큼 |

- 확률값0.25, 값2/255, NaN/Inf, complex·string·object dtype, 모양 오류는 `ValueError`입니다. 영역 밖 값도 입력 형식 검사 대상입니다.
- `region`의 정수0/1 배열은 bool 배열과 구분해 거부합니다. 자동 threshold·round·resize는 하지 않습니다.
- 모든 입력을 보존하고, 읽기 전용 배열도 처리합니다. 픽셀 합계를 uint8에 담아 overflow시키지 않습니다.
- NumPy 배열 입력만 필수입니다. list 입력 편의 지원은 요구하지 않습니다.

## 계산 정의와 빈 경우

선택 영역 안의 예측 foreground 집합을 P, 정답 foreground 집합을 T라고 할 때:

```text
Dice = 2 × |P ∩ T| / (|P| + |T|)
```

둘 다 foreground가 없으면 **1.0**으로 정합니다. 이는 기존 프로젝트가 사용하는 합의된 규칙이며, 핵을 검출했다는 뜻은 아닙니다.
한쪽에만 foreground가 있으면 **0.0**입니다.

평가할 픽셀 자체가 없는 경우(빈 H/W 또는 `region`이 전부 False)는 **ValueError**입니다.
‘평가 영역은 있지만 모두 배경’과 ‘평가 영역 자체가 없음’을 구분합니다. 기존 배포 실험의 점수는 수정하지 않습니다.

## 확인 예시

```text
prediction = [[1, 1],
              [0, 0]]

target     = [[1, 0],
              [1, 0]]

region     = [[True,  True],
              [False, False]]
```

- `region=None`: Dice **0.5**
- 위 `region` 사용: Dice **2/3**

이 예시는 손으로 검산할 수 있는 합성 배열이며 실제 병리 영상의 실험 결과가 아닙니다.

## 제공 코드와 직접 작성할 범위

- Codex 제공: 함수 서명·설명·NumPy import, `tests/learner/test_dice_score.py`의20개 검사.
- 사용자 작성: `dice_score` 함수 본문의 입력 검증·선택 영역 처리·계산.
- 기존 `binary_metrics`를 호출하지 않고 NumPy로 직접 계산합니다. 테스트 기대값은 유지합니다.
- 정답 함수 본문은 넣지 않았습니다. 필요한 경우 힌트나 정답을 요청할 수 있습니다.

## 실습 파일 받기

Mac 터미널에서 프로젝트 루트로 이동해 새 파일 두 개만 받습니다. 기존 사용자 함수와 반례 테스트를 보존합니다.
이 명령은 전체 브랜치를 갱신하지 않습니다. 전체 테스트 수치는 GitHub 최신 코드 기준입니다.

```bash
cd ~/Projects/pathology-edge
git fetch origin
if [ -e src/pathology_edge/learner_metrics.py ] || [ -e tests/learner/test_dice_score.py ]; then
  printf '%s\n' '실습 파일이 이미 있습니다. 작성 내용을 보존하고 해당 파일을 확인하세요.'
else
  git restore --source=origin/main -- src/pathology_edge/learner_metrics.py tests/learner/test_dice_score.py
fi
```

이전에 사용한 가상환경을 활성화합니다. 이 실습은 NumPy·pytest만 필요합니다.

```bash
source .venv/bin/activate
python -m pip install numpy pytest
```

위 설치 명령은 해당 Python 환경에 필요한 패키지가 있는지 확인하고 부족한 패키지를 설치합니다.

## 직접 실행할 검사

저장소 루트에서, 이번 함수의 계약만 확인합니다.

```bash
python -m pytest --run-learner tests/learner/test_dice_score.py -q
```

작성 전에는20개가 `NotImplementedError`로 실패하는 것이 예상 상태입니다. 작성 후 기대 결과는 **20 passed**입니다.
20개는 알려진 점수·영역 제한·빈 foreground·입력 보존·큰 uint8 합계·잘못된 입력 검사를 포함합니다.
검토 전에는 일반 전체 검사에서 이20개만 명시적으로 skip하며 통과로 기록하지 않습니다.

보내주실 것은 **작성한 함수와 실행 결과**입니다. 실패하면 전체 traceback도 함께 보내 주세요.
확인 후 다음 단계로 넘어갑니다. 사용자가 실행하기 전에는 사용자 테스트 완료로 기록하지 않습니다.
