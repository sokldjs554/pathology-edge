# 실제 WSI 확장 구현 결정

2026-11-08 Asia/Seoul. 사용자 요청에 따라 조사→비교 후 구현한다. 기존 main40f18fc는 보존하고 feature/wsi-review 작업트리에서 진행한다.

## 조사에 따른 결정

[16개 비교](../WSI_LANDSCAPE.md), [WSI 자료](../WSI_DATA_OPTIONS.md), [AIVIS/IHC](../AIVIS_IHC_FEASIBILITY.md)를 근거로 한다. WSI viewer, overlap/Hann, seam 평가, provenance 자체는 기존 기능이다. 차별화 표현은 이 CPU baseline에서 실제 좌표·오류·후보 억제·비용을 추적하고 한계를 구분하는 포트폴리오로 제한한다.

- 실제 공개 CMU-1-JP2K-33005.svs(CC0),46000×32893,0.499µm/px를 사용한다. Huron-1은 macro에서 일부 스캔 영역만 확인되어 주 뷰어에서 제외한다.
- OpenSlide4.0.1/Python1.4.7로 실제 원본을 검증하고 native level0의3개1024px ROI만 추론한다. 원본SHA256 9a1923cd9bcb260ba4d99d64f8d6e32550648c332ba48817f920662f3a513420. 조직형·진단·염색 종류는 출처가 확인한 범위만 표시한다.
- OpenSeadragon을 고정 버전으로 vendoring하고 공식 OpenSlide DZI 타일을 확대 수준에 따라 요청한다. 공식 원본과 동일한 JP2K 변형의 크기/경로를 사용한다. 외부 타일 서비스 의존성과 로딩 실패를 표시한다. 전체 파일의 PNG 확대 흉내나 신규 유료 서버를 쓰지 않는다.
- ROI 제안(추론 전 전체 영상의 조직 포함 여부만으로 선택): R1(5888,20608),R2(29440,9728),R3(15872,26112),각1024×1024. 기존 TinyUNet/threshold0.5를 그대로 사용한다. 모델/원 결과/사용자 함수는 변경하지 않는다.
- WSI는 GT 없음. 새 segmentation Dice/검출 정확도/개선·악화 판정을 만들지 않는다. 무겹침 vs Hann 겹침의 예측 불일치, 추가/제거 픽셀, raw/NMS 후보와 기원 patch·IoU·거리·억제 사유를 표시한다. GT 기반 개선/악화는 별도 TNBC 화면으로 연결한다.
- WSI 새 페이지와 기존 경계 화면을 명확한 내비게이션으로 연결한다. 조직 전체→ROI→동일 좌표 비교→patch/후보 근거 순서. 현재 시야가 분석 영역 밖이면 미분석임을 표시한다. 물리 눈금과 화면 확대 배율/스캐너 objective를 혼동하지 않는다.
- Patherea P1은 별도 실제 IHC 자료: 저자 fold1 test고정,train에서val분리,GT-center 조건4class CPU color-feature baseline. WSI/기존TNBC와 결과를 섞지 않는다. 자동검출·임상Ki67검증으로 표현하지 않는다.

## 검증

1. 실제 읽은 ROI 픽셀/level0 bounds/metadata와 overlay 좌표를 검증한다. 일반 배율 함수 사용자 과제는 그대로 둔다.
2. ROI×방식별3회warm CPU시간·독립worker peakRSS·읽기시간을 기록한다. 전체WSI추론 비용으로 쓰지 않는다.
3. raw 후보 patchID→origin/bbox→suppressed kept ID/IoU/거리/순위규칙을 실제 출력으로 대조한다.
4. DeepZoom 서로 다른 level/native tile를 실제 요청하고 source metadata/local crop 위치와 일치하는지 검증한다.
5. 기존36Python+5geometry+26browser회귀를 유지하고 WSI/IHC 검사를 추가한다. 지원 브라우저 실행은 기존 GitHub Actions Chromium/WebKit 경로를 사용한다.
6. 공개 배포, source/dist byte parity, 실제 공개URL 재검사, 전후캡처·기여구분을 기록한다. 원본WSI와큰ZIP은저장소/배포에넣지않는다.

## 작업 분담

Codex: 조사·WSI원본검증·ROI추론·viewer·IHC기준선·테스트·배포. 사용자: 기존 local_to_level0 구현과12개명시적실습검사, 새WSI 화면검토는 아직 예정. 사용자 완료를 추정하지 않는다.
