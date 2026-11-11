# 57단계: ViT 출력에 작은 공간 보정 모듈 연결하기

상태: **사용자 코드 제출·13 passed in 25.76s 보고 확인 완료**. 제출 클래스를 그대로 반영하고 별도 실행에서도 13개 통과를 확인했습니다. 다음은 [58단계 실제 비교 학습](STEP_58.md)입니다. 아래 요구사항과 초기 실습 파일 다운로드는 기록용이며 다시 받을 필요가 없습니다.

## 왜 이 부분을 작성하나요?

[사용자 원본 감사와 오류 분석](USER_RESEARCH_AUDIT.md)을 완료했습니다. `09_1`의 전체 Dice는0.402373→0.344220으로 하락했고, 전체 FN(놓친 정답 픽셀)은28,445→30,376으로 증가했습니다. 선택한128×128 ROI에서는FP164→509,FN1,848→2,361로 둘 다 늘었습니다. 사용자 `09_6`은FP/FN이 모두 줄며 개선됐지만, 확대 예측에는 각진 조각도 관찰됩니다.

이를 근거로 **이웃 픽셀의 예측을 함께 보는 작은 학습 가능한 보정이 국소 모양에 도움이 되는지** 시험합니다. 토큰화가 실패 원인이라고 확정한 것은 아닙니다. 이 모듈만으로 통째로 놓친 큰 핵을 복구한다고 기대하지 않습니다.128px 입력 타일 안에서 동작하며 다른 타일의 픽셀을 직접 읽지 않습니다. 기존 겹침·병합 방식과도 별도입니다.

## 작성 위치와 역할

다운로드 후 작성 파일: `/workspaces/pathology-edge/work/step57-refinement/learner_refinement.py`.

작성할 함수는 `LocalResidualHead.__init__`와 `LocalResidualHead.forward`입니다. 저장소의 대응 위치는 [`src/pathology_edge/learner_refinement.py`](../src/pathology_edge/learner_refinement.py)입니다. 사용자 작성본은 검토 후 비교 실행기의 동결 소스에 연결합니다.

제공되는 코드: import, `nn.Module` 상속과 `super().__init__()`, 입력 검사 `_validate_logits`, ViT 연결 wrapper, 학습·검증·선택·보존 실행기,13개 실습 테스트. **두 함수의 `NotImplementedError` 부분만 직접 작성**합니다. 입력 검사와 기존 프로젝트 파일을 변경하지 않습니다.

## 입출력·구현 계약

입력 `logits`: 유한한 실수 PyTorch Tensor, `(B,1,H,W)`, 모든 축 크기는1 이상. 확률로 바꾸기 전의 모델 출력이므로 음수나1보다 큰 값도 정상입니다.

출력은 입력과 같은 shape·dtype·device의 **raw logits**입니다. 입력을 제자리에서 바꾸거나 gradient를 끊지 않습니다.

`__init__`에서 다음 두 학습 가능한 층을 정의합니다.

| 속성 이름 | 입력→출력 채널 | kernel / stride / padding | bias |
|---|---|---|---|
| `self.conv1` | 1→8 | 3 / 1 / 1, zero padding | 사용 |
| `self.conv2` | 8→1 | 3 / 1 / 1, zero padding | 사용 |

두 번째 층의 **weight와 bias를 모두0으로 초기화**합니다. 첫 번째 층은 PyTorch의 기본 초기화를 사용합니다. 추가 파라미터는153개입니다.

`forward`는 제공된 입력 검사 뒤에 **conv1 → ReLU → conv2**로 보정값을 만들고, **원래 입력 logits에 더해** 반환합니다. sigmoid·threshold·NumPy 변환·detach는 사용하지 않습니다. 함수 정답 코드는 제공하지 않으며, 필요하면 특정 부분의 힌트를 요청할 수 있습니다.

## 예시와 테스트

