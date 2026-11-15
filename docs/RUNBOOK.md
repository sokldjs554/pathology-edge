# 실행 안내

목적에 맞는 경로 하나부터 시작하세요. **공개/로컬 화면은 저장 결과를 표시하고, CLI의 `infer`가 실제 모델을 실행합니다.** 아래 명령은 ‘처음 받기’를 제외하면 `pathology-edge` 저장소 루트에서 실행합니다.

| 목적 | 필요한 환경 | 결과 |
|---|---|---|
| 데모 체험 | 브라우저 | 저장된 예제 선택·확대·경계/후보 비교 |
| 로컬 화면 | Git, Python 3 | 같은 정적 작업대를 localhost에서 열기 |
| 검산·실제 추론 | Ubuntu 24.04/Python 3.12 또는 Codespaces 개발 환경 | 저장 점수 검산 또는 새 mask·확률맵·JSON |
| 학습부터 재현 | 위 환경 + TNBC 원자료 | 새 실험 폴더의 모델·선택 기록·test 결과 |
| Docker | 동작하는 Docker Engine | 고정 Linux 패키지를 사용하는 컨테이너 |

## 1. 설치 없이 데모 보기

[경계 비교](https://pathology-edge-lab.ykh13571.chatgpt.site/)에서 예제를 선택하고 ‘좋아진 경계 보기’·‘나빠진 경계 보기’를 누릅니다. 두 영상이 같은 위치로 이동하고 선택 영역의 설명이 표시됩니다. ‘중복 병합’에서는 억제 후보와 유지 후보의 출처를 봅니다.

[WSI](https://pathology-edge-lab.ykh13571.chatgpt.site/wsi.html)는 전체 슬라이드 탐색과 분석 ROI 3개, [IHC](https://pathology-edge-lab.ykh13571.chatgpt.site/ihc.html)는 정답 중심 조건의 분류 결과를 제공합니다. 새 추론·파일 업로드 기능을 제공하는 화면은 아닙니다.

<a id="local-viewer"></a>
## 2. 로컬 화면 열기

**처음 받기 — 상위 작업 폴더에서 실행:**

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/sokldjs554/pathology-edge.git pathology-edge
cd pathology-edge
git sparse-checkout set dist
```

현재 main의 화면용 파일과 WSI 타일을 받는 경량 checkout입니다. 이미 저장소가 있다면 새로 복제하지 않고 그 폴더로 이동하세요. 다음 명령은 **저장소 루트**에서 실행합니다.

```bash
python3 -m http.server 8000 --directory dist --bind 127.0.0.1
```

브라우저에서 `http://127.0.0.1:8000`을 열면 TNBC 예제 7개, `/wsi.html`에는 WSI, `/ihc.html`에는 IHC 화면이 보입니다. Python 모델 패키지 설치는 필요 없습니다. 종료는 터미널의 `Ctrl-C`입니다.

Codespaces에서는 다음 명령을 실행한 후 **Ports의 8000 → Open in Browser**를 사용합니다. 포트 공개 범위는 Private로 유지합니다.

```bash
python -m http.server 8000 --directory dist --bind 0.0.0.0
```

<a id="development"></a>
## 3. 검산·모델 실행용 개발 환경

화면만 열 때는 이 절차를 생략합니다. 프로젝트는 Python≥3.11을 선언하며, 고정 패키지와 실제 CPU 검증 환경은 **Ubuntu 24.04·Python 3.12**입니다. Linux용 lock을 macOS 11에 그대로 적용하는 경로는 검증하지 않았습니다. macOS 11에서는 정적 화면을 로컬로 열고 모델 실행은 Codespaces/Ubuntu를 이용할 수 있습니다.

### Codespaces

저장소의 **Code → Codespaces**에서 `main`을 선택해 환경을 만듭니다. `.devcontainer/`는 Ubuntu 24.04·Python 3.12·CPU 패키지와 C++ 확장을 준비하며 데이터 다운로드·학습·서버는 자동 시작하지 않습니다. 준비 완료 후 **Codespaces 저장소 루트**에서 설치를 확인합니다.

```bash
python --version
python -m pip check
python -c "import pathology_edge, torch, cv2; from pathology_edge import _patch_cpp; print(pathology_edge.__file__); print(torch.__version__, cv2.__version__); print('C++ import: OK')"
```

Python 3.12, 의존성 충돌 없음, 현재 저장소의 소스 경로와 `C++ import: OK`가 예상 결과입니다. Codespaces 자체를 쓸 때 내부에 Docker CLI가 없어도 이 실행 경로는 가능합니다.

### 로컬 Ubuntu 24.04

위 경량 checkout을 사용했다면 **저장소 루트**에서 먼저 전체 소스·모델·증거 파일을 받습니다. 이 단계는 큰 보관 ZIP도 내려받으므로 화면 전용 경로보다 공간이 더 필요합니다.

```bash
git sparse-checkout disable
```

일반 clone과 Codespaces에는 위 확장 명령이 필요 없습니다. **로컬 Ubuntu 저장소 루트**에서 다음을 실행합니다.

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-dev g++ git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-lock.txt
CC=gcc CXX=g++ python -m pip install --no-build-isolation --no-deps -e .
python -m pip check
python -c "import torch, cv2; from pathology_edge import _patch_cpp; print(torch.__version__, cv2.__version__); print('C++ import: OK')"
```

새 터미널에서는 루트로 이동해 `source .venv/bin/activate`를 다시 실행합니다. 모델 실행에 유료 API 키나 GPU는 필요 없습니다. 원본 WSI와 후속 연구의 모델·데이터는 해당 실험 문서의 별도 입력입니다.

### 저장 점수 먼저 검산하기

**개발 환경의 저장소 루트**에서 실행합니다. 체크인된 mask·정답·표시 결과를 읽으며 새 모델 추론이나 데이터 다운로드를 하지 않습니다.

```bash
python scripts/audit_dice.py --output work/dice-audit.json
```

예상 출력은 `42/42 Dice values and 6/6 image means match.` 및 `7 test images / 2 case groups; no inference run.`입니다. 자세한 근거는 `work/dice-audit.json`에 저장됩니다.

<a id="inference"></a>
## 4. 한 장에 실제 모델 추론하기

**개발 환경의 저장소 루트**에서 실행합니다. 입력은 제공된 512×512 TNBC `10_1` 이미지, 모델은 `artifacts/model.pt`입니다. 모델 SHA를 `artifacts/training.json`과 대조합니다. 두 명령 모두 Python 패치 추출을 사용해 무겹침/겹침만 바꿉니다.

```bash
python -m pathology_edge.cli infer --image dist/assets/10_1.png --mode no_overlap --prediction-dir work/quick-infer/no-overlap
python -m pathology_edge.cli infer --image dist/assets/10_1.png --mode overlap --prediction-dir work/quick-infer/overlap
```

각 출력 폴더에 `mask.png`(0/255 이진 영상), `probability.npy`(확률맵), `result.json`(후보·패치 좌표·시간·입력/모델 해시)이 생성됩니다. 터미널에는 `prediction_dir`, `objects`, `seconds`가 표시됩니다. 이 결과가 새 추론 결과이며 공개 데모의 저장 수치를 갱신하지는 않습니다. 다시 실행하면 같은 `work/quick-infer` 출력이 갱신됩니다.

C++ 추출을 확인하려면 동일 이미지·방식에 `--backend cpp --threads 2`를 추가하고 별도 출력 폴더를 지정합니다. `--threads`는 추출기의 스레드 수이며 모델의 CPU 스레드와 구분합니다. 처리 시간은 환경·동시 작업에 따라 달라집니다.

<a id="reproduction"></a>
## 5. TNBC 데이터·학습·평가 재현

**개발 환경의 저장소 루트**에서 원자료를 준비합니다.

```bash
python -m pathology_edge.cli prepare
```

공식 TNBC v1.1 ZIP 약25.2MB를 `data/`에 받고 checksum, 이미지/라벨 쌍·값·분리·중복 해시를 확인합니다. 예상 출력은 `{"images": 50, "manifest": "data/manifest.json"}`이며 분리는 train33/validation10/test7장입니다. 상세 그룹·출처는 manifest에 있습니다. 기존 정상 ZIP은 재사용합니다.

다음 **한 블록을 같은 터미널에서** 실행합니다. 새 폴더를 만들어 체크인된 `artifacts/`와 기존 학습 결과를 보존합니다. `Run:` 경로를 기록해 두세요.

```bash
mkdir -p work
PATHOLOGY_RUN_DIR="$(mktemp -d work/reproduction.XXXXXX)"
printf 'Run: %s\n' "$PATHOLOGY_RUN_DIR"
python -m pathology_edge.cli train --output "$PATHOLOGY_RUN_DIR" --seed 20261107 --epochs 16 --steps 20
python -m pathology_edge.cli evaluate --output "$PATHOLOGY_RUN_DIR"
python -m pathology_edge.cli export --output "$PATHOLOGY_RUN_DIR" --dest "$PATHOLOGY_RUN_DIR/export"
```

- `train`: train/validation으로 epoch·threshold를 선택하고 `model.pt`, `training.json`을 저장합니다. test는 선택에 쓰지 않습니다.
- `evaluate`: 선택된 모델과 manifest 해시를 확인한 뒤 test 결과를 `evaluation.json`, 방식별 예측 파일 등에 기록합니다. 같은 폴더의 기존 평가 결과는 재사용합니다.
- `export`: 해당 실행의 `export/results.json`과 `export/assets/`에 표시용 데이터·오버레이를 생성합니다. **대화형 앱 전체를 생성하는 명령은 아닙니다.** 현재 작업대에는 별도의 사례·출처·UI 파일도 필요하므로 HTML·CSS·JS 세 파일만 복사해 완성된 새 데모라고 취급하지 않습니다.

환경에 따라 선택 점수·시간이 달라질 수 있습니다. 새 결과에는 실제 코드 커밋·수정 파일·환경·모델 해시를 함께 남기고 기존 연구 결과와 구분합니다. 재사용한 test 결과로 모델을 다시 선택하면 새로운 미노출 평가가 아닙니다.

<a id="tests"></a>
## 6. 테스트와 결과 확인

**개발 환경의 저장소 루트**에서 실행합니다.

```bash
python -m pytest tests/learner -q
python -m pytest exercises/step57/test_local_refinement.py -q
python -m pytest -q
python scripts/validate_demo.py
```

순서대로 좌표·지표·분리·손실·ROI 연결의 실습 테스트, 직접 보정 head의 13개 계약 테스트, 현재 checkout 전체 테스트, 정적 데모의 실제 영상/결과·DOM 연결 검사입니다. 테스트 개수는 브랜치와 커밋에 따라 달라집니다. 완료된 실습의 기본 검사와 별도 `exercises/` 계약 검사를 구분하며, 과거 준비 단계의 skip 수와 혼동하지 않습니다.

`validate_demo.py`의 예상 출력은 `PASS: 7 real samples, 42 images/overlays...`입니다. 브라우저 확대·이동 검사를 대신하지 않습니다. [직접 화면 확인 항목](INTERVIEW_UI.md) · [브라우저 검증 재현](UI_VERIFICATION.md).

원 TNBC 데이터까지 준비했다면 `python scripts/verify_cpp_real.py`로 실제 영상의 Python/C++ 출력 일치를 확인할 수 있습니다. `python scripts/benchmark.py`는 합성 RGB의 추출 구간·메모리 측정이며 의학적 성능이나 전체 모델 추론 속도 측정이 아닙니다.

<a id="docker"></a>
## 7. Docker로 실행하기

**Docker Engine이 동작하는 저장소 루트**에서 실행합니다. 기존 Ubuntu/Codespaces 개발 환경과 선택 가능한 별도 경로입니다.

```bash
docker --version
docker info
docker build -t pathology-edge:research .
docker run --rm pathology-edge:research python -m pytest -q
docker run --rm -p 127.0.0.1:8000:8000 pathology-edge:research
```

마지막 명령 후 `http://127.0.0.1:8000`에서 정적 작업대를 확인합니다. 추론 파일을 호스트에 보관하려면 같은 루트에서 별도 터미널로 실행합니다.

```bash
mkdir -p work
docker run --rm -v "$PWD/work:/app/work" pathology-edge:research python -m pathology_edge.cli infer --image dist/assets/10_1.png --backend cpp --threads 2 --prediction-dir work/docker-infer
```

결과는 호스트의 `work/docker-infer/`에 남습니다. 기관 프록시 때문에 인증서가 필요한 경우에만 신뢰하는 CA를 `docker build --secret id=build_ca,src=/경로/ca-bundle.crt -t pathology-edge:research .`로 전달합니다. 과거 Docker 실행·실패·성공 범위는 [검증 이력](PROJECT_HISTORY.md#verification)에 있습니다.

## 8. WSI·IHC·후속 연구를 재현하려면

| 경로 | 입력과 범위 | 안내 |
|---|---|---|
| WSI ROI 예측·전체 탐색 타일 | 별도 원본 SVS·OpenSlide, ROI 3개의 예측과 전체 영상 타일 생성은 서로 다른 작업 | [WSI 실험](WSI_EXPERIMENT.md), [기존 상세 명령 원문](history/main-RUNBOOK-20261115.txt) |
| 정답 중심 조건 IHC | Patherea P1의 이미지·주석·고정 분할 | [IHC 실험](IHC_EXPERIMENT.md) |
| 자동 검출·최종 사전학습 비교 | research 브랜치의 코드·고정 실행 폴더·원자료·모델 | [최종 연구 실행/출처](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_FINAL_TRANSFER.md) |

후속 연구의 일부 경로는 원본 고정 실행 폴더를 전제로 합니다. 검토 ZIP만으로 모든 학습·외부 평가 입력이 설치되는 것은 아닙니다. 공개 데이터 이용 조건과 원본 해시를 확인하고 각 실험의 별도 출력 경로를 사용합니다.

## 9. 실행이 막혔을 때

| 증상 | 먼저 확인할 것 |
|---|---|
| `No module named pytest` / `pathology_edge` | 개발 환경의 Python인지 확인. Codespaces는 준비 완료 여부, 로컬은 `.venv` 활성화와 editable 설치 확인 |
| `scripts/`·모델 파일 없음 | 화면 전용 sparse checkout인지 확인하고 개발 환경 절차에서 확장 |
| `_patch_cpp` import 실패 | C++17 컴파일러 설치 후 `CC=gcc CXX=g++ python -m pip install --no-build-isolation --no-deps -e .` 재실행 |
| `docker: No such file or directory` | Docker 경로 대신 Codespaces/Ubuntu 절차 사용. 이 오류를 Docker 검증 완료로 기록하지 않음 |
| 모델 SHA/checksum 불일치 | 모델·메타데이터가 같은 커밋/실행인지 확인. 해시 검사를 끄거나 기존 결과를 덮어써 통과시키지 않음 |
| 화면이 안 열림 | 실행 루트·서버 포트 확인. Codespaces는 Ports에서 열기, 로컬은 `127.0.0.1:8000` 사용 |

문의할 때는 실행 폴더·명령 전체·traceback, `git rev-parse HEAD`, `git diff --stat`, OS·Python·패키지 버전, 모델/이미지 ID를 함께 남깁니다. 화면 문제에는 브라우저·화면 크기·선택 순서·캡처를 추가합니다. 토큰·비밀번호·개인 의료 영상은 제외합니다.
