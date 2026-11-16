# PathologyEdge · 첫 방문 비교 흐름

[공개 데모](https://pathology-edge-lab.ykh13571.chatgpt.site/)는 같은 위치의 **A(겹침 없음) / B(겹침·결합)** 영상으로 시작합니다. 색상과 영상 중심 작업대는 유지하고, 처음 보는 사람에게 필요한 조작을 앞에 배치했습니다.

## 먼저 눌러 볼 순서

1. **좋아진 경계 보기** 또는 **나빠진 경계 보기**를 누릅니다. 저장된 실제 사례의 같은 위치로 두 영상이 이동합니다. 버튼은 전체 예제 중 해당 사례를 선택하므로 상단 예제 번호도 함께 바뀔 수 있습니다.
2. 영상 위 한 줄에서 **선택 상자의 경계 Dice A → B**, 정답 일치·불일치로 바뀐 픽셀 수를 확인합니다. Dice는 높을수록 정답과 비슷합니다. 이 수치는 흰 64px 상자와 기준 경계 띠가 겹치는 영역에 한정되며 이미지 전체 점수나 핵 개수가 아닙니다.
3. **+/− · 맞춤**으로 확대하고 드래그·스크롤로 이동합니다. 양쪽 시야는 연결됩니다. 작은 화면은 A/B 버튼으로 같은 위치를 전환합니다.
4. **근거 보기**를 누르면 선택 경계의 결과부터 표시합니다. 좌표·다른 사례 선택은 **다른 경계·좌표 확인**, 선택 기준은 **이 위치를 고른 기준**을 펼칩니다.

## 더 살펴볼 때

**상세 도구** 한 곳에서 다음 기능을 엽니다. 첫 화면의 왼쪽 작업대 메뉴와 반복 비교 메뉴는 제거했습니다.

| 도구 | 확인할 내용 |
| --- | --- |
| 원본·정답 4분할 | A/B 예측과 실제 원본·정답을 같은 위치로 비교. 각 영상의 크게 보기 / 비교로 돌아가기 제공 |
| B 영상만 | B 결과 단독 탐색. A/B 비교로 돌아가기 제공 |
| 후보 표 | 후보 번호 검색·시야/경계 필터 → 행 선택 → 위치·원영상 확대 조각·후보 정보 연결 |
| 중복 병합 | 동일 겹침 추론의 raw 후보와 NMS 후 후보 비교. 억제가 올바른지 자체적으로 입증하는 표시가 아님 |
| 표시 설정 | 분할·정답·후보·패치 경계·불투명도 조절 |
| 검토 패널 | 개별 이미지 전체·경계·내부 지표와 후보 상세 |
| 전체 실험·출처 | 7개 이미지·2개 케이스 그룹의 평균, 처리 비용·측정 조건·한계·출처 |
| 이동·예제 | 1:1, 현재 예제 경계, 예제 썸네일 목록, 좌표 상세 |

상세 도구는 `Esc`, 바깥 클릭 또는 기능 선택으로 닫습니다. 결과 패널은 사용자가 열며 사례 버튼을 처음 눌렀을 때 자동으로 영상을 좁히지 않습니다. WSI와 IHC의 별도 분석 흐름은 그대로 유지합니다.

## 변경 전후와 검증

- [이전 첫 화면](../artifacts/ui-readability/entry.png) · [이전 4분할](../artifacts/ui-readability/four.png)
- [현재 첫 화면](../artifacts/ui-progressive/entry.png) · [개선 사례](../artifacts/ui-progressive/improved.png) · [악화 사례](../artifacts/ui-progressive/worsened.png)
- [현재 4분할](../artifacts/ui-progressive/four.png) · [후보 데이터](../artifacts/ui-progressive/candidate-data.png) · [작은 화면](../artifacts/ui-progressive/mobile.png)
- UI 코드 [`27eb62a`](https://github.com/sokldjs554/pathology-edge/commit/27eb62a619271c42ee4ffbbe45d388864906f930), Sites 버전 14 / 소스 `01be56294db63114ba1944259e8b09ffb9384155`.
- [코드의 실제 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43747305455): Chromium·WebKit 각각 62개 통과. 초기 노출 범위, 국소 수치, 두 영상의 같은 위치, 4분할·크게 보기, 후보 연결, 키보드·작은 화면·오류 상태를 확인했습니다.
- [CPU 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43747305456): Python 462개 통과, Dice 42개·평균 6개 일치. Node 로직 테스트 14개도 통과했습니다.
- [공개 주소 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43747526658): Chromium·WebKit 각각 62개 통과, 실패·건너뜀·불안정 테스트 0개. 느린 사례 로딩 중 4분할 선택도 유지됩니다.
- [배포 파일 2,195개 대조](../artifacts/ui-progressive/deployment-parity.json) · [검증 기록](../artifacts/ui-progressive/verification.json). 화면 캡처는 이 공개 주소 검사에서 수집했습니다.
- [버전 12 기록](UI_REVIEW_ENTRY_V12.md) · [버전 8 기록](UI_LINKED_WORKBENCH_V8.md)

기존 저장 이미지·마스크·실험 결과를 표시합니다. 새 추론·임상 검증·WSI 전체 핵 검증을 실행하는 화면이 아니며, 사용자 작성 알고리즘과 실험 수치는 변경하지 않습니다. 사용자의 이번 수정본 직접 확인은 아직 완료로 기록하지 않습니다.
