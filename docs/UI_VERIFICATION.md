# UI 검증 기록과 재현

최신 경계 사례·설명 UI와 공개 버전5 검증은 [INTERVIEW_UI.md](INTERVIEW_UI.md)에 있습니다. 아래는 기존 작업대 개편 당시의 기록입니다.

후속 사용자 제보로 확인한 이동 오류와 WebKit 캔버스 수정은 [PAN_FIX](PAN_FIX.md)에 기록했습니다.
현재 검사는 Chromium/WebKit 각각19개, 좌표5개이며 아래는 최초 UI 개편 당시의 이력입니다.

2026-11-07 · Codex 실행. 사용자 실행·화면 검토 완료를 뜻하지 않습니다.
[UI 조사/변경 이유](UI_REVIEW.md) · [사용자 검토 순서](REVIEW.md)

## 환경과 검사 범위

GitHub Actions Ubuntu24.04 / Node22 / Playwright1.56.1 / Chromium.
관리형 작업 환경의 공유 브라우저 연결이 불가능하여 CI의 실제 Chromium으로 페이지를 열고
마우스·휠·키보드·폼 조작을 수행했습니다. 렌더링된 PNG 캡처를 Codex가 별도로 눈으로 확인했습니다.
HTML을 그림으로 재구성한 캡처가 아닙니다.

