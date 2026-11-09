# 12단계: 실제 목록의 그룹과 저장된 이미지 해시 함께 검사

상태: **사용자 실행·출력 제출 대기**. 11단계에서 사용자는 서로 다른 그룹의 같은 파일이 분할을 넘을 수 있으므로 해시 비교도 필요하다고 설명했습니다. 이번에는 새 함수를 작성하지 않고 확인 명령 하나를 실행합니다.

2026-11-09 받은 후속 출력에는 기존 그룹 검사 결과만 있고 `unique_image_hashes`·`image_hash_leaks`가 없습니다. 해시 검사를 실행했는지 확인되지 않아 완료나 실패로 기록하지 않았습니다. 아래의 **해시 검사만 다시 확인하기** 명령으로 두 줄을 확인합니다. [출력 검토 기록](../artifacts/learning/step12-output-incomplete.json).

## 무엇을 확인하는가

`artifacts/manifest.json`의50개 레코드에서 사용자 작성 `find_group_leaks`로 그룹 ID를 검사하고, 저장된 `image_sha256`이 서로 다른 split에 등장하는지도 비교합니다. 해시 비교와 출력 코드는 Codex 제공입니다. 이를 사용자 작성 코드로 기록하지 않습니다.

이번 명령은 저장된 해시 문자열을 비교합니다. 원본 이미지 파일을 읽어 SHA-256을 새로 계산하는 작업은 아니며, 새 데이터 다운로드·패키지 설치·모델 추론은 필요하지 않습니다.

## 실행 명령

Mac 터미널에서 **저장소 루트**로 이동해 기존 가상환경을 활성화한 뒤 아래 블록 전체를 실행합니다. 새 파일을 받을 필요는 없습니다.

```bash
cd ~/Projects/pathology-edge
source .venv/bin/activate

PYTHONPATH=src python - <<'PY'
import json
from collections import defaultdict
from pathlib import Path
from pathology_edge.learner_split import find_group_leaks

records = json.loads(Path("artifacts/manifest.json").read_text())["records"]
hash_splits = defaultdict(set)
for record in records:
    hash_splits[record["image_sha256"]].add(record["split"])
hash_leaks = {h: sorted(splits) for h, splits in hash_splits.items() if len(splits) > 1}

print("records:", len(records))
print("unique_image_hashes:", len(hash_splits))
print("group_leaks:", find_group_leaks(records))
print("image_hash_leaks:", hash_leaks)
PY
```

기대 출력:

```text
records: 50
unique_image_hashes: 50
group_leaks: {}
image_hash_leaks: {}
```

**터미널 출력 전체**를 보내 주세요. 실패하면 실행 명령과 traceback을 함께 보내 주세요. 사용자가 실행하기 전에는 완료로 기록하지 않습니다.

## 해시 검사만 다시 확인하기

그룹 검사 실행은 이미10단계에서 확인했습니다. 아래는 남은 저장 해시 비교만 수행하는 축약 명령입니다. **저장소 루트**에서 실행하며 추가 패키지는 필요하지 않습니다.

```bash
cd ~/Projects/pathology-edge
source .venv/bin/activate
python - <<'PY'
import json
from pathlib import Path

records = json.loads(Path("artifacts/manifest.json").read_text())["records"]
seen = {}
for record in records:
    seen.setdefault(record["image_sha256"], set()).add(record["split"])
print("unique_image_hashes:", len(seen))
print("image_hash_leaks:", {h: sorted(s) for h, s in seen.items() if len(s) > 1})
PY
```

기대 결과는 `unique_image_hashes: 50`과 `image_hash_leaks: {}`입니다. **이 명령에서 실제로 출력된 두 줄**을 보내 주세요. 출력이 다르거나 오류가 나면 해당 내용을 그대로 보내 주세요.

## 결과를 해석할 범위

두 `{}`는 이 목록에서 그룹 ID와 저장된 동일 파일 해시가 여러 split에 걸쳐 나타나지 않는다는 뜻입니다. 같은 영상을 다른 인코딩으로 저장한 파일이나 서로 겹치는 crop은 파일 해시가 다를 수 있어 별도 검토가 필요합니다. 실제 환자의 독립성도 이 검사로 확인하지 않습니다.

- 사용자 완료: 그룹 함수 작성·18개 테스트 보고·그룹 목록 검사 실행·그룹과 파일 중복 구분 설명.
- 사용자 예정: 이번 명령 실행과 출력 제출.
- Codex 완료: 해시 비교 호출 코드 제공, 실제50개 레코드 확인, 합성 동일 해시 사례가 검출되는지 대조. [준비 기록](../artifacts/learning/step12-preparation.json).
