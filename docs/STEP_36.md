# 36단계: BCE-only 비교군을 한 번 학습

상태: **사용자 선택 결과·환경 보고 확인, 실행 경로·손실 설정 확인 대기**. epoch 12·threshold 0.5·validation Dice 0.5211708103759707·95.53081978800037초·보고서 모델 SHA `b200555e…`를 받았습니다. 보고된 환경과 train 33/validation 10장은 앞선 Codespaces 보고와 같습니다. Run 경로·`loss_mode`·전체 history·파일 해시 재계산은 아직 확인되지 않았습니다. [보고 근거](../artifacts/learning/step36-review.json).

다음은 [37단계](STEP_37.md)의 저장된 BCE-only 설정·사용자 코드 보관본 검사 후 두 번째 학습입니다. 아래 최초 실행 명령은 참고용이며 첫 비교군을 반복 실행하지 않습니다.

## 비교할 내용

| 고정할 것 | 값 |
|---|---|
| 데이터 | 동일한 TNBC train 33장 / validation 10장과 manifest |
| 모델 | TinyUNet, 29,761 parameters |
| seed / epochs / steps | 20261107 / 16 / 20 |
| 학습 설정 | batch 8, crop 128, Adam 0.001, 기존 회전·반전 |
| 모델 선택 | 검증 이미지 평균 Dice의 최고 epoch·threshold, 후보 0.35/0.5/0.65 |
| 첫 비교군 | `bce_only`: BCE만 사용 |
| 다음 비교군 | `learner_dice`: BCE + 사용자가 작성한 soft Dice |

가설은 “Dice 항을 더했을 때 검증 결과가 어떻게 달라지는가”입니다. 개선을 보장하지 않으며, 같은 Codespaces의 두 결과를 비교합니다. 기존 Codex 호스트 점수나 34단계 다른 시점 실행만을 두 번째 비교군으로 대신하지 않습니다. 기존 test 7장은 이미 열람했으므로 새 모델 선택·반복 튜닝에 사용하지 않고 새 test 성능도 보고하지 않습니다.

## 최초 실행 명령 — 결과 보고 후 반복하지 않음

작성한 Codespaces 파일을 그대로 보존합니다. `bce_only` 모드는 35단계 준비 커밋부터 있어 이번 실행을 위해 `git pull`이나 파일 초기화가 필요하지 않습니다. 두 비교군 실행 사이에는 코드·패키지·컨테이너 설정을 바꾸지 않습니다. 실제 환경은 각 보고서에서 다시 대조합니다.

**실행 위치:** Codespaces의 저장소 루트 `/workspaces/pathology-edge`, Bash 터미널.

```bash
set -o pipefail
cd /workspaces/pathology-edge &&
mkdir -p work &&
BCE_RUN_DIR="$(mktemp -d "$PWD/work/my-bce-only.XXXXXX")" &&
printf '%s\n' "$BCE_RUN_DIR" > work/step36-bce-run-path.txt &&
git rev-parse HEAD > "$BCE_RUN_DIR/source-commit.txt" &&
git status --short > "$BCE_RUN_DIR/source-status.txt" &&
git diff HEAD -- src/pathology_edge > "$BCE_RUN_DIR/source.diff" &&
cp src/pathology_edge/learner_losses.py "$BCE_RUN_DIR/learner-loss-source.py" &&
python -u -m pathology_edge.cli train \
  --data data --output "$BCE_RUN_DIR" \
  --seed 20261107 --epochs 16 --steps 20 --loss bce_only \
  2>&1 | tee "$BCE_RUN_DIR/train.log" &&
printf 'Run: %s\n' "$BCE_RUN_DIR" &&
sed -n '/"best_epoch"/,$p' "$BCE_RUN_DIR/training.json"
```

새 폴더에 학습 결과와 로그를 저장하고, 실행 당시 커밋·미커밋 소스 차이·사용자 함수 파일도 함께 보관합니다. 기존 공개 모델과 `my-tnbc-baseline.nD5R9k`를 덮어쓰지 않습니다. 폴더·기록 저장이나 학습이 실패하면 `&&`와 `pipefail`로 이후 성공 요약을 출력하지 않습니다.

**제출할 것:** 명령 끝의 `Run:` 경로와 `best_epoch`부터 마지막 `}`까지의 결과. 예상되는 구조는 16 epochs 완료, `protocol.json`의 손실 `BCE only`·모드 `bce_only`, 모델·보고서 생성입니다. 점수·선택 epoch·threshold·시간은 미리 정답으로 고정하지 않습니다. 오류면 traceback과 실행 폴더를 보내고 임의로 재학습하지 않습니다.

터미널이 초기화돼도 실행 경로는 파일로 남습니다. 이 경우 학습을 반복하지 말고 다음 읽기 명령으로 경로를 확인합니다.

```bash
cd /workspaces/pathology-edge
cat work/step36-bce-run-path.txt
```

## 역할과 기록

- 사용자 U48: 선택 결과·환경 출력 보고를 확인했습니다. 실제 경로·손실 설정과 저장 기록 대조는 남아 있습니다.
- Codex: CLI·보관 명령·실행 조건 준비와 결과 검토. 사용자 계산 본문은 변경하지 않습니다.
- 사용자 soft Dice를 포함한 두 번째 비교 학습은 37단계의 검사 성공을 조건으로 안내했습니다. 사용자 실행 보고를 받기 전까지 U49는 예정입니다.

검증 평균은 설정 선택에 사용한 데이터의 탐색적 결과입니다. 한 seed의 점수 차이만으로 일반화·통계적 유의성·임상 효과를 주장하지 않습니다. 이 비교는 패치 경계 처리 전후를 새 test에서 검증하는 실험도 아닙니다.

[35단계 코드 검토 기록](../artifacts/learning/step35-review.json) · [Codex 연결 검증](../artifacts/learning/step36-preparation.json) · [기여 기록](CONTRIBUTIONS.md)
