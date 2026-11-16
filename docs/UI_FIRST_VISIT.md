# PathologyEdge · 첫 화면에서 실제 차이 읽기

## 바뀐 진입 흐름

첫 화면은 저장된 `11_1-improved` 사례를 바로 엽니다. 사용자가 경계를 찾아 확대해야 했던 이전 흐름을 바꾸었습니다. 직접 이미지나 사례가 지정된 링크는 해당 대상을 우선합니다. 사례 파일이 없거나 검증에 실패하면 기존 이미지 비교로 남고 오류를 표시합니다.

설명은 영상 위 여러 줄 대신 왼쪽 읽기 영역으로 옮겼습니다. 패치가 맞닿는 A와 절반 겹치는 B의 **설명용 도식**을 보여 주며, 실제 예측과 구분합니다. 영상 제목도 ‘겹치지 않게 잘라 분석’과 ‘겹쳐 분석한 뒤 결과 결합’으로 표시합니다. 128px 패치와 이동 간격은 보조 정보입니다.

영상에는 **각 방식의 실제 예측 면과 윤곽**을 표시합니다. 점선은 A의 128px 이동 경계를 두 영상에 공통 표시한 비교 기준이며, B의 모든 패치 경계를 뜻하지 않습니다. 양쪽에 같은 청록·분홍 픽셀을 덮는 변경 강조는 기본으로 끄고, 필요할 때 켜도록 했습니다. 면 불투명도는 채움의 진하기를 조절하며 0%에서는 면과 윤곽을 함께 숨깁니다.

왼쪽 A 예측·B 예측·정답 마스크는 흰 64px 상자를 그대로 잘라 표시합니다. 별도 추론이나 모양 보정은 없습니다. **마스크는 상자 전체이고, 아래 Dice·변경 픽셀 수는 상자 안의 경계 띠만 평가한 값**입니다. 선택 사례를 전체 평균으로 표시하지 않습니다.

중복 병합에서는 설명과 영상 제목이 ‘같은 겹침 추론의 후보 억제 전·후’로 바뀝니다. 서로 다른 패치 방식을 비교하는 도식은 숨깁니다. 후보 억제가 올바르다는 의미로 표현하지 않습니다.

## 직접 확인 순서

