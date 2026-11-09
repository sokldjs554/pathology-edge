# 12단계: 실제 목록의 그룹과 저장된 이미지 해시 함께 검사

상태: **2026-11-09 사용자 해시 검사 실행 보고 확인 완료**. 사용자가 `unique_image_hashes: 50`, `image_hash_leaks: {}`를 제출했습니다. 저장된 목록과 일치합니다. [실행 보고 검토](../artifacts/learning/step12-review.json). 아래는 재실행 참고이며, 다음은 [13단계 데모 악화 경계 확인](STEP_13.md)입니다.

처음 받은 후속 출력에는 그룹 결과만 있어 완료·실패로 기록하지 않았습니다. 축약 명령 안내 뒤 필요한 두 줄을 받았으므로 현재는 완료입니다. [이전 출력 누락 기록](../artifacts/learning/step12-output-incomplete.json)은 당시 증거로 보존합니다.

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

필요한 출력 두 줄을 받아 완료로 기록했습니다. 지금 다시 실행할 필요는 없습니다. 이후 재실행에 실패하면 실행 명령과 traceback을 보내 주세요.

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

기대 결과는 `unique_image_hashes: 50`과 `image_hash_leaks: {}`이며, 사용자가 이 두 줄을 제출했습니다. 이후 재실행에서 출력이 다르거나 오류가 나면 해당 내용을 그대로 보내 주세요.

## 결과를 해석할 범위

두 `{}`는 이 목록에서 그룹 ID와 저장된 동일 파일 해시가 여러 split에 걸쳐 나타나지 않는다는 뜻입니다. 같은 영상을 다른 인코딩으로 저장한 파일이나 서로 겹치는 crop은 파일 해시가 다를 수 있어 별도 검토가 필요합니다. 실제 환자의 독립성도 이 검사로 확인하지 않습니다.

- 사용자 완료: 그룹 함수 작성·18개 테스트 보고·그룹 목록 검사 실행·그룹과 파일 중복 구분 설명.
- 사용자 완료: 이번 저장 해시 비교 명령 실행과 두 줄 출력 제출. 비교 코드는 Codex 제공이며 원본 이미지 재해시를 수행한 것은 아닙니다.
- Codex 완료: 해시 비교 호출 코드 제공, 실제50개 레코드 확인, 합성 동일 해시 사례가 검출되는지 대조. [준비 기록](../artifacts/learning/step12-preparation.json).
