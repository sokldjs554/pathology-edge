# 실행 안내 — 필요할 때 참고

이 문서는 이후 재현을 위한 참고자료입니다. 아래 전체를 한 번에 수행하는 과제가 아닙니다.
1·2단계 코드·실행 보고,3단계 해석,4단계 Dice 구현·20개 통과 보고,5단계 실제 검산,6~8단계 해석,9단계 그룹 함수·18개 통과 보고,10단계 그룹 검사,11단계 파일 중복 구분,12단계 저장 해시,13단계 국소 점수·같은 위치,14단계 드래그,15단계 스크롤 보고를 확인했습니다. 16단계의 강조 표시 전환도 사용자 확인을 받았습니다. 17단계의 개선 사례 전환·같은 위치·국소 점수도 사용자 보고로 확인했습니다. 18단계의 변경 픽셀 수와 핵 개수 구분 설명도 확인했습니다. 19단계의 시간 집계·측정 범위 설명도 확인했습니다. 20단계의 실제 병합 후보 이동·번호 표시도 사용자 확인을 받았습니다. 21단계의 NMS 대응과 실제 핵 정답 구분 설명도 확인했습니다. 22단계의 WSI R1 이동·양쪽 같은 조직 위치도 사용자 확인을 받았습니다. 23단계의 같은 경계 위치·추가/제거 표시도 사용자 확인을 받았습니다. 24단계의 WSI 예측 변화 해석도 안내 후 확인했습니다. 25단계의 WSI 후보 쌍·원 패치 ID 표시도 사용자 확인을 받았습니다. 26단계의 WSI 이동 요청에 통합 정상 보고를 받았습니다. 27단계의 WSI 탐색·ROI 분석·TNBC 정답 검증 범위 구분 설명도 확인했습니다. 28단계에서 IHC 두 분류 표시 보고를 받았습니다. 29단계의 IHC 입력 조건은 Codex 보완 설명 후 사용자 수정 답변으로 확인했습니다. 30단계의 첫 사례 종양·비종양 오류 해석도 확인했습니다. 31단계의 분자·분모 각각 1 감소 해석도 확인했습니다. 32단계의 주석 세포 양성률과 전체 WSI·임상 검증 범위 구분도 확인했습니다. [STEP_33](STEP_33.md)의 보정되지 않은 예측 점수 해석까지 확인했습니다. 배정한 IHC 해석 질문과 [34단계 Codespaces 학습 실행·저장·설정 대조](STEP_34.md)를 마쳤습니다. 모델 선택 해석과 [35단계 soft Dice 함수 작성·계약 테스트](STEP_35.md)를 확인했습니다. 36·37단계 두 학습의 경로·모드·결과 보고를 받았습니다. 38단계의 12개 true 검사 출력도 받았습니다. 39단계 비교 설명도 확인했으며 40단계 사용자 코드·테스트 보고와 Codex 검토를 완료했습니다. 41단계 해석과 42단계 사용자 반복 실행·감사 성공 보고를 확인했으며 43단계 면접 작성은 사용자 요청으로 보류했고 44단계 환경 보고를 받아 현재 과제는 [45단계 Ubuntu 재현 검사](STEP_45.md)입니다. 미확인 항목과 후속 후보는 [검토 현황](NEXT_STEPS.md)에 구분했습니다.
사용자 실행 완료는 로그를 받은 뒤에만 기록합니다. 모든 명령은 별도 표시가 없으면
**`pathology-edge` 저장소 루트**에서 실행합니다.

## 1. 환경 확인

Codespaces 환경 준비·학습 재현은 [34단계](STEP_34.md)에서 완료했습니다. 35단계 사용자 함수 검토를 마쳤고 두 비교군 결과와 38단계 저장 조건·파일 검사 보고를 받아 39단계 해석까지 확인해 현재는 [40단계](STEP_40.md)의 연결 함수를 준비했습니다. 갱신 전 사용자 저장소는 `790a336`에서 loss 파일 한 개가 수정된 상태였습니다. 이후 백업·복원 절차의 실습 파일 갱신·원본 보존 성공 보고를 받았습니다. 이후 사용자 본문을 그대로 반영해 Codex 독립 계약 8개·전체 175개와 실제 WSI 좌표를 검증했습니다. 41단계 해석까지 마쳤으며 42단계 반복 학습 실행 보고도 받았습니다. 43단계 면접 작성을 보류했고 44단계 환경 보고를 확인했습니다. 현재는 45단계에서 기존 설치 패키지로 별도 고정 소스의 C++ 빌드·전체 테스트·저장 결과를 검증합니다. 저장소의 `.devcontainer/`가 Ubuntu 24.04·Python 3.12·CPU 패키지를 설치하고, 작업 폴더가 마운트된 뒤 editable 설치합니다. Codespaces에서는 아래 로컬 Ubuntu 설치 명령을 반복할 필요가 없습니다. 데이터 다운로드·학습·서버 실행은 자동으로 시작하지 않습니다.

