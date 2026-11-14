# PathologyEdge · 학습한 세포 중심 검출 추가 자료

먼저 `review.html`을 브라우저로 여세요. 설치 없이 저장된 결과를 볼 수 있습니다.
정답·기존 LoG 검출·학습한 검출의 세 패널에서 같은 영상을 비교합니다.
첫 사례·검출 seed20261117·CNN seed20261113을 유지하고 `학습 위치 지도`를 켰다 끄는 것이
이번 사용자 검토 한 단계입니다. 사용자 확인은 아직 예정이며 자동 테스트 실행과 구분합니다.

`KI67_LEARNED_CENTERS.md`에는 모든3검출seed×4고정분류기의 실제 결과와 한계가 있습니다.
`STEP_80.md`는 첫 화면 확인 안내입니다. 원래 큰 공개 데모는 변경하지 않았습니다.

## 실제 이미지 한 장 추론

ZIP을 푼 **이 폴더**에서 기존 Ubuntu Python3.12환경으로 실행합니다.
아래 명령은 원영상만 입력하며 정답 좌표를 전달하지 않습니다. 출력 이름은 새 경로를 사용하세요.

```bash
PYTHONPATH=frozen_source python scripts/infer_ki67_centers.py \
  --bundle inference-bundle.json --image examples/first-case.png \
  --detector-seed 20261117 --classifier cnn-20261113 \
  --output my-first-prediction.json
```

새 환경에 패키지가 없다면 먼저 `python -m pip install -r requirements-inference.txt`를 실행합니다.
CPU PyTorch·NumPy·SciPy·Pillow를 설치하는 명령입니다. 기존 사용자 Codespaces 환경의 패키지를
자동으로 바꾸지는 않았으며, 사용자 실행 완료로 기록하지 않았습니다.
일반 단일영상 패치(각변4~2048px)만 지원하고 원본 WSI 파일은 지원하지 않습니다.

`inference-bundle.json`은 모델·소스 SHA를 검사합니다. seed는20261117/18/19,
분류기는lr 또는cnn-20261113/14/15입니다. `portable-replay.json`은12개 조합의 좌표·점수·클래스를
실제 저장 결과와 대조한 실행 기록입니다. 모델 점수는 보정된 임상 확률이 아닙니다.

## 증거 파일의 범위

- `protocol.json`, `selection*.json`, `training-*.json`: 조건·선택·모든epoch 기록.
- `seed-*/internal/`:407장 내부 결과·예측 좌표·독립 검산. 양성률은10케이스 단위.
- `seed-*/external/`:BCData133장 종양-only 결과·독립 검산. 양성률은영상 단위.
- `baseline/`, `previous-filter/`:앞선 기준 검출·후보 제거 결과. 새 결과로 덮어쓰지 않았습니다.
- `initial-relu-validation/`:첫 ReLU3seed실험·실패seed와 검증자료 진단 원본을 보존합니다.
  이 초기 실험에는 테스트/BCData 평가가 없고, 새 모델과 같은 검증 자료를 사용한 개발 이력입니다.
- `frozen_source/`, `models/`:새 검출3개와 기존 분류4개, 해당 소스. 전체 학습 재현에는 원자료와
  이전 전체 실험 폴더가 필요합니다. 이 ZIP만으로 가능한 것은 한 장 추론·내부 저장 결과 재검산·화면 열기입니다.
- `screenshots/`:1440px/390px 브라우저 확인과36개 표시 조합의 실제 저장 JSON 대조 기록.
- `CONTRIBUTIONS.md`, `confirmed-user-reviews/`, `user-file-preservation.json`:
  기존 사용자 기록 U93까지와 미확인 U94를 구분. 이번 모델 구현·학습·추론은 사용자 직접 수행이 아닙니다.

이미 결과를 살펴본 기존 자료의 재평가입니다. 새 미노출 외부 검증·임상 검증·전체 WSI 정답 검증이 아닙니다.
BCData 원영상·HDF5·개별 세포 좌표는 포함하지 않았습니다. 외부 재검산 전체 재현에는 별도 원자료가 필요합니다.
분모0 양성률은 계산 불가이며 비교 시 유효 영상/케이스 수도 함께 확인해야 합니다.

## 출처와 이전 전달 자료

Patherea 이미지/주석: Dejan Štepec et al., “Patherea: Cell Detection and Classification for the 2020s,”
Medical Image Analysis(2025), https://doi.org/10.1016/j.media.2025.103868 .
https://huggingface.co/datasets/ds2268/patherea · https://creativecommons.org/licenses/by-nc/4.0/ .
원영상에 예측 위치·지도·점수 비교를 추가했습니다. 저자의 보증을 뜻하지 않으며 연구·비상업 용도 자료입니다.
이 데이터 라이선스가 프로젝트 코드 전체에 새 라이선스를 선언하는 것은 아닙니다.
BCData: https://sites.google.com/view/bcdataset (연구·비상업용; 이 패키지에는 집계만 포함).

이 ZIP은 추가 자료이며 이전 전체 전달 자료를 대체하지 않습니다.

- U86까지 전체: https://raw.githubusercontent.com/sokldjs554/pathology-edge/ff486a3be0f01fcdc98e9aad5dd67d6a7424d39e/artifacts/handoff/PathologyEdge-Final-Handoff-20261113.zip
- 첫 자동 검출·분류: https://raw.githubusercontent.com/sokldjs554/pathology-edge/751f92e5c83069d1bdb651b4b7dce6e9b0d36726/artifacts/handoff/PathologyEdge-AutoKi67-Addendum-20261113.zip
- 후보 제거: https://raw.githubusercontent.com/sokldjs554/pathology-edge/c3b9dedaf3129fdc207ab1e444bc13f14584810b/artifacts/handoff/PathologyEdge-CandidateFilter-20261113.zip
- 저장소: https://github.com/sokldjs554/pathology-edge · 연구 작업 PR: https://github.com/sokldjs554/pathology-edge/pull/2
- 기존 공개 데모: https://pathology-edge-lab.ykh13571.chatgpt.site/
