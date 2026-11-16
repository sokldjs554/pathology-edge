# PathologyEdge · H&E 기반 화면 색상

[공개 데모](https://pathology-edge-lab.ykh13571.chatgpt.site/)의 세 작업 화면에 같은 색상 체계를 적용했습니다. 기존 베이지·금색 대신 실제 H&E 영상의 핵 염색과 에오신 색에서 가져온 자주·분홍을 화면의 식별 색으로 사용합니다. 이는 프로젝트의 시각적 정체성이며 병리 판독의 표준 색상 규칙을 뜻하지 않습니다.

| 역할 | 색상 | 적용 위치 |
| --- | --- | --- |
| 상단 구분 | 짙은 자주 `#302039` | 공통 헤더 |
| 주요 조작 | 핵 염색 계열 보라 `#613575` | 사례 버튼, 선택 상태, 링크, 밝은 배경의 키보드 초점 |
| 현재 위치 | 에오신 분홍 `#e397b6` | 로고, 현재 메뉴 밑줄, 어두운 배경의 키보드 초점 |
| 정보 | 흰색·옅은 회색 | 도구, 결과 패널, 표 |
| 영상 주변 | 중성 짙은 회색 `#252a2e` | 영상 프레임 |

영상에 필터를 씌우지 않습니다. 원본 조직·분할 마스크·정답·클래스 색상·청록 개선/분홍 악화 강조는 기존 데이터와 같습니다. 배치와 글자 크기, 사례 선택, 확대·이동, 표시 전환, 실험 수치도 이번 변경 대상이 아닙니다. 공통 스타일은 [`dist/stain-theme.css`](../dist/stain-theme.css)에 분리했습니다.

현재 첫 화면 구조는 [실제 사례로 시작하는 비교 화면](UI_FIRST_VISIT.md)에 있습니다. 아래는 색상 개편 당시 버전 16의 기록입니다.

## 화면

- 경계 비교: [변경 전](../artifacts/ui-case-context/simple-improved.png) → [변경 후](../artifacts/ui-stain-theme/simple-improved.png)
- [첫 화면](../artifacts/ui-stain-theme/simple-entry.png) · [원본·정답 포함 4분할](../artifacts/ui-stain-theme/readability-four.png) · [후보 표](../artifacts/ui-stain-theme/studio-data-laptop.png)
- [WSI 전체 탐색](../artifacts/ui-stain-theme/wsi-overview.png) · [WSI ROI](../artifacts/ui-stain-theme/wsi-roi-native.png) · [IHC 세포 분류](../artifacts/ui-stain-theme/ihc-desktop.png)
- [작은 화면](../artifacts/ui-stain-theme/simple-375.png) · [작은 화면의 상세 도구](../artifacts/ui-stain-theme/context-menu-375.png) · [작은 화면의 IHC](../artifacts/ui-stain-theme/ihc-375.png)

## 검증

- UI 소스 [`9e075e3`](https://github.com/sokldjs554/pathology-edge/commit/9e075e39d08378b3d68cd78303ec8dbe46777761), Sites 버전 16, 배포 소스 `5f822909e07d0982069857b1a692496a964c2581`.
- [코드의 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43786871708): Chromium·WebKit 각각 66개 통과. 예제 선택, A/B 시야 연결, 확대·이동, 실제 강조 픽셀, 수치 유지, 상세 도구, WSI·IHC, 작은 화면을 검사했습니다.
- [공개 주소 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43787486212): Chromium·WebKit 각각 66개 통과. 이 실행에서 화면 캡처를 수집했습니다. [검증 기록](../artifacts/ui-stain-theme/verification.json).
- [CPU 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43786871797): Python 462개 통과, 저장 Dice 42개·평균 6개 일치. Node 로직 테스트 14개 통과.
- 주요 색 조합의 WCAG 계산 대비비: 본문 14.83:1, 주요 버튼 9.23:1, 선택 메뉴 15.09:1, 상단 보조 글자 7.97:1, 사례 줄 보조 글자 5.21:1, 영상 제목의 보조 글자 6.82:1. 이는 확인한 조합의 계산값이며 전체 접근성 인증을 뜻하지 않습니다.
- [배포 파일 대조](../artifacts/ui-stain-theme/deployment-parity.json): 저장소와 배포 소스 2,196개 파일 일치. 공개 HTTP에서는 변경한 HTML 3개·공통 CSS와 실험 결과 JSON 2개를 대조했습니다.

직접 확인할 순서는 **경계 비교 → 좋아진/나빠진 경계 보기 → 상세 도구 → WSI 탐색 → IHC 세포 분류**입니다. 상단의 색상과 선택 표시가 세 화면에서 이어지는지 확인할 수 있습니다. 이번 색상 수정본의 사용자 직접 확인은 아직 완료로 기록하지 않습니다.
