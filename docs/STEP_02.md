# 2단계: 가까운 서로 다른 핵이 억제되는 반례 검토

상태: **반례 해석 확인 완료 · 사용자 테스트 작성·실행 대기**.
사용자는 서로 다른 핵2개가1개로 과소 집계되고, IoU0이어도 거리6px가8px 이하이므로 OR 조건이 작동한다고 설명했습니다. 정확한 해석입니다.
이제 같은 사례를 재현하는 테스트 함수 하나만 작성합니다.

## 프로젝트에서 맡는 역할

`src/pathology_edge/merge.py::deduplicate`는 서로 다른 패치에서 나온 후보의 중복을 줄입니다.
확률맵을 합치는 픽셀 분할 경로와는 별개입니다. 후보 수가 줄었다는 사실만으로 검출 성능을 평가할 수 있는지 살펴보는 단계입니다.

## 현재 코드의 규칙

- 패치 ID가 다른 후보끼리 비교합니다.
- `IoU >= 0.3` **또는** 원본 좌표의 중심 거리 `<= 8px`이면 나중 후보를 억제합니다.
- 패치 경계에 닿지 않은 후보를 먼저 처리하며, 같은 조건이면 score가 높은 순서입니다.
- 반환값은 유지 후보 목록과 `suppressed_index → kept_index` 대응입니다. 번호는 입력 목록의 0부터 시작합니다.

## 이번에 볼 합성 사례

다음은 규칙을 이해하기 위해 만든 **합성 입력**입니다. 실제 WSI의 핵 정답이나 모델 예측으로 제시하지 않습니다.
두 후보는 서로 다른 실제 핵에 해당한다고 이 교육 사례의 정답을 정했습니다.
좌표는 이미 같은 원본 좌표계이며 상자는 `[x0,y0,x1,y1)`입니다.

| 후보 | 원 패치 ID | 중심 `(x,y)` | 상자 | score | 패치 경계 접촉 |
|---|---:|---|---|---:|---|
| A / index 0 | 0 | (99.5,49.5) | [98,48,102,52] | 0.9 | 없음 |
| B / index 1 | 1 | (105.5,49.5) | [104,48,108,52] | 0.8 | 없음 |

상자의 IoU는 **0**, 중심 거리는 **6px**입니다. score 역시 이 합성 입력의 값이며 임상 확신도가 아닙니다.
Codex는 위 입력을 현재 `deduplicate`에 넣어 동작을 확인했습니다([입력·실행 기록](../artifacts/learning/step02-synthetic-nms.json)).
이 확인은 사용자 실행 기록에 포함하지 않습니다.

## 직접 작성할 파일·함수

파일: `tests/learner/test_merge_counterexample.py`

함수: `test_distance_rule_can_suppress_distinct_nuclei(candidate_pair)`

이 테스트는 현재 NMS의 알려진 과소 집계 사례를 재현하는 기록입니다. 통과는 **이 한계를 재현했다는 뜻**이며 알고리즘의 정확도나 개선을 입증하지 않습니다.

- Codex 제공: import, 위 두 후보를 만드는 `candidate_pair` fixture, 테스트 함수 이름, 미완료 과제 표시.
- 사용자 작성: `NotImplementedError`를 지우고 함수 본문만 작성합니다. fixture와 기존 병합 알고리즘은 이번 작성 범위에 포함하지 않습니다.
- 입력: fixture가 매번 새로 만드는 후보 dict 두 개의 list입니다. `x/y`, `bbox`, `score`, `patch_id`, `touches_edge`는 위 표와 같습니다.
- 호출할 함수: `box_iou(a, b)`는 상자 좌표 list 두 개를 받아 수치를 반환합니다. `deduplicate(objects)`는 후보 목록을 받아 `(kept, removed)` 두 list를 반환합니다.
- `kept`에는 원 후보의 `raw_index`가 추가됩니다. `removed`에는 `suppressed_index`와 `kept_index`가 있습니다. 둘 다 원래 입력 목록의 index입니다.
- 테스트 함수 자체의 반환값은 없습니다. 실제 함수 결과를 `assert`로 검사합니다.

## 본문에서 확인할 조건

1. 실제 fixture 좌표로 상자 IoU가0이고 중심 거리가6px인지 확인합니다. `hypot`는 import해 두었습니다.
2. 실제 `deduplicate`를 기본 임계값으로 호출합니다.
3. 유지 후보1개, 억제 대응1개가 나오는지 확인합니다.
4. 남은 원래 후보 index는0(A), 억제된 index는1(B)이며, B가 A에 대응해 억제됐는지 확인합니다.

입력 두 핵이 별개라는 합성 정답과 유지1개의 차이를 테스트 docstring 또는 짧은 주석으로 설명하세요.
결과값을 직접 만들어 검사를 통과시키지 않고 실제 함수의 반환값을 검증합니다. 완성된 테스트 코드는 먼저 제공하지 않았습니다.

## 로컬에 이번 실습 파일 받기

이전에 안내한 위치에 저장소를 받았다면 Mac 터미널에서 아래를 실행합니다. 다른 곳에 받았다면 첫 경로만 바꿉니다.
작성한 좌표 함수를 보존하면서 이번에 필요한 두 파일만 받는 명령입니다.

```bash
cd ~/Projects/pathology-edge
git fetch origin
if [ -e tests/learner/test_merge_counterexample.py ]; then
  printf '%s\n' '실습 파일이 이미 있습니다. 기존 작성 내용을 보존하고 이 파일을 열어 확인하세요.'
elif git diff --quiet HEAD -- src/pathology_edge/merge.py; then
  git restore --source=origin/main -- src/pathology_edge/merge.py tests/learner/test_merge_counterexample.py
else
  printf '%s\n' 'merge.py에 로컬 변경이 있습니다. 파일을 보존했으니 git status --short 결과를 보내 주세요.'
fi
```

`merge.py`의 변경은 OpenCV·NumPy를 이미지 성분 추출 함수 안에서만 import하도록 옮긴 것입니다.
`box_iou`·`deduplicate`의 알고리즘은 동일합니다. 이번 테스트에는 pytest만 필요하며, 앞선 NumPy·pytest 환경을 그대로 사용할 수 있습니다.

## 직접 실행할 명령

앞서 사용한 가상환경을 활성화하고 **저장소 루트**에서 실행합니다. 이 명령은 지금 작성한 반례 테스트 하나만 검사합니다.

```bash
python -m pytest --run-learner tests/learner/test_merge_counterexample.py -q
```

작성 전에는 `NotImplementedError`로1개 실패하는 것이 예상 동작이고, 작성 후 기대 결과는 **1 passed**입니다.
일반 `python -m pytest -q`에서는 검토 전인 이1개만 skip합니다. 완료한 좌표 함수12개는 계속 실행됩니다.
전체 프로젝트 환경에서 Codex는 **68 passed, 1 skipped**를 확인했습니다. 이 결과를 사용자 실행으로 기록하지 않습니다.

보내주실 것은 **작성한 테스트 함수와 실행 결과**입니다. 실패하면 생략하지 않은 traceback도 함께 보내 주세요.
코드와 결과를 검토한 후 다음 단계로 진행합니다.

## 기여 구분

- 사용자 완료: 과소 집계와 OR 거리 조건에 대한 해석.
- 사용자 예정: 테스트 본문 작성·실행. 임계값 변경이나 새 병합 정책 결정은 아직 배정하지 않았습니다.
- Codex 완료: 합성 입력·fixture·빈 테스트 틀, 최소 의존성 분리, 기존68개 회귀 검사와 입력 검증. [준비 검증 기록](../artifacts/learning/step02-preparation.json).
