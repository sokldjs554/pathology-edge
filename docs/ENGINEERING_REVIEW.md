# 실제 코드로 설명하는 C++·멀티스레딩·OpenCV·Docker

공고의 기술 스택과 현재 구현을 연결하는 자료다. 새 대규모 실험이나 전체 모듈 재작성을 요구하지 않는다. **아래 자료를 준비한 사실과 지원자가 직접 읽고 설명·실행한 사실을 구분한다.** GIL·원자적 작업 배분, 연결 성분과 실제 핵의 차이, Docker 재현성의 한계에 대한 **본인 설명을 확인했다**. [응답과 확인 범위](USER_REVIEW_20261118.md). 새 구현·테스트·Docker 직접 실행은 추가하지 않았다.

## 이미 확인된 범위

- C++ 추출 8조건·72회 측정과 CPU/affinity 정보 제출, 원본 감사: [기여 U63·U70](CONTRIBUTIONS.md), [원본 감사](USER_RESEARCH_AUDIT.md).
- 2048² 패치 추출의 최대 1.96배를 전체 추론 가속으로 확대할 수 없다고 설명: U66.
- Ubuntu 고정 소스 재현과 PR 생성·병합: U57–U61.
- Docker CI의 build/checks 성공 화면 확인: U62. 직접 Docker Engine에서 build한 경험으로 확대하지 않는다.
- 직접 작성한 7개 항목은 [README](../README.md)의 범위를 유지한다. C++ 추출기·Dockerfile 전체 작성 경험으로 바꾸지 않는다.

## 검토한 코드: C++ 패치 추출

읽을 순서: [`patches.extract`](../src/pathology_edge/patches.py) → [`cpp/patches.cpp`의 `extract`](../cpp/patches.cpp) → [`test_native_matches_python_with_trailing_padding`](../tests/test_pipeline.py).

| 구간 | 실제 코드에서 확인할 내용 |
|---|---|
| Python 호출 | HWC RGB 배열을 연속 메모리로 만들고 `(x,y)`를 int64 `(N,2)`로 전달. 동일 패치 크기 검사 |
| C++ 입력·출력 | RGB 영상, 좌표, 패치 크기, 1–64 스레드. 출력은 uint8 `(N,size,size,3)` |
| 끝부분 패치 | 출력 전체를 255로 채운 뒤 원본 안에 있는 행·열만 복사. 원본 밖에 핵 픽셀을 만들어 넣지 않음 |
| 작업 배분 | `next.fetch_add(1)`로 패치 인덱스를 하나씩 배정. 각 패치는 출력 버퍼의 서로 다른 구간을 사용 |
| GIL·스레드 | 배열 확보·검사를 마친 후 `py::gil_scoped_release` 범위에서 C++ worker 수행. `std::thread` 생성·join과 GIL 해제는 서로 다른 역할 |
| 조건 | worker 실행 중 다른 호출자가 입력 배열을 수정하지 않는다는 전제가 필요. GIL 해제만으로 외부 배열 변경까지 안전해지는 것은 아님 |
| 비용 | 스레드 생성·작업 배분 비용과 메모리 복사 비용. 작은 입력이나 CPU 할당이 적은 환경에서는 스레드 증가가 느려질 수 있음 |

**설명을 확인한 질문:** `py::gil_scoped_release`와 `std::atomic`의 `fetch_add`는 각각 어떤 문제를 해결하며, GIL 해제만으로 같은 출력 패치를 여러 worker가 쓰는 문제까지 방지할 수 있는가?

본인은 GIL 해제가 C++ worker의 출력 메모리를 보호하지 않으며, 원자적 증가가 서로 다른 작업 번호를 배정한다고 설명했다. 패치 번호별 출력 구간이 겹치지 않는 점은 검토 피드백으로 연결했다. 모듈 전체의 독립 검토·구현 완료로 확대하지 않는다.

<details>
<summary>필요할 때 실행하는 출력 일치 검사</summary>

