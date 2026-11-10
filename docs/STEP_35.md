# 35단계: 역전파가 가능한 soft Dice 손실 직접 작성

상태: **사용자 구현·테스트 대기**. 34단계의 직접 학습·저장·설정 대조와 모델 선택 해석은 완료했습니다. 이번에는 함수 하나를 작성하고 8개 계약 테스트를 실행합니다. 비교 학습은 제출 코드를 검토한 다음 진행합니다.

## 지금 작성할 파일과 역할

**파일:** `src/pathology_edge/learner_losses.py`

**함수:** `soft_dice_loss(logits, target, smooth=1.0)`

모델이 낸 실수 점수(logit)를 핵일 확률로 바꾸고, 정답과의 겹침을 학습 손실로 계산합니다. 앞서 작성한 NumPy `dice_score`는 이진 예측을 평가했지만 이번 함수는 확률을 그대로 사용하고 모델까지 gradient가 이어져야 합니다. 손실은 **낮을수록 좋습니다**.

현재 파일의 `_validate_loss_inputs(...)`와 함수 선언·검사 호출은 Codex가 제공합니다. **검사 호출 다음의 `raise NotImplementedError(...)`를 계산과 `return`으로 바꾸는 부분만** 직접 작성하세요. 입력 검사를 다시 작성하거나 `model.py`의 기존 손실을 수정할 필요는 없습니다.

## 입력·출력 계약

| 항목 | 조건 |
|---|---|
| `logits` | 비어 있지 않은 `(N, 1, H, W)` 실수형 PyTorch Tensor. sigmoid를 적용하기 전 점수이며 모두 유한값 |
| `target` | 같은 shape·dtype·device의 실수형 Tensor. 값은 0 또는 1 |
| `smooth` | 유한한 양수 실수 스칼라, 기본 1.0 |
| 반환값 | 입력과 같은 dtype·device의 **0차원 Tensor**. 배치 이미지들의 손실 평균 |
| gradient | `logits.requires_grad=True`라면 반환값의 `backward()`로 입력에 유한 gradient가 도달해야 함 |

유효하지 않은 입력은 제공된 검사가 `ValueError`로 거절합니다. 사용자는 유효한 입력의 수식과 Tensor 연산에 집중합니다.

## 계산 요구사항 — Python 정답 코드는 제공하지 않음

1. `logits`에 sigmoid를 적용해 확률 `p`를 얻습니다.
2. **이미지마다** 채널·높이·너비를 합산합니다. 배치 차원 `N`까지 한꺼번에 합산하지 않습니다.
3. 이미지 `i`의 점수는 아래와 같습니다.

   `D_i = (2 × Σ(p_i × target_i) + smooth) / (Σp_i + Σtarget_i + smooth)`

4. 반환 손실은 `mean(1 − D_i)`입니다. 여기에는 BCE를 더하지 않습니다. BCE와 합치는 코드는 Codex가 담당합니다.

확률을 threshold로 이진화하지 마세요. 계산·반환 과정에서 `.detach()`, `.numpy()`, `.item()` 또는 Python `float()`로 gradient를 끊지 마세요. 입력 Tensor도 수정하지 않습니다. 테스트에서 출력 값을 확인할 때 쓰는 `.item()`과 함수 내부 반환 계산을 구분합니다.

손계산 예시: `(1,1,2,2)`의 logits가 모두 0이고 target이 `[[1,0],[1,0]]`이면 확률은 모두 0.5입니다. 확률 합 2, 정답 합 2, 곱의 합 1이므로 `smooth=1`일 때 점수는 3/5, **손실은 0.4**입니다.

## Codespaces에서 진행하는 순서

모든 명령은 **저장소 루트 `/workspaces/pathology-edge`**에서 실행합니다.

```bash
cd /workspaces/pathology-edge
git status --short
git pull --ff-only
```

첫 명령 출력으로 기존 변경을 확인하고, 두 번째로 실습 파일·테스트를 받습니다. 기존 수정 파일이 보이거나 pull이 실패하면 덮어쓰거나 초기화하지 말고 출력을 보내 주세요. 이미 설치된 editable Python 환경에서 바로 사용할 수 있으며 컨테이너 재생성은 필요 없습니다.

Codespaces 파일 탐색기에서 `src/pathology_edge/learner_losses.py`를 열어 본문을 작성·저장한 뒤 실행합니다.

```bash
python -m pytest -q tests/learner/test_soft_dice_loss.py --run-learner
```

정상 구현의 목표는 **8 passed**입니다. float32/64 반환 형식, 손계산 0.4, 빈 전경, 배치의 이미지별 평균, smoothing, 큰 logit의 안정성, gradient 방향과 수치 미분을 검사합니다. 본문을 작성하기 전에는 `NotImplementedError`로 실패하는 것이 예상 상태입니다.

**제출할 것:** 작성한 `soft_dice_loss` 함수와 테스트 출력. 실패하면 해당 traceback도 함께 보냅니다. 사용자 통과 기록은 실제 제출 후에만 완료 처리합니다.

전체 테스트는 코드 검토 후 사용할 참고 명령입니다. 지금은 위 함수의 8개 테스트가 현재 과제입니다.

```bash
python -m pytest -q --run-learner
```

기본 `python -m pytest -q`는 미완료 learner 테스트를 건너뛰므로 본인 함수의 성공을 확인하는 명령으로 대신 사용하지 않습니다.

## Codex가 준비한 연결과 이후 비교

`train`의 `--loss`에는 세 모드가 있습니다.

| 모드 | 동작 | 현재 역할 |
|---|---|---|
| `baseline` (기본) | 기존 Codex BCE + soft Dice | 원래 실행·저장 결과 보존 |
| `bce_only` | 평균 BCE-with-logits만 사용 | 이후 Dice 항을 제외한 비교군 |
| `learner_dice` | BCE + 사용자가 작성한 soft Dice | 함수 검토 후 실행할 실습 모델 |

아직 구현하지 않은 `learner_dice`가 학습 가능한 것처럼 취급하지 않습니다. 비교할 때는 **같은 Codespaces에서 두 비교군을 모두 새 폴더에 실행**하고, seed 20261107·16 epochs·20 steps·데이터·모델·옵티마이저·검증 선택 규칙을 고정합니다. 가설은 “BCE에 Dice 항을 더했을 때 검증 결과가 어떻게 달라지는가”이며 개선을 보장하지 않습니다. 사용자 검토 전 이 비교 학습은 배정하지 않습니다.

이후 학습에서도 기존 `artifacts/`와 34단계 사용자 실행 폴더를 덮어쓰지 않습니다. 기존 결과가 있는 폴더로 학습을 요청하면 거절하도록 보호했습니다. 변형 결과에는 실제 손실 모드와 learner 파일 해시가 기록됩니다. 기존 test는 이미 열람했으므로 새 설정을 고르는 데 사용하지 않고 검증 결과의 탐색적 비교로 한정합니다.

Codex의 기반 검증·별도 실행은 [준비 근거](../artifacts/learning/step35-preparation.json), 사용자/도움 범위는 [기여 기록](CONTRIBUTIONS.md)에 구분합니다. 직접 구현 완료 후에도 모델 구조 전체를 본인이 설계했다거나 새 test 성능을 검증했다고 설명하지 않습니다.
