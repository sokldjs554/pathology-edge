# 1단계: 패치 좌표를 원본 좌표로 되돌리기

상태: **사용자 작성·실행 대기**. Python 상 / NumPy·Ubuntu 사용 가능, macOS 11.7.11 기준.
지금은 이 단계만 수행하세요. 다른 후보 과제는 이 코드를 검토한 뒤 정합니다.

## 작성 위치와 역할

`src/pathology_edge/learner_coordinates.py`의 `local_to_level0` 함수 본문을 작성합니다.
검출 결과를 패치·배율과 무관한 원본 좌표로 맞추는 기능입니다. 현재 실험은
512×512 PNG의 원래 픽셀 좌표만 사용합니다. 이 함수가 완성되어 검토되면
피라미드 배율/모델 입력 리사이즈를 지원하는 어댑터에 연결할 예정입니다.
따라서 지금 데모의 정상 동작은 사용자 코드의 완료를 뜻하지 않습니다.

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
- 사용자 작성: 함수 본문의 입력 검증과 변환 연산. 테스트에서 기대값을 바꾸지 않습니다.
- 정답 구현은 넣지 않았습니다. 필요하면 힌트 또는 정답을 요청할 수 있습니다.

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
마지막 명령은 저장소 루트에서 실행합니다. 작성 전 `NotImplementedError`는 예상 결과입니다.

## 보내주실 것

작성한 함수 전체, 위 테스트의 마지막 결과와 실패 traceback,
`sw_vers`, `uname -m`, `python --version` 출력,
그리고 예제에서 x와 y가 다르게 변하는 이유 한 문장을 보내 주세요.
제가 정확성·입력 검증·좌표계 설명을 검토한 뒤에만 다음 단계로 넘어갑니다.
실행하지 않은 테스트는 사용자 완료로 기록하지 않습니다.

