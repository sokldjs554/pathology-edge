# 40단계: 실제 ROI 메타데이터를 본인 좌표 함수에 연결

상태: **실습 파일 갱신·손실 함수 원본 보존 보고 확인, 사용자 연결 함수 작성·테스트 예정**. 사용자가 “실습 파일 갱신 완료. 작성한 손실 함수 원본 보존.”을 보고했습니다. 갱신 후 커밋과 파일은 직접 조회하지 않았으며, 새 함수 코드·테스트 출력은 아직 받지 않았습니다. 이번에는 이미 작성한 `local_to_level0`를 다시 구현하지 않고, 실제 WSI 읽기·리사이즈 정보와 연결합니다.

## 실습 파일 수신 완료 — 아래 갱신 명령은 참고용

갱신 전 보고된 Codespaces 상태는 `790a336`, 변경 파일은 `src/pathology_edge/learner_losses.py` 하나였습니다. 아래 명령의 성공 보고를 받았으므로 **다시 실행하지 않고 다음 절의 함수 작성으로 진행합니다**. 아래는 그 파일의 검증된 백업을 만든 뒤 저장소를 갱신하고, 작성한 파일을 그대로 복구하도록 제공한 명령입니다. 명령이 실패해도 종료 처리에서 백업을 복원합니다. 다른 변경이 생겼으면 수정 전에 중단합니다. 백업 경로도 파일로 남깁니다.

**실행 위치:** Codespaces Bash 터미널, 기존 저장소 `/workspaces/pathology-edge`.

```bash
(
set -eu
cd /workspaces/pathology-edge
test "$(git status --porcelain)" = ' M src/pathology_edge/learner_losses.py' || { printf 'Git 상태가 달라졌습니다. git status --short 출력을 보내 주세요.\n'; exit 1; }
mkdir -p work
LOSS_BACKUP="$(mktemp "$PWD/work/learner-loss-before-step40.XXXXXX.py")"
cp src/pathology_edge/learner_losses.py "$LOSS_BACKUP"
cmp src/pathology_edge/learner_losses.py "$LOSS_BACKUP"
printf '%s\n' "$LOSS_BACKUP" > work/step40-loss-backup-path.txt
trap 'cp "$LOSS_BACKUP" src/pathology_edge/learner_losses.py' EXIT
git fetch origin
git cat-file -e origin/main:src/pathology_edge/learner_wsi.py
git restore -- src/pathology_edge/learner_losses.py
git merge --ff-only origin/main
cp "$LOSS_BACKUP" src/pathology_edge/learner_losses.py
cmp "$LOSS_BACKUP" src/pathology_edge/learner_losses.py
trap - EXIT
printf '실습 파일 갱신 완료. 작성한 손실 함수 원본 보존.\n'
git status --short
)
```

실행 뒤 손실 파일이 여전히 `M`으로 표시될 수 있습니다. 원본 파일의 주석·공백 등을 그대로 보존한 결과이며 오류가 아닙니다. 성공 문구가 없거나 오류가 나면 출력을 보내고 다음 편집은 기다립니다. 백업은 삭제하지 않습니다.

## 직접 작성할 부분 하나

**파일:** `src/pathology_edge/learner_wsi.py`

**함수:** `roi_points_to_level0(points_xy, geometry)`

기존에 제공된 타입 검사 아래의 `raise NotImplementedError(...)`만 메타데이터 연결과 반환으로 바꾸세요. `local_to_level0`는 이미 import돼 있습니다. 수식을 다시 복사하지 말고 본인이 작성한 이 함수를 호출합니다.

| 입력·필드 | 의미 |
|---|---|
| `points_xy` | 모델 입력 이미지의 연속적인 `(x,y)` 좌표, shape `(N,2)` |
| `geometry.origin_level0_xy` | OpenSlide에 요청한 ROI 원점. 이미 level-0 단위이므로 다시 배율을 곱하지 않음 |
| `geometry.level_downsample` | OpenSlide가 제공한 실제 배율. `level` 번호로 추측하지 않음 |
| `geometry.read_size_wh` | 경계 crop까지 반영한 실제 읽기 이미지의 `(width,height)` |
| `geometry.model_size_wh` | 리사이즈 후 모델 입력의 `(width,height)` |

작성 범위는 **x/y 각각의 리사이즈 비율을 구하고, 원점·downsample·두 비율을 기존 함수에 전달해 결과를 반환하는 것**입니다. 비율은 각 축의 “모델 입력 크기 ÷ 실제 읽기 크기”입니다. 요청 크기나 NumPy 배열의 `(height,width)` 순서와 혼동하지 마세요.

