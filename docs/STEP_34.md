# 34단계: Codespaces에서 TinyUNet 학습 직접 재현

상태: **사용자 epoch 14~16 학습 로그 확인, 저장 결과·재현 차이 검토 대기**. Ubuntu 24.04.5 LTS·패키지 환경·데이터 50쌍 준비에 이어 마지막 epoch 로그를 받았습니다. epoch 16의 threshold 0.5 검증 Dice는 사용자 0.5012017684535199, 기준 실행 0.5051041697403853으로 다릅니다. 원인은 아직 확인하지 않았습니다. 사용자가 학습을 실행해 epoch 16까지 도달한 사실과, 최종 파일 저장·선택 모델·정확한 재현 여부를 구분합니다. 전체 테스트 실행도 미확인입니다. [사용자 보고 검토 기록](../artifacts/learning/step34-review.json)

이번 단계의 목표는 기존 모델을 같은 조건으로 직접 학습하고 로그를 확인하는 것입니다. 모델·손실 코드를 바꾸는 비교 실험은 이 결과를 검토한 뒤 진행합니다.

## 역할과 범위

| 담당 | 이번에 할 일 | 기록 기준 |
|---|---|---|
| 사용자 | Codespace 생성, 환경 확인, 데이터 준비, 기존 학습 명령 실행, 결과 제출 | 실제 출력과 보고를 받은 뒤에만 실행 완료 |
| Codex | Ubuntu/Python 설정, 재현 명령·보관 경로 준비, 별도 컨테이너 검증, 제출 결과 검토 | Codex 로그를 사용자 실행으로 기록하지 않음 |

이번에 직접 작성할 모델 코드는 없습니다. 기존 [model.py](../src/pathology_edge/model.py)의 `TinyUNet`·`loss_fn`과 [experiment.py](../src/pathology_edge/experiment.py)의 `train`은 Codex 구현입니다. 이번 기여는 **학습 재현·결과 검토**이며, 새 모델 구현 기여로 바꾸지 않습니다.

## 초기 설정 참고: Codespace 생성과 환경 확인

아래는 처음 환경을 만드는 절차입니다. 현재 사용자는 학습 로그까지 제출했으므로 새 Codespace 생성·설치·학습을 반복하지 않고 **저장 결과를 확인**합니다.

