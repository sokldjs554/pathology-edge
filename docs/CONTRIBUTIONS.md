# 기여 기록

기준: 2026-11-07 (Asia/Seoul). 실제 코드/로그/사용자 설명이 확인된 뒤 상태를 바꿉니다.
Codex 실행 로그는 사용자 실행의 증거가 아닙니다. Git 커밋 작성자와 실제 기여도도 구분합니다.

| ID | 담당 | 분류 | 내용 | 상태 | 증거 |
|---|---|---|---|---|---|
| U01 | 사용자 | 코드 | `local_to_level0` | 예정 | 제출 전 |
| U02 | 사용자 | 테스트 | 1단계 단위 테스트 | 예정 | 출력 수신 전 |
| U03 | 사용자 | 화면 | 데모 선택·확대·경계 비교 | 예정 | 확인 수신 전 |
| U04 | 사용자 | 검토·결정 | 좌표계와 리사이즈 설명 | 예정 | 설명 수신 전 |
| U05 | 사용자 | 검토·결정 | 데이터 분리·결과·한계 검토 | 예정 | 자료 제공 후 검토 예정 |
| U00 | 사용자 | 환경 정보 | macOS 11.7.11, Python 상, NumPy·Ubuntu 사용 가능 | 확인 | 채팅 답변. 실행 검증은 아님 |
| C01 | Codex | 조사 | 회사·공개 데이터 확인, 공고 원문 접근 실패 기록 | 완료 | `docs/RESEARCH.md`, `artifacts/data-source.json` |
| C02 | Codex | 구현 | 데이터·모델·경계 처리·C++·데모·테스트 | 완료 | `src/`, `cpp/`, `dist/`, `tests/` (U01 함수 제외) |
| C03 | Codex | 실험 | CPU 학습 16 epochs, validation 선택, 고정 test 평가 | 완료 | `artifacts/training.json`, `evaluation.json`, `model.pt` |
| C04 | Codex | 검증 | Debian·Ubuntu Docker 각 33 tests 통과 | 완료 | `tests-host.txt`, `tests-ubuntu-docker.txt`. 사용자 과제 12 tests는 skip |
| C05 | Codex | 검증 | 실제 이미지 C++ 일치, 스레드 벤치마크 | 완료 | `cpp_real_parity.json` 14확률맵 동일, `benchmark.json` |
| C06 | Codex | 배포 | Sites 공개 데모 | 완료 | `artifacts/deployment.json` |
| C07 | Codex | 화면·출력 | 실제 모델 비교·오류 이미지 생성 및 비교 그림 확인 | 완료 | `boundary_comparison.png`, `error_*.png`. 브라우저 캡처 아님 |
| C08 | Codex | 화면 | 브라우저 클릭·반응형 UI 검증·화면 캡처 | 미수행 | 지원 브라우저 도구 부재. 정적 파일·DOM 연결 검사는 완료 |
| C09 | Codex | CI | GitHub Actions Ubuntu 설치·C++ 빌드·테스트·정적 데모 검사 | 완료 | `artifacts/github-ci.json`, run `42364930156`, 소스 commit `0a9c24c` 성공 |

## 검토 후 추가할 기록 형식

날짜 / 담당 / 변경 파일·함수 / 실행 명령·환경 / 결과 로그 / 결정 이유 / 확인자.
사용자 코드는 Codex가 수정한 부분이 있으면 구간과 수정 이유를 따로 남깁니다.

## 면접에서 현재 말할 수 있는 범위

“Codex와 프로젝트를 구성하고, 제가 직접 맡은 좌표 변환은 작성·검증 예정입니다.”
아직 직접 구현·학습·테스트·화면 확인을 끝냈다고 설명할 수 없습니다.
완료 후에도 Codex가 수행한 모델 학습과 본인이 실행한 재현 실험을 분리합니다.