macOS 11.7.11의 첫 과제는 [STEP_01.md](STEP_01.md)의 NumPy·pytest 환경이면 충분합니다.
전체 모델 실행은 검증된 Ubuntu 24.04 환경을 권장합니다. macOS 11에는 최신 PyTorch/Docker
Desktop 지원을 보장하지 않습니다. 이미 가진 Ubuntu 환경, 호환되는 가상머신 또는 원격 Ubuntu를
사용할 수 있습니다. 유료 GPU·외부 API는 필요 없습니다.

```bash
pwd
python3 --version
git --version
g++ --version
uname -m
cat /etc/os-release
docker --version
docker info
```

`pwd`는 저장소 루트인지, Python은 3.12인지, g++는 C++17 지원인지 확인합니다.
마지막 네 항목 중 OS 파일은 Ubuntu에서만 실행하고 Docker는 Docker 경로를 사용할 때만 확인합니다.
GPU 확인은 선택 사항이며 이 프로젝트는 CPU로 실행했습니다.

## 2. Ubuntu 개발 환경 설치

아직 프로그램이 없다면 Ubuntu에서 시스템 패키지를 설치합니다.

```bash
sudo apt-get update
sudo apt-get install python3 python3-venv python3-dev g++ git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-lock.txt
CC=gcc CXX=g++ python -m pip install --no-build-isolation --no-deps -e .
python -c "import torch, cv2; from pathology_edge import _patch_cpp; print(torch.__version__, cv2.__version__)"
```

마지막 명령이 Python·OpenCV·C++ 바인딩이 함께 로드되는지 확인합니다.
`requirements-lock.txt`는 실제 Linux CPU 실행 버전입니다. macOS 전용 lock이 아닙니다.
`clang++`가 없다는 오류가 나면 Ubuntu에서는 위 `CC=gcc CXX=g++` 지정이 필요합니다.

## 3. 데이터 준비

```bash
python -m pathology_edge.cli prepare
```

공식 Zenodo v1.1 ZIP 약 25.2MB를 `data/`에 받고 MD5를 확인합니다.
원본 경로 탈출 방지, 이미지·마스크 쌍, 라벨값, 케이스 분리와 중복 hash를 검사한 뒤
`data/manifest.json`을 만듭니다. `data/`는 Git에 업로드하지 않습니다.
재실행은 동일 ZIP을 재사용합니다. 다운로드가 중단되어 checksum 오류가 나면 해당 ZIP만
다른 이름으로 옮긴 뒤 다시 실행하고 원본 오류 로그를 보관하세요.

## 4. 제공 모델로 실제 추론

```bash
python -m pathology_edge.cli infer --image dist/assets/10_1.png --mode no_overlap --prediction-dir work/infer-before
python -m pathology_edge.cli infer --image dist/assets/10_1.png --mode overlap --backend cpp --threads 4 --prediction-dir work/infer-after
```

첫 명령은 무겹침 Python 추출, 둘째는 겹침 C++ 4 thread 추출을 사용합니다.
모델 자체의 CPU 스레드는 4개로 고정되어 있으므로 `--threads`와 구분합니다.
각 폴더의 `mask.png`, `probability.npy`, `result.json`에서 좌표·후보 수·시간을 확인하세요.
모델 SHA-256이 맞지 않으면 실행을 중단합니다. GPU나 API 키가 필요 없습니다.

## 5. 학습·평가 재현

제공된 최종 테스트 결과를 덮어쓰지 않도록 새 실험 폴더를 사용합니다.

```bash
python -m pathology_edge.cli train --output work/reproduction --seed 20261107 --epochs 16 --steps 20
python -m pathology_edge.cli evaluate --output work/reproduction
python -m pathology_edge.cli export --output work/reproduction --dest work/reproduced-demo
```