- 처음 생성한 모듈에 `[-3, 0, 2]` 같은 logits를 넣으면 값이 그대로 나와야 합니다. 마지막 층이0이어서 초기 보정값이0이기 때문입니다.
- `(2,1,13,19)`와 `(1,1,1,1)` 입력에서도 크기가 유지돼야 합니다.
- 테스트가 층 값을 정해 보정값을1로 만들면, 입력2의 출력은3이어야 합니다. 확률로 바꾸지 않았는지와 잔차 덧셈을 검사합니다.
- 첫 backward에서는 마지막 층이0이므로 첫 층 gradient가0인 것이 정상입니다. optimizer가 마지막 층을 바꾼 다음에는 첫 층까지 gradient가 도달하는지 확인합니다.

실습 테스트는 일반 프로젝트 테스트와 분리되어 있으며, 작성 전에는 `NotImplementedError`로 실패합니다. 본문을 완성한 뒤 **Codespaces 저장소 루트**에서 실행하세요.

```bash
cd /workspaces/pathology-edge
/opt/venv/bin/python -m pytest -q work/step57-refinement/test_local_refinement.py
```

13개 통과 출력과 작성한 클래스 코드를 보내 주세요. 실패하면 같은 명령의 실패한 테스트 이름과 traceback을 보내면 됩니다. 사용자 실행 전에는 테스트 완료로 기록하지 않습니다.

## 실습 파일 받기

다음 블록은 Codespaces 터미널에서 실행합니다. 알려진 Python은`/opt/venv/bin/python`입니다. **새 실습 폴더만 만들며 기존 프로젝트 코드·학습 결과는 바꾸지 않습니다.** 폴더가 이미 있으면 `mkdir`에서 멈추므로 재다운로드하지 말고 기존 작성본을 사용하세요.

```bash
(
set -e
cd /workspaces/pathology-edge
mkdir work/step57-refinement
curl -fsSL --retry 2 https://raw.githubusercontent.com/sokldjs554/pathology-edge/00f64310c50e95bf0cbb35a84838ed499a8666e2/artifacts/learning/step57-exercise.zip -o work/step57-refinement/exercise.zip
printf '%s  %s\n' 'f9466bf39394f583426195901f698a7446d94d5acf567085ba68cf5600a7eff4' 'work/step57-refinement/exercise.zip' | sha256sum -c -
/opt/venv/bin/python -m zipfile -e work/step57-refinement/exercise.zip work/step57-refinement
)
```

다운로드가 끝나면 Explorer의 `work/step57-refinement/learner_refinement.py`를 엽니다. 파일에 이미 본인이 작성한 코드가 있으면 덮어쓰지 않습니다. 다운로드 실패로 중단되면 오류를 보내 주세요.

## 코드 확인 후 진행할 비교

seed20261116을 미리 고정합니다. 기본 ViT33,632개와 보정 포함33,785개 파라미터 모델을 각각 처음부터 학습합니다. 공통 ViT의 초기 가중치 SHA·이미지 crop/증강 순서가 같은지 검사하고, 기존33train/10validation·16epoch×20step·batch8·Adam0.001·BCE+작성한Dice·threshold0.35/0.5/0.65를 유지합니다. 모든 조건과 원본 소스를 새 폴더에 기록합니다.

[`run_refinement_comparison.py`](../scripts/run_refinement_comparison.py)는 본문이 미완성이면 사전 검사에서 멈추고 두 모델의 학습을 시작하지 않습니다. 이번 단계에서는 실제 보정 모델 학습이나 성능 개선을 수행한 것으로 기록하지 않습니다. 결과가 낮아져도 그대로 남깁니다. 기존validation에서 모델을 선택하므로 독립test·외부·임상 검증을 뜻하지 않습니다.

후속 상태: 사용자 본문을 그대로 반영해13개 계약 검사·실제 ViT 연결을 확인했습니다. [개발 참고 실제 비교](../artifacts/experiments/vit-refinement-reference-20261112/README.md)도 완료했으며, 사용자 직접 비교 실행은 [58단계](STEP_58.md)로 구분합니다. 위의 미완성/학습 대기 표현은 최초 준비 시점의 설명입니다.
