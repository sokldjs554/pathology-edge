# PathologyEdge · 비교 화면과 사용 흐름

[공개 데모](https://pathology-edge-lab.ykh13571.chatgpt.site/)는 **A/B 2분할 비교**로 시작합니다. 같은 영상에서 A는 겹침 없이 처리한 결과, B는 겹침 처리 후 결합한 결과입니다. 첫 예제 자체에서 B가 더 좋은 결과라고 가정하지 않습니다.

## 먼저 눌러 볼 순서

1. 처음 표시된 A/B 영상을 확인하고, 강조된 **좋아진 경계 보기** 또는 **나빠진 경계 보기**를 누릅니다. 두 영상이 저장된 실제 사례의 같은 위치로 이동합니다.
2. 영상 위의 **A/B 2분할 / 원본·정답 4분할**로 배치를 선택합니다. 4분할 진입 시 슬라이드 목록을 접어 영상 높이를 확보합니다. 2분할로 돌아오면 이전 목록 상태를 복원합니다.
3. 네 영상의 **크게 보기**를 누르면 선택 영상이 작업 영역을 채웁니다. **비교로 돌아가기** 또는 `Esc`로 복원합니다. 화면 배치 변경은 원본 좌표를 유지하며, **맞춤**은 전체 영상으로 시야를 재설정합니다.
4. **결과 확인**에서 개별 이미지·선택 경계·전체 실험 지표를 구분해 읽습니다. 4분할에서는 반복 하단 설명을 줄이고 영상에 공간을 배정하며, 지표는 결과 패널에서 확인할 수 있습니다.
5. 왼쪽 **후보 데이터 → #12 검색 → 행 선택**으로 해당 위치·실제 확대 조각·수치를 확인합니다. 표의 번호는 저장된 후보 번호이며, 정답 핵 수나 임상적으로 보정된 신뢰도가 아닙니다.
6. **WSI 탐색 / 경계 비교 / IHC 세포 분류** 메뉴는 모든 화면에서 같은 이름을 사용합니다. WSI의 **슬라이드·모델·분석 범위**를 펼치면 해시·출처·분석 범위를 확인할 수 있습니다.

| 작업 화면 | 역할 |
| --- | --- |
| 병리 작업대 | B 결과를 단독 탐색. ‘B 결과 탐색 중’ 표시와 맞춤·1:1·이동·확대 제공 |
| 다중 비교 | 기본 A/B 2분할, 선택적 원본·정답 포함 4분할. 각 영상 크게 보기와 같은 좌표 복원 |
| 후보 데이터 | 영상 옆 실제 후보 표의 검색·시야/경계 필터, 후보 위치·확대 조각·상세 정보 연결 |

핵심 데스크톱 버튼·설명은 13px 이상, 후보 표 값은 14px로 키웠습니다. 작은 화면에서는 A/B 전환과 내부 스크롤을 사용하며, 반복 안내를 줄여 영상 시작 위치를 확보합니다. WSI·IHC도 큰 영상과 하단 ROI/사례 목록을 유지합니다.

## 변경 전후

- [이전 첫 화면: B 단독 탐색](../artifacts/ui-studio-20261116/studio-image-laptop.png) → [현재 첫 화면: A/B 2분할](../artifacts/ui-readability/entry.png)
- [이전 4분할](../artifacts/ui-studio-20261116/studio-compare-laptop.png) → [현재 4분할](../artifacts/ui-readability/four.png)
- [후보 데이터 화면](../artifacts/ui-readability/candidate-data.png) · [WSI 화면](../artifacts/ui-readability/wsi.png) · [IHC 화면](../artifacts/ui-readability/ihc.png)

## 실제 데이터와 검증 범위

기존 저장 이미지·마스크·결과 JSON을 표시합니다. 새 추론이나 임상 검증을 수행하는 화면이 아닙니다. 원본 참고 영상에는 예측을 합성하지 않으며, 정답 참고 영상은 실제 원본과 저장된 정답 마스크를 사용합니다. 실험 수치·사용자 작성 Python 코드는 변경하지 않습니다.

로컬 관리 브라우저 도구가 없어 기존 GitHub Actions의 Chromium·WebKit에서 실제 브라우저 검사와 화면 캡처를 수행합니다. 사용자의 이번 수정본 직접 확인은 아직 완료로 기록하지 않습니다.

- UI 코드 [`2852b33`](https://github.com/sokldjs554/pathology-edge/commit/2852b335654e1739d73b02be89d970234eada9c4), Sites 버전 12 / 소스 `d908780f0a4ee7a9e75b1eb60c438b3a78c2dcc5`.
- [코드의 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43741673952): Chromium·WebKit 각각 55개. 2/4분할·네 영상 크게 보기·같은 좌표·화면 크기 변경 후 목록 복원·작은 화면·출처 접기·메뉴 일치를 확인합니다.
- [CPU 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43741679797): Python 462개, 저장 Dice 42개·평균 6개 일치. Node 로직 테스트 14개도 통과했습니다.
- [최종 공개 주소 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43742062792): Chromium·WebKit 각각 55개 통과, 실패·건너뜀·불안정 테스트 0개. [배포 파일 2,193개 일치](../artifacts/ui-readability/deployment-parity.json) · [검증 기록](../artifacts/ui-readability/verification.json).

[이전 버전 8의 기록](UI_LINKED_WORKBENCH_V8.md) · [버전 11의 검증 기록](../artifacts/ui-studio-20261116/verification.json)