- 기존 배포 화면: [run42372155048](https://github.com/sokldjs554/pathology-edge/actions/runs/42372155048).
- 새 UI 첫 검증: [run42373323457](https://github.com/sokldjs554/pathology-edge/actions/runs/42373323457), 11 browser tests 통과.
- 후보 표시 수정 + 원본 픽셀 대조 추가: [run42373527725](https://github.com/sokldjs554/pathology-edge/actions/runs/42373527725), 12 browser tests 통과.
- 화면 좌표 수학: 4 tests 통과. 커서 중심 확대, 이동 범위, 맞춤/좌표 역변환, 후보 선택 반경·원래 인덱스 보존.
- 기존 pytest: Debian33 passed / 사용자 함수12 skipped. Ubuntu CI에서도33 passed /12 skipped.
- 정적 검사: 7개 예제·42 PNG·DOM 대상·사전 계산/WSI 한계 문구 통과.

## 최종 배포 검증

- UI 소스: GitHub `7429786a007de401ca12c504e8fbc60099fee9ba`.
- Sites 소스: `4553d905429245cd9738546f91fa04ab56076856`, 공개 버전3.
- [UI checkout 검증](https://github.com/sokldjs554/pathology-edge/actions/runs/42374144704),
  [기존 CPU 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/42374144546) 통과.
- 상태 표시 수정 후 [공개 배포 검증](https://github.com/sokldjs554/pathology-edge/actions/runs/42374307057) 12개 통과.
- 확대/축소 버튼·불투명도 키보드 조작까지 포함한 최종 [공개 배포 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/42374425111)와 [checkout 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/42374424993)는 각각 **12 passed, 0 failed, 0 skipped**입니다. 브라우저 테스트 소스는 `2b4af09`이며 캡처는 이 공개 배포 검사에서 저장했습니다.
- [원시 브라우저 보고서](../artifacts/ui/browser-production-report.json) · [검증 요약](../artifacts/ui/verification.json).
- 후속 커밋은 테스트·문서·증거만 변경하며 배포되는 `dist/`는 위 UI 소스와 같습니다.

## 실제 조작과 대조

| 검사 | 확인 방법 |
|---|---|
| 예제7장 | 목록 변경 직후 각ID·선택 썸네일·4개 지표·raw/merged 수를 `results.json`과 비교 |
| 표시 이미지 | 10_1/11_2의 1:1 canvas 픽셀을 해당 원본 PNG 픽셀과 직접 비교 |
| 확대/축소/이동 | 버튼·wheel·drag·방향키·개요도·F 맞춤 후 양쪽 배율/원본 중심 일치 검사 |
| 오버레이 | 분할/GT/격자/후보 토글 시 canvas 실제 픽셀 변화 |
| 평가 영역 | 전체/경계/내부 지표 대조, 강조 영역 캡처 확인 |
| 중복 병합 | 저장된 suppressed_index→kept_index 및 raw_index 연결, 실제 후보 bbox/patch ID, 영상 원 클릭 |
| 반응형 | 1440×1000,1024×768,390×844,375×667. 가로 넘침·고정 작업대 높이·패널 접근·A/B 전환 |
| 실패/빈 상태 | 테스트에서 지연/HTTP503/이미지404/빈 samples 응답을 주입. 이전 수치 제거·조작 비활성화·재시도 확인 |
| 연속 선택 | 예제를 빠르게 바꿔 최종 선택과 이미지/수치가 일치하는지 확인 |
| 실제 파일 | HTML/JS/CSS/수학 모듈/결과 JSON의 SHA-256 대조. HTML의 검증된 호스팅 삽입 스크립트는 별도 기록 |

로딩은 결과 파일 로딩이며 분석 실행이 아닙니다. 상태 캡처의 `injected`는 **테스트가 주입한 응답**이라는 뜻입니다.
일반 화면/병합/경계 캡처에는 실제 저장된 이미지와 결과만 사용합니다.

## 측정된 화면 변화

1440×1000에서 canvas 시작은 y418→227px, 문서 전체 높이는1472→1000px입니다.
선택 후보 상세를 스크롤로 찾아 내려가던 구조를 영상 옆 패널로 바꿨습니다.
390px 화면은 174px 두 영상을 390px 단일 canvas의 A/B 전환으로 바꿨습니다.
전체 맞춤 시 실제 이미지 크기는 남은 높이에도 제한되며 375×667에서는 더 작게 맞춰집니다.
확대 버튼/핀치 구현/단일 영상으로 자세히 볼 수 있습니다.

## 보존한 실험과 미검증 범위

[보존 검사](../artifacts/ui/invariants.json): 결과 JSON·모델 checkpoint·42개 PNG·사용자 작성 대기 함수의 바이트가 동일합니다.
모델을 재학습하거나 test 결과를 조정하지 않았습니다. UI의 배율과 오버레이 색 변경은 표시 변경입니다.

Chromium 자동 조작과 캡처 검토를 완료했으며 **사용자의 macOS11.7.11/Safari, 실제 터치 기기, 보조공학 기기**는 미검증입니다.
이 작업은 연구 UI 검증입니다. 병리 전문가 사용성·임상적 유효성·실시간 추론·WSI 전체 분석의 검증이 아닙니다.

## 직접 재현할 명령

현재 사용자 과제는 STEP_01입니다. 아래는 UI 검사를 추가로 실행하려 할 때 쓰는 명령이며
사용자가 실행했다는 기록은 아닙니다. macOS11.7에는 최신 Playwright 브라우저 지원이 제한되므로
Ubuntu 환경 또는 GitHub Actions 실행을 권장합니다.

```bash
# 저장소 루트: 기존 모델/데이터/C++ 테스트 (Python 개발 환경 설치 후)
python -m pytest -q
# 저장소 루트: 화면의 좌표 계산 테스트 (Node22)
node --test web-tests/viewer-math.test.cjs

# web-tests 폴더: 정확한 버전의 브라우저 테스트 의존성 설치
cd web-tests
npm ci
# web-tests 폴더, Ubuntu: Chromium과 필요한 시스템 라이브러리 설치
npx playwright install --with-deps chromium
# web-tests 폴더: checkout의 dist를 임시 localhost 서버로 열어 검증/캡처
npx playwright test
# web-tests 폴더: 현재 공개 배포를 조작하고 이 checkout과 파일 hash도 대조
UI_BASE_URL=https://pathology-edge-lab.ykh13571.chatgpt.site npx playwright test
```

또는 GitHub Actions → **UI browser review** → **Run workflow** → target=`checkout`/`production`.
`production`은 checkout과 배포 파일이 다르면 실패하도록 설계했습니다.
결과는 `ui-browser-evidence-chromium` / `ui-browser-evidence-webkit` artifact의 `captures/`, `report.json`, 실패시 trace에 있습니다.
실패를 보낼 때 실행 폴더·명령·commit·전체 오류·대상URL·예제ID·브라우저/창 크기를 함께 적어 주세요.

## 배포 소스 대조와 호스팅 처리

GitHub UI 소스와 Sites 배포용 소스는 별도 저장소라 Git SHA가 서로 다릅니다.
배포 대상으로 지정한 `dist/`의 모든47개 파일을 별도로 대조합니다.
[전체 파일 hash](../artifacts/ui/production-all-files.json)와 [브라우저 요청의 소스 대조](../artifacts/ui/served-source-parity.json)를 보세요.

첫 외부 CI 검사 [run42373806271](https://github.com/sokldjs554/pathology-edge/actions/runs/42373806271)는
화면 조작11개를 통과했지만 HTML 원문 hash가 달라 실패했습니다. trace 응답을 확인하니
Cloudflare가 `</body>` 앞에 JS challenge를 삽입했고 나머지 바이트는 저장소와 같았습니다.
관리형 환경의 직접 GET은 삽입 없는 원본47개가 모두 일치했습니다.

검사를 완화해 임의 스크립트를 무시하지 않습니다. 관찰한 challenge 템플릿의 SHA-256을 고정하고
요청별 ray ID/시간 필드만 정규화합니다. 템플릿이 달라지거나 다른 코드가 추가되면 실패합니다.
원문 hash, 소스 hash, 삽입 스크립트 hash/크기를 각각 남깁니다. JS/CSS/JSON은 원문 바이트 그대로 비교합니다.
이 보완 뒤 [run42374025834](https://github.com/sokldjs554/pathology-edge/actions/runs/42374025834)의 공개 페이지12개 검사가 통과했습니다.
