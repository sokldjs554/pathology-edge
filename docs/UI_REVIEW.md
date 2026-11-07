# 병리 영상 작업 화면 개선

2026-11-07 · 조사/구현/검증 담당: Codex. 사용자 화면 확인은 아직 대기 중입니다.
[공개 데모](https://pathology-edge-lab.ykh13571.chatgpt.site) · [검증 기록](UI_VERIFICATION.md)

## 기존 데모에서 실제 확인한 문제

배포된 페이지를 Chromium에서 직접 열어 예제 선택·확대·오버레이·후보 선택을 조작하고
캡처했습니다. 기존 기능 자체는 동작했지만 핵심 영상과 비교 조작의 우선순위가 낮았습니다.

| 관찰 | 실제 근거 | 변경 |
|---|---|---|
| 소개·큰 수치 카드가 영상 앞 공간을 차지 | 1440×1000에서 영상 canvas 시작 y=418px, 선택 후보 정보 y=1189px, 문서 높이1472px | 고정 높이 작업대, 압축된 상단 도구 모음, 우측 결과 패널 |
| 예제 선택 후 별도 ‘불러오기’가 필요 | 목록을 11_2로 바꿔도 불러오기 전에는 10_1 결과 유지 | 썸네일/목록 선택 즉시 해당 저장 결과 로드, 로딩 중 이전 수치 제거 |
| 모바일 영상이 매우 작고 아래에 위치 | 390×844에서 y=1227px, 각 canvas 폭174px | 같은 시야를 유지하는 A/B 전환, 한 영상에 전체 폭 사용 |
| 병합 전 후보는 체크박스에 숨어 있음 | 주 비교 화면과 별도 후보 표시 의미를 읽어야 함 | ‘경계 전후’와 ‘중복 병합’ 모드를 구분, 억제→유지 대응 선택 |
| 확대 위치와 수치 적용 범위 연결이 약함 | 위치 개요도 없음, 전체 지표와 현재 시야 혼동 여지 | 개요도·현재 x/y 범위, 전체/경계/내부의 실제 평가 영역 강조 |
| 상세 결과 확인 시 영상을 놓치기 쉬움 | 후보 상세가 비교 영상 아래 | 이미지/선택 후보/실험 탭, 영상 옆에서 후보 좌표와 patch ID 검토 |

[이전 데스크톱](../artifacts/ui/before-desktop.png) · [이전 후보 선택](../artifacts/ui/before-selected.png) ·
[이전 모바일](../artifacts/ui/before-mobile.png) · [측정 JSON](../artifacts/ui/baseline-observations.json)

## 실제 제품·도구에서 참고한 내용

직접 확인한 공개 문서와 이미지의 범위입니다. 제품을 설치하거나 임상 워크플로를 수행한 것은 아닙니다.
타사 스크린샷은 이 저장소에 재배포하지 않으며 로고·화면 디자인을 복제하지 않았습니다.

| 출처 | 관찰한 화면/흐름 | PathologyEdge에 적용한 이유 |
|---|---|---|
| [QuPath First steps](https://qupath.readthedocs.io/en/stable/docs/starting/first_steps.html), [작업 화면](https://qupath.readthedocs.io/en/stable/_images/steps_image.jpg), [overview 예](https://qupath.readthedocs.io/en/stable/_images/steps_overview.jpg) | 영상 중심 레이아웃, 얇은 상단 도구, 측정/객체 패널, 작은 위치 개요도, 좌표·눈금 | 핵과 seam을 보면서 후보 정보를 읽을 수 있도록 좌우 패널과 동기 뷰를 배치. 512px PNG에서도 확대 위치를 잃지 않도록 개요도 추가 |
| [Aperio ImageScope DX User’s Guide](https://www.leicabiosystems.com/sites/default/files/media_product-download/2021-02/Aperio_ImageScope_DX_User_s_Guide.pdf), PDF 9쪽/31쪽 | slide tray, 영상과 thumbnail navigator, 고정 도구 모음, 복수 영상의 동기 탐색 | 작은 썸네일 목록으로 예제 탐색, 같은 원본 위치를 유지하는 A/B 비교. 스캐너 배율 대신 검증 가능한 PNG px 눈금만 사용 |
| [에이비스 제품 개요](https://www.aivis.kr/product/overview), [공개 Breast Ki-67 이미지](https://www.aivis.kr/images/overview/carousel/Carousel_03_BreastKi67.webp), [공개 workflow 이미지](https://www.aivis.kr/images/overview/workflow/Workflow_03.webp) | 조직 영상 위 개별 세포 마커, 선택 영역과 분석 결과를 함께 표시하는 공개 예시 | 후보를 누르면 위치·상자·patch ID가 연결되고, 지표를 선택하면 대응 영역을 표시. 제품의 Ki-67 분류·세포 수정·임상 정량 기능을 이 데모에 있는 것처럼 옮기지 않음 |

## 최종 작업 흐름

1. 기본 예제의 실제 결과가 자동으로 열립니다. 왼쪽 썸네일이나 상단 목록에서 예제를 바꿉니다.
2. ‘경계 전후’에서 A 무겹침과 B 겹침 결과를 같은 시야로 비교합니다. ‘경계로 이동’, Ctrl/⌘+스크롤 확대, 드래그·스크롤 이동,
   개요도, 1:1, 맞춤을 같은 도구 모음에서 찾을 수 있습니다.
3. ‘분할’은 실제 예측 마스크, ‘정답’은 실제 GT입니다. 색을 구분하고 투명도를 조절합니다.
   후보는 별도 성분 경로이며 마스크의 연결 성분 수와 같다고 가정하지 않습니다.
4. 이미지 탭의 전체/경계/내부를 선택하면 해당 영역의 **저장된** Dice·IoU·Precision·Recall이 나타납니다.
   평가에서 제외되는 영역은 어둡게 처리합니다. 확대/이동은 수치를 재계산하지 않습니다.
5. ‘중복 병합’은 **같은 겹침 추론**의 raw와 NMS 후 결과입니다. 첫 병합 사례 또는 대응 목록을 선택하면
   억제 raw(분홍)→유지 raw(파랑)와 연결된 patch ID를 추적합니다. 같은 핵이라는 정답 보증은 아닙니다.
6. 실험 탭에서 전체7장의 성능, 악화 사례10_3, 모델 hash, 측정 범위, 데이터 출처와 연구 한계를 확인합니다.

작은 화면에서는 A/B 중 하나를 넓게 보고 전환합니다. 결과 패널은 닫을 수 있는 서랍이며 확대 중심은 유지합니다.
데스크톱은 두 영상을 기본으로 나란히 표시합니다. 단일 영상과 ‘영상 넓게’도 지원합니다.

## 사실성과 상태 처리

- 상단/도움말/상태에 사전 계산 결과임을 표시합니다. ‘분석 실행’ 버튼이나 가짜 진행률은 없습니다.
- 모델/결과/이미지/학습 조건을 변경하지 않았습니다. 오버레이 색상·투명도는 표시 방식만 바꿉니다.
- 로딩은 JSON/PNG 파일 읽기입니다. HTTP 실패·이미지 실패·timeout에 실제 오류와 재시도를 제공합니다.
- 예제0개는 빈 상태로 안내하고 조작을 비활성화합니다. 새 예제 로딩/실패 시 이전 수치를 지웁니다.
- 연속 선택 시 이전 요청을 취소하고 최신 요청만 반영합니다.
- 임상 진단용·실시간 추론·Ki-67 양성률·WSI 전체 성능을 제공하지 않습니다.
- 눈금과 좌표는 원본 PNG px, 화면 배율은 CSS px/PNG px입니다. μm나 현미경 배율을 추정하지 않습니다.

## 변경 전후 캡처

직접 실행한 Chromium 캡처입니다. 비교 기준 예제는10_1이며 병합 확대 예제는11_2입니다.

| 화면 | 이전 | 개선 후 |
|---|---|---|
| 데스크톱1440×1000 | [이전 화면](../artifacts/ui/before-desktop.png) | [공개 배포 화면](../artifacts/ui/after-desktop.png) |
| 모바일390×844 | [이전 화면](../artifacts/ui/before-mobile.png) | [공개 배포 화면](../artifacts/ui/after-390.png) |
| 후보 검토 | [이전 상세 위치](../artifacts/ui/before-selected.png) | [중복 병합 쌍](../artifacts/ui/after-merge.png) |

추가: [경계 확대](../artifacts/ui/after-boundary-zoom.png), [경계 평가 영역](../artifacts/ui/after-boundary-scope.png),
[1024px](../artifacts/ui/after-1024.png), [375px](../artifacts/ui/after-375.png),
[로딩](../artifacts/ui/state-loading-injected.png), [오류](../artifacts/ui/state-error-injected.png), [빈 목록](../artifacts/ui/state-empty-injected.png).
상태 캡처는 테스트 응답 주입이며 정상 배포에 실제 장애가 있었다는 뜻이 아닙니다.