반환은 float64 `(N,2)` 배열이고 입력은 바꾸지 않습니다. 빈 `(0,2)`는 허용하며 좌표를 반올림하거나 이미지 경계로 강제 제한하지 않습니다. 잘못된 점 배열은 기존 `local_to_level0`의 검사로 거절합니다. `RoiGeometry` 필드 검사는 Codex가 제공합니다.

이번 좌표는 패치 사각형의 **픽셀 경계 좌표**입니다. OpenCV 성분 중심과 같은 픽셀 인덱스를 리사이즈한 영상 간 옮길 때 필요한 중심 보정까지 구현했다고 설명하지 않습니다.

## 손으로 확인할 예시

- 원점 `(1000,2000)`, downsample `4`, 실제 읽기 `(400,200)`, 모델 입력 `(200,50)`.
- 모델 좌표 `[[10,20],[0,0]]`의 예상 결과는 `[[1080,2320],[1000,2000]]`입니다.
- 슬라이드 경계 때문에 요청 `(40,30)`에서 실제 읽기가 `(10,20)`으로 줄고 모델 입력이 `(20,10)`이라면, 비율 계산에 사용할 크기는 `(10,20)`입니다.

실제 CMU 슬라이드의 downsample은 level 1에서 **4.000060805058981**, level 2에서 **16.003163017031632**입니다. 정수 4·16이나 `2**level`로 대체하지 않습니다. Codex는 원본에서 5개 읽기 조건과 기존 native R1 이미지 픽셀 일치를 확인했습니다. 이는 ROI 읽기 검증이고 아직 미작성인 사용자 좌표 연결 검증은 아닙니다.

## 작성 후 실행할 테스트

**위치:** 같은 저장소 루트 `/workspaces/pathology-edge`. 파일을 저장한 뒤 실행합니다.

```bash
python -m pytest -q tests/learner/test_wsi_coordinates.py --run-learner
```

목표는 **8 passed**입니다. 비등방 리사이즈, native 좌표, 소수 downsample, 입력 보존·빈 배열·잘못된 입력, 실제 crop 크기 사용, 기존 native patch manifest와의 일치, 마지막 패치의 padding 제외를 검사합니다. 처음의 미구현 틀에서는 8개 `NotImplementedError` 실패가 예상 상태입니다.

**제출할 것:** 작성한 함수 본문과 테스트 결과. 실패하면 traceback도 함께 보내 주세요. 그 전까지 U52는 예정입니다.

전체 테스트의 참고 명령은 `python -m pytest -q --run-learner`입니다. 현재 기본 `python -m pytest -q`는 이 미완료 계약 8개를 건너뛰므로 개인 함수 성공 확인을 대신하지 않습니다. 지금은 위 8개만 실행하면 됩니다.

## Codex가 준비한 것과 남은 범위

Codex는 `wsi_roi.py`의 메타데이터 검사·OpenSlide ROI 읽기·리사이즈와 `roi_patch_manifest` 호출부를 준비했습니다. 읽기 요청이 오른쪽/아래 경계를 넘으면 완전히 들어가는 선택-level 픽셀 수까지만 잘라 실제 크기를 기록합니다. 축소 level에서는 마지막 1픽셀 미만의 잔여 영역을 제외할 수 있으며 native level 0의 마지막 행·열은 보존합니다. RGBA는 흰 배경과 합성하고 RGB는 bilinear, 원본 alpha==255 마스크는 nearest-neighbor로 리사이즈합니다. 이 마스크는 보간 커널 전체의 유효성을 보장하는 마스크가 아닙니다.

사용자 함수가 미완성이므로 일반 배율의 patch 좌표 반환은 아직 완료되지 않았습니다. 기존 `wsi_export.py`와 공개 native 결과는 그대로이며, 실제 export 연결·좌표 대조는 제출 코드 검토 후 진행합니다. 이번에 새 모델 추론·WSI 정확도 평가·전체 슬라이드 분석을 수행한 것은 아닙니다.

[실제 ROI 읽기 근거](../artifacts/learning/step40-real-roi-reads.json) · [준비·검증 기록](../artifacts/learning/step40-preparation.json) · [사용자 갱신 보고](../artifacts/learning/step40-review.json) · [기여 기록](CONTRIBUTIONS.md)
