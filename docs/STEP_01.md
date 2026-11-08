# 1단계: 패치 좌표를 원본 좌표로 되돌리기

상태: **사용자 코드·테스트 실행 보고·좌표계 설명 확인 완료** (2026-11-08).
사용자는 `12 passed in 0.31s`를 보고했고, Codex는 같은 12개 테스트를 독립 실행해 통과를 확인했습니다.
제출한 알고리즘은 수정하지 않았습니다. 채팅의 HTML/Markdown 이스케이프만 정리해 저장했습니다.
사용자는 x축1/2·y축1/4 축소를 역으로 되돌리기 위해 각 scale로 나눈다고 설명했고, Codex가 정확한 설명으로 확인했습니다. 후속 진행 상태는 [NEXT_STEPS](NEXT_STEPS.md)에서 확인할 수 있습니다.
Python 상 / NumPy·Ubuntu 사용 가능, macOS 11.7.11 기준 안내는 아래에 유지합니다.

## 작성 위치와 역할

`src/pathology_edge/learner_coordinates.py`의 `local_to_level0` 함수 본문을 작성합니다.
검출 결과를 패치·배율과 무관한 원본 좌표로 맞추는 기능입니다. 기존 실험은
512×512 PNG의 원래 픽셀 좌표를 사용하며, 새 WSI 실험은 native level-0 ROI만 읽고 원점을 더합니다.
일반 배율 변환 함수는 이번 제출로 구현·검토됐고, 피라미드 배율/모델 입력 리사이즈를 지원하는
실제 파이프라인 어댑터 연결은 별도 후속 작업입니다. 기존 데모의 분석 경로는 유지됩니다.

## 입출력 계약

| 인수 | 의미 / 조건 |
|---|---|
| `points_xy` | 유한 실수 NumPy 배열 `(N,2)`. 열 순서 `(x,y)`, 모델 입력 좌표 |
| `origin_level0_xy` | 원본 level-0에서 패치 왼쪽 위의 `(x,y)`, 길이 2 |
| `level_downsample` | 원본 1픽셀 대비가 아니라, 선택한 level의 1픽셀에 해당하는 level-0 픽셀 수. 양의 유한 스칼라 |
| `model_scale_xy` | 각 축의 `모델 입력 크기 / level 패치 크기`. 길이 2, 양의 유한 실수 |
| 반환 | 입력과 같은 순서의 `(N,2)` float64 배열. 단위는 level-0 픽셀 |

이미지 배열의 `(row,column)`과 좌표의 `(x,y)`를 혼동하지 않습니다.
좌표는 픽셀 중심 오프셋 보정이 없는 연속 좌표입니다. 원점은 경계의 왼쪽 위이며,
round/clip을 하지 않습니다. 음수 좌표는 허용합니다. 빈 `(0,2)` 입력도 허용합니다.
입력을 제자리 수정하지 않습니다. 모양 오류, NaN/Inf, 0 이하 배율은 `ValueError`입니다.
`level_downsample`은 스칼라만 허용합니다. 리스트를 배열로 바꾸는 편의 기능은 필수가 아닙니다.

## 제공된 부분 / 직접 작성 범위

- Codex 제공: 함수 서명·설명, 독립 단위 테스트, 프로젝트 실행 기반.
- 사용자 작성·제출: 함수 본문의 입력 검증과 변환 연산. 테스트 기대값은 바꾸지 않았습니다.
- Codex 검토: 변환 순서, shape·finite·양수 조건, 빈 배열·소수·음수 좌표·입력 보존을 확인했습니다.
- 사용자 제출은 정수/부동소수 dtype을 허용하며 bool·complex·string·object dtype은 거부합니다.
- [검토 기록](../artifacts/learning/step01-review.json)에 사용자 실행 보고와 Codex 검증을 구분했습니다.

예: 점 `[[10,20],[0,0]]`, 원점 `(1000,2000)`, downsample `4`,
model scale `(0.5,0.25)`이면 `[[1080,2320],[1000,2000]]`이 나와야 합니다.
두 축의 리사이즈 비율이 다른 이유를 말로 설명해 보세요.

## macOS에서 이번 단계만 실행하기

Terminal에서 작업을 보관할 상위 폴더로 이동한 뒤:

```bash
git clone https://github.com/sokldjs554/pathology-edge.git
cd pathology-edge
sw_vers
uname -m
python3 --version
git --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'numpy>=1.24' 'pytest>=8'
python -m pytest --run-learner tests/learner/test_coordinates.py -q
```

`sw_vers`/`uname -m`: macOS 버전과 Intel/Apple Silicon 확인.
Python 3.10 이상을 권장합니다. 이 단계에는 PyTorch, Docker, GPU가 필요 없습니다.
macOS 11용 최신 패키지 wheel이 없다면 설치 오류를 보내 주세요. OS를 업그레이드하거나
지원되지 않는 Docker Desktop을 설치해야 한다고 가정하지 않습니다.
마지막 명령은 저장소 루트에서 실행합니다. 초기 템플릿의 `NotImplementedError`는 사용자 제출 코드로 교체됐습니다.
검토 완료한 12개 테스트는 이제 `python -m pytest -q`에도 기본 포함됩니다. 기존 `--run-learner` 명령도 계속 사용할 수 있습니다.

## 보내주실 것

함수 전체, `12 passed in 0.31s` 결과, 축별 리사이즈를 역으로 되돌리는 이유를 모두 받았습니다. **1단계는 완료**입니다. 다음은 [STEP_02](STEP_02.md)의 합성 사례 하나를 검토합니다. 새로운 실행 문제가 있을 때만 실행 명령·OS/Python 버전·traceback을 함께 보내 주세요.
전체 프로젝트 테스트와 추가 계약 검사는 Codex 실행 기록이며 사용자 실행으로 기록하지 않습니다.

