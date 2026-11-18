# 상단 메뉴와 로고 이동

`RESEARCH STUDIO`는 별도 기능이 아니라 로고 안의 장식 문구였습니다. WSI·IHC 화면의 로고가 `wsi.html`로 연결되어 있어 WSI 탐색과 같은 곳으로 이동했습니다. 문구를 세 화면에서 제거하고 로고를 공통 첫 화면으로 연결했습니다.

| 클릭 대상 | 도착 화면 |
| --- | --- |
| PathologyEdge 로고 | 첫 화면 · TNBC 경계 비교 (`/`) |
| WSI 탐색 | 실제 슬라이드 탐색 (`wsi.html`) |
| 경계 비교 | TNBC 이미지의 A/B 경계 비교 (`index.html`) |
| IHC 세포 분류 | 저장된 IHC 세포 분류 결과 (`ihc.html`) |

로고에 ‘첫 화면 · 경계 비교’ 도움말과 접근성 이름을 적용했습니다. 로고와 경계 비교 메뉴는 같은 작업 화면을 여는 의도적인 홈/기능 진입점입니다. 별도의 Studio 기능이 있는 것으로 표시하지 않습니다.

공개 호스팅은 `wsi.html → /wsi`, `ihc.html → /ihc`, `index.html → /`로 HTTP 307 이동합니다. 같은 문서의 주소 정규화이며 서로 다른 기능이 합쳐지는 것은 아닙니다.

## 검증 범위

기존 브라우저 탐색 검사에 **세 화면에서 로고를 클릭해 실제 첫 화면에 도착하는지**, **각 메뉴를 클릭해 해당 경로·화면·선택 표시가 함께 바뀌는지**를 추가했습니다. 수정 전 HTML 링크 해석에서 WSI 로고가 `/wsi.html`로 가는 오류를 재현했고, 수정 후 세 화면 모두 `/`로 이동함을 확인했습니다.

이번 변경은 세 HTML 페이지의 로고 링크·문구에 한정됩니다. 경계 이동·후보 표·WSI·IHC의 분석 코드와 결과 파일은 변경하지 않았습니다. 사용자 본인이 수정 화면을 검토했다고 기록하지 않습니다.

- 배포 버전 **20**, UI 소스 [`445ebe6`](https://github.com/sokldjs554/pathology-edge/commit/445ebe61dbb83c7de1ce3b2c570fbc4e9ed96e9f), Site 소스 `bf5fac1c135d378dfaaa6fa85e3803736ebfea38`.
- [소스 체크아웃 전체 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43823879734): Chromium·WebKit 각각 **75개 통과**. 건너뜀·실패·재시도로만 통과한 항목 모두 0개. 최종 검사 커밋은 `b418a194c26e774b1e21db510e3a760b511ee759`이며 배포한 `445ebe6`과 dist 파일은 동일합니다.
- [공개 배포 집중 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43823894909): Chromium·WebKit 각각 **5개 통과**. 세 화면의 로고·메뉴 이동, 첫 화면, 데스크톱·모바일에서 현재 이미지의 개선/악화 경계 유지, 확대·이동을 확인했습니다. 건너뜀·실패·재시도로만 통과한 항목 모두 0개.
- Node **16개**, [기존 Python 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43823005340) **462개** 통과. 저장 Dice **42/42개**·평균 **6/6개** 일치. 정적 데모 검사 통과.
- 배포 소스 **2,196개** 파일을 GitHub 소스와 대조하고, 공개 HTTP의 주요 **10개** 파일 해시가 일치함을 확인했습니다. [대조 기록](../artifacts/ui-navigation/deployment-parity.json)

첫 배포 검사에서는 로고의 홈 복귀가 통과한 뒤, 메뉴의 최종 주소를 `.html` 형식으로만 기대한 검사 1개가 두 브라우저에서 실패했습니다([기록](https://github.com/sokldjs554/pathology-edge/actions/runs/43823550696)). 공개 서버의 307 응답을 확인하고, 위 세 주소의 정확한 별칭만 허용하도록 검사를 보완했습니다. 링크 목적지·실제 도착 화면·현재 메뉴 표시 검사는 유지하며 배포 코드는 변경하지 않았습니다.

## 공개 배포 화면

[WSI 탐색](../artifacts/ui-navigation/navigation-studio-wsi.png) · [경계 비교](../artifacts/ui-navigation/navigation-studio-tnbc.png) · [IHC 세포 분류](../artifacts/ui-navigation/navigation-studio-ihc.png)

캡처는 위 공개 배포 집중 검사의 Chromium 결과입니다. [검증 기록과 출처](../artifacts/ui-navigation/verification.json)
