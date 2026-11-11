# 58단계: 작성한 보정 모듈의 실제 학습 비교

상태: **사용자 두 모델 학습·검산 성공 SUMMARY와 ORIGINAL_FILES_PRESERVED=true 수신 완료**. `refinement-source.586qqgs1/work/my-vit-refinement.0881ce7d2afe`의 결과를 확인했습니다. 다음은 [59단계 원본 보관](STEP_59.md)입니다. 아래 학습 명령은 기록용이며 다시 실행할 필요가 없습니다.

## 확인한 코드

제출한 `LocalResidualHead`를 그대로 반영했습니다. 3×3 합성곱 1→8→1, ReLU, raw logits 잔차 덧셈이며 파라미터는 153개입니다. 두 번째 층의 weight와 bias가 모두 0이어서 최초 출력은 기준 ViT와 같습니다. 첫 번째 층은 기본 초기화를 유지합니다. 사용자 `13 passed in 25.76s` 보고와 별도 실행의 13개 통과를 구분해 기록했습니다.

## 이번에 비교하는 조건

| 항목 | 기준 | 변경 |
|---|---|---|
| 모델 | SmallViT | SmallViT + 작성한 LocalResidualHead |
| 파라미터 | 33,632 | 33,785 |
| 학습 시작 | 처음부터 | 처음부터, 공통 ViT 초기 가중치 동일 |
| 비교값 | 기준 점수 | 변경 점수 − 기준 점수 |

seed는 **20261116**으로 미리 고정했습니다. 이전 seed20261113의 모델을 재사용하지 않습니다. train33장·validation10장, 16epoch×20step, batch8, crop128, Adam0.001, BCE+작성한 soft Dice, threshold0.35/0.5/0.65를 유지합니다. crop/증강 순서의 해시도 두 모델 사이에 대조합니다. 각 모델의 epoch와 threshold는 검증 전체 이미지 평균 Dice로 선택합니다.

평가는 validation10장·2그룹의 전체/128px 패치 경계/내부 Dice입니다. test7장은 해시 확인만 하고 추론·평가하지 않습니다. 예측 확률을 저장해 60개 평가 영역을 독립 재계산합니다. CPU 파이프라인 시간은 no_overlap 조건의 처리 시간이며 웹 로딩 시간이 아닙니다. 시간·RSS는 참고 관찰값이고 통제된 속도 벤치마크가 아닙니다.

## Codespaces에서 실행

기존 프로젝트 루트 `/workspaces/pathology-edge`에서 실행합니다. Python은 앞서 확인한 `/opt/venv/bin/python`을 사용합니다. 이 명령은 고정 소스를 새 `work/refinement-source.*` 체크아웃에 받고 그 안의 새 결과 폴더에서 두 모델을 학습합니다. 기존 브랜치·작성 파일·이전 모델을 덮어쓰지 않습니다. Git fetch/worktree 등록에 따른 Git 메타데이터는 추가됩니다.

```bash
(
set -e
cd /workspaces/pathology-edge
PATHOLOGY_REFINEMENT_LAUNCHER="$(mktemp /workspaces/pathology-edge/work/start-refinement.XXXXXX.py)"
curl -fsSL --retry 2 https://raw.githubusercontent.com/sokldjs554/pathology-edge/b084453347c4d774c3e6835b850450e19037004d/scripts/start_refinement_comparison.py -o "$PATHOLOGY_REFINEMENT_LAUNCHER"
printf '%s  %s\n' '55a0711a84ad17ba451270dd487aa7bd5c16c4c25125d5926bab11ca7f393744' "$PATHOLOGY_REFINEMENT_LAUNCHER" | sha256sum -c -
/opt/venv/bin/python "$PATHOLOGY_REFINEMENT_LAUNCHER" --repo /workspaces/pathology-edge --source-commit 1744544ec2f88bff1e3eac8a7bfe99b9335d9d48
)
```

입력으로 기존 `data/manifest.json`과 `work/step57-refinement/learner_refinement.py`가 필요합니다. 둘 중 하나가 없으면 학습 전에 멈춥니다. **로컬 실습 파일은 보존·클래스 AST 대조용이고, 실제 학습은 고정 소스에 반영한 제출 클래스와 제공 import/helper를 사용합니다.** AST 대조는 클래스만 대상으로 하며 클래스 밖 코드를 실행하거나 자동으로 복사해 적용하지 않습니다. 공백·주석·클래스/메서드 설명 문자열·인자/반환 타입 주석 차이는 허용합니다. 연산, 층 설정, 기본값, 함수 시그니처, decorator 등 나머지 AST가 다르면 차이(diff)를 출력하고 학습을 멈춥니다. 클래스 밖의 변경을 연결했다고 주장하지 않습니다.

