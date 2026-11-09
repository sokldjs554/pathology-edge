# 10단계: 직접 작성한 함수로 실제 그룹 분리 확인

상태: **사용자 실행·결과 제출 대기**. 9단계 함수 본문과 `18 passed in 0.04s` 보고를 확인했습니다. 이번에는 새 함수를 작성하지 않고 기존 실험의 데이터 목록에 본인 함수를 적용합니다.

## 무엇을 확인하는가

`artifacts/manifest.json`은 저장소에 포함된 TNBC50장 전체의 분리 기록입니다. 각 `records` 항목에는 `id`, `group_id`, `split`, 이미지·마스크 경로와 hash 등이 있습니다. 이번에는 `group_id`와 `split`만 검사합니다. 픽셀 파일 다운로드나 모델 설치는 필요하지 않습니다.

아래 호출 코드는 Codex 제공이며, 그룹을 판단하는 `find_group_leaks` 본문은 사용자 작성입니다. 빈 입력에도 `{}`를 반환하는 계약이므로, 실제로50개 레코드를 읽었는지도 함께 출력합니다.

## 직접 실행할 명령 하나

Mac 터미널에서 **`pathology-edge` 저장소 루트**로 이동해 기존 가상환경을 활성화합니다. 새 파일을 받을 필요는 없습니다.

```bash
cd ~/Projects/pathology-edge
source .venv/bin/activate
```

같은 폴더에서 아래 블록 전체를 실행합니다. `PYTHONPATH=src`는 이 명령이 현재 프로젝트의 `src/pathology_edge/learner_split.py`를 읽도록 지정합니다.

```bash
PYTHONPATH=src python - <<'PY'
import json
from collections import Counter
from pathlib import Path
from pathology_edge.learner_split import find_group_leaks

records = json.loads(Path("artifacts/manifest.json").read_text())["records"]
print("records:", len(records))
print("groups:", len({r["group_id"] for r in records}))
print("images_by_split:", dict(Counter(r["split"] for r in records)))
print("group_leaks:", find_group_leaks(records))
PY
```

기대 출력:

```text
records: 50
groups: 11
images_by_split: {'train': 33, 'validation': 10, 'test': 7}
group_leaks: {}
```

11그룹은 train·validation·test 전체에 걸친 수이며, 앞서 평가한 test만의 그룹 수는2입니다.

**터미널 출력 전체**를 보내 주세요. 실패하면 실행 명령과 traceback도 함께 보내 주세요. `NotImplementedError`이면 실제로 불러온 `src/pathology_edge/learner_split.py`에 아직 빈 함수가 남아 있는지 확인합니다. 작성한 본문을 다른 파일에 저장하지 않았는지도 확인해 주세요.

## 결과의 범위와 기여

`group_leaks: {}`는 **이 목록의 그룹 ID가 서로 다른 split에 걸쳐 나타나지 않는다**는 뜻입니다. 서로 다른 그룹에 같은 이미지나 유사 crop이 없는지, 실제 환자가 독립적인지까지 확인하지는 않습니다. 이미지 hash를 다시 계산하거나 학습·추론을 실행하는 명령이 아닙니다.

- 사용자 완료: 함수 본문 작성·18개 단위 테스트 통과 보고.
- 사용자 예정: 위 실제 metadata 검사 실행과 출력 제출.
- Codex 완료: 같은 함수로 실제50개 레코드의 `{}`를 확인하고, 메모리에서만 한 레코드의 split을 바꾼 합성 오류가 검출되는지 확인. 원본 파일은 보존했습니다. [검증 기록](../artifacts/learning/step09-real-group-audit.json).