[개발 환경](RUNBOOK.md#development)을 준비한 **저장소 루트**에서 실행한다. C++ 확장이 설치된 동일 Python을 사용한다.

```bash
python -m pytest tests/test_pipeline.py -k native_matches_python_with_trailing_padding -q
```

현재 기준 예상 결과는 **12 passed**다. 네 영상/패치 조건 × 스레드 1·2·4에서 Python/C++ 출력 배열과 끝부분 흰 padding의 일치를 확인한다. 합성 입력의 기능 검사이며 속도·의학적 성능 측정이나 새 학습이 아니다. 체크인된 실험 결과를 덮어쓰지 않는다.

실패하면 실행 위치, 명령, 전체 오류, `python --version`, `git rev-parse HEAD`, `git diff --stat`를 전달한다. 본인이 실행하기 전에는 본인 테스트 완료로 기록하지 않는다.
</details>

<details>
<summary>OpenCV가 맡는 구간과 확인한 설명</summary>

[`data.tissue_mask`](../src/pathology_edge/data.py)는 RGB→HSV 후 S>15·V<250으로 보수적인 조직 마스크를 만든다. 종양 판별 모델이 아니다. [`merge.components`](../src/pathology_edge/merge.py)는 이진 예측의 8방향 연결 성분을 추출하고 면적·중심·bbox·평균 점수·경계 접촉 여부를 계산한다. 중심과 bbox에 패치 원점을 더해 원본 좌표로 옮긴다. [`experiment.classical`](../src/pathology_edge/experiment.py)은 RGB→회색조와 밝기 cutoff를 쓰는 별도 기준선이다.

본인은 연결 성분이 붙으면 여러 핵을 하나로, 끊기면 한 핵을 여러 개로 셀 수 있으므로 핵 후보로 보고 정답 주석과 비교해야 한다고 설명했다. RGB/BGR 색상 변환에 관한 별도 답변이나 OpenCV 모듈 전체 검토는 확인하지 않았다. 남은 참고 내용을 새 필수 과제로 배정하지 않는다.

필요할 때 개발 환경의 **저장소 루트**에서:

```bash
python -m pytest tests/test_pipeline.py -k 'component_coordinate_and_padding or valid_split_and_background_gate' -q
```

현재 예상 결과 **2 passed**. 좌표·padding 관련 후보 처리와 조직 검사/유효 분리의 기존 검사를 실행하며 종양 분류 정확도를 검증하는 명령은 아니다.
</details>

<details>
<summary>Ubuntu와 Docker의 재현 범위</summary>

[`Dockerfile`](../Dockerfile)은 Ubuntu 24.04 → Python venv → 고정 Python 패키지 → C++ 확장 빌드 → 정적 HTTP 서버의 순서다. [`requirements-lock.txt`](../requirements-lock.txt)는 Python 패키지 버전을 고정한다. Ubuntu 이미지 태그와 apt 패키지는 digest/버전까지 고정된 완전한 비트 단위 환경은 아니며, 하드웨어·스레드·실행 순서 차이에 따른 시간 차이도 남는다.

[`docker-reproduction.yml`](../.github/workflows/docker-reproduction.yml)의 빌드와 컨테이너 내부 검사는 서로 다른 단계다. Codespaces에 Docker가 없었던 사용자 실행은 Ubuntu 재현으로, 원격 Docker 성공은 CI 결과 확인으로 기록한다.

Docker를 직접 사용할 수 있게 된 경우에만 [RUNBOOK Docker 절차](RUNBOOK.md#docker)를 따른다. 이 자료를 읽었다는 사실만으로 Docker 직접 빌드 완료를 추가하지 않는다. 본인은 같은 이미지의 코드·패키지와 외부 데이터·모델·설정의 고정을 구분하고, 하드웨어·비결정적 연산·스레드·부하·예열 등에 따라 점수와 시간이 달라질 수 있다고 설명했다. 같은 Dockerfile의 재빌드와 동일 digest의 이미지 사용 구분은 후속 피드백으로 제공했다.
</details>
