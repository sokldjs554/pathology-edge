# 51단계: 현재 C++ 패치 추출 성능 직접 확인

상태: **사용자 실행·성공 요약·8행 비교표·CPU 정보 제출 확인 완료**. `my-cpp-review.nd9wyi24`에서8조건·검사 성공·원본 보존·오류 없음 요약과 후속 표를 받았습니다. [제출 요약](../artifacts/learning/step51-user-summary.json), [제출 수치](../artifacts/learning/step51-user-measurements.json), [확인 범위](../artifacts/learning/step51-review.json)를 기록했습니다. 반올림된 출력이며 원시 시간·소스 해시 파일에는 직접 접근하지 않았습니다. 후속 [52단계 범위 해석](STEP_52.md)도 확인했으며 현재 과제는 [53단계 CNN–ViT 실행](STEP_53.md)입니다.

## 완료한 작업: 저장된 비교표 읽기

아래 명령의 출력 제출을 확인했습니다. 재실행할 필요는 없습니다. Codespaces의 `/workspaces/pathology-edge`에서 저장된 JSON만 읽는 기록용 명령입니다. 경로의 `review.nd9wyi24`에는 역슬래시를 넣지 않습니다.

```bash
cd /workspaces/pathology-edge && python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("work/my-cpp-review.nd9wyi24/summary.json").read_text())
print("size  backend  threads  median_ms  Python대비  peak_MiB")
for row in data["comparison"]:
    print("{size:4d}  {backend:6s}  {threads}t  {median_ms:.3f}  {speedup_vs_python:.2f}x  {peak_process_rss_mib:.1f}".format(**row))
env = data["environment"]
print("CPU:", env["cpu_model"])
print("논리 CPU / affinity:", env["visible_logical_cpus"], env["affinity_cpu_count"])
print("CPU 할당 정보:", env["cgroup"])
PY
```

`median_ms`는 작을수록 빠르고, `Python대비`는 같은 크기의 Python 시간을 해당 구현의 시간으로 나눈 값입니다. 1보다 크면 Python보다 빠릅니다. `peak_MiB`는 전체 프로세스의 최대 메모리이며 아래 측정 범위를 함께 봅니다. 파일을 찾지 못하면 오류 내용을 보내고 기존 실행 폴더를 확인합니다.

기존 Codespaces의 Python 환경에서 현재 설치된 Python/C++ 패치 추출기를 비교합니다. 기존 체크아웃의 수정한 `learner_wsi.py`와 `artifacts/benchmark.json`을 보존하며, 설치·빌드·`git pull`·`stash`가 필요하지 않습니다. 이전 `scripts/benchmark.py`는 실행하지 않습니다.

## 실행 조건과 저장 내용

- 입력: seed 42의 합성 `uint8` RGB 영상, 512×512와 2048×2048. 패치128, 겹침64로 각각64개·1,024개입니다.
- 비교: Python 1스레드, C++ 1·2·4스레드, 총8조건. 조건마다 새 프로세스에서 출력 일치를 먼저 검사하고9회 측정합니다. `python -O`에서도 일치 검사가 꺼지지 않습니다.
- 시간: `patches.extract` 호출의 출력 할당·crop 복사·흰색 패딩과 Python 래퍼 비용입니다. 입력 생성·격자 생성·출력 비교·해시·파일 입출력·모델 추론은 측정 구간 밖입니다.
- 메모리: 각 프로세스의 **절대 최대 RSS**입니다. 두 비교 출력과 비교용 임시 배열·입력·import 메모리가 포함됩니다. 추출기만의 추가 메모리나 추론 메모리가 아닙니다.
- 환경: Python·패키지 버전, CPU 모델, 보이는 논리 CPU 수, CPU affinity, 읽을 수 있는 cgroup 제한을 기록합니다. 논리 CPU 수가 실제 CPU 할당량을 뜻하지는 않습니다.
- 출처: 실제 import한 패키지·`patches.py`·C++ 확장 경로가 현재 저장소의 `src/pathology_edge`인지 확인합니다. Git 커밋·dirty 상태, 추적 파일과 로컬 소스·C++ 바이너리의 실행 전후 SHA256, 실행기 SHA256을 남깁니다. 현재 Python/C++ 소스와 설치된 바이너리 사본도 결과 폴더에 보관합니다.
- 보존: `work/my-cpp-review.*`를 매번 새로 만들고 기존 폴더를 재사용하지 않습니다. 실패한 조건의 stdout·stderr, 완료한 조건의 원시9회 측정값, 최종 성공 여부를 남기며 실패 시 종료 코드는0이 아닙니다.

