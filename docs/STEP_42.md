# 42단계: 새 seed 3개에서 손실 비교 반복

상태: **Codex 실행 도구 준비, 사용자 실행·결과 제출 예정**. [41단계](STEP_41.md)까지 WSI 좌표 구현·검증·해석을 마쳤습니다. 이번 한 작업은 기존 손실 비교를 3개 seed에서 반복하고 모든 결과를 제출하는 것입니다. 새 함수 작성이나 설치는 없습니다.

## 비교 기준과 역할

| 항목 | 사전에 고정한 조건 |
|---|---|
| 가설 | BCE에 사용자가 구현한 soft Dice를 더했을 때 선택된 validation Dice 차이가 반복에서도 어떻게 나타나는가 |
| seed | `20261110`, `20261111`, `20261112` — 이전에 결과를 본 `20261107`은 이번 평균에 넣지 않음 |
| A / B | `bce_only` / `learner_dice`(BCE + 사용자 soft Dice) |
| 데이터 / 모델 | 기존 train 33장·validation 10장 / TinyUNet 29,761 parameters |
| 고정 학습 조건 | 16 epochs·epoch당 20 steps·batch 8·기존 optimizer/augmentation |
| 선택 규칙 | 각 실행의 epoch·threshold 0.35/0.5/0.65 중 validation 이미지별 평균 Dice 최대; 동률은 기존 첫 조합 |
| 보고 | 6개 결과 전부, 각 방식 평균·표본 표준편차, 같은 seed의 B−A와 평균·표준편차·상승/동률/하락 수 |
| 비용 | 각 실행의 학습 시간·방식별 평균·표준편차. 웹 로딩/추론 시간 아님 |

이 조건·새 seed·실행 도구는 기존 보완 순서 안에서 Codex가 정했습니다. 사용자가 독자적으로 고안한 실험 설계로 소급하지 않습니다. 사용자는 본인 soft Dice를 포함한 6회 학습을 실행하고 결과를 검토합니다. 새 모델 구조/ViT 비교는 이번 단계에 포함하지 않습니다.

도구는 실행 전에 현재 패키지 Python 소스, 사용자 손실 함수, manifest, 설정, Git 커밋·변경 상태와 실행 도구를 새 폴더에 보관합니다. 여섯 학습은 이 보관본을 새 프로세스에서 불러옵니다. A/B, B/A, A/B 순으로 실행 순서를 일부 번갈아 쓰지만 시간 측정의 시스템 부하를 통제한 벤치마크는 아닙니다. 원본 소스와 기존 모델·데모는 덮어쓰지 않습니다.

## 지금 실행할 명령 하나

**위치:** Codespaces Bash 터미널, 기존 저장소 루트 `/workspaces/pathology-edge`. 기존 활성 Python 환경을 사용합니다. `git pull`, 파일 복구, 재설치 없이 단일 도구만 `work/`에 받습니다. 아래 다운로드는 고정 커밋과 SHA-256을 확인한 뒤 실행합니다.

```bash
cd /workspaces/pathology-edge &&
mkdir -p work &&
curl -fL 'https://raw.githubusercontent.com/sokldjs554/pathology-edge/2538c4f58ba87fbf8ad2f0341c13e89dfc626582/scripts/run_loss_repeats.py' -o work/run-loss-repeats-step42.py &&
printf '%s\n' '664fabf4bcbaade3ea988a8d1b048775acbe0a4776a64d767d21fe2408bd3067  work/run-loss-repeats-step42.py' | sha256sum -c - &&
python -u work/run-loss-repeats-step42.py --data data
```

예상 흐름은 `Run: .../work/my-loss-repeats.<고유값>` → `[1/6]`부터 `[6/6]` → 각 16 epochs → `SUMMARY`와 JSON입니다. 앞선 사용자 학습 시간으로는 총 약 10분 규모지만 현재 호스트 부하에 따라 달라집니다. 점수·개선 방향·선택 epoch는 정답으로 미리 정하지 않습니다.

**제출할 것:** 처음 표시된 `Run:` 경로와 마지막 `SUMMARY` 아래 JSON 전체. 사용자 실행은 그 출력을 받은 후 기록합니다. 마지막 JSON의 `all_checks_passed`는 여섯 실행이 모두 있고 설정·manifest·소스·모델 해시·선택 규칙·기록 환경 검사를 통과했다는 뜻이며, Dice가 개선됐다는 뜻이 아닙니다.

## 중단·오류 또는 터미널 초기화

실패한 실행도 새 출력 폴더에 보존합니다. 자동 재시도·좋은 seed 교체·일부 결과만 평균내기는 하지 않습니다. 오류면 마지막 메시지와 아래 경로를 보내고 임의로 학습을 다시 시작하지 않습니다.

```bash
cd /workspaces/pathology-edge
cat work/step42-repeat-run-path.txt
```

학습이 끝났는데 요약을 놓쳤다면 저장 결과만 읽습니다. 아래 명령은 새 학습이나 파일 쓰기를 하지 않으며, 미완료·불일치가 있으면 오류를 냅니다.

```bash
cd /workspaces/pathology-edge
python work/run-loss-repeats-step42.py --summarize "$(cat work/step42-repeat-run-path.txt)"
```

## 해석의 한계

validation 10장은 이미 epoch·threshold 선택에 사용한 같은 데이터입니다. 세 seed의 표준편차는 관찰한 학습 변동이지 새로운 환자/기관의 불확실성이나 통계적 유의성 증명이 아닙니다. 같은 test 7장·2개 그룹의 한계를 해결하지 않으며 이번에는 test 평가를 실행하지 않습니다. 기존 로더는 데이터 무결성을 위해 50장 파일 해시를 읽지만 test 예측·점수는 계산하지 않습니다.

시간은 기존 `train()`의 학습·validation·체크포인트 저장·고전 validation 비교를 포함합니다. 초기 데이터 로딩·프로세스 시작은 제외됩니다. seed마다 선택된 epoch가 달라도 실제로는 모두 16 epochs 학습합니다.

[기여 기록](CONTRIBUTIONS.md) · [실행 도구](../scripts/run_loss_repeats.py) · [고정 설계](superpowers/specs/2026-11-10-paired-seed-repeats-design.md)

## Codex 별도 검증

도구의 15개 검사와 기본 전체 190개 검사가 통과했습니다. Codex 호스트에서도 고정한 6회 학습을 완료하고 전체 기록 감사를 통과했습니다. 선택된 검증 Dice 평균±표본 SD는 A `0.508521±0.012424`, B `0.546342±0.006688`, seed별 B−A는 세 개 모두 양수였습니다. 이는 사용자 실행의 정답이나 사용자 수행 기록이 아닙니다. 사용자 환경의 결과도 좋아진/나빠진 방향과 관계없이 전부 보고합니다. [Codex 모든 결과·비용](../artifacts/learning/step42-codex/summary.json) · [검증 근거](../artifacts/learning/step42-preparation.json).