실행 중 원래 폴더나 새 체크아웃의 파일·브랜치를 변경하지 마세요. 코드·모델 선택을 바꿔 점수를 높이기 위한 재실행도 하지 않습니다. 결과가 낮아져도 그대로 기록합니다.

## 보내 주실 출력

각 모델의 epoch1–16 출력 뒤 다음 두 가지를 보내 주세요.

1. 마지막 `SUMMARY {...}` 전체.
2. `ORIGINAL_FILES_PRESERVED=true` 줄.

SUMMARY에는 두 모델 점수·선택 epoch/threshold·SHA·초기 가중치 SHA·60영역 검사·새 체크아웃 보존 여부가 들어갑니다. 마지막 보존 표시는 **원래 체크아웃과 ignored 실습 파일**의 전후 대조입니다. 기존 ignored 작업 결과 전체를 하나하나 해시한 의미는 아니며 데이터는 manifest로 별도 검사합니다.

실패하면 traceback과 `PREPARING_SOURCE_DIR`, `SOURCE_DIR`, `RUN_DIR` 중 출력된 경로를 보내세요. `SUMMARY` 없이 보존 표시만 나왔다면 학습 완료가 아닙니다. 부분 출력은 지우지 말고 유지합니다. 터미널이 초기화돼도 새 체크아웃의 `work/SOURCE_PATH.txt`, 결과의 `RUN.txt`, `work/launcher-status.json`에서 위치·상태를 확인할 수 있습니다.

사용자가 실행하기 전에는 학습 완료로 기록하지 않습니다. 동일한 기존 validation에서 선택한 한 seed 결과이므로 독립 test·외부 데이터·임상 검증이나 일반적인 개선을 입증하지 않습니다. 보정 모듈은 128px 입력 타일 안에서 작동하며 서로 다른 타일의 픽셀을 직접 연결하지 않습니다.

## 클래스 불일치 오류의 수정

사용자가 기존 검사기의 `The submitted class differs from the reviewed code` 오류를 보고했습니다. 이 검사는 학습 호출보다 앞서 실행되므로 해당 시도에서는 모델 학습이 시작되지 않았습니다. 초기 실습 파일의 설명 문자열만 그대로 남겨 둔 코드와 `__init__ -> None`만 추가한 코드가 거부되는 것을 별도로 재현했습니다. 사용자 파일의 실제 차이는 아직 받지 않았으므로 이 재현을 사용자 원인의 확정으로 기록하지 않습니다.

새 launcher `b084453`는 설명 문자열과 인자/반환 타입 표시만 비교에서 제외하고, 나머지 차이를 보여 줍니다. **학습 소스는 계속 `1744544`, seed는20261116**이며 기존 데이터·모델·실험 결과는 그대로입니다. 위 명령은 새 검사기를 받되 같은 고정 학습 소스를 사용합니다. `learner-connection.json`의 `class_match_policy`에 정규화 범위를 기록합니다. 이전 기록의 raw AST 해시와 새 정책의 normalized AST 해시는 직접 비교하지 않습니다. 작성 파일은 수정할 필요가 없습니다. 다시 중단되면 새 메시지의 `reviewed class`/`local submitted class` diff를 보내 주세요.

## 받은 결과와 확인 범위

[사용자 SUMMARY](../artifacts/learning/step58-user-summary.json)와 [채팅 수치 검산](../artifacts/learning/step58-user-review.json)을 보관했습니다. 전체 Dice0.570565→0.590386, 경계0.558802→0.559040, 내부0.560475→0.582999입니다. 세 차이와 선언된 프로토콜·초기 가중치 SHA를 대조했습니다. 기준epoch12/보정epoch14, 둘 다threshold0.35이며60영역·test 평가 false·새 체크아웃 보존 true와 별도 원래 체크아웃/실습 파일 보존 true를 보고받았습니다. 이전 검사기 오류 후 진행 성공은 확인됐지만 당시 로컬 파일의 구체적 차이를 원인으로 확정하지 않습니다. 원본 확률·체크포인트를 직접 받아 검산하는 일은59단계로 구분합니다.
