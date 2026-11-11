# 53단계: 고정 조건 CNN–ViT 비교 실행

상태: **실행 안내 / 사용자 실행·결과 대기**. C++ 측정과 범위 해석은 [51](STEP_51.md)·[52단계](STEP_52.md)에서 확인했습니다. 이번에는 아래 블록을 한 번 실행하고 결과를 보내는 한 단계입니다.

복사할 명령을 줄이기 위해 같은 내용을 [`scripts/start_model_comparison.sh`](../scripts/start_model_comparison.sh)에 넣었습니다. 채팅에서는 게시 커밋에 고정한 이 파일 하나를 새 `work` 경로로 받아 Bash로 실행하도록 안내합니다. 아래 블록과 스크립트를 각각 실행하지 않고 둘 중 한 방식만 사용합니다.

## 무엇을 실행하나요?

고정 소스 `917038feb5c80b1c7175d94ba44c208d9940220d`의 TinyUNet과 SmallViTSegmenter를 각각 학습합니다. 같은 seed20261113·train33장·validation10장,128px crop·batch8·16epochs×20steps·Adam0.001·BCE+사용자 soft Dice를 사용합니다. 두 모델의 crop/증강 순서는 같고, 검증 점수로 epoch와 threshold를 각각 선택합니다. 테스트7장은 파일 해시 검사만 하며 추론·평가하지 않습니다.

실행 도구와 모델은 제공된 코드를 사용합니다. 새 체크아웃에는 저장소에 반영된 사용자 손실 함수가 들어 있으며, 원래 폴더의 미커밋 수정을 새 소스에 자동 적용하지 않습니다. 기존 Python 환경을 그대로 사용합니다. 이 단계는 모델 전체를 사용자가 직접 구현했다는 기록과 구분합니다.

## Codespaces에서 한 번 실행

기존 Python 학습이 성공했던 터미널에서 아래 블록 전체를 실행합니다. 시작 폴더는 `/workspaces/pathology-edge`이며, 원래 `data`를 읽고 `work/vit-source.*`에 별도 체크아웃·결과를 만듭니다. 기존 작업 브랜치나 수정한 파일을 덮어쓰지 않습니다. 소스 다운로드·새 worktree 등록은 Git 메타데이터를 추가합니다.

```bash
cd /workspaces/pathology-edge &&
test -f data/manifest.json &&
mkdir -p work &&
PATHOLOGY_VIT_SOURCE="$(mktemp -d /workspaces/pathology-edge/work/vit-source.XXXXXX)" &&
git fetch origin 917038feb5c80b1c7175d94ba44c208d9940220d &&
git worktree add --detach "$PATHOLOGY_VIT_SOURCE" 917038feb5c80b1c7175d94ba44c208d9940220d &&
python - "$PATHOLOGY_VIT_SOURCE" <<'PY'
import runpy
import sys
import uuid
from pathlib import Path

original = Path.cwd()
source = Path(sys.argv[1]).resolve()
work = source / "work"
work.mkdir(exist_ok=True)
(work / "SOURCE_PATH.txt").write_text(str(source) + "\n")
print("SOURCE_DIR=" + str(source), flush=True)
helper = runpy.run_path(str(source / "scripts/run_model_comparison.py"))
before = helper["original_state"](original)
helper["dump"](work / "original-before.json", before)
try:
    helper["run"](source, original / "data", work / ("my-cnn-vit." + uuid.uuid4().hex[:12]))
finally:
    after = helper["original_state"](original)
    helper["dump"](work / "original-after.json", after)
    if before != after:
        raise RuntimeError("Original checkout changed; inspect original-before/after.json")
    print("ORIGINAL_FILES_PRESERVED=true", flush=True)
PY
```

`data/manifest.json`이 없으면 학습 전에 중단합니다. 첫 단계에서 출력 없이 멈췄다면 그 상태를 알려 주세요.

실행 중에는 원래 작업 폴더나 새 체크아웃의 코드·브랜치를 바꾸지 않습니다. 각각16개의 epoch 출력 후 `SUMMARY {...}`가 나옵니다. 학습·검증 시간은 환경과 부하에 따라 달라지며 이전 참고 시간과 같을 필요는 없습니다. 이전 참고 점수보다 높거나 낮아도 결과를 고르기 위해 재실행하지 않습니다.

## 보내 줄 출력

- 마지막 `SUMMARY {...}` 전체: 두 모델 점수·선택 epoch/threshold·시간·`all_checks_passed`·`original_files_preserved`·`test_evaluation_run`을 포함합니다.
- 마지막 `ORIGINAL_FILES_PRESERVED=true` 줄: 원래 체크아웃의 학습 전후 상태를 별도 비교한 결과입니다.

`SUMMARY`의 보존 검사는 **새 학습 체크아웃**, 마지막 표시는 **원래 작업 체크아웃**을 대상으로 합니다. 원래 체크아웃 검사는 추적 파일과 Python 소스 해시·Git commit/status 비교이며 모든 ignored 파일·Git 내부 메타데이터까지 포함하는 검사는 아닙니다. 원래 데이터는 학습 실행기의 manifest·파일 해시 검사로 별도 확인합니다.

실패하면 오류와 `SOURCE_DIR`/`RUN_DIR` 경로를 보내 주세요. 성공한 SUMMARY 없이 보존 표시만 나왔다면 학습 완료가 아닙니다. 실패 로그와 부분 결과는 그대로 둡니다. 터미널이 초기화돼도 `work/vit-source.*/work/SOURCE_PATH.txt`와 내부 `my-cnn-vit.*/RUN.txt`에 경로가 남습니다. 결과를 확인한 뒤 검토 질문을 한 단계씩 진행합니다.

이 명령의 원본 보존·오류 종료 동작은 작은 임시 저장소에서 확인했습니다. 학습 부분은 모의 함수로 바꾸고 성공·학습 실패·원본 변경3경로를 확인했으며 새 모델 학습은 실행하지 않았습니다. [검증 범위](../artifacts/learning/step53-preparation.json). 사용자의 새 학습 결과를 받기 전에는 실행 완료로 기록하지 않습니다.
