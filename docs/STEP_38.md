# 38단계: 두 학습의 저장 조건과 모델 파일 대조

상태: **사용자 확인 예정**. 두 실행의 경로·손실 모드·선택 결과 보고를 받았습니다. 이번 작업은 저장된 파일을 읽는 검사 한 번이며, 학습·추론·test 평가는 실행하지 않습니다. 코드·패키지를 갱신할 필요도 없습니다.

## 받은 결과

| 사용자 실행 | 선택 epoch | threshold | 선택된 validation Dice | 학습 시간 |
|---|---:|---:|---:|---:|
| BCE only | 12 | 0.5 | 0.5211708103759707 | 95.53081978800037초 |
| BCE + 사용자 soft Dice | 13 | 0.35 | 0.5357829224369672 | 101.19188755800042초 |

Dice 차이는 B−A = **+0.0146121120609965**, 이번 학습 소요 시간 차이는 **+5.66106777000005초**입니다. epoch·threshold는 두 방식에 같은 검증 선택 규칙을 적용한 결과이며 같아야 하는 고정 설정이 아닙니다. 같은 threshold에서 비교한 점수라고 설명하지 않습니다.

사용자 Dice 실행의 보고서 모델 SHA·epoch·threshold·선택 점수는 34단계 사용자 기본 손실 실행의 보고 값과 같습니다. 이번 실행 경로와 소요 시간은 다릅니다. 보고서 값의 일치를 모델 파일을 직접 읽은 검사와 구분합니다. 이전 실행을 이번 비교군으로 대신하지 않았습니다.

## 지금 실행할 읽기 명령

**위치:** Codespaces Bash 터미널, `/workspaces/pathology-edge`. 아래 블록 전체를 붙여 넣습니다. Python 본문은 모두 같은 들여쓰기 수준이며 파일을 생성·수정하지 않습니다.

```bash
cd /workspaces/pathology-edge &&
python -c '
import json, hashlib
from pathlib import Path
paths = [Path("work/my-bce-only.FiYHbx"), Path("work/my-learner-dice.WKJxeD")]
reports = [json.loads((p / "training.json").read_text()) for p in paths]
protocols = [json.loads((p / "protocol.json").read_text()) for p in paths]
reference = json.loads(Path("artifacts/protocol.json").read_text())
controls = lambda c: {k:v for k,v in c.items() if k not in ("loss", "loss_mode", "loss_source_sha256")}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
selected = [max(((h["validation_dice"][str(t)], h["epoch"], t) for h in r["history"] for t in r["config"]["thresholds"]), key=lambda x:x[0]) for r in reports]
checks = {}
checks["loss_modes"] = [p.get("loss_mode") for p in protocols] == ["bce_only", "learner_dice"] and [p["loss"] for p in protocols] == ["BCE only", "BCE + learner soft Dice"]
checks["protocol_matches_report"] = all(p == r["config"] for p,r in zip(protocols,reports))
checks["fixed_controls"] = all(controls(p) == controls(reference) for p in protocols)
checks["environment_equal"] = reports[0]["environment"] == reports[1]["environment"]
checks["counts"] = all((r["train_images"],r["validation_images"],r["parameter_count"]) == (33,10,29761) for r in reports)
checks["manifest_equal"] = (paths[0]/"manifest.json").read_bytes() == (paths[1]/"manifest.json").read_bytes()
checks["manifest_hashes"] = all(sha(p/"manifest.json") == r["config"]["manifest_sha256"] for p,r in zip(paths,reports))
checks["source_records_equal"] = all((paths[0]/f).read_bytes() == (paths[1]/f).read_bytes() for f in ("source-commit.txt","source.diff","learner-loss-source.py"))
checks["learner_source_hash"] = sha(paths[1]/"learner-loss-source.py") == protocols[1]["loss_source_sha256"]
checks["model_file_hashes"] = all(sha(p/"model.pt") == r["model_sha256"] for p,r in zip(paths,reports))
checks["epochs_16"] = all([h["epoch"] for h in r["history"]] == list(range(1,17)) for r in reports)
checks["best_selection"] = all(s == (r["best_validation_dice"],r["best_epoch"],r["threshold"]) for s,r in zip(selected,reports))
print(json.dumps({"checks":checks,"all_passed":all(checks.values())},indent=2))
'
```

**출력 전체를 보내 주세요.** 예상 정상 출력은 12개 검사와 `all_passed`가 모두 `true`인 JSON입니다. `false`나 오류가 나오면 그대로 보내며 재학습·파일 덮어쓰기를 하지 않습니다. source 기록 차이는 문서 커밋만 달라진 경우에도 생길 수 있으므로 곧바로 학습 실패로 단정하지 않습니다.

검사 범위는 저장된 protocol·보고 환경·manifest·소스 기록·보관된 사용자 함수·모델 파일·학습 history와 선택 규칙입니다. 원본 이미지 전체의 해시를 새로 계산하거나 사용자 Codespaces를 Codex가 직접 검증하는 명령은 아닙니다. 소스 비교도 저장된 커밋·tracked source diff·사용자 함수 보관본의 범위이며 기록되지 않은 파일까지 증명하지 않습니다.

## 기록과 해석

- U48·U49: 두 비교 학습의 실행·결과 제출은 사용자 보고에 근거해 완료로 기록했습니다.
- U50: 이번 저장 조건·파일 대조 실행은 출력 수신 전까지 예정입니다.
- Codex: 수치 차이 계산·보고 간 대조·검사 명령 준비와 별도 검증을 담당합니다. 사용자의 실행으로 대신 기록하지 않습니다.

현재 말할 수 있는 내용은 “이번 두 실행에서 사용자 Dice 포함 방식의 **선택된 검증 점수가 높았다**”입니다. 검증 세트는 모델 선택에 사용됐고 한 seed의 결과입니다. 새로운 test 성능 개선·일반화·임상 효과·통계적 유의성이나 안정적인 처리 속도 차이를 입증한 결과가 아닙니다. 저장 조건 확인 후 해석을 한 단계씩 진행합니다.

[두 실행 보고](../artifacts/learning/step37-review.json) · [기여 기록](CONTRIBUTIONS.md)
