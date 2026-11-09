# 9단계: 분할을 넘나드는 케이스 그룹 찾기

상태: **사용자 코드 작성·테스트 실행 대기**. 이번에는 함수 하나만 작성합니다.

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
- 정답 구현은 제공하지 않았습니다. 제출 후 검토하며, 구체적인 도움을 요청하면 설명합니다.

## 파일 받기

Mac 터미널에서 **저장소 루트**로 이동해 새 실습 파일 두 개만 받습니다. 기존 Dice 파일은 갱신하지 않습니다. 이미 파일이 있으면 작성 내용을 보존합니다.

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

Python3.10 이상과 pytest면 이 실습을 실행할 수 있습니다. 함수 파일을 편집기에서 열고 `raise NotImplementedError(...)`를 본인 구현으로 교체해 저장하세요. **정확한 저장 위치는 `src/pathology_edge/learner_split.py`입니다.**

## 작성 후 검사

**같은 저장소 루트**에서 이번 함수의 계약만 검사합니다.

```bash
python -m pytest --run-learner tests/learner/test_group_leaks.py -q
```

작성 후 기대 결과는 **18 passed**입니다. 빈 함수인 상태에서는18개가 `NotImplementedError`로 실패하며, 이를 구현 완료나 통과로 기록하지 않습니다. 검토 전까지 일반 전체 검사에서는 이18개를 skip합니다.

**작성한 함수와 테스트 출력 전체**를 보내 주세요. 실패하면 실행 명령과 traceback을 함께 보내 주세요. 전체 프로젝트 검사는 이번 사용자 과제가 아닙니다.

## 검사의 한계

이 함수가 누수 없음을 반환해도 서로 다른 그룹에 같은 이미지가 있는지, 비슷한 crop이 있는지, 실제로 서로 다른 환자인지까지 보장하지 않습니다. 파일 hash·유사 이미지·환자 명부 검사는 별개입니다. 이번 과제에서는 데이터를 옮기거나 모델을 재학습하지 않습니다.