`train`은 학습/validation만 읽어 최적 epoch·threshold를 선택합니다. `evaluate`는
모델·manifest hash를 확인하고 고정된 설정으로 test를 평가합니다. 이미 평가 결과가 있으면
그 결과를 반환하며 새로 선택하지 않습니다. 기존 evaluation이 있는 폴더에 재학습은 금지합니다.
`export`는 실제 결과 JSON·오버레이만 내보냅니다. 세 번째 명령의 별도 폴더에는 앱 소스가 없으므로,
데모로 보려면 `dist/index.html`, `style.css`, `app.js`를 그 폴더에 복사하세요.
하드웨어별 시간과 작은 수치 차이는 가능합니다. 재현 결과는 제공된 결과와 별도로 기록합니다.

## 6. 테스트

```bash
python -m pytest --run-learner tests/learner/test_group_leaks.py -q
python -m pytest -q
python -m pytest --run-learner -q
python scripts/verify_cpp_real.py
python scripts/validate_demo.py
python scripts/benchmark.py
```

순서대로 사용자 과제만 / 구현된 전체 기능 / 사용자 과제 포함 전체 / 실제 이미지 C++ 일치 /
데모 파일 연결 / 추출 속도·메모리를 확인합니다. **검토 완료한 좌표 함수의 12개 테스트는 이제 전체 기본 테스트에도 포함됩니다.**
완료한 좌표·NMS 반례·Dice·그룹 테스트는 기본 검사에 포함됩니다. 9단계 검토 후 기본 검사는 **107개 통과·0개 skip**입니다. 그룹의18개도 `--run-learner` 없이 실행할 수 있습니다.
`verify_cpp_real.py`에는 준비한 원 데이터가 필요합니다. benchmark는 합성 RGB를 사용하며
의학적 성능 근거로 쓰지 않습니다. 다른 무거운 작업을 끈 상태에서 실행하세요.

## 7. 로컬 데모

```bash
python -m http.server 8000 --directory dist --bind 127.0.0.1
```

루트에서 실행한 뒤 브라우저로 `http://127.0.0.1:8000`을 엽니다.
이 서버는 저장된 실제 모델 결과를 제공하며 추론 서버가 아닙니다. 외부 사용자 업로드도 없습니다.
종료는 Terminal에서 Ctrl-C입니다. 클릭 점검 항목은 [REVIEW.md](REVIEW.md)에 있습니다.

새 WSI는 `http://127.0.0.1:8000/wsi.html`, IHC는 `/ihc.html`입니다. WSI 전체 확대 타일도 저장소의 `dist/wsi/slide_files/`에서 제공하므로 이 정적 서버만으로 탐색할 수 있습니다. ROI 밖의 영상 탐색은 모델 추론이 아닙니다.

## 추가 WSI / IHC 재현 참고

아래는 이후 WSI 재현용입니다. 현재 사용자 과제는 [45단계](STEP_45.md)의 별도 소스 재현 검사이며 WSI 재실행은 아직 배정하지 않았습니다. 전체 프로젝트 설치는 Python 3.11 이상, 실제 검증 환경은 Ubuntu/Python3.12입니다. 경량 실습의 Python3.10 이상 조건과 구분합니다.

저장소 루트에서, WSI 원본 읽기 기능을 설치하고 원본을 별도 `work/`에 내려받습니다. 약132.6MB이며 CC0입니다.

```bash
python -m pip install 'openslide-python==1.4.7' 'openslide-bin==4.0.1.2'
mkdir -p work/wsi
curl -fL 'https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1-JP2K-33005.svs' -o work/wsi/CMU-1-JP2K-33005.svs
sha256sum work/wsi/CMU-1-JP2K-33005.svs
PYTHONPATH=src python -m pathology_edge.wsi_export --slide work/wsi/CMU-1-JP2K-33005.svs --output-dist work/wsi-reproduced --artifacts work/wsi-run
python scripts/export_wsi_tiles.py --slide work/wsi/CMU-1-JP2K-33005.svs --output-dir work/wsi-reproduced/wsi/slide_files --report work/wsi-run/local-tiles.json --dist-json work/wsi-reproduced/wsi.json --experiment-json work/wsi-run/experiment.json --public-provenance work/wsi-reproduced/wsi/provenance.json
python -m pytest tests/test_wsi_export.py tests/test_ihc_baseline.py -q
```

