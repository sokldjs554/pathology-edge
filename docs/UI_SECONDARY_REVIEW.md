# WSI·IHC 선택 결과 중심 화면

이번 변경은 WSI·IHC 화면에 한정됩니다. 보라색·흰색 스타일, 저장 영상·예측·모델·실험 조건·데이터 출처를 유지했습니다. TNBC 경계 비교 HTML/JS/CSS와 모든 JSON·영상 자산은 변경하지 않았습니다.

| 화면 | 기본으로 보이는 내용 | 필요할 때 펼치는 내용 |
|---|---|---|
| WSI | 큰 슬라이드, R1–R3 선택, 탐색/A·B 전환, 확대·축소·전체 맞춤, 현재 중심의 분석 여부, 저장 결과·핵 정답 없음 | 표시 설정: 영역·예측·경계·후보·차이·불투명도·1:1. 상세 근거: ROI 처리 기록, 중복 후보·패치 출처, 모델·데이터·측정 조건 |
| IHC | 원본과 선택 중심, 세포 crop, 정답·예측·선택 점수, 오류/일치 한 문장, 네 클래스 점수, 이전·다음·성공/실패 전환 | 전체 실험 결과: Macro-F1·Accuracy·클래스별 성능·혼동행렬. 방법·출처: 분리·모델 선택·특징·측정·주석 한계·원자료·JSON 링크 |

WSI 상세 패널은 처음에는 닫힙니다. IHC는 따로 나뉘던 확대 세포 열과 전체 성능 패널을 하나의 선택 세포 패널로 합쳤습니다. 작은 화면에서는 선택 세포가 영상 아래에 놓이고 상세 내용은 패널 내부에서 스크롤합니다. 원본과 crop의 좌표 체계는 그대로입니다. IHC 사례 목록은 선택 메뉴·이전/다음과 중복되어 기본으로 접었습니다.

WSI는 현재 중심이 저장된 분석 범위 밖이면 ‘미분석’으로 표시합니다. 핵 정답이 없어 예측 변화가 정확도 개선이 아님을 영상 옆에 명시합니다. IHC는 정답 중심을 입력한 저장 분류이며 자동 검출이 아닙니다. 선택 점수는 전체 테스트 정확도와 별도 위치에 두었습니다.

## 직접 확인할 순서

1. WSI 탐색 → 전체 영상 이동·확대 → R1 선택 → A/B 비교 → ‘차이가 큰 경계’. 양쪽 영상은 같은 실제 저장 위치를 가리킵니다.
2. ‘표시 설정’에서 핵 예측을 껐다 켜기 → ‘상세 근거’의 처리 기록 펼치기 → 중복 후보·출처 추적. 패널을 닫아도 선택 ROI·중복 쌍·확대 위치가 유지됩니다.
3. IHC 세포 분류 → 실패 사례의 정답·예측·점수·오류 문장 확인 → 다음·이전 → 정답 사례 전환. 선택한 세포와 원본 위치·crop·점수가 함께 바뀝니다.
4. ‘전체 실험 결과’를 펼쳐 전체 테스트 성능 확인 → ‘방법·출처’에서 분리·측정·원자료 링크 확인. 개별 점수와 전체 성능을 구분합니다.
5. 노트북 크기에서 패널을 닫았다 열어 같은 위치/사례가 유지되는지 확인합니다.

이번 수정본을 사용자가 직접 검토했다는 기록은 아직 없습니다. 새 데이터 학습·추론 실험은 수행하지 않았습니다.

## 전후 화면

기본 화면 전후는 1440×1000입니다. 변경 전은 공개 버전 20 캡처입니다. 변경 후는 2026-11-16 공개 버전 22를 실제 Chromium으로 조작한 자동 검사에서 저장한 화면이며, 저장한 캡처도 직접 검토했습니다.

