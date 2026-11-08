# 5단계: 내가 작성한 Dice로 실제 저장 결과 재계산

상태: **사용자 실행·결과 확인 대기**. 4단계 Dice 코드와 `20 passed in 0.01s` 보고를 확인했습니다.
이번에는 새 함수를 작성하지 않고, 본인이 작성한 함수로 실제 결과를 확인하는 명령 하나를 실행합니다.

## 무엇을 확인하는가

`scripts/audit_dice.py`는 사용자 작성 `learner_metrics.dice_score`를 호출합니다.
TNBC test7장·2개 케이스 그룹의 저장 결과에서 무겹침·겹침 두 방식 × 전체·경계·내부를 계산하므로 **42개 Dice**를 비교합니다.
이미지별 점수를 산술평균한 **6개 평균**도 원 실험 기록과 화면 JSON에 대조합니다.

| 입력 | 역할 |
|---|---|
| `dist/assets/*_gt.png` | 배포에 사용한 정답 이진 마스크 |
| `artifacts/predictions/{no_overlap,overlap}/*.png` | 저장한 실제 모델 예측 마스크 |
| `dist/results.json` | 화면에 표시하는 이미지별 점수·평균·오버레이 경로 |
| `artifacts/evaluation.json` | 원 실험 결과와 테스트 이미지·그룹 수 |
| `artifacts/training.json` | 공통 경계 정의: 패치128px, 내부 경계 양쪽8px |

PNG의 값이0/255인지 검사한 뒤 bool로 변환하여 Dice 함수에 전달합니다.
이미지 바깥쪽 테두리는 경계 평가 영역에 넣지 않습니다. 두 처리 방식에 같은 경계 마스크를 사용합니다.
화면 오버레이의 alpha 영역도 저장 예측 마스크와 같은지 확인합니다.

새 학습이나 추론을 실행하지 않습니다. WSI·IHC의 정확도 평가도 아닙니다.
해당 정답 마스크 자체의 의학적 타당성을 다시 검증하는 작업과 구분합니다.

## 실행 준비

프로젝트 루트에서 새 검산 스크립트만 받습니다. 기존에 작성한 Dice 함수는 보존합니다.

```bash
cd ~/Projects/pathology-edge
git fetch origin
if [ -e scripts/audit_dice.py ]; then
  printf '%s\n' '스크립트가 이미 있습니다. 기존 변경 내용을 보존하고 해당 파일을 확인하세요.'
else
  git restore --source=origin/main -- scripts/audit_dice.py
fi
source .venv/bin/activate
python -m pip install numpy pillow
```

이 실습은 NumPy와 PNG를 읽는 Pillow만 필요합니다. PyTorch·OpenCV·SciPy 설치나 데이터 재다운로드는 필요하지 않습니다.

## 직접 실행할 명령 하나

**`pathology-edge/` 저장소 루트**에서 실행합니다.

```bash
python scripts/audit_dice.py --output work/my-dice-audit.json
```

저장된 마스크로 다시 계산한 값이 화면과 원 실험 기록에 모두 맞는지 확인하는 명령입니다.
결과는 `work/my-dice-audit.json`에 저장하며 기존 모델·실험·화면 파일을 덮어쓰지 않습니다.

정상적인 출력의 핵심은 다음과 같습니다.

```text
42/42 Dice values and 6/6 image means match.
7 test images / 2 case groups; no inference run.
method           all       boundary  interior
no_overlap       0.558001  0.491793  0.572866
overlap          0.560790  0.527261  0.569630
```

화면의 소수3자리 표시와 이 출력의 소수6자리 표시를 구분합니다. 평균은 이미지별 Dice의 산술평균이며 모든 픽셀을 한꺼번에 합친 Dice가 아닙니다.
JSON에는 이미지·방식·영역별 값과 원 값, 입력 파일·사용자 함수 SHA가 들어갑니다.
사용자 로컬 파일의 주석 등이 저장소와 다르면 함수 파일 SHA가 달라질 수 있으며, 그 자체로 계산 실패를 뜻하지 않습니다.

**이번에 보내주실 것은 터미널 출력 전체**입니다. 실패하면 실행 명령과 traceback을 그대로 보내 주세요.
결과를 확인한 뒤 다음 단계로 진행합니다. 추가 코드 작성이나 전체 프로젝트 테스트 실행을 이번 과제로 요구하지 않습니다.

## 기여 구분

- 사용자 완료: Dice 함수 구현, 단위 테스트20개 통과 보고.
- Codex 완료: PNG·기록 읽기와 검산 스크립트, 기존 사용자 함수로42개 점수·6개 평균 대조. [Codex 실행 기록](../artifacts/learning/step04-real-dice-audit.json).
- 사용자 예정: 위 검산 명령 실행과 실제 출력 확인. Codex가 성공한 결과를 사용자 실행으로 기록하지 않습니다.
