# 4단계: 전체·경계 영역의 Dice 직접 계산

상태: **2026-11-09 사용자 코드·테스트 실행 보고 검토 완료**. 제출한 함수 본문과 `20 passed in 0.01s` 보고를 확인했습니다.
Codex도20개 계약 검사·전체89개 검사를 통과했습니다. 아래는 완료한 과제의 계약과 재실행 안내입니다.
현재 할 일은 [5단계 실제 결과 검산](STEP_05.md) 하나입니다.

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
- 처음에는 빈 함수만 제공했습니다. 현재 저장소 본문은 사용자가 제출한 코드이며 채팅의 HTML·Markdown 이스케이프만 정리했습니다. 알고리즘은 수정하지 않았습니다.

## 파일 받기 참고

이미 작성한 파일이 있다면 다시 받을 필요가 없습니다. 아래는 새 작업 폴더에서 검토 완료 코드를 받을 때의 참고 명령입니다. 기존 사용자 함수와 반례 테스트를 보존합니다.
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

검토 완료한 코드의 기대 결과는 **20 passed**입니다. 과제 준비 당시 빈 함수의 `NotImplementedError` 실패 기록은 과거 증거로 남겼습니다.
20개는 알려진 점수·영역 제한·빈 foreground·입력 보존·큰 uint8 합계·잘못된 입력 검사를 포함합니다.
이20개는 이제 일반 전체 검사에도 포함되며, `--run-learner` 없이 실행해도 됩니다. 검토 후 전체 결과는 **89 passed, 0 skipped**입니다.

## 검토 결과와 다음 단계

입력 전체의0/1 검사가 NaN·Inf도 거부하고, Python 정수로 픽셀 수를 계산하며, 입력 보존·빈 foreground와 빈 평가 영역 구분을 충족했습니다.
Codex는 이 함수로 저장된 TNBC 점수42개·평균6개를 다시 계산해 원 실험·화면 JSON과 일치함을 확인했습니다. 새 추론은 실행하지 않았습니다.
[검토 기록](../artifacts/learning/step04-review.json) · [실제 결과 검산 기록](../artifacts/learning/step04-real-dice-audit.json).

사용자가 실제 결과 검산을 실행한 것으로 기록하지 않았습니다. 다음은 [STEP_05.md](STEP_05.md)의 명령 하나를 직접 실행하고 출력을 확인하는 단계입니다.