1. [데모](https://pathology-edge-lab.ykh13571.chatgpt.site/)를 엽니다. `11_1` 개선 사례가 표시되고 양쪽 흰 상자가 같은 위치를 가리킵니다. 노란 윤곽과 A/B/정답 마스크의 모양을 비교합니다.
2. 선택 경계의 Dice `0.626 → 0.854`, 정답 일치로 변경 `268px`, 불일치로 변경 `11px`를 확인합니다. 핵 개수가 아닙니다.
3. **나빠진 경계 보기**를 누릅니다. 이미지·마스크·좌표·점수가 함께 바뀌며 악화 사례라고 표시됩니다.
4. **변경 강조**를 켰다 끕니다. 공통 변경 지도만 바뀌고 점수는 유지됩니다.
5. **상세 도구**에서 4분할·크게 보기·후보 표·중복 병합·전체 실험을 확인합니다. 작은 화면에서는 A/B 전환과 접혀 있는 실제 마스크 비교를 사용할 수 있습니다.
6. WSI 탐색과 IHC 세포 분류로 이동해 기존 슬라이드·ROI·세포 결과를 확인합니다.

사용자가 이번 수정본을 직접 확인한 것으로 기록하지 않습니다. 자동 검사와 화면 검토는 실제 면접관 대상 사용성 시험을 대신하지 않습니다.

## 근거와 검증

실제 저장 이미지·마스크·실험 수치·사용자 작성 알고리즘은 변경하지 않았습니다. 새로 실행한 모델 추론이나 실험은 없습니다.

- UI 소스: [`cbe1910`](https://github.com/sokldjs554/pathology-edge/commit/cbe1910fb2bb2ee9df6d344de2edb662839c7dd4), `feat/linked-pathology-workbench`. [PR #3](https://github.com/sokldjs554/pathology-edge/pull/3)은 Draft이며 main에 병합하지 않았습니다.
- 공개 배포: 버전 **18**, Site 소스 `08e56df844ca1b057ad2bc0a2c0e39ee04089a09`. GitHub UI 소스와 배포 소스의 2,196개 파일이 일치합니다. 공개 HTTP로 변경된 6개 파일과 WSI/IHC 페이지·사례/결과 JSON 등 10개 파일의 해시를 확인했습니다. [대조 기록](../artifacts/ui-clarity/deployment-parity.json)
- [소스 체크아웃 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43813930114): Chromium **73개**, WebKit **73개** 통과. 건너뜀·실패·재시도로만 통과한 항목 모두 0개입니다.
- [공개 배포 주소 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43814496194): 같은 UI 커밋으로 Chromium **73개**, WebKit **73개** 통과. 건너뜀·실패·재시도로만 통과한 항목 모두 0개입니다. 아래 변경 후 화면은 이 검사의 Chromium 캡처입니다.
- [기존 Python 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43813930136): **462개 통과**. 저장된 Dice **42/42개**, 이미지 평균 **6/6개** 일치. Node 검사 **14개** 통과, 정적 데모 검사 통과.

검사에는 자동 진입·개선/악화 사례·예제 변경·명시적 이미지/사례 링크·새로고침·확대/이동·오버레이·4분할·영상 크게 보기·후보 표와 확대 조각·중복 억제 추적·지표 범위·빈 화면/오류/재시도·WSI·IHC가 포함됩니다. 작은 화면과 태블릿의 조작, 가로 넘침, 영상 높이도 확인했습니다.

이번 추가 검사에서는 A/B/정답 미니 마스크의 **모든 표시 픽셀**을 저장 마스크와 대조하고, 예측 윤곽을 원본 마스크의 4방향 이웃으로 별도 계산해 대조합니다. 설명용 패치 도식은 예측 결과와 구분합니다.

독립 코드 검토에서 발견한 초기 이미지 로딩 중 사용자 레이아웃 선택 덮어쓰기와 모바일 평가 범위 설명 숨김을 수정했습니다. 실제 브라우저 검사에서 발견한 작은 화면 높이 문제도 수정한 뒤 전체 검사를 다시 실행했습니다.

공개 주소의 최종 브라우저 검사 결과와 화면 출처는 [검증 기록](../artifacts/ui-clarity/verification.json)에 정리합니다.

## 변경 전후 화면

아래 변경 후 화면은 공개 배포 주소에서 브라우저 검사를 실행하며 캡처했습니다.

| 화면 | 변경 전 · 버전 16 | 변경 후 · 버전 18 |
| --- | --- | --- |
| 첫 화면 | [기존 A/B 진입](../artifacts/ui-stain-theme/simple-entry.png) | [실제 사례·예측 윤곽·정답 비교](../artifacts/ui-clarity/clarity-first.png) |
| 개선 사례 | [공통 강조 지도](../artifacts/ui-stain-theme/simple-improved.png) | [실제 A/B 예측과 국소 지표](../artifacts/ui-clarity/simple-improved.png) |
| 악화 사례 | [이전 화면](../artifacts/ui-stain-theme/simple-worsened.png) | [변경 후](../artifacts/ui-clarity/clarity-worsened.png) |
| 4분할 | [이전 화면](../artifacts/ui-stain-theme/readability-four.png) | [원본·정답 포함 비교](../artifacts/ui-clarity/readability-four.png) |
| 후보 표 | [이전 화면](../artifacts/ui-stain-theme/studio-data-laptop.png) | [영상·후보 연결](../artifacts/ui-clarity/studio-data-laptop.png) |

[375px 화면](../artifacts/ui-clarity/clarity-375.png) · [1024px 화면](../artifacts/ui-clarity/clarity-1024.png) · [중복 억제 화면](../artifacts/ui-clarity/clarity-merge.png) · [WSI 탐색](../artifacts/ui-clarity/wsi-overview.png) · [WSI ROI](../artifacts/ui-clarity/wsi-roi-native.png) · [IHC](../artifacts/ui-clarity/ihc-desktop.png)
