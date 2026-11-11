# 45단계: 별도 소스 복사본으로 Ubuntu 재현 검사

상태: **사용자 실행·성공 JSON 보고 확인 완료**. `my-ubuntu-repro.xzo4_nb_`에서 고정 소스 191개 테스트·Dice42/6·C++ 빌드·정적 데모 검사와 원본 보존 성공을 보고했습니다. [제출 요약](../artifacts/learning/step45-user-summary.json) · [검토 기록](../artifacts/learning/step45-review.json). 46단계 로그 staging 보고도 받아 47단계 commit·push와 공개 로그·CI 대조도 마쳐 현재 할 일은 [48단계 PR 생성](STEP_48.md)이며 아래 재현 명령은 다시 실행하지 않습니다. 44단계에서 사용자 Codespaces는 `0b1cdea`, 수정 파일은 `src/pathology_edge/learner_wsi.py` 하나, 작업 폴더 여유 공간은 약26GB라는 보고를 받았습니다. Docker 실행 파일은 현재 경로에서 찾지 못했습니다. 43단계 면접 문장 작성은 계속 보류합니다.

## 완료한 실행 절차 — 참고용

현재 Ubuntu·Python 환경으로 **고정된 공개 소스 복사본을 검증**합니다. 기존 저장소를 갱신하거나 Python 패키지를 재설치하지 않습니다. 검증 대상은 제출 코드가 검토·반영된 소스 커밋 `9c55480fc721d23160016e1c472b9bdcc8f8eb21`입니다. 이후 추가한 안내 문서·재현 도구의 커밋과 구분합니다.

**위치:** 기존 Codespaces Bash 터미널, `/workspaces/pathology-edge` 저장소 루트. 아래는 완료한 실행 명령입니다.

```bash
(
set -e
cd /workspaces/pathology-edge
mkdir -p work
REPRO_SCRIPT="$(mktemp "$PWD/work/reproduce-step45.XXXXXX.py")"
curl -fL --retry 2 --connect-timeout 20 --max-time 120 https://raw.githubusercontent.com/sokldjs554/pathology-edge/5dd3ed93c472f96ea14be362118b040cfcb4d36b/scripts/reproduce_snapshot.py -o "$REPRO_SCRIPT"
printf '%s  %s\n' ce75b14cb851bdd20af7c050be70ff5fd724d9ad3adef625bdc09c2cd05dc321 "$REPRO_SCRIPT" | sha256sum -c -
python -u "$REPRO_SCRIPT"
)
```

도구는 고정 커밋과 SHA-256을 확인해 내려받습니다. GitHub에서 별도 소스를 받고 C++을 빌드하므로 네트워크 속도에 따라 수분 걸릴 수 있습니다. 이번 Codex 복사본은 실행 폴더 약427MB를 사용했으며, 시작 전 최소2GiB 여유 공간을 검사합니다. 설치·업데이트·Docker 명령은 없습니다.

## 명령이 수행하는 범위

1. 새 `work/my-ubuntu-repro.<고유값>/`에 원래 Git 커밋·변경 상태·추적 파일 및 Python 소스 해시를 기록하고, 원래 Python 소스를 백업합니다.
2. 그 안의 `source/`에 고정 커밋을 받습니다. 현재 수정 중인 `learner_wsi.py`를 덮어쓰거나 이 복사본에 덧씌우지 않습니다.
3. 현재 설치 패키지와 고정 lock의 버전 및 의존성을 확인하고, 복사본에서 GCC로 C++ 확장을 빌드합니다. 각 검사 프로세스만 복사본을 import하므로 기존 editable 설치 경로는 유지합니다.
4. 고정 소스의 전체 **191개 테스트·skip 0개**, 저장 **42개 Dice·6개 평균**, 데모의 정적 파일 연결을 검사합니다.
5. 원래 저장소의 커밋·변경 상태·파일 해시를 다시 비교하고 JSON과 단계별 로그를 저장합니다. 실패해도 새 실행 폴더와 실패 기록을 남깁니다.

사용자가 직접 작성한 파일의 원본 보존을 검사하는 것과, 그 미커밋 파일을 새로 검토하는 것은 구분합니다. 이번 실행 대상은 공개 소스에 반영된 검토 완료 버전입니다. 원래 `work/`의 모델·학습 결과는 이 도구의 입력이나 출력 대상이 아닙니다.

전체 테스트에는 작은 합성 입력으로 모델 연산·학습 함수를 확인하는 검사가 포함됩니다. 새로운 TNBC 학습·테스트 성능 실험, WSI 추론, 브라우저 조작, Docker 이미지 빌드는 수행하지 않습니다. 정적 데모 검사는 실제 브라우저 화면 검사와 다릅니다.

## 제출 완료한 결과와 검사 기준

마지막 `SUMMARY` JSON 전체를 받았습니다. 제출값은 아래 기준과 모두 일치합니다. 사용자 실행 폴더의 원본 로그를 Codex가 직접 열어 본 검증과 구분합니다.

- `all_checks_passed: true`
- `original_files_preserved: true`
- `source_commit: 9c55480fc721d23160016e1c472b9bdcc8f8eb21`
- `checks.tests`: `tests: 191`, `skipped: 0`, `failures: 0`, `errors: 0`
- `dice_checks: 42`, `mean_checks: 6`, `cpp_rebuilt: true`, `static_demo_check: true`
- `docker_build_run: false`

오류가 나면 자동 설치·재시도 대신 JSON과 오류 마지막 부분을 보내 주세요. 버전 불일치도 원본 환경을 바꾸지 않고 중단합니다. JSON이 나오기 전 실패했다면 마지막 출력만 보내면 됩니다. 사용자 U57은 성공 보고를 받아 완료로 기록했습니다.

## 역할과 Codex 검증

사용자 역할은 위 재현 실행·로그 제출입니다. 도구·검사 설계·실행 안내는 Codex 작성입니다. Codex Linux 호스트에서는 이 고정 소스의 191개·Dice42/6·정적 검사를 통과했고 원본 보존도 확인했습니다. 현재 저장소는 도구 자체의 10개 추가 검사를 포함해 **201개**가 통과했습니다. 191개와201개는 서로 다른 코드 범위입니다.

첫 Codex 실행에서 기본 `clang++`가 없어 실패한 후, 기존 Docker/devcontainer와 동일하게 GCC를 명시했습니다. 독립 검토에서 부모의 `PYTHONOPTIMIZE`가 검증 assert를 제거할 수 있는 문제를 찾아 제거했고, 회귀 검사와 부모 최적화가 켜진 상태의 전체 재현을 통과했습니다. 최종 호스트는 Debian 기반이며 사용자 Ubuntu 성공이나 Docker 성공으로 기록하지 않습니다.

[준비·검증 근거](../artifacts/learning/step45-preparation.json) · [Codex 전체 실행 요약](../artifacts/learning/step45-codex/summary.json) · [기여 기록](CONTRIBUTIONS.md)