1. [저장소](https://github.com/sokldjs554/pathology-edge)의 `main`에서 **Code → Codespaces → Create codespace on main**을 누릅니다. 기본 2-core급 CPU 환경으로 시작할 수 있으며 GPU는 필요 없습니다.
2. 개발 컨테이너 빌드와 `postCreateCommand` 설치가 끝날 때까지 기다립니다. 새 설정은 Ubuntu 24.04/Python 3.12이며 모델 학습은 자동 실행하지 않습니다.
3. 기존 Codespace를 재사용한다면 작업을 보존한 상태에서 최신 커밋을 받은 뒤 명령 팔레트의 **Codespaces: Rebuild Container**로 설정을 적용합니다. 설치 실패/복구 모드라면 설치 로그부터 확인합니다.
4. Codespaces 터미널의 **저장소 루트 `/workspaces/pathology-edge`**에서 아래 확인만 먼저 실행하고 출력을 보내 주세요. 파일을 수정하거나 학습하지 않습니다.

```bash
cd /workspaces/pathology-edge
python - <<'PY'
import platform, sys
from pathlib import Path
import torch, cv2, pathology_edge
from pathology_edge import _patch_cpp

print(next(line for line in Path('/etc/os-release').read_text().splitlines()
           if line.startswith('PRETTY_NAME=')))
print('Python:', sys.version.split()[0], 'executable:', sys.executable)
print('Architecture:', platform.machine())
print('PyTorch:', torch.__version__, 'OpenCV:', cv2.__version__)
print('Source:', Path(pathology_edge.__file__).resolve())
print('C++ import: OK')
PY
git status --short --branch
```

예상 조건은 Ubuntu 24.04, Python 3.12.x, CPU PyTorch, `/opt/venv/bin/python`, `/workspaces/pathology-edge/src/pathology_edge/` 소스 경로, `C++ import: OK`입니다. 출력이 다르면 설치를 반복하기 전에 그 출력을 검토합니다. 이전 Mac 실습용 가상환경은 Codespaces에 복사하지 않습니다.

## 데이터 준비와 이후 학습 순서 — 한 번에 한 작업씩

아래 명령은 모두 **Codespaces 저장소 루트**에서 실행합니다. 현재는 마지막 epoch 로그를 받았으므로 아래 결과 요약만 실행합니다. 기준 수치를 맞추려고 다시 학습하거나 조건을 바꾸지 않습니다.

### 완료한 데이터 준비 명령 — 재설치 시 참고

```bash
cd /workspaces/pathology-edge
python -c "from pathlib import Path; print(next(x for x in Path('/etc/os-release').read_text().splitlines() if x.startswith('PRETTY_NAME=')))"
python -m pathology_edge.cli prepare
```

첫 Python 명령은 이전 제출에서 빠진 운영체제 이름을 출력합니다. `prepare`는 TNBC v1.1 ZIP을 받아 체크섬·이미지/마스크·분리 기록을 검사합니다. 출력은 `images: 50`, `manifest: data/manifest.json`이어야 합니다. 기존 분할은 train 33장, validation 10장, test 7장입니다. 데이터 준비 자체는 모델 학습이나 평가가 아닙니다.

### 실행한 학습 명령 — 기록 참고

다음은 **Bash 터미널**에서 한 블록으로 실행합니다. 실행마다 새 디렉터리를 만들므로 기존 `artifacts/` 모델과 공개 결과를 덮어쓰지 않습니다. `&&`는 폴더 생성·소스 상태 기록이 실패하면 학습을 시작하지 않게 하고, `pipefail`은 학습 오류를 `tee`의 성공으로 가리지 않게 합니다.

```bash
set -o pipefail
mkdir -p work &&
PATHOLOGY_RUN_DIR="$(mktemp -d "$PWD/work/my-tnbc-baseline.XXXXXX")" &&
export PATHOLOGY_RUN_DIR &&
printf 'Run: %s\n' "$PATHOLOGY_RUN_DIR" &&
git rev-parse HEAD > "$PATHOLOGY_RUN_DIR/source-commit.txt" &&
git status --short > "$PATHOLOGY_RUN_DIR/source-status.txt" &&
python -u -m pathology_edge.cli train \
  --data data \
  --output "$PATHOLOGY_RUN_DIR" \
  --seed 20261107 --epochs 16 --steps 20 \
  2>&1 | tee "$PATHOLOGY_RUN_DIR/train.log"
```

이 학습은 초기 가중치부터 시작해 train 33장으로 업데이트하고 validation 10장으로 epoch·threshold를 선택합니다. test 파일의 무결성은 검사하지만 test 성능을 계산하거나 모델 선택에 사용하지 않습니다. `evaluate`·`export` 명령은 이번 단계에 포함하지 않습니다.

Bash가 0이 아닌 종료 상태를 내거나 traceback이 보이면 성공으로 기록하지 않습니다. 재시도할 때도 위 블록 전체를 실행해 새 폴더를 만듭니다. 종료된 터미널에서 이어갈 때는 로그가 있는 실제 폴더를 `PATHOLOGY_RUN_DIR`에 지정해야 합니다.

### 지금 할 일: 같은 터미널에서 저장 결과 요약

이 명령은 기존 파일만 읽습니다. `Run:` 경로가 이전 보고에서 빠져 있으므로 경로도 함께 출력합니다. 환경 변수나 파일이 없으면 자동으로 다른 실행을 고르지 않고 오류를 확인합니다.

```bash
python - <<'PY'
import hashlib, json, os
from pathlib import Path

value = os.environ.get('PATHOLOGY_RUN_DIR')
if not value:
    raise SystemExit('PATHOLOGY_RUN_DIR이 없습니다. 학습 때 나온 Run: 경로를 보내 주세요.')
run = Path(value)
report = json.loads((run / 'training.json').read_text())
summary = {'run': str(run), 'completed_epochs': len(report['history'])}
for key in ('train_images', 'validation_images', 'best_epoch', 'threshold',
            'best_validation_dice', 'seconds', 'model_sha256', 'config', 'environment'):
    summary[key] = report[key]
for name in ('source-commit.txt', 'source-status.txt'):
    summary[name] = (run / name).read_text().strip()
summary['model_file_matches_report'] = (
    hashlib.sha256((run / 'model.pt').read_bytes()).hexdigest() == report['model_sha256']
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY
```

고정된 기존 결과의 참고값은 **16 epochs, best epoch 12, threshold 0.5, validation Dice 0.530508395092291**입니다. 이 값은 test 평균 Dice와 다릅니다. CPU·라이브러리 차이로 재현 값이나 시간에 차이가 날 수 있으며, 맞추려고 반복 튜닝하지 않고 차이와 환경을 함께 보고합니다.

`training.json`, `protocol.json`, `manifest.json`, `model.pt`, `train.log`, 두 소스 상태 파일을 해당 폴더에 보관합니다. 생성된 결과를 자동으로 Git에 올리지 않으며 기존 실험은 그대로 둡니다.

## 결과를 보낼 때

현재는 **위 저장 결과 요약의 출력 전체**를 보내 주세요. 마지막 epoch의 점수만으로 저장된 best epoch·threshold·모델 재현까지 완료로 판단하지 않습니다. 불일치 검토에 필요할 때 전체 학습 history를 추가로 확인합니다. 학습은 다시 실행하지 않습니다.

오류라면 실행한 명령, 실행 폴더, traceback 전체, 생성된 run 경로, 코드 수정 여부를 함께 알려 주세요. `No module named ...`는 설치/복구 모드부터 확인하며 임의로 패키지 버전을 바꾸지 않습니다.

## Codex 검증과 이후 단계

Codex가 Debian 호스트와 Ubuntu 24.04 컨테이너에서 각각 같은 seed·16 epoch 학습을 별도 폴더로 실행했습니다. 두 실행 모두 기존 학습 history·설정·모델 가중치 및 파일 SHA256이 일치했고, best epoch 12·threshold 0.5·validation Dice 0.530508395092291을 재현했습니다. 호스트와 컨테이너에서 기존 Python 테스트도 각각 **107개 통과**했습니다. 컨테이너의 실제 빌드·editable 설치·데이터 준비·실행 근거는 [준비 기록](../artifacts/learning/step34-preparation.json)에 있습니다.

이는 **Codex의 로컬 Docker 검증**입니다. 이후 사용자 환경·데이터 준비와 epoch 14~16 학습 로그 제출은 별도 기록했습니다. 사용자 실행의 마지막 점수는 기준과 달라 선택 모델·환경·설정을 추가로 확인 중입니다. Codex 실행을 사용자의 기여로 기록하지 않으며 사용자 전체 테스트·새 test 평가·공개 결과 변경도 없습니다.

학습 보고 검토 후에만 사용자가 직접 작성할 손실/증강 등 비교 실험 하나를 배정합니다. WSI 배율 연결과 반복·비교 모델 보강은 그다음 순서로 유지합니다.

[공고와 보완 순서](JOB_MATCH_2026-11-10.md) · [기여 기록](CONTRIBUTIONS.md) · [GitHub 개발 컨테이너 설명](https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/adding-a-dev-container-configuration/introduction-to-dev-containers)