SHA는 `9a1923cd9bcb260ba4d99d64f8d6e32550648c332ba48817f920662f3a513420`여야 합니다. export는 세1024px ROI에 고정 모델을 실행하며 전체 WSI를 분석하지 않습니다. 기존 결과를 덮어쓰지 않는 출력 경로를 지정했습니다. 마지막 명령은 WSI 좌표·후보 출처·실제 mask와 IHC split/metric/model 검사를 실행합니다. 새 WSI 다운로드 없이도 체크인된 산출물의 검사 자체는 가능합니다.

두 번째 export는 분석을 실행하지 않고 전체 WSI를 2,071개의 JPEG 타일로 변환합니다. 출력 약133MiB와 생성 중 메모리 약944MiB가 별도로 필요했습니다. 일반 `wsi_export` 뒤에 이 명령을 실행해야 타일 출처가 자체 정적 파일로 바뀝니다. macOS의 SHA 확인은 `sha256sum` 대신 `shasum -a 256`을 사용합니다.

IHC의 pinned ZIP 준비·실행 명령은 [IHC_EXPERIMENT](IHC_EXPERIMENT.md)에 있습니다. 데이터의 비상업적 이용 조건을 유지하며, 저자 fold1 test를 모델 선택에 사용하지 않습니다. test 결과를 보며 재튜닝한 결과는 같은 고정 test 평가로 보고하지 마세요.

## 8. Docker / Ubuntu 24.04

```bash
docker build -t pathology-edge:research .
docker run --rm pathology-edge:research cat /etc/os-release
docker run --rm pathology-edge:research python -m pytest -q
docker run --rm -p 127.0.0.1:8000:8000 pathology-edge:research
```

Ubuntu 기반 이미지의 빌드, 실제 OS, 전체 기능 테스트, 데모 서버를 확인하는 명령입니다.
추론도 다음처럼 실행할 수 있습니다. 컨테이너가 사라지기 전에 결과 보관이 필요하면
호스트의 `work/`를 `/app/work`로 마운트하세요.

```bash
docker run --rm pathology-edge:research python -m pathology_edge.cli infer --image dist/assets/10_1.png --backend cpp --threads 4
```

기관/실행환경의 인증서 프록시가 있을 때만 신뢰하는 CA bundle을 build secret으로 전달합니다.
TLS 검증을 끄지 않습니다. CA는 결과 이미지에 복사되지 않습니다.

```bash
docker build --secret id=build_ca,src=/etc/ssl/certs/ca-certificates.crt -t pathology-edge:research .
```

## 실패·불일치 때 보내주실 정보

- 작업한 커밋: `git rev-parse HEAD`, 수정 파일: `git diff --stat`
- 실행 폴더: `pwd`, 실행한 명령 전체, 종료 코드, 생략하지 않은 traceback
- OS/아키텍처, `python --version`, 주요 패키지 버전
- 이미지 ID, model SHA-256, 실행 방식·threshold·backend·스레드 수
- UI 문제라면 화면 크기, 브라우저 버전, 선택 이미지·버튼 순서, 표시된 숫자 또는 캡처

개인 의료 영상, 토큰, 계정 비밀번호는 포함하지 마세요. 실행하지 못한 단계는 미실행이라고 적어 주세요.

## 최신 Docker 검증 범위

반복 실험 테스트가 실제 checkout의 `.git`에 의존하던 문제를 수정해 소스 아카이브에서 관련 16개 테스트, 호스트에서 전체 191개 테스트를 통과했습니다. Git fixture 실행을 위해 루트 Dockerfile에 `git`도 추가했습니다. 이번 새 Docker 이미지 빌드와 기존 Ubuntu 이미지 내 소스 복사는 호스트 저장 공간 부족으로 완료하지 못했으며, 컨테이너 테스트 성공으로 기록하지 않습니다. 과거 Docker 검증과 이번 변경의 검증을 구분합니다. [근거·제한](../artifacts/learning/step43-docker-preparation.json). 43단계 면접 작성은 보류했으며 44단계에서 Docker 실행 파일 없음·Git 상태·공간 보고를 받아 현재는 [45단계 Ubuntu 재현 검사](STEP_45.md) 하나를 안내합니다. Docker 검증은 미완료로 남깁니다.
