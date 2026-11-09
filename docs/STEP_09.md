# 9단계: 분할을 넘나드는 케이스 그룹 찾기

상태: **2026-11-09 사용자 코드·테스트 실행 보고 검토 완료**. 제출한 본문과 `18 passed in 0.04s`를 확인했습니다. 알고리즘 수정 없이 반영했으며 Codex 독립18개·전체107개 검사가 통과했습니다. 아래는 완료한 과제의 계약과 재실행 참고입니다. 현재 할 일은 [10단계 실제 그룹 분리 확인](STEP_10.md)입니다.

## 작성 위치와 역할

- 파일: `src/pathology_edge/learner_split.py`
- 함수: `find_group_leaks(records: list[dict]) -> dict[str, list[str]]`
- 역할: 같은 케이스 그룹이 train·validation·test 중 둘 이상에 등장하는 경우를 모두 보고합니다.

기존 `data.check_split`은 그룹·파일 hash·중복 ID를 검사하다 문제가 있으면 예외로 멈춥니다. 이번 함수는 **그룹 단위 누수 보고**에만 집중하는 독립 실습입니다. 기존 함수를 호출하거나 수정하지 않습니다. 이미지 hash가 달라도 같은 그룹이면 이 검사 대상입니다.

## 입출력과 조건

| 항목 | 계약 |
|---|---|
| `records` | dict들의 list. 각 dict의 `group_id`와 `split`만 읽고 다른 필드는 무시 |
| `group_id` | 공백만으로 이루어지지 않은 문자열. 문자열을 그대로 식별자로 사용하며 정수 변환·공백 제거 등 정규화 금지 |
| `split` | 문자열 `train`, `validation`, `test` 중 하나 |
| 반환 | 누수 그룹을 key로, 등장한 분할들의 list를 value로 하는 dict |
| 분할 목록 | 중복 없이 **train → validation → test** 순서. dict key 순서는 요구하지 않음 |
| 누수 없음·빈 입력 | `{}`. 빈 입력에 누수가 없다는 뜻이며, 유효한 학습 데이터셋이라는 뜻은 아님 |
| 잘못된 입력 | list가 아니거나, 원소가 dict가 아니거나, 필수 필드 누락·타입/값 오류이면 `ValueError`. 메시지 문구는 자유 |
| 입력 보존 | list·dict·추가 필드를 수정하지 않음. 입력 레코드 순서가 바뀌어도 반환 내용은 동일 |

한 그룹이 같은 split에 여러 번 등장하는 것은 허용합니다. 모든 누수 그룹을 반환해야 하며 처음 발견한 하나만 반환하면 안 됩니다. 누수 자체는 정상적인 **검사 결과**이므로 예외를 발생시키지 않습니다.

## 손으로 확인할 예시

합성 입력입니다. 실제 데이터 분리를 바꾼 것이 아닙니다.

```python
records = [
    {"group_id": "01", "split": "test"},
    {"group_id": "02", "split": "validation"},
    {"group_id": "01", "split": "train"},
    {"group_id": "01", "split": "test"},
]
```

기대 반환값:

```python
{"01": ["train", "test"]}
```

## 직접 작성할 부분과 제공 코드

- 사용자: `find_group_leaks` 본문 전체. 입력 검증과 그룹별 분할 보고를 작성합니다.
- Codex: 함수 서명·계약·빈 본문, `tests/learner/test_group_leaks.py`의18개 검사.
- Python 표준 라이브러리만 사용합니다. NumPy·영상 라이브러리·모델 설치는 필요하지 않습니다.
- 처음에는 빈 함수만 제공했습니다. 현재 본문은 사용자가 제출한 코드이며 채팅의 HTML·Markdown 이스케이프만 정리했습니다. 알고리즘은 수정하지 않았습니다.

## 파일 받기

이미 작성한 파일이 있으면 다시 받을 필요가 없습니다. 아래는 새 작업 폴더에서 검토 완료 파일 두 개를 받는 참고 명령입니다. 기존 Dice 파일은 갱신하지 않습니다. 이미 파일이 있으면 작성 내용을 보존합니다.

```bash
cd ~/Projects/pathology-edge
git fetch origin
if [ -e src/pathology_edge/learner_split.py ] || [ -e tests/learner/test_group_leaks.py ]; then
  printf '%s\n' '실습 파일이 이미 있습니다. 작성 내용을 보존하고 해당 파일을 확인하세요.'
else
  git restore --source=origin/main -- src/pathology_edge/learner_split.py tests/learner/test_group_leaks.py
fi
source .venv/bin/activate
python -m pip install pytest
```

Python3.10 이상과 pytest면 이 실습을 실행할 수 있습니다. 본문은 이미 제출·검토됐습니다. **사용자 로컬 구현의 저장 위치는 `src/pathology_edge/learner_split.py`입니다.**

## 작성 후 검사

**같은 저장소 루트**에서 이번 함수의 계약만 검사합니다.

```bash
python -m pytest --run-learner tests/learner/test_group_leaks.py -q
```

검토 완료한 코드의 기대 결과는 **18 passed**입니다. 이18개는 일반 전체 검사에도 포함되며 `--run-learner` 없이 실행해도 됩니다. 전체 결과는 **107 passed, 0 skipped**입니다. 준비 당시89통과/18skip과 빈 함수의 실패 로그는 과거 증거로 유지합니다.

## 검토 결과와 다음 단계

`strip()`은 공백뿐인 그룹인지 검사하는 데만 사용해 원래 식별자를 보존합니다. set으로 같은 분할의 반복을 제거하고, 명시한 순서로 모든 누수 그룹을 반환합니다. 입력 보존·잘못된 입력·빈 입력 계약도 충족했습니다.
Codex는 이 함수로 실제50개 레코드의 그룹 누수가 없고, 메모리 복사본의 합성 분할 오류는 검출함을 확인했습니다. [검토 기록](../artifacts/learning/step09-review.json) · [실제 목록 검증](../artifacts/learning/step09-real-group-audit.json).

사용자의 실제 목록 검사 실행은 아직 예정입니다. 다음은 [STEP_10.md](STEP_10.md)의 명령 하나를 실행하고 출력 전체를 보내는 단계입니다.

## 검사의 한계

이 함수가 누수 없음을 반환해도 서로 다른 그룹에 같은 이미지가 있는지, 비슷한 crop이 있는지, 실제로 서로 다른 환자인지까지 보장하지 않습니다. 파일 hash·유사 이미지·환자 명부 검사는 별개입니다. 이번 과제에서는 데이터를 옮기거나 모델을 재학습하지 않습니다.
