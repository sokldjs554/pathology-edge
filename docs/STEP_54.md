# 54단계: 사용자 CNN–ViT의 이미지별 결과 확인

상태: **출력 요청 / 사용자 결과 대기**. [53단계](STEP_53.md)의 두 학습·실행기 감사·원래 체크아웃 보존 성공 보고는 확인했습니다. 이제 같은 저장 결과를 이미지별로 읽는 한 단계입니다. 새 학습·추론은 실행하지 않습니다.

## 제출 요약에서 확인한 결과

검증10장·2그룹의 이미지별 Dice 평균입니다. 아래 차이는 ViT−CNN입니다.

| 영역 | TinyUNet | 소형 ViT | 차이 |
|---|---:|---:|---:|
| 전체 | 0.503768 | 0.557644 | +0.053876 |
| 패치 경계 | 0.453280 | 0.530161 | +0.076881 |
| 내부 | 0.504595 | 0.550867 | +0.046272 |

CNN은 epoch8·threshold0.35, ViT는 epoch15·threshold0.35를 선택했습니다. 두 모델 모두16epoch를 학습하는 실행기이며8·15는 저장 모델의 선택 epoch입니다. 사용자 요약의 `all_checks_passed`가 true이지만 전체 epoch 로그를 직접 받은 것은 아닙니다.

같은 Codespaces 실행에서 학습·epoch 검증은97.409초와32.458초, warm 파이프라인 중앙값은143.131ms와40.459ms, 학습·검증 전체 프로세스 peak RSS는550.1MiB와467.6MiB였습니다. 파이프라인은 이미지마다3회 중앙값을 이미지 간 다시 중앙값으로 집계한 값이며, 출력 할당·조직 검사·모델 순전파·확률 결합·성분 추출을 포함합니다. 모델 로딩·디스크 I/O·정답 평가는 제외하며 무겹침 모드라 NMS를 하지 않습니다. 순서 교차·반복 속도 실험은 아닙니다.

학습 seed 하나와 이전부터 사용한 validation에서 epoch/threshold를 고른 비교이며 test·외부·임상 검증을 실행하지 않았습니다. 파라미터 수도 CNN29,761개·ViT33,632개로 다릅니다. 이번 평균만으로 모든 이미지나 ViT 전반의 우열을 판단하지 않습니다.

[사용자 제출 요약](../artifacts/learning/step53-user-summary.json), [검산·확인 범위](../artifacts/learning/step53-review.json). 개발 참고 실행과 사용자 실행은 별도 기록입니다. 참고 CNN의0.540674·epoch15와 사용자 CNN의0.503768·epoch8이 다르며 모델 SHA도 다릅니다. CPU·Python/platform 등 환경이 다르고, 같은 seed가 서로 다른 환경에서 bit 단위 동일 학습을 보장하지는 않습니다. 요약만으로 차이의 구체 원인을 확정하지 않으며 좋은 숫자를 얻기 위한 재학습도 요청하지 않습니다.

## 지금 실행할 명령

Codespaces의 원래 `/workspaces/pathology-edge`에서 아래 블록을 실행하고 표 전체와 마지막 집계 줄을 보냅니다. `training.json` 두 파일만 읽으며 코드를 받거나 바꿀 필요가 없습니다.

```bash
cd /workspaces/pathology-edge && python - <<'PY'
import json
import math
from pathlib import Path

run = Path("work/vit-source.tdbTh0/work/my-cnn-vit.4de29faebea2")
reports = [json.loads((run / name / "training.json").read_text())
           for name in ("tiny_unet", "small_vit")]
rows = [report["validation"]["rows"] for report in reports]
maps = [{row["id"]: row for row in group} for group in rows]
if any(len(group) != 10 or len(index) != 10 for group, index in zip(rows, maps)) or maps[0].keys() != maps[1].keys():
    raise ValueError("Expected the same 10 validation image IDs")
print("image  CNN_Dice  ViT_Dice  ViT-CNN")
deltas = []
for image_id in sorted(maps[0]):
    a, b = [index[image_id]["metrics"]["all"]["dice"] for index in maps]
    if not all(math.isfinite(value) and 0 <= value <= 1 for value in (a, b)):
        raise ValueError("Invalid Dice value")
    deltas.append(b - a)
    print(f"{image_id:5s}  {a:.6f}  {b:.6f}  {b-a:+.6f}")
print("ViT 상승/동일/하락:", sum(d > 0 for d in deltas), sum(d == 0 for d in deltas), sum(d < 0 for d in deltas))
PY
```

상승/동일/하락은 반올림 전 저장 점수를 기준으로 셉니다. 표시된 두 점수의 뺄셈과 차이의 마지막 자리가 다를 수 있습니다. 경로 오류가 나면 오류와 경로를 보내 주세요. 이 출력이 오기 전에는 사용자의 개별 이미지 개선·악화 개수나 검토 완료를 기록하지 않습니다.
