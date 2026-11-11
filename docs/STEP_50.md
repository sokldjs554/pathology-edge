# 50단계: Docker 재현 결과 확인

상태: **Codex 실행 준비 중 / 사용자 결과 확인 예정**. 면접 문장 작성은 보류합니다.

45단계에서는 사용자가 Codespaces의 기존 패키지로 고정 소스를 재현했습니다. 이번에는 GitHub가 제공하는 Ubuntu 24.04 실행 환경에서 루트 Dockerfile을 빌드하고, 생성한 이미지 안에서 검사합니다. Codespaces에 Docker를 설치하거나 작성한 파일을 갱신할 필요가 없습니다.

## 역할과 실행 범위

- Codex: `.github/workflows/docker-reproduction.yml`과 `scripts/check_docker.sh` 구현, 첫 실제 실행·로그 검토.
- 사용자: Codex 실행이 성공한 뒤 안내한 결과 화면 한 가지 확인. 아직 수행하지 않았습니다.
- 수동 실행 전용이며 기존 push/PR의 `CPU checks`와 별도입니다. 실행 주체 입력은 기여 증빙을 대신하지 않습니다.
- 빌드한 이미지 ID로 실행하고 커밋 라벨·추적 파일 SHA256을 대조합니다. `.openai` 배포 설정은 기존 `.dockerignore`에 따라 제외됩니다. C++ 바이너리는 이미지 안에서 새로 빌드합니다.
- 컨테이너에서 고정 패키지·Python/C++ import·전체 pytest(0 skip)·저장 Dice 42개/평균6개·정적 데모·HTTP 응답을 검사합니다. 검사 후에도 추적 파일 해시가 같은지 확인합니다.
- 검사 컨테이너는 외부 네트워크 없이 실행합니다. 이미지 빌드 중에는 Ubuntu·Python 패키지를 내려받습니다.
- 새 데이터셋 학습·성능 평가·브라우저 조작·데모 배포는 포함하지 않습니다. 단위 테스트의 합성 모델 연산은 실행될 수 있습니다.

## 지금 확인할 화면

Codex의 첫 실제 실행이 끝나면 실행 링크와 확인할 상태를 여기에 기록합니다. 사용자에게는 성공한 실행의 **Summary** 확인만 배정하며 동일 빌드 반복은 요구하지 않습니다.

나중에 직접 다시 실행하려면 [Actions → Docker reproduction](https://github.com/sokldjs554/pathology-edge/actions/workflows/docker-reproduction.yml)에서 **Run workflow → main → execution_owner: user → Run workflow**를 누릅니다. 이는 현재 과제로 배정하지 않았습니다.

로그는 실행 화면 **Artifacts**의 `docker-reproduction-커밋-시도번호`에서 30일간 내려받을 수 있습니다. 실행 실패 시 실행 URL과 실패한 단계 이름을 보내면 됩니다. 실패한 빌드나 일부 검사만으로 전체 성공을 기록하지 않습니다.

## 재현의 한계

Python 패키지는 잠겨 있지만 `ubuntu:24.04` 태그와 apt 패키지는 시간이 지나면 바뀔 수 있습니다. 이번 검증은 기록한 이미지 ID·실행 로그·소스 커밋의 재현 확인이며, 미래의 완전히 동일한 이미지나 임상 성능을 보장하지 않습니다. 45단계 고정 소스의191개 테스트와 이번 main의 전체 테스트 수를 구분합니다.
