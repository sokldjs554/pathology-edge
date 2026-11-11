# 50단계: Docker 재현 결과 확인

상태: **실제 Docker 빌드·검사 성공 / 사용자 결과 확인 완료**. 면접 문장 작성은 보류합니다.

45단계에서는 사용자가 Codespaces의 기존 패키지로 고정 소스를 재현했습니다. 이번에는 GitHub가 제공하는 Ubuntu 24.04 실행 환경에서 루트 Dockerfile을 빌드하고, 생성한 이미지 안에서 검사합니다. Codespaces에 Docker를 설치하거나 작성한 파일을 갱신할 필요가 없습니다.

## 실행과 확인 범위

- 자동화: `.github/workflows/docker-reproduction.yml`과 `scripts/check_docker.sh`로 이미지 빌드·검사·로그 저장.
- 사용자: 실행 결과 화면의 두 성공 항목을 확인했고 “두 항목 잘 보여”라고 보고했습니다.
- 수동 실행 전용이며 기존 push/PR의 `CPU checks`와 별도입니다. 실행 주체 입력은 기여 증빙을 대신하지 않습니다.
- 빌드한 이미지 ID로 실행하고 커밋 라벨·추적 파일 SHA256을 대조합니다. `.openai` 배포 설정은 기존 `.dockerignore`에 따라 제외됩니다. C++ 바이너리는 이미지 안에서 새로 빌드합니다.
- 컨테이너에서 고정 패키지·Python/C++ import·전체 pytest(0 skip)·저장 Dice 42개/평균6개·정적 데모·HTTP 응답을 검사합니다. 검사 후에도 추적 파일 해시가 같은지 확인합니다.
- 검사 컨테이너는 외부 네트워크 없이 실행합니다. 이미지 빌드 중에는 Ubuntu·Python 패키지를 내려받습니다.
- 새 데이터셋 학습·성능 평가·브라우저 조작·데모 배포는 포함하지 않습니다. 단위 테스트의 합성 모델 연산은 실행될 수 있습니다.

## 확인한 화면

1. [실제 Docker 실행 결과](https://github.com/sokldjs554/pathology-edge/actions/runs/42974715514)를 엽니다.
2. **Summary**에서 `Docker build: success`와 `Checks inside image: success`가 모두 표시되는지 확인합니다.
3. 사용자 답변으로 두 항목의 표시 확인을 마쳤습니다. 동일 빌드를 다시 실행할 필요는 없습니다.

GitHub Actions의 빌드·검사와 사용자의 결과 화면 확인을 구분하며, U62는 결과 화면 확인 완료로 기록했습니다.

나중에 직접 다시 실행하려면 [Actions → Docker reproduction](https://github.com/sokldjs554/pathology-edge/actions/workflows/docker-reproduction.yml)에서 **Run workflow → main → execution_owner: user → Run workflow**를 누릅니다. 이는 현재 과제로 배정하지 않았습니다.

로그는 실행 화면 **Artifacts**의 `docker-reproduction-커밋-시도번호`에서 30일간 내려받을 수 있습니다. 실행 실패 시 실행 URL과 실패한 단계 이름을 보내면 됩니다. 실패한 빌드나 일부 검사만으로 전체 성공을 기록하지 않습니다.

## 실제 확인한 결과

- 소스 커밋: `20cc5ac9f52601cacef2d41324c14a6da234c6b4`
- 이미지 ID: `sha256:c402d00c72a1d29212aa3aed83eab1b4967e02dd9906ae2e04071db8cc1aad90`
- Ubuntu 24.04.5 / Python 3.12.3 / 고정 패키지32개 일치 / 이미지 내부 C++ import 성공
- pytest **201 passed in 7.20s**, skip/failure/error 0개
- 저장 Dice **42/42**, 이미지 평균 **6/6** 일치; 새 추론 없음
- 추적 소스2,722개 검사 전후 해시 일치·정적 데모·HTTP 응답 검사 성공
- 같은 소스의 기존 `CPU checks`도 성공

[검증 기록](../artifacts/learning/step50-review.json) · [보존한 원본 로그 ZIP](../artifacts/reproductions/docker-20cc5ac/evidence.zip) · [간단한 검사 로그](../artifacts/reproductions/docker-20cc5ac/container.log). GitHub의 30일 만료와 별개로 원본 ZIP을 저장소에도 보존했습니다. 후속 문서·로그 기록 커밋과 실제 빌드한 소스 커밋을 구분합니다.

## 재현의 한계

Python 패키지는 잠겨 있지만 `ubuntu:24.04` 태그와 apt 패키지는 시간이 지나면 바뀔 수 있습니다. 이번 검증은 기록한 이미지 ID·실행 로그·소스 커밋의 재현 확인이며, 미래의 완전히 동일한 이미지나 임상 성능을 보장하지 않습니다. 45단계 고정 소스의191개 테스트와 이번 main의 전체 테스트 수를 구분합니다.