기본 실행은8조건 한 라운드로, 보통1분 이내에 끝나는 작은 점검입니다. 실제 시간은 Codespaces 부하에 따라 달라집니다. `--rounds 3`은 순방향·역방향·교차 순서의24개 독립 프로세스와 조건당27개 측정을 남기는 추가 확인 옵션입니다. 세 라운드는 모든 순서 효과를 완전히 상쇄하지 않습니다. 이번 사용자 실행은 기본 한 라운드입니다.

## 처음 실행할 때 사용한 명령 — 기록용

실행기는 커밋 `478670eed931102d38412b9e13f94a519379a607`에 고정합니다. 아래 명령은 실행기 한 파일만 새 `work` 폴더에 받고, 현재 설치된 코드를 측정합니다.

기존 Python/C++ import가 성공했던 Codespaces 터미널에서 다음 블록을 한 번 실행합니다. `/workspaces/pathology-edge`의 현재 소스를 그대로 사용합니다.

```bash
cd /workspaces/pathology-edge && python - <<'PY'
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.request

runner_commit = "478670eed931102d38412b9e13f94a519379a607"
if not re.fullmatch(r"[0-9a-f]{40}", runner_commit):
    raise SystemExit("Runner download commit is not published/pinned yet.")
repo = Path.cwd()
(repo / "work").mkdir(exist_ok=True)
download = Path(tempfile.mkdtemp(prefix="cpp-review-runner.", dir=repo / "work"))
script = download / "benchmark_cpp_review.py"
url = ("https://raw.githubusercontent.com/sokldjs554/pathology-edge/"
       + runner_commit + "/scripts/benchmark_cpp_review.py")
with urllib.request.urlopen(url, timeout=30) as response, script.open("xb") as target:
    target.write(response.read())
raise SystemExit(subprocess.run([sys.executable, str(script), "--repo", str(repo)], cwd=repo).returncode)
PY
```

완료 후 터미널의8줄 비교표와 마지막 `SUMMARY` 줄을 확인합니다. `all_checks_passed: true`, `original_files_preserved: true`, `completed_cases: 8`이 모두 있어야 완료된 비교입니다. 실패하면 재설치하거나 파일을 바꾸기 전에 `SUMMARY`의 `path`와 오류 내용을 확인합니다. 원래 파일의 변경 여부도 실패 결과에 남습니다.

각 실행은 처음에 `RUN_DIR=...`를 출력합니다. 터미널이 초기화되어도 그 폴더의 `RUN.txt`, `summary.json`, `original-before.json`, `original-after.json`, `*.stderr.log`가 남습니다. 폴더 이름을 잊으면 Codespaces 탐색기의 `work` 아래 `my-cpp-review.*`를 찾습니다. 같은 명령을 다시 실행하면 새 결과 폴더가 만들어집니다.

## 결과를 읽는 기준

`median_ms`는9회 측정의 중앙값입니다. `speedup_vs_python`은 같은 영상 크기의 Python 중앙값을 해당 조건의 중앙값으로 나눈 값이며,1보다 작으면 그 조건이 더 느립니다. 작은 영상에서는 스레드 생성 비용 때문에 C++ 4스레드가 빠르지 않을 수 있습니다. 현재 CPU 할당량과 다른 작업 부하도 함께 봅니다.

이 비교는 합성 입력의 패치 추출 속도입니다. 병리 정확도·전체 파이프라인 속도·임상 효용을 검증하지 않습니다. 설치된 C++ 바이너리를 재빌드하지 않으므로 파일 해시와 보관한 소스만으로 그 바이너리의 실제 빌드 소스·컴파일러·옵션까지 증명할 수는 없습니다.

실행 도구의 개발 검증과 사용자의 Codespaces 실행을 구분합니다. **사용자 성공 요약·반올림 표·CPU 정보를 확인했습니다.** 512²에서 C++1스레드0.265ms,2048²에서 C++4스레드11.453ms가 최저였습니다. 사용자 해석은52단계에서 확인하며 원시9회 값의 재계산이나 원인별 성능 분석을 완료했다고 기록하지 않습니다.
