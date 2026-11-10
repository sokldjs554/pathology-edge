# 35단계: 역전파가 가능한 soft Dice 손실 직접 작성

상태: **완료**. 사용자 `8 passed in 21.06s` 보고와 계산 본문을 받았습니다. 제출 계산은 변경하지 않고 반영했으며 Codex 독립 계약 테스트 8개, 전체 기본 테스트 140개가 통과했습니다. 사용자 테스트와 Codex 실행을 구분합니다. [보고 기록](../artifacts/learning/step35-review.json)

## 다음 할 일

현재 과제는 [36단계 BCE-only 비교군 한 번 학습](STEP_36.md)입니다. 두 번째 비교군은 첫 실행 결과를 확인한 뒤 안내합니다. 아래는 완료한 구현의 요구사항·검증 참고입니다. 작성한 Codespaces 파일을 보존하고 지금 `git pull`이나 초기화는 하지 않습니다.

## 작성한 파일과 역할

**파일:** `src/pathology_edge/learner_losses.py`

**함수:** `soft_dice_loss(logits, target, smooth=1.0)`

모델이 낸 실수 점수(logit)를 핵일 확률로 바꾸고, 정답과의 겹침을 학습 손실로 계산합니다. 앞서 작성한 NumPy `dice_score`는 이진 예측을 평가했지만 이번 함수는 확률을 그대로 사용하고 모델까지 gradient가 이어져야 합니다. 손실은 **낮을수록 좋습니다**.

`_validate_loss_inputs(...)`와 함수 선언·검사 호출은 Codex가 제공했습니다. 사용자는 **검사 호출 다음의 sigmoid·이미지별 합산·soft Dice·평균 반환 부분**을 작성했습니다. 원래 `NotImplementedError`는 제출한 본문으로 교체됐습니다. `model.py`의 기존 손실은 유지했습니다.

## 입력·출력 계약

| 항목 | 조건 |
|---|---|
| `logits` | 비어 있지 않은 `(N, 1, H, W)` 실수형 PyTorch Tensor. sigmoid를 적용하기 전 점수이며 모두 유한값 |
| `target` | 같은 shape·dtype·device의 실수형 Tensor. 값은 0 또는 1 |
| `smooth` | 유한한 양수 실수 스칼라, 기본 1.0 |
| 반환값 | 입력과 같은 dtype·device의 **0차원 Tensor**. 배치 이미지들의 손실 평균 |
| gradient | `logits.requires_grad=True`라면 반환값의 `backward()`로 입력에 유한 gradient가 도달해야 함 |

유효하지 않은 입력은 제공된 검사가 `ValueError`로 거절합니다. 사용자는 유효한 입력의 수식과 Tensor 연산에 집중합니다.

## 계산 요구사항과 검토

1. `logits`에 sigmoid를 적용해 확률 `p`를 얻습니다.
2. **이미지마다** 채널·높이·너비를 합산합니다. 배치 차원 `N`까지 한꺼번에 합산하지 않습니다.
3. 이미지 `i`의 점수는 아래와 같습니다.

   `D_i = (2 × Σ(p_i × target_i) + smooth) / (Σp_i + Σtarget_i + smooth)`

4. 반환 손실은 `mean(1 − D_i)`입니다. 여기에는 BCE를 더하지 않습니다. BCE와 합치는 코드는 Codex가 담당합니다.

확률을 threshold로 이진화하지 마세요. 계산·반환 과정에서 `.detach()`, `.numpy()`, `.item()` 또는 Python `float()`로 gradient를 끊지 마세요. 입력 Tensor도 수정하지 않습니다. 테스트에서 출력 값을 확인할 때 쓰는 `.item()`과 함수 내부 반환 계산을 구분합니다.

손계산 예시: `(1,1,2,2)`의 logits가 모두 0이고 target이 `[[1,0],[1,0]]`이면 확률은 모두 0.5입니다. 확률 합 2, 정답 합 2, 곱의 합 1이므로 `smooth=1`일 때 점수는 3/5, **손실은 0.4**입니다.

## 완료한 테스트와 재실행 참고

모든 명령은 **저장소 루트 `/workspaces/pathology-edge`**에서 실행합니다.

```bash
python -m pytest -q tests/learner/test_soft_dice_loss.py --run-learner
```

사용자는 **8 passed in 21.06s**를 보고했습니다. float32/64 반환 형식, 손계산 0.4, 빈 전경, 배치의 이미지별 평균, smoothing, 큰 logit의 안정성, gradient 방향과 수치 미분을 검사합니다. Codex는 교체 전 8개 미구현 실패를 확인하고, 제출 본문으로 8개 통과(1.39초)를 독립 확인했습니다.

함수의 기본 CI 포함과 실제 함수의 BCE 결합·역전파·학습 해시 검사를 반영한 전체 테스트는 다음 명령입니다. 현재 사용자에게 반복 실행을 요청하는 것은 아닙니다.

```bash
python -m pytest -q
```

이 변경이 포함된 저장소의 Codex 결과는 **140 passed in 8.05s**, 건너뜀 0개입니다. 8개 계약도 기본 검사에 포함됐습니다. 사용자 Codespaces의 이전 테스트 파일에서는 `--run-learner`가 필요할 수 있으며 현재 파일을 강제로 갱신하지 않습니다. 전체 140개 결과는 사용자가 실행한 기록이 아닙니다.

## Codex가 준비한 연결과 이후 비교

`train`의 `--loss`에는 세 모드가 있습니다.

| 모드 | 동작 | 현재 역할 |
|---|---|---|
| `baseline` (기본) | 기존 Codex BCE + soft Dice | 원래 실행·저장 결과 보존 |
| `bce_only` | 평균 BCE-with-logits만 사용 | 36단계의 첫 사용자 비교군 |
| `learner_dice` | BCE + 사용자가 작성한 soft Dice | 실제 함수 검토·Codex 학습 연결 확인, 사용자 실행은 첫 비교군 확인 후 |

Codex의 실제 `learner_dice` 16 epoch 실행은 같은 호스트 기준선과 history·모델 해시·22개 가중치 Tensor가 같았습니다. 이는 제출 계산의 연결·동등성 확인이며 사용자의 비교 실험 완료가 아닙니다. 비교할 때는 **같은 Codespaces에서 두 비교군을 모두 새 폴더에 실행**하고, seed 20261107·16 epochs·20 steps·데이터·모델·옵티마이저·검증 선택 규칙을 고정합니다. 가설은 “BCE에 Dice 항을 더했을 때 검증 결과가 어떻게 달라지는가”이며 개선을 보장하지 않습니다.

이후 학습에서도 기존 `artifacts/`와 34단계 사용자 실행 폴더를 덮어쓰지 않습니다. 기존 결과가 있는 폴더로 학습을 요청하면 거절하도록 보호했습니다. 변형 결과에는 실제 손실 모드와 learner 파일 해시가 기록됩니다. 기존 test는 이미 열람했으므로 새 설정을 고르는 데 사용하지 않고 검증 결과의 탐색적 비교로 한정합니다.

Codex의 기반 검증은 [당시 미구현 상태의 준비 근거](../artifacts/learning/step35-preparation.json), 제출 이후 실제 학습은 [현재 연결 검증](../artifacts/learning/step36-preparation.json), 사용자/도움 범위는 [기여 기록](CONTRIBUTIONS.md)에 구분합니다. 모델 구조 전체를 본인이 설계했다거나 새 test 성능을 검증했다고 설명하지 않습니다.
