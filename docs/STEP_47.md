# 47단계: 재현 로그를 커밋하고 검토 브랜치 업로드

상태: **사용자 commit·push 완료 보고와 원격 확인 완료**. 브랜치 `review/ubuntu-QEoc7d`, 커밋 `e0814061d9fee08bb0324d331d4d08e6d62a849a`를 GitHub에서 대조했고 push CI 성공도 확인했습니다. 현재 작업은 [48단계 PR 생성](STEP_48.md)이며 아래 명령을 다시 실행하지 않습니다. 46단계에서 예정한 로그9개·843줄 추가 staging 출력을 받았습니다. 사용자 폴더 경로와 브랜치 이름은 채팅으로 받지 않았으며 앞서 저장한 `work/step46-pr-path.txt`에서 읽습니다. 면접 문장 작성은 계속 보류합니다.

## 완료한 commit·push 명령 — 참고용

기존 **Codespaces Bash 터미널**, `/workspaces/pathology-edge`에서 아래는 완료 보고를 받은 실행 명령입니다. 별도 PR 작업 폴더에 이미 staging한 로그9개를 커밋하고 그 `review/ubuntu-*` 브랜치를 GitHub에 올립니다. 이 업로드로 로그가 공개 저장소의 해당 브랜치에 올라갑니다. GitHub PR 생성·병합은 다음 단계입니다.

```bash
(
set -e
cd /workspaces/pathology-edge
PR_WORK="$(cat work/step46-pr-path.txt)"
PR_BRANCH="$(git -C "$PR_WORK" branch --show-current)"
case "$PR_BRANCH" in review/ubuntu-*) ;; *) printf '예상한 PR 브랜치가 아닙니다.\n'; exit 1 ;; esac
test "$(git -C "$PR_WORK" rev-parse HEAD)" = 9c55480fc721d23160016e1c472b9bdcc8f8eb21
test "$(git -C "$PR_WORK" diff --cached --name-only | wc -l)" -eq 9
test -z "$(git -C "$PR_WORK" diff --cached --name-only -- . ':(exclude)artifacts/reproductions/ubuntu-9c55480/*')"
git -C "$PR_WORK" commit -m "docs: record Ubuntu reproduction for 9c55480"
git -C "$PR_WORK" push -u origin "$PR_BRANCH"
printf 'Branch: %s\n' "$PR_BRANCH"
git -C "$PR_WORK" log -1 --format='%h %s'
git -C "$PR_WORK" ls-remote --exit-code origin "refs/heads/$PR_BRANCH"
)
```

## 명령의 의미와 확인할 출력

- 경로와 브랜치를 저장 파일·Git에서 읽고, 시작 커밋이 `9c55480`인지 확인합니다.
- staging 파일9개가 지정된 재현 로그 경로 안에 있는지 검사한 뒤 commit합니다. 기존 Git 작성자 설정을 사용하며 사용자 이름·이메일을 임의로 설정하지 않습니다.
- `push -u`는 이 브랜치를 원격에 올리고 이후 같은 브랜치의 업로드 대상을 연결합니다. 강제 push나 `main` 병합은 하지 않습니다.
- 마지막은 브랜치 이름, 생성한 커밋, 원격 브랜치의 커밋 조회입니다. 로컬·원격 해시가 같아야 합니다. 저장소의 기존 Actions가 push로 시작될 수 있으며 그 결과는 별도로 확인합니다.

사용자가 commit·push 출력과 브랜치·해시를 제출했고 원격 일치도 확인했습니다. [검토 기록](../artifacts/learning/step47-review.json). 인증·작성자 설정 오류가 나거나 보호 조건에서 중단되면 마지막 출력을 보내 주세요. 커밋 뒤 push가 실패했다면 커밋은 남아 있으므로 이 블록 전체를 반복하지 않습니다.

이번 사용자 기여는 실제 재현 로그를 Git 변경으로 기록·게시하는 것입니다. Codex가 제공한 모델·도구·검사 코드를 사용자가 구현했다는 뜻으로 확대하지 않습니다. U59는 사용자 출력과 실제 원격 확인으로 완료했습니다. U58은 staging 보고만 확인했고 PR 생성·리뷰·병합은 아직 미수행입니다.

Codex는 본인 로그와 별도 로컬 bare 저장소를 이용해 이 Git 흐름을 리허설했습니다. 사용자 브랜치를 대신 commit·push하거나 GitHub PR을 생성한 것은 아닙니다. [준비 근거](../artifacts/learning/step47-preparation.json) · [staging 보고 검토](../artifacts/learning/step46-review.json) · [기여 기록](CONTRIBUTIONS.md)
