# Pathology Edge

**병리 이미지의 패치 경계가 핵 분할에 미치는 영향을 재현하고 검토하는 연구용 작업대.**
같은 모델의 무겹침·겹침 처리를 비교하고, 정확도·처리 시간·메모리·실패 사례를 함께 공개합니다.

[공개 데모](https://pathology-edge-lab.ykh13571.chatgpt.site) · [지금 할 1단계 과제](docs/STEP_01.md) · [실행 안내](docs/RUNBOOK.md) · [기여 기록](docs/CONTRIBUTIONS.md) · [검토 질문](docs/REVIEW.md)

연구·교육용입니다. 에이비스와 무관한 독립 프로젝트이며 실제 진단·치료 결정에 사용할 수 없습니다.
**H&E 핵 분할입니다. Ki-67 양성률, 종양 세포 분류, WSI 전체 성능은 검증하지 않았습니다.**

## 실제 결과

TNBC v1.1의 50개 512×512 이미지·이진 핵 마스크를 사용했습니다.
폴더 그룹 단위로 train 33 / validation 10 / test 7장을 분리했습니다.
공식 설명은 11환자이나 독립 환자 명부가 없어 `Slide_01..11`을 케이스 그룹으로 사용한 한계가 있습니다.
선택된 모델은 test를 보지 않고 validation으로 epoch 12·threshold 0.5를 결정했습니다.

| 방식 | 전체 Dice | 경계 Dice | 내부 Dice | 시간/장 ms | 전체 프로세스 peak MiB |
|---|---:|---:|---:|---:|---:|
| OpenCV 기준 | 0.4867 | 0.4658 | 0.4916 | 3.7 | 412.9 |
| TinyUNet 무겹침 | 0.5580 | 0.4918 | 0.5729 | 57.2 | 430.5 |
| TinyUNet 겹침 + 병합 | 0.5608 | 0.5273 | 0.5696 | 309.3 | 437.3 |
| TinyUNet 512px 전체 (참고) | 0.5655 | 0.5313 | 0.5744 | 88.5 | 487.3 |

경계는 기준 128px 격자의 내부 경계 양쪽 8px이며 모든 방식에 같은 영역을 적용했습니다.
Dice는 이미지별 점수의 평균입니다. 시간은 모델 로딩·디스크 I/O·지표 계산을 제외한
패치 추출→조직 게이트→추론→확률 합산→성분 추출→NMS의 warm CPU 3회 중앙값을 이미지 간 다시 중앙값으로 집계했습니다.
메모리는 방식별 별도 프로세스의 절대 peak RSS이며 런타임·warmup·평가를 포함합니다. 추가 메모리만을 뜻하지 않습니다.

겹침은 경계 Dice를 약 **+0.0355**, 전체 Dice를 **+0.0028** 높였지만 시간은 약 **5.4배** 걸렸습니다.
그룹10 전체 Dice는 0.5187→0.5003으로 하락했고 그룹11은 0.6104→0.6415로 상승했습니다.
두 그룹·한 seed의 결과이므로 일반적인 해결이나 유의한 개선을 주장하지 않습니다.
512px 전체 입력과의 경계 확률 차이는 MAE 0.0560→0.0068로 감소했습니다. 이는 일관성 지표이며 정답 정확도를 대신하지 않습니다.

![실제 모델의 같은 위치 비교 — 브라우저 캡처 아님](artifacts/boundary_comparison.png)

위는 개선이 가장 적은 `10_3`입니다. 전체 Dice가 0.6627→0.6347로 하락합니다.
[GT·FP·FN 비교](artifacts/error_10_3.png), [낮은 점수 사례](artifacts/error_10_4.png),
[개선 사례](artifacts/error_11_2.png)를 함께 보세요. 이미지는 실제 결과 시각화이며 브라우저 화면 캡처가 아닙니다.

## 핵심 구현

```text
공식 ZIP + checksum → 원본/GT 쌍 검사 → 케이스 그룹 분리
  → OpenCV 조직 마스크 / Python·C++ 패치 추출
  → TinyUNet 추론 (각 패치의 원래 PNG 좌표 보존)
  ├─ 확률맵 가중 합산 → 이진 분할 → Dice·IoU / 경계·내부 평가
  └─ 패치별 연결 성분 → 원래 PNG 좌표 → cross-patch NMS → 후보 검토
  → 고정 결과 JSON·overlay → 동기화 웹 작업대
```

각 패치는 좌표·유효 영역·level·downsample을 갖습니다. 이번 PNG에는 실제 WSI 원점·배율·MPP가 없으므로
물리 해상도는 null이고 좌표 단위는 `provided_png_pixels`입니다. 일반 배율·리사이즈 변환은 사용자 과제로 남겨 두었습니다.

무겹침은 128px/stride128, 겹침은 128px/stride64이며 trailing patch를 흰색으로 padding합니다.
512px 입력은 각각 16·64개 패치입니다. 픽셀은 Hann 계열 중앙 가중치로 합칩니다.
성분은 경계에 닿지 않은 후보 우선으로 정렬하고, 다른 patch 사이 IoU≥0.3 또는 중심 거리≤8px이면 억제합니다.
NMS는 근접한 다른 핵을 합치거나 잘린 조각을 놓칠 수 있는 휴리스틱입니다.

이진 GT의 연결 성분 중심으로 계산한 proxy F1은 겹침 raw 0.2671→NMS 0.4943이지만,
**진짜 세포별 instance label·종양 세포 정확도·Ki-67 지표가 아닙니다.**
픽셀 합산과 성분 NMS는 별도 경로이므로 녹색 영역의 연결 성분 수와 선택 가능한 후보 수가 다를 수 있습니다.

## C++ / 스레드 측정

`cpp/patches.cpp`는 실제 RGB crop·흰색 padding을 수행합니다. GIL을 해제하고 독립 패치를
std::thread로 분담합니다. Python 배열 복사 구현과 동일한 출력을 검증했습니다.

| 입력 | 구현 | 스레드 | 중앙값 ms | 전체 프로세스 peak MiB | Python 대비 |
|---|---|---:|---:|---:|---|
| 512² | python | 1 | 0.248 | 42.0 | 일치 |
| 512² | cpp | 1 | 0.123 | 42.1 | 일치 |
| 512² | cpp | 2 | 0.162 | 42.0 | 일치 |
| 512² | cpp | 4 | 0.208 | 41.9 | 일치 |
| 2048² | python | 1 | 11.967 | 188.9 | 일치 |
| 2048² | cpp | 1 | 8.400 | 189.6 | 일치 |
| 2048² | cpp | 2 | 6.761 | 188.5 | 일치 |
| 2048² | cpp | 4 | 5.299 | 188.9 | 일치 |

합성 uint8 RGB, 패치128/겹침64, warmup 후 9회, allocation·복사·padding 포함.
의학적 성능 실험이 아닙니다. peak 메모리는 정합성 검사의 두 출력 배열까지 포함하므로 연산만의 추가 메모리로 해석하지 않습니다.
작은 입력에서 4 thread는 C++ 1 thread보다 느립니다. 입력이 커지면 이번 환경에서는 다중 스레드가 빨랐습니다.
실제 test 7장의 무겹침·겹침 **14개 확률맵도 Python/C++ 경로가 bit-for-bit 일치**했습니다.
원시값: [benchmark.json](artifacts/benchmark.json), [cpp_real_parity.json](artifacts/cpp_real_parity.json).

## 업무·기술 대응

공고 원문은 열리지 않았습니다. 아래는 **사용자가 제공한 공고 요약**에 대한 대응이며
경력·학력·우대 조건 원문을 검증했다고 주장하지 않습니다. [조사·데이터 비교](docs/RESEARCH.md)를 참고하세요.

| 기술/업무 | 코드와 실제 실행 |
|---|---|
| Python / 실험·재현성 | `data.py`, `experiment.py`, `cli.py`, manifest·protocol·hash |
| PyTorch / 설계·학습·추론 | `model.py` TinyUNet, 29,761 parameters, 16 epochs 실행·checkpoint 저장 |
| Computer Vision / 병리 이미지 | 핵 분할, 경계·내부 평가, 확률 합산, 연결 성분·오류 overlay |
| OpenCV | RGB/HSV/gray 전처리, 배경 제외, threshold 기준 방식, 연결 성분 |
| C++ | `cpp/patches.cpp`, Python/C++ 실제 추출·추론 출력 정합성 |
| 멀티스레딩 | C++ 1·2·4 thread 실행, 두 크기에서 시간·메모리 비교 |
| Ubuntu | Ubuntu 24.04 Docker 안의 테스트·실제 이미지 추론 |
| Docker | Ubuntu 기반 Dockerfile 실제 빌드·실행, CA proxy 대응은 secret 사용 |
| Git / GitHub / CI | 실행 코드·실험 파일·테스트 게시, `.github/workflows/ci.yml` |
| classification / detection / segmentation | segmentation 핵심 검증. detection은 CC centroid proxy만. classification 미구현 |

회사 제품은 종양 세포 기반 Ki-67 정량화를 다룹니다. 이 프로젝트는 그 전제인 세포 수준 영상 처리와
재현·오류 추적 역량을 보여줍니다. 제품과 같은 성능·임상 범위를 갖는다고 설명하지 않습니다.

## 실행과 검증 상태

- 학습: Debian 13, AMD EPYC 9V74, 노출 CPU 5개, Torch thread4, GPU 없음. 약 **42.6초**.
- 일반 테스트: Debian **33 passed**, Ubuntu 24.04 Docker **33 passed**.
- 사용자 좌표 함수 관련 **12 tests skipped**. 완성 또는 통과로 기록하지 않습니다.
- 실제 모델 추론·학습·평가·C++ 정합성·정적 UI 파일과 실제 결과 연결 검사 완료.
- 공개 데모는 [Sites](https://pathology-edge-lab.ykh13571.chatgpt.site)에 배포했습니다.
- 브라우저 클릭·화면 캡처는 지원 도구 부재로 미검증입니다. UI 테스트 계획을 [REVIEW](docs/REVIEW.md)에 제공합니다.
- macOS 11.7.11에서의 사용자 실행은 아직 확인하지 않았습니다.
- GitHub Actions: [run 42364930156](https://github.com/sokldjs554/pathology-edge/actions/runs/42364930156) 성공. 소스 commit `0a9c24c`의 설치·C++ 빌드·pytest·JS 구문·데모 파일 검사를 실행했습니다. 이후 CI 기록만 추가한 문서 커밋은 재실행하지 않았습니다.

[![CPU checks](https://github.com/sokldjs554/pathology-edge/actions/workflows/ci.yml/badge.svg)](https://github.com/sokldjs554/pathology-edge/actions/workflows/ci.yml)

```bash
# 저장소 루트, 개발 환경 설치 후: 제공 모델의 실제 추론
python -m pathology_edge.cli infer --image dist/assets/10_1.png --backend cpp --threads 4
# 저장소 루트: 일반 테스트 (사용자 과제는 명시적 skip)
python -m pytest -q
# 저장소 루트: 사전 계산 결과를 로컬 웹에서 검토
python -m http.server 8000 --directory dist --bind 127.0.0.1
```

상세한 환경·데이터·학습·평가·Docker 명령은 [RUNBOOK](docs/RUNBOOK.md)에 있습니다.
무료 CPU만 사용했으며 유료 API, 외부 사전학습 모델, 의료 영상 업로드 기능은 사용하지 않았습니다.

## 사용자와 Codex의 역할

지금 사용자가 직접 작성할 부분은 `src/pathology_edge/learner_coordinates.py`의
`local_to_level0` 하나입니다. [1단계 요구사항·macOS 테스트](docs/STEP_01.md)에 따라
코드와 실제 테스트 출력을 보내면 검토한 뒤 다음 단계로 진행합니다. 정답 코드는 비워 두었습니다.

그 결과에 의존하지 않는 모델·기반 코드·데모·검증은 Codex가 수행했습니다.
[기여 기록](docs/CONTRIBUTIONS.md)은 코드 작성 / 테스트·화면 확인 / 검토·결정 / Codex 작업을
구분합니다. 사용자가 실제로 수행한 근거를 받기 전에는 사용자 항목을 완료로 바꾸지 않습니다.
[후속 후보](docs/NEXT_STEPS.md)는 현재 과제가 아닙니다.

## 남은 한계

실제 WSI·MPP 보존 실험, Ki-67 양성/음성·종양 분류, ViT/사전학습 비교, 다중 seed·신뢰구간,
외부 데이터·병리 전문가·임상 검증은 미수행입니다. 일반 배율 좌표 함수는 사용자 작성 대기입니다.
단순 핵 foreground만으로 임상 세포 수를 정할 수 없고, 두 테스트 그룹의 성능 차이가 큽니다.
현재 test를 보며 모델을 다시 선택하면 새 평가 설계가 필요합니다.

데이터·모델·의존성 출처와 조건은 [THIRD_PARTY.md](THIRD_PARTY.md)에 있습니다.
TNBC 예제의 CC BY 4.0을 유지하며, 자체 코드의 일괄 오픈소스 라이선스는 사용자 결정 전이라 선언하지 않았습니다.
