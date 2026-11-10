# 37단계: 사용자 soft Dice를 포함한 비교군 학습

상태: **사용자 실행 예정**. 첫 실행의 결과 보고는 받았지만 실제 Run 경로와 `loss_mode` 출력은 아직 받지 않았습니다. 아래 명령은 저장된 경로를 읽고 **BCE-only 설정과 사용자 함수 보관본을 검사한 뒤에만** 두 번째 학습을 시작합니다. 검사에 실패하면 오류를 보내 주세요. 첫 비교군을 다시 학습하지 않습니다.

## 이번 한 작업

같은 Codespaces에서 `learner_dice`를 한 번 실행합니다. 이는 **BCE + 사용자가 작성한 soft Dice**입니다. `baseline`을 실행하는 것이 아닙니다. 첫 비교군과 데이터·모델·seed 20261107·16 epochs·20 steps·검증 선택 규칙을 유지하며, 코드·패키지·컨테이너 설정을 바꾸지 않습니다. `git pull`이나 재설치 없이 현재 작성한 파일을 보존합니다.

사용자가 제출한 첫 실행의 선택 결과는 epoch 12, threshold 0.5, validation Dice **0.5211708103759707**, 95.53081978800037초, 29,761 parameters, train 33/validation 10장입니다. 보고서의 모델 SHA는 `b200555e5e8e3a1552e815fc731aacad6809df53ee46552d4d41ed1c915923ce`입니다. 이 해시는 보고서 필드이며 Codex가 사용자 모델 파일을 직접 읽어 재계산한 값은 아닙니다. [보고 구분](../artifacts/learning/step36-review.json).

## 실행 명령

**위치:** Codespaces Bash 터미널, 저장소 루트 `/workspaces/pathology-edge`.

```bash
set -o pipefail
cd /workspaces/pathology-edge &&
BCE_RUN_DIR="$(cat work/step36-bce-run-path.txt)" &&
python -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p.get("loss_mode")=="bce_only" and p["loss"]=="BCE only", "BCE-only 설정이 아닙니다"; print("BCE-only 설정 확인")' "$BCE_RUN_DIR/protocol.json" &&
cmp src/pathology_edge/learner_losses.py "$BCE_RUN_DIR/learner-loss-source.py" &&
DICE_RUN_DIR="$(mktemp -d "$PWD/work/my-learner-dice.XXXXXX")" &&
printf '%s\n' "$DICE_RUN_DIR" > work/step37-dice-run-path.txt &&
git rev-parse HEAD > "$DICE_RUN_DIR/source-commit.txt" &&
git status --short > "$DICE_RUN_DIR/source-status.txt" &&
git diff HEAD -- src/pathology_edge > "$DICE_RUN_DIR/source.diff" &&
cp src/pathology_edge/learner_losses.py "$DICE_RUN_DIR/learner-loss-source.py" &&
python -u -m pathology_edge.cli train \
  --data data --output "$DICE_RUN_DIR" \
  --seed 20261107 --epochs 16 --steps 20 --loss learner_dice \
  2>&1 | tee "$DICE_RUN_DIR/train.log" &&
python -c 'import json,sys; from pathlib import Path; keys=("best_epoch","threshold","best_validation_dice","seconds","model_sha256"); [print(json.dumps({"run":d,"loss_mode":r["config"]["loss_mode"],**{k:r[k] for k in keys}})) for d in sys.argv[1:] for r in [json.loads((Path(d)/"training.json").read_text())]]' "$BCE_RUN_DIR" "$DICE_RUN_DIR"
```

마지막 **JSON 두 줄 전체**를 보내 주세요. 각 줄에 실행 경로·손실 모드·선택 결과·시간·보고서 해시가 함께 출력됩니다. 첫 실행의 빠진 경로와 손실 정보도 이때 확인합니다. 코드 보관본 차이로 `cmp`가 실패하면 덮어쓰지 말고 출력을 보냅니다. 경로 파일이 없으면 추측한 폴더로 진행하지 말고 오류를 보냅니다.

새 실행 경로는 `work/step37-dice-run-path.txt`에 남습니다. 터미널이 초기화돼도 학습을 반복하지 않고 이 파일을 읽습니다. 기존 공개 모델과 첫 비교군은 덮어쓰지 않습니다.

## 검토와 역할

- 사용자 U48: 첫 실행의 선택 결과·환경 보고 확인. 실제 경로·손실 설정·전체 history·모델 파일 해시 재계산은 아직 확인되지 않았습니다.
- 사용자 U49: 이번 두 번째 학습과 출력 제출은 예정입니다. 명령 안내만으로 완료로 바꾸지 않습니다.
- Codex: 명령·기록 준비, 제출 결과 대조. 실제 사용자 Codespace에는 직접 접근하지 않습니다.

두 결과가 모이면 저장된 protocol에서 손실 외 설정, manifest, 실행 환경, 소스 기록을 대조합니다. 34단계의 이전 baseline이나 Codex 호스트 점수를 새 비교군으로 대신하지 않습니다. 검증 데이터는 epoch·threshold 선택에 사용했으므로 이 비교도 탐색적 검증 결과입니다. 한 seed의 변화로 test 개선·일반화·통계적 유의성·임상 효과를 주장하지 않습니다. 단일 학습 소요 시간 차이만으로 속도 개선을 단정하지 않습니다.

[첫 실행 안내](STEP_36.md) · [기여 기록](CONTRIBUTIONS.md)
