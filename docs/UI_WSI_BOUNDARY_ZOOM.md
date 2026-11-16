# WSI 경계 확대 보기

‘차이가 큰 경계’를 누르면 저장된 64×64 경계를 중심에 놓고 최대 300%로 표시합니다. 1440px 데스크톱에서는 상자가 64px에서 약 192px로 커집니다. 원본 좌표의 사방 48px를 함께 맞추므로 주변 조직이 남고, 작은 화면에서는 공간에 맞춰 배율을 낮춥니다.

- 확대된 화면은 기존 **확대 표시** 문구와 실제 배율로 구분합니다. 새로운 광학 디테일이나 추론 결과를 생성하지 않습니다.
- 양쪽 영상의 중심은 동일한 저장 좌표입니다. 표시 영역이 커져도 64×64 안의 추가·제거 픽셀 수는 바뀌지 않습니다.
- 일반 ROI·후보 이동은 원본 100% 이내입니다. **원본 1:1**을 누르면 선택 경계의 중심을 유지한 채 100%로 돌아갑니다.
- 원본 PNG, 예측·차이 오버레이, 상세 근거, 슬라이드 탐색, TNBC/IHC 데이터는 그대로입니다.

## 직접 확인

[WSI 탐색](https://pathology-edge-lab.ykh13571.chatgpt.site/wsi.html) → 영역 목록 → R1 → **차이가 큰 경계**를 누릅니다. 데스크톱에서 양쪽의 같은 상자가 약192px로 보이고, 300%·확대 표시가 나오는지 확인합니다. 이어 **원본 1:1**을 누르면 중심과 수치는 유지되면서 상자만 작아집니다.

사용자의 이번 수정본 직접 확인은 아직 기록하지 않았습니다.

## 화면

[이전 100% 화면](../artifacts/ui-wsi-native/wsi-native-boundary-1440.png) · [확대된 데스크톱](../artifacts/ui-wsi-boundary-zoom/wsi-native-boundary-enlarged-1440.png) · [작은 화면](../artifacts/ui-wsi-boundary-zoom/wsi-native-boundary-enlarged-375.png)

이전 화면은 버전26, 새 화면은 아래에 기록한 배포 실행에서 수집합니다. 동일한 경계 좌표의 표시 배율을 비교합니다.

## 배포와 검증

- 배포 버전27, UI [`81bf9e3`](https://github.com/sokldjs554/pathology-edge/commit/81bf9e3c65b9fe89fdae296225b96c9cd3428e8e), Site 소스 `d27412a8fe2f4f7df3ea6d36ef79e2c9d1600b86`.
- [소스 전체 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43889874919): Chromium·WebKit 각각88개 통과, 실패·skip·flaky 0. [Chromium 보고서](../artifacts/ui-wsi-boundary-zoom/source-chromium-report.json) · [WebKit 보고서](../artifacts/ui-wsi-boundary-zoom/source-webkit-report.json).
- [Node 21개 통과](../artifacts/ui-wsi-boundary-zoom/node-tests.log): 일반 ROI의 100% 제한과 명시적 경계 확대의 300% 제한을 구분해 검사했습니다.
- 데스크톱 상자의 기하학적 너비192px를 검사했습니다. 표시 테두리1.5px는 별도로 취급합니다. 작은 화면에서는 경계가 커지면서 주변 조직도 남는지 확인했습니다.
- [파일 대조](../artifacts/ui-wsi-boundary-zoom/public-parity.json): Site 배포 파일2,197개와 저장소가 같고, 공개 주소의 WSI JS·HTML·CSS·결과 JSON 해시도 일치합니다. 영상·마스크·실험 수치·모델은 변경하지 않았습니다.
- [공개 주소의 WSI 원본·확대 동작 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43891195353): Chromium·WebKit 각각7개 통과, 실패·skip·flaky 0. [Chromium](../artifacts/ui-wsi-boundary-zoom/public-chromium-report.json) · [WebKit](../artifacts/ui-wsi-boundary-zoom/public-webkit-report.json). 새 화면 캡처는 이 공개 배포 실행에서 수집했습니다.

실제 브라우저에서 자동 조작하고 캡처를 검토한 결과입니다. 주석 없는 WSI의 정확도 개선이나 사용자의 직접 화면 검토를 새로 기록한 것은 아닙니다.