| 화면 | 변경 전 | 변경 후 |
|---|---|---|
| WSI 탐색 | [기존 전체 보기](../artifacts/ui-navigation/navigation-studio-wsi.png) | [간결한 전체 보기](../artifacts/ui-secondary-review/secondary-wsi-first-1440.png) |
| IHC 분류 | [기존 세포·전체 성능 배치](../artifacts/ui-navigation/navigation-studio-ihc.png) | [선택 세포 중심 배치](../artifacts/ui-secondary-review/secondary-ihc-first-1440.png) |
| TNBC 경계 비교 | [기존 화면](../artifacts/ui-navigation/clarity-first.png) | [유지된 비교 화면](../artifacts/ui-secondary-review/clarity-first.png) |

[1024px WSI A/B](../artifacts/ui-secondary-review/secondary-wsi-compare-1024.png) · [1024px IHC 전체 실험 펼침](../artifacts/ui-secondary-review/secondary-ihc-results-1024.png) · [375px WSI](../artifacts/ui-secondary-review/secondary-wsi-first-375.png) · [375px IHC](../artifacts/ui-secondary-review/secondary-ihc-first-375.png)

작은 화면에서는 WSI의 개별 A/B 선택 버튼을 비교 중에만 보여줍니다. IHC 전체 실험·방법은 패널 내부에서 펼치고 스크롤하며, 원본 영상의 선택 위치는 유지됩니다.

## 검증과 배포

- UI 커밋: [`d8d4263`](https://github.com/sokldjs554/pathology-edge/commit/d8d42635345876bf870959515e5d9f989ddd4450).
- 배포 버전: **22**. Site 소스: `c92fd2c3769aee268c0f7a257a5e8bfacfcfcca9`.
- [공개 데모](https://pathology-edge-lab.ykh13571.chatgpt.site/) · [Draft PR #3](https://github.com/sokldjs554/pathology-edge/pull/3). UI 브랜치에 반영했으며 main에 병합하지 않았습니다.
- [소스 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43831993467): Chromium·WebKit 각각 **81개 통과**, 실패·건너뜀·재시도로만 통과한 항목 0개.
- [공개 데모 브라우저 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43832804523): 배포 버전 22에서 Chromium·WebKit 각각 **81개 통과**, 실패·건너뜀·재시도로만 통과한 항목 0개. 로컬 파일이 아닌 공개 URL을 열어 확인했습니다.
- Node **16개** 통과. [Python 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/43832001679) **462개** 통과. 저장 Dice **42/42개**, 평균 **6/6개** 일치. 정적 데모 검사 통과.
- 배포 소스 **2,197개** 파일과 GitHub dist를 대조했습니다. 공개 HTTP에서 UI·근거·공유 스타일 **18개** 파일도 일치했습니다. [해시 대조](../artifacts/ui-secondary-review/deployment-parity.json)
- 검사 시각·원본 보고서·캡처 해시·배포 연결은 [검증 기록](../artifacts/ui-secondary-review/verification.json)에 있습니다. `before-secondary-*`는 변경 전 소스 검사 캡처이며, `secondary-*`와 위 표의 변경 후 캡처는 최종 공개 배포 검사에서 가져왔습니다.

검사는 실제 원본·crop·좌표·16개 IHC 사례 점수·클래스 지표·혼동행렬·분리를 저장 JSON과 비교합니다. WSI는 R1–R3 좌표와 마스크·처리 기록, 저장 경계로 이동, NMS 후보·원래 패치의 대응을 검사합니다. 패널 변경 전후의 level-0 중심과 원본 대비 배율, 선택 세포, 오버레이를 확인합니다. 1440×1000·1024×768·375×667의 전체 흐름과 기존 390px 반응형 검사, 로딩·빈 결과·HTTP 오류·누락 이미지·타일/오버레이 재시도도 포함합니다.

검사 중 발견한 경계 이동 후 위치 복귀와 IHC 상세 표를 펼칠 때 문서 밖으로 잡히던 숨김 caption의 영역을 수정했습니다. 실제 경계 좌표 도착 및 펼친 상태의 문서 가로·세로 크기를 회귀 검사합니다. WSI 재시도 시 이전 ROI 표시도 초기화합니다.
