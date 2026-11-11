# 46단계: 직접 실행한 재현 로그를 PR용 브랜치에 준비

상태: **로그9개·843줄 staging 보고 확인**. 실제 폴더·브랜치 이름은 채팅으로 받지 않았으며 다음 명령에서 저장한 경로를 읽습니다. 현재 작업은 [47단계 commit·push](STEP_47.md)이고 아래 준비 명령은 다시 실행하지 않습니다. 45단계에서 고정 소스 `9c55480`의 사용자 191개 테스트·Dice42/6·정적 검사와 원본 보존 성공 JSON을 받았습니다. Docker 빌드와 새로운 데이터 실험은 수행하지 않았습니다. 면접 문장 작성은 보류 상태를 유지합니다.

[공고 대조](JOB_MATCH_2026-11-10.md)의 실제 Git 협업 보완으로 넘어갑니다. 이번 변경은 **사용자가 직접 실행한 재현의 원본 로그를 저장소에서 검토할 수 있게 추가하는 것**입니다. 새 알고리즘 구현이나 팀 협업 경력을 뜻하지 않습니다. Codex가 채팅에서 받은 요약과, 사용자 실행 폴더의 원본 로그를 구분합니다.

## 완료 보고를 받은 준비 명령 — 참고용

기존 Codespaces 터미널, `/workspaces/pathology-edge`에서 아래는 staging 출력을 받은 명령입니다. 네트워크 다운로드 없이 이미 검증한 소스로부터 **새 PR 작업 폴더**를 만들고, 원본 로그 9개를 복사해 Git에 staging합니다. 원래 저장소와 검증용 `source/`는 변경하지 않습니다. 이 단계에는 학습·재현 재실행·commit·push·PR 생성이 없습니다.

```bash
(
set -e
cd /workspaces/pathology-edge
REPRO_RUN="$PWD/work/my-ubuntu-repro.xzo4_nb_"
PIN=9c55480fc721d23160016e1c472b9bdcc8f8eb21
test "$(git -C "$REPRO_RUN/source" rev-parse HEAD)" = "$PIN"
PR_WORK="$(mktemp -d "$PWD/work/my-repro-pr.XXXXXX")"
printf 'PR folder: %s\n' "$PR_WORK"
git clone --quiet --no-hardlinks --no-checkout "$REPRO_RUN/source" "$PR_WORK"
git -C "$PR_WORK" switch -c "review/ubuntu-${PR_WORK##*.}" "$PIN"
git -C "$PR_WORK" remote set-url origin https://github.com/sokldjs554/pathology-edge.git
EVIDENCE_DIR="$PR_WORK/artifacts/reproductions/ubuntu-9c55480"
mkdir -p "$EVIDENCE_DIR"
for NAME in summary.json pytest.log pytest.xml cpp-build.log dependency-versions.json pip-check.log snapshot-imports.log static-demo.log dice-audit.json; do
cp "$REPRO_RUN/$NAME" "$EVIDENCE_DIR/$NAME"
done
git -C "$PR_WORK" add -- artifacts/reproductions/ubuntu-9c55480
printf '%s\n' "$PR_WORK" > work/step46-pr-path.txt
git -C "$PR_WORK" branch --show-current
git -C "$PR_WORK" diff --cached --stat
)
```

## 생성되는 것과 확인할 결과

- `work/my-repro-pr.<고유값>/`: 검증한 소스 커밋에서 출발하는 별도 Git 저장소입니다. 원래 미커밋 `learner_wsi.py`는 옮기거나 수정하지 않습니다.
- `review/ubuntu-<고유값>`: 그 복사본에만 생성하는 작업 브랜치입니다. 추후 GitHub PR은 이 브랜치와 `main`의 차이를 검토합니다.
- `artifacts/reproductions/ubuntu-9c55480/`: 아래 9개 원본 로그를 추가하는 예정 경로입니다.

| 파일 | 검토할 근거 |
|---|---|
| `summary.json` | 실행 소스·환경·검사 집계·보존 결과 |
| `pytest.log`, `pytest.xml` | 191개 테스트 결과와 skip/failure/error 수 |
| `cpp-build.log` | 사용자 환경에서의 실제 C++ 빌드 명령 |
| `dependency-versions.json`, `pip-check.log` | 고정 버전 일치와 패키지 의존성 검사 |
| `snapshot-imports.log` | 복사본 Python 코드·C++ 확장을 불러온 경로 |
| `static-demo.log` | 정적 데모 파일 검사 결과 |
| `dice-audit.json` | 저장 Dice42개·평균6개 및 입력 파일 해시 |

사용자가 위 파일9개·843줄 추가 통계를 제출했습니다. 폴더 경로·브랜치 이름은 아직 별도 확인하지 않았습니다. 오류가 나면 원래 폴더의 파일을 복구하거나 지우지 말고 마지막 오류를 보내 주세요. 새 작업 폴더는 그대로 남으며 경로는 성공 시 `work/step46-pr-path.txt`에도 저장됩니다.

확인 후 같은 작업 폴더에서 commit·push·PR 생성으로 이어갑니다. U58은 staging 출력 보고를 확인했으며, PR 생성·리뷰·병합은 아직 수행한 것으로 기록하지 않습니다. 도구와 명령은 Codex 제공, 실제 재현 실행과 이번 Git 조작은 사용자가 수행합니다.

Codex는 본인 실행 로그로 이 준비 명령만 별도 리허설했습니다. 사용자 원본 로그 접근이나 사용자 PR 생성과 구분합니다. [준비 확인 근거](../artifacts/learning/step46-preparation.json) · [45단계 보고 검토](../artifacts/learning/step45-review.json) · [기여 기록](CONTRIBUTIONS.md)
