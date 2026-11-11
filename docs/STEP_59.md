# 59단계: 완료한 보정 비교의 원본 보관

상태: **사용자 원본 ZIP·SHA 수신,70개 파일·두 모델SHA·60영역 독립 감사 완료**. [최종 감사 결과](USER_REFINEMENT_AUDIT.md). 아래 압축 명령은 기록용이며 다시 실행할 필요가 없습니다. 추가 필수 사용자 과제는 없습니다.

## 이번 사용자 실행에서 확인한 수치

[제출 SUMMARY 원문 수치](../artifacts/learning/step58-user-summary.json) · [검산과 확인 범위](../artifacts/learning/step58-user-review.json).

| 항목 | SmallViT | + 작성한 보정 모듈 | 변화 |
|---|---:|---:|---:|
| 검증 전체 Dice | 0.570565 | 0.590386 | +0.019820 |
| 검증 경계 Dice | 0.558802 | 0.559040 | +0.000238 |
| 검증 내부 Dice | 0.560475 | 0.582999 | +0.022525 |
| CPU 파이프라인 중앙값 | 43.672ms | 55.680ms | +12.009ms |
| 학습+epoch 검증 시간 | 34.852s | 52.631s | +17.779s |
| 전체 worker 최대 RSS | 469.395MiB | 481.242MiB | +11.848MiB |

전체·내부 Dice의 상승 폭에 비해 경계 변화는 매우 작습니다. 이 한 결과로 경계 문제가 해결됐거나 개선이 일반화된다고 말하지 않습니다. CPU 파이프라인 시간은 약27.50% 늘었으며, 시간·전체 worker RSS는 관찰값이고 통제된 속도/모듈 단독 메모리 측정이 아닙니다.

기준 모델은 epoch12·threshold0.35, 보정 모델은 epoch14·threshold0.35를 선택했습니다. seed20261116, train33/validation10, 검증2그룹이며 test7장 평가는 미수행으로 보고됐습니다. 초기 ViT SHA는 기존 고정 사전 검사와 일치하고, 세 Dice 차이는 제출된 원본 수치에서 다시 빼도 같습니다.

사용자 환경은 EPYC7763·논리CPU2·Python3.12.3입니다. EPYC9V74·논리CPU5·Python3.12.14에서 수행한 개발 참고 비교와 별도로 기록합니다. 개발 참고에서는 보정 모델 epoch13을 선택했고 경계 Dice가 감소했습니다. 환경·선택 결과의 차이를 같은 실험의 추가 seed로 합치거나 원인을 단정하지 않습니다.

처음에는 SUMMARY와 `ORIGINAL_FILES_PRESERVED=true`를 확인했고, 이후 `refinement-evidence.nvOJR4.zip`과 SHA를 받아 실제 파일까지 대조했습니다. 모델SHA·동결 소스/실행기·확률맵60영역과 제출 SUMMARY가 모두 일치합니다. [원본 감사 기록](../artifacts/experiments/user-vit-refinement-20261112/review.json).

## Codespaces에서 ZIP 만들기

저장소 루트 `/workspaces/pathology-edge`에서 아래 블록을 실행합니다. Python 표준 ZIP 도구만 사용하며, 이번 성공 경로를 명시해 실패한 이전 폴더가 선택되지 않도록 했습니다. 원본을 읽어 새 ZIP을 만들고 ZIP 자체의 SHA256을 출력합니다. 모델 학습·추론은 실행하지 않습니다.

```bash
(
set -e
cd /workspaces/pathology-edge
PATHOLOGY_REFINEMENT_PARENT=/workspaces/pathology-edge/work/refinement-source.586qqgs1/work
PATHOLOGY_REFINEMENT_ARCHIVE="$(mktemp /workspaces/pathology-edge/work/refinement-evidence.XXXXXX.zip)"
/opt/venv/bin/python -m zipfile -c "$PATHOLOGY_REFINEMENT_ARCHIVE" \
  "$PATHOLOGY_REFINEMENT_PARENT/my-vit-refinement.0881ce7d2afe" \
  "$PATHOLOGY_REFINEMENT_PARENT/launcher-status.json" \
  "$PATHOLOGY_REFINEMENT_PARENT/learner-connection.json" \
  "$PATHOLOGY_REFINEMENT_PARENT/submitted_learner_refinement.py" \
  "$PATHOLOGY_REFINEMENT_PARENT/original-before.json" \
  "$PATHOLOGY_REFINEMENT_PARENT/original-after.json" \
  "$PATHOLOGY_REFINEMENT_PARENT/SOURCE_PATH.txt"
sha256sum "$PATHOLOGY_REFINEMENT_ARCHIVE"
)
```

마지막 줄은 `SHA256  /workspaces/pathology-edge/work/refinement-evidence.XXXXXX.zip` 형식입니다. 이 SHA 줄과 해당 ZIP을 보내 주세요. Codespaces 왼쪽 Explorer에서 출력된 ZIP을 찾아 우클릭 → **Download**로 받은 뒤 채팅에 첨부하면 됩니다. 오류가 나면 새 학습을 하지 말고 메시지를 보내 주세요.

두 체크포인트·20개 검증 확률맵·동결 코드/실행기·학습 로그·설정·소스/데이터 해시·새/원래 체크아웃과 실습 파일 보존 기록을 받기 위한 단계입니다. ZIP의 SHA/CRC 확인은 운반 중 무결성 검사이며 과학적 검산 자체를 대신하지 않습니다. 원본을 받으면 저장 확률에서60개 평가 영역을 재계산하고 제출한 모델 SHA와 대조합니다. 첨부된 스냅샷 코드를 실행하거나 새 학습으로 사용자 원본을 대체하지 않습니다.

준비 과정에서는 같은 형식의 개발 참고 실행을 실제 표준 ZIP 명령으로 묶고70개 파일 내용·모델 SHA·원본 파일 보존을 확인했습니다. [준비 검증 범위](../artifacts/learning/step59-preparation.json). 이후 사용자 ZIP과 SHA를 받아 생성·제출을 확인했습니다. 당시 준비 검증과 이번 원본 독립 감사는 별도 기록입니다.
