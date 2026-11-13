# Pathology Edge

**병리 이미지의 패치 경계가 핵 분할에 미치는 영향을 재현하고 검토하는 연구용 작업대.**
같은 모델의 무겹침·겹침 처리를 비교하고, 정확도·처리 시간·메모리·실패 사례를 함께 공개합니다.

[실제 WSI 탐색](https://pathology-edge-lab.ykh13571.chatgpt.site/wsi.html) · [정답 경계 실험](https://pathology-edge-lab.ykh13571.chatgpt.site/) · [IHC 분류](https://pathology-edge-lab.ykh13571.chatgpt.site/ihc.html) · [Docker 재현·확인 완료](docs/STEP_50.md) · [실행 안내](docs/RUNBOOK.md) · [기여 기록](docs/CONTRIBUTIONS.md)

연구·교육용입니다. 에이비스와 무관한 독립 프로젝트이며 실제 진단·치료 결정에 사용할 수 없습니다.
**공개 데모는 WSI 탐색, 제한된 ROI의 예측 비교, IHC 정답 중심점 조건 분류를 구분합니다. 별도 연구 코드에서는 자동 IHC 패치 검출·분류를 실험했으며, 임상 Ki-67 검사·WSI 전체 모델 처리·임상 검증은 수행하지 않았습니다.**

[자동 Ki-67 패치 실험](docs/AUTO_KI67_EXPERIMENT.md) · [후보 제거 전후·외부 실패 결과](docs/KI67_CANDIDATE_FILTER.md): 후보 필터로 내부 검출 F1은0.0982→0.1260으로 올랐지만 BCData133장에서는 네 방식의 F1이 모두 하락했습니다. 필터는 연구 비교 기능이며 공개 데모 기본 분석에 적용하지 않았습니다. 기존 평가 자료의 재평가로, 새 미노출 외부 검증이 아닙니다.

[학습한 세포 중심 검출](docs/KI67_LEARNED_CENTERS.md): 정답 좌표 없이 새 중심을 예측하는 소형 검출기를3seed로 학습했습니다. 내부407장 검출 F1은0.0982→0.3172~0.3553, BCData133장 종양2-class F1도12개 조합 모두 상승했습니다. 다만 내부 재현율은 하락했고 양성률 오차는 일부 악화됐습니다. 기존 자료 재평가이며 새 미노출 외부·임상 검증이 아닙니다. 모델·한 장 추론 명령·실제 전후 화면을 별도 자료로 제공합니다.

[모델·전후 화면 ZIP 다운로드](https://raw.githubusercontent.com/sokldjs554/pathology-edge/8ba7d50e37579dd2e2782d8fd40549375d024896/artifacts/handoff/PathologyEdge-LearnedCenters-20261113.zip) · [첫 화면 확인 순서](docs/STEP_80.md).113파일·5.47MB, 공개 다운로드와 전체 파일 해시를 확인했습니다.

[검출 누락 원인·재현율 조건 비교](docs/KI67_RECALL_DIAGNOSIS.md): 검증227장의 누락을 피크 없음·점수 미달·거리 억제·대응 경쟁으로 분리했습니다. 고정3seed 중 하나만 재현율 조건을 만족했습니다. 같은 모델의 설정 비교에서 내부407장 재현율은0.3943→0.6060으로 올랐지만 F1은0.3553→0.1924로 낮아졌습니다. 내부·BCData의 네 분류기 양성률 MAE는 모두 줄었으나 세포 F1은 모두 하락했습니다. 기존 기본값을 유지하며 [비교 화면 ZIP](artifacts/handoff/PathologyEdge-RecallReview-20261113.zip)과 [첫 확인 순서](docs/STEP_82.md)를 별도로 제공합니다.

[최신 통합 상태·U97](docs/HANDOFF_U97.md) · [Cowork 전달용 완료 작업·개인 구현 근거](docs/COWORK_HANDOFF.md) · [보정 head 3개 seed 실험](docs/REFINEMENT_REPEATS_RESULTS.md) · [MoNuSeg 외부 평가](docs/EXTERNAL_MONUSEG_VALIDATION.md) · [임상·전체 WSI 검증 상태](docs/CLINICAL_WSI_VALIDATION_STATUS.md)

추가 보정 실험에서는 기존 TNBC validation10장의 3개 seed 평균 전체 Dice가 **0.555994→0.576699**였지만, 고정한 사용자 모델 쌍의 외부 MoNuSeg14ROI 평균은 **0.551974→0.534943**으로 하락했습니다. 두 실험은 모델·평가 범위가 달라 합산하지 않습니다. 공개 데모의 기존 결과는 유지합니다.

후속 공개 자료 점검에서 [실제 WSI 연결 PanopTILs 3ROI](docs/PANOPTILS_WSI_PROBE.md)의 유효 정답 영역 Dice는 **0.479080→0.435576**, [BCData 외부 IHC 10ROI](docs/EXTERNAL_BCDATA_VALIDATION.md)의 정답 중심 조건 분류 accuracy는 **31.61%**, 양성률 MAE는 **24.26%p**였습니다. 전이 실패를 포함한 연구 결과이며 전체 WSI 정답 검증·임상 검증으로 해석하지 않습니다.

**원본·주석 직접 대조 확대:** [새 WSI 원본과 연결 사례](docs/ORIGINAL_ANNOTATION_EVALUATION.md)는 전체 바이트 확인 후 윤곽 정답2case의 ROI를 평가해 Dice **0.654638→0.654510**을 얻었고, 사각형만 있는1case는 배경 대조로 분리했습니다. 앞선3ROI의 CSV/mask 엄격 일치 영역 재평가는 **0.481569→0.437627**입니다. [BCData 공식test402장](docs/BCDATA_FULL_TEST.md)은 원본1,206파일과 주석 중복을 대조한 뒤65,165중심에서 **accuracy19.97%·양성률MAE44.74%p**를 확인했습니다. 원자료 품질 문제와 실패 사례도 보존합니다.

**NuCLS 좌표·치수 후속 처리:** [36쌍의 격자 불일치를 처리](docs/NUCLS_GRID_ALIGNMENT.md)해 확보한51시야·5케이스 모두를 평가했습니다. 기본/잔차 보정 Dice는 **0.628150→0.613006**,8시야 상승·43시야 하락입니다. 기존15시야 결과와 원자료를 보존했으며, 이는 공개 주석 영역 평가로 전체 WSI·임상 검증은 아닙니다.

## 실제 WSI와 IHC 확장

| 화면 | 실제 데이터·실행 범위 | 확인할 수 있는 것 | 평가 범위 |
|---|---|---|---|
| WSI 탐색 | CC0 CMU-1 JP2K SVS,46,000×32,893,0.499µm/px | 전체 스캔→native 상세 타일→3개 분석 ROI→동기화 경계 비교→후보와 원 패치 추적 | 고정 모델을3×1024²에 실행. 원본 파일 면적의0.2079%, GT 없음. 예측 차이를 정확도라고 부르지 않음 |
| 정답 경계 실험 | 기존 TNBC test7장/2그룹 | 좋아진·나빠진 경계, 정답과 오류 픽셀, 비용 | 기존 결과를 그대로 유지 |
| IHC 분류 | Patherea P1 Ki67,29case/1,330patch/19,972점,CC BY-NC4 | 실제 염색·GT 중심·정답/오답·네 클래스 점수 | train/val/test15/4/10case, 정답 중심점 조건의4종 세포 분류. 자동 검출 아님 |

WSI의 확대 영상은 OpenSeadragon6.1.1이 OpenSlide4.0.1로 원본 SVS에서 생성한 전체 다중 해상도 타일을 요청합니다. 공식 외부 타일은 로컬에서 열렸지만 배포 도메인의 요청을403으로 거부해, 확보한 CC0 원본에서 타일을 생성하여 데모와 함께 제공합니다. 실제 원본 SHA를 확인하고 OpenSlide4.0.1로 읽은 native ROI에 기존 TinyUNet을 실행했습니다. 같은 좌표의 예측·XOR 차이·원 패치와 NMS 사유가 연결됩니다. JPEG Q75와 분석 입력인 원본 RGB는 손실압축 때문에 픽셀값이 완전히 같지 않으며 좌표 정렬을 별도로 검사합니다.

세 WSI ROI에서 warm CPU 중앙값은 무겹침 **0.297–0.329초**, 겹침 **1.249–1.899초**, 독립 worker peak RSS **446–474MiB**였습니다. 전체 WSI 처리 비용이 아닙니다. [실험·좌표·선택 규칙](docs/WSI_EXPERIMENT.md).

별도 IHC 실험은 RGB/HSV/OD 특징과 LogisticRegression으로 주어진 세포 중심의 종양+/종양−/기타+/기타−를 분류했습니다. 고정 test10case·6,419세포에서 **macro-F1 0.600906**, accuracy0.703692였습니다. 양성 비종양 F1은 **0.205650**으로 낮았습니다. 검출 오류와 전체 슬라이드 Ki67 지수는 평가하지 않았습니다. 저자 fold1 test를 고정하고 train에서만 validation을 나눠 C를 선택했습니다. [실행 결과·한계](docs/IHC_EXPERIMENT.md).

Hann 겹침·경계 평가·WSI linked view·provenance 자체는 선행 기능입니다. 이 프로젝트의 설명 가능한 강점은 **같은 작은 CPU 모델의 실제 결과를 원본 좌표→패치→후보→억제 사유→오류·비용으로 추적하는 좁고 재현 가능한 검토 흐름**입니다. [16개 프로젝트·논문 비교](docs/WSI_LANDSCAPE.md), [WSI·도구·권리 비교](docs/WSI_DATA_OPTIONS.md), [AIVIS 업무와 IHC 자료](docs/AIVIS_IHC_FEASIBILITY.md)를 설계 전에 조사했습니다. 타사 모델 성능은 직접 재현한 값이 아닙니다.

## 영상 작업대

새 WSI·IHC 화면의 조사, 실제 실험, 검증·배포 및 직접 확인 순서는 [확장 보고서](docs/WSI_REVIEW.md)에 정리했습니다. 아래 새 화면에서 실제 WSI를 탐색할 수 있습니다.

![실제 WSI 전체 탐색 — 공개 버전7](artifacts/ui/wsi/wsi-overview.png)

[변경 전](artifacts/ui/wsi/before-desktop.png) · [WSI 경계 비교](artifacts/ui/wsi/wsi-boundary.png) · [후보 출처](artifacts/ui/wsi/wsi-candidate-provenance.png) · [IHC 분류](artifacts/ui/wsi/ihc-desktop.png)

기존 TNBC 정답 경계 화면도 유지했습니다.

QuPath·Aperio·에이비스의 공개 화면을 조사해 영상 중심의 검토 화면으로 구성했습니다.
썸네일 선택 → 같은 위치 확대 → 경계 비교 → 억제/유지 후보 추적을 한 화면에서 수행합니다.
‘좋아진 경계 보기’는 `11_1`, ‘나빠진 경계 보기’는 `10_3`의 실제 오류 변화로 이동합니다.
‘현재 예제 경계’로 `10_1`의 악화도 확인할 수 있습니다. 정답과 대조한 11개 국소 사례는 사후 설명용이며 평균 성능의 대표값이 아닙니다.
큰 화면은 동기화 A/B, 작은 화면은 같은 시야의 A/B 전환입니다. 사전 계산된 실제 결과를 표시하며 새 추론을 실행하지 않습니다.

![실제 차이가 있는 경계 — Chromium 화면](artifacts/ui/interview/after-improved.png)

[이번 변경 전](artifacts/ui/interview/before-desktop.png) · [악화 경계](artifacts/ui/interview/after-worsened.png) · [실험 비교](artifacts/ui/interview/after-experiment.png) ·
[모바일](artifacts/ui/interview/after-390.png) · [사례 선택·수치 대조·직접 확인 순서](docs/INTERVIEW_UI.md) · [조사 출처와 변경 이유](docs/UI_REVIEW.md) · [UI 검증·재현 명령](docs/UI_VERIFICATION.md) · [확대 후 이동 오류 수정](docs/PAN_FIX.md)

## 실제 결과

TNBC v1.1의 50개 512×512 이미지·이진 핵 마스크를 사용했습니다.
폴더 그룹 단위로 train 33 / validation 10 / test 7장을 분리했습니다.
공식 설명은 11환자이나 독립 환자 명부가 없어 `Slide_01..11`을 케이스 그룹으로 사용한 한계가 있습니다.
선택된 모델은 test를 보지 않고 validation으로 epoch 12·threshold 0.5를 결정했습니다.

| 방식 | 전체 Dice | 경계 Dice | 내부 Dice | 시간/장 ms | 전체 프로세스 peak MiB |
|---|---:|---:|---:|---:|---:|
| OpenCV 기준 | 0.4867 | 0.4658 | 0.4916 | 3.7 | 412.9 |
| TinyUNet 무겹침 | 0.5580 | 0.4918 | 0.5729 | 57.2 | 430.5 |
| TinyUNet 겹침 + 병합 | 0.5608 | 0.5273 | 0.5696 | 309.3 | 437.3 |
| TinyUNet 512px 전체 (참고) | 0.5655 | 0.5313 | 0.5744 | 88.5 | 487.3 |

경계는 기준 128px 격자의 내부 경계 양쪽 8px이며 모든 방식에 같은 영역을 적용했습니다.
Dice는 이미지별 점수의 평균입니다. 시간은 모델 로딩·디스크 I/O·지표 계산을 제외한
패치 추출→조직 게이트→추론→확률 합산→성분 추출→NMS의 warm CPU 3회 중앙값을 이미지 간 다시 중앙값으로 집계했습니다.
메모리는 방식별 별도 프로세스의 절대 peak RSS이며 런타임·warmup·평가를 포함합니다. 추가 메모리만을 뜻하지 않습니다.

겹침은 경계 Dice를 약 **+0.0355**, 전체 Dice를 **+0.0028** 높였지만 시간은 약 **5.4배** 걸렸습니다.
그룹10 전체 Dice는 0.5187→0.5003으로 하락했고 그룹11은 0.6104→0.6415로 상승했습니다.
두 그룹·한 seed의 결과이므로 일반적인 해결이나 유의한 개선을 주장하지 않습니다.
512px 전체 입력과의 경계 확률 차이는 MAE 0.0560→0.0068로 감소했습니다. 이는 일관성 지표이며 정답 정확도를 대신하지 않습니다.

![실제 모델의 같은 위치 비교 — 브라우저 캡처 아님](artifacts/boundary_comparison.png)

위는 개선이 가장 적은 `10_3`입니다. 전체 Dice가 0.6627→0.6347로 하락합니다.
[GT·FP·FN 비교](artifacts/error_10_3.png), [낮은 점수 사례](artifacts/error_10_4.png),
[개선 사례](artifacts/error_11_2.png)를 함께 보세요. 이미지는 실제 결과 시각화이며 브라우저 화면 캡처가 아닙니다.

## 핵심 구현

[후속 네 가지 보완](docs/RESEARCH_FOLLOWUP.md): 개발 참고 CNN–ViT 비교를3개 seed로 확장해 검증 전체 Dice 평균0.537512→0.565899를 확인했습니다. 원본 ZIP·180영역 재감사·동일ROI 오류 그림과 고정 소스1744544의 Docker366개 검사 근거를 보관하며, 사용자 원본ZIP112파일·C++72회·ViT60영역 감사도 완료했고 [실제 사용자 오류 그림](docs/USER_RESEARCH_AUDIT.md)을 확인할 수 있습니다. 사용자가 [작은 보정 모듈](docs/STEP_57.md)을 작성해13개 검사를 통과했다고 보고했고 제출 코드를 검증·연결했습니다. [개발 참고 비교](artifacts/experiments/vit-refinement-reference-20261112/README.md)에서 전체 Dice는 상승하고 경계는 하락했습니다. [사용자 Codespaces 비교](docs/STEP_59.md)의 성공 보고도 받아 전체 Dice0.570565→0.590386·경계0.558802→0.559040을 확인했습니다. 경계 변화는 매우 작고 처리 시간은 늘었습니다. 사용자 원본70파일·모델SHA·60영역 독립 검산까지 [완료했습니다](docs/USER_REFINEMENT_AUDIT.md). 요청한 네 보완은 해당 범위에서 마무리했습니다.

추가로 [소형 ViT와 TinyUNet 비교 및 C++ 측정 도구](docs/CPP_VIT_COMPARISON.md)를 구현했습니다. **사용자 Codespaces 실행**의 validation10장 전체 Dice는 CNN0.503768→ViT0.557644였고, 검사·두 체크아웃 보존 성공 보고를 받았습니다. 외부 가중치 없는 작은 모델의 한 seed·검증 데이터 선택 결과이며 위의 공개 test 결과와 구분합니다. 개발 참고 실행0.540674→0.557642와 사용자 실행을 따로 기록합니다. [C++ 측정·범위 해석](docs/STEP_52.md)은 확인했고, [이미지별 표](docs/STEP_54.md)도 받아7개 상승·3개 하락을 확인했고, [입력 토큰 형상 설명](docs/STEP_55.md)까지 확인해 요청한 두 보완을 해당 범위에서 마무리했습니다.

```text
공식 ZIP + checksum → 원본/GT 쌍 검사 → 케이스 그룹 분리
  → OpenCV 조직 마스크 / Python·C++ 패치 추출
  → TinyUNet 추론 (각 패치의 원래 PNG 좌표 보존)
  ├─ 확률맵 가중 합산 → 이진 분할 → Dice·IoU / 경계·내부 평가
  └─ 패치별 연결 성분 → 원래 PNG 좌표 → cross-patch NMS → 후보 검토
  → 고정 결과 JSON·overlay → 동기화 웹 작업대
```

각 패치는 좌표·유효 영역·level·downsample을 갖습니다. 이번 PNG에는 실제 WSI 원점·배율·MPP가 없으므로
물리 해상도는 null이고 좌표 단위는 `provided_png_pixels`입니다. 일반 배율·리사이즈 변환과 ROI 메타데이터 연결 함수를 사용자가 작성했습니다. 실제 OpenSlide ROI 읽기→변환→패치 영역 생성은 7조건에서 검증됐습니다. 원래 공개 native 추론 경로는 유지하며 일반 배율 모델 추론은 별도 미수행입니다.

무겹침은 128px/stride128, 겹침은 128px/stride64이며 trailing patch를 흰색으로 padding합니다.
512px 입력은 각각 16·64개 패치입니다. 픽셀은 Hann 계열 중앙 가중치로 합칩니다.
성분은 경계에 닿지 않은 후보 우선으로 정렬하고, 다른 patch 사이 IoU≥0.3 또는 중심 거리≤8px이면 억제합니다.
NMS는 근접한 다른 핵을 합치거나 잘린 조각을 놓칠 수 있는 휴리스틱입니다.

이진 GT의 연결 성분 중심으로 계산한 proxy F1은 겹침 raw 0.2671→NMS 0.4943이지만,
**진짜 세포별 instance label·종양 세포 정확도·Ki-67 지표가 아닙니다.**
픽셀 합산과 성분 NMS는 별도 경로이므로 녹색 영역의 연결 성분 수와 선택 가능한 후보 수가 다를 수 있습니다.

## C++ / 스레드 측정

`cpp/patches.cpp`는 실제 RGB crop·흰색 padding을 수행합니다. GIL을 해제하고 독립 패치를
std::thread로 분담합니다. Python 배열 복사 구현과 동일한 출력을 검증했습니다.

| 입력 | 구현 | 스레드 | 중앙값 ms | 전체 프로세스 peak MiB | Python 대비 |
|---|---|---:|---:|---:|---|
| 512² | python | 1 | 0.248 | 42.0 | 일치 |
| 512² | cpp | 1 | 0.123 | 42.1 | 일치 |
| 512² | cpp | 2 | 0.162 | 42.0 | 일치 |
| 512² | cpp | 4 | 0.208 | 41.9 | 일치 |
| 2048² | python | 1 | 11.967 | 188.9 | 일치 |
| 2048² | cpp | 1 | 8.400 | 189.6 | 일치 |
| 2048² | cpp | 2 | 6.761 | 188.5 | 일치 |
| 2048² | cpp | 4 | 5.299 | 188.9 | 일치 |

합성 uint8 RGB, 패치128/겹침64, warmup 후 9회, allocation·복사·padding 포함.
의학적 성능 실험이 아닙니다. peak 메모리는 정합성 검사의 두 출력 배열까지 포함하므로 연산만의 추가 메모리로 해석하지 않습니다.
작은 입력에서 4 thread는 C++ 1 thread보다 느립니다. 입력이 커지면 이번 환경에서는 다중 스레드가 빨랐습니다.
실제 test 7장의 무겹침·겹침 **14개 확률맵도 Python/C++ 경로가 bit-for-bit 일치**했습니다.
원시값: [benchmark.json](artifacts/benchmark.json), [cpp_real_parity.json](artifacts/cpp_real_parity.json).

## 업무·기술 대응

2026-11-10에 지정된 사람인 공고 55507517의 모바일 본문에서 자격·우대·접수 일정을 확인했습니다. 주요 업무·기술 목록은 [병역일터의 별도 공식 채용공고](https://work.mma.go.kr/caisBYIS/search/cygonggogeomsaekView.do?byjjeopche_cd=&cygonggo_no=2000001538893&menu_id=m_m7_1)로도 대조했으며 두 공고의 고용 조건·마감일은 구분합니다. [현재 공고와 프로젝트·사용자 기여의 대조 및 보완 우선순위](docs/JOB_MATCH_2026-11-10.md), [제품·IHC 조사](docs/AIVIS_IHC_FEASIBILITY.md)를 참고하세요.

| 기술/업무 | 코드와 실제 실행 |
|---|---|
| Python / 실험·재현성 | `data.py`, `experiment.py`, `cli.py`, manifest·protocol·hash |
| PyTorch / 설계·학습·추론 | `model.py` TinyUNet, 29,761 parameters, 16 epochs 실행·checkpoint 저장 |
| Computer Vision / 병리 이미지 | 핵 분할, 경계·내부 평가, 확률 합산, 연결 성분·오류 overlay |
| OpenCV | RGB/HSV/gray 전처리, 배경 제외, threshold 기준 방식, 연결 성분 |
| C++ | `cpp/patches.cpp`, Python/C++ 실제 추출·추론 출력 정합성 |
| 멀티스레딩 | C++ 1·2·4 thread 실행, 두 크기에서 시간·메모리 비교 |
| Ubuntu | Ubuntu 24.04 Docker 안의 테스트·실제 이미지 추론 |
| Docker | Ubuntu 기반 Dockerfile 실제 빌드·실행, CA proxy 대응은 secret 사용 |
| Git / GitHub / CI | 실행 코드·실험 파일·테스트 게시, `.github/workflows/ci.yml` |
| classification / detection / segmentation | TNBC segmentation 평가, WSI ROI 탐색적 추론, IHC GT-center 분류와 별도 자동 IHC 패치 검출·분류·후보 제거 실험. 외부 일반화·임상 성능 입증은 미완료 |

회사 제품은 종양 세포 기반 Ki-67 정량화를 다룹니다. 이 프로젝트는 그 전제인 세포 수준 영상 처리와
재현·오류 추적 역량을 보여줍니다. 제품과 같은 성능·임상 범위를 갖는다고 설명하지 않습니다.

## 실행과 검증 상태

- 학습: Debian 13, AMD EPYC 9V74, 노출 CPU 5개, Torch thread4, GPU 없음. 약 **42.6초**.
- 일반 테스트: 클래스 대조 검사기 수정 후 원격 CI **374 passed in 17.84s**, skip 없음. [최신 검사 근거](artifacts/learning/step58-class-match-fix.json). 제출 모듈 연결 당시366개와 고정 모델 소스1744544의 Docker366개 검증은 [기존 근거](artifacts/learning/step57-accepted-review.json)에 보관합니다. 별도 실습 검사도13개 통과했고 사용자 `13 passed in 25.76s` 보고와 구분했습니다. 앞선 원본 보관·오류 분석·반복 실행 확장의331개 검사도 통과했습니다. [이전 검사 근거](artifacts/experiments/final-followup-checks/summary.json). C++/ViT 최초 확장의269개 검사도 통과했습니다. [이전 검사 근거](artifacts/experiments/cpp-vit-checks/summary.json). 이전 재현 도구의201개, 고정 소스 `9c55480`의191개 테스트·저장 Dice42/6·정적 데모 검사도 통과했습니다. [재현 도구 근거](artifacts/learning/step45-preparation.json). WSI 사용자 계약은 별도 검증의8개 통과와 사용자 **8 passed in 7.08s**를 따로 확인했습니다. [반복 도구 근거](artifacts/learning/step42-preparation.json) · [WSI 검토 근거](artifacts/learning/step40-review.json).
- 사용자가 그룹 누수 보고 함수와 **18 passed in 0.04s**를 제출했습니다. 별도 검증에서도18개 통과와 실제50개 목록의 그룹 누수 없음·메모리 복사본의 합성 누수 검출을 확인했습니다. [검토 기록](artifacts/learning/step09-review.json). 준비 당시89통과/18skip은 과거 기록입니다. 사용자도 실제 목록50개·11그룹의 `group_leaks: {}` 출력을 제출했습니다. [사용자 실행 보고 검토](artifacts/learning/step10-review.json).
- 사용자가 Dice 함수와 **20 passed in 0.01s**를 제출했습니다. 별도 검증에서20개 통과와 실제 TNBC 점수42개·평균6개의 원 실험/화면 일치를 확인했습니다. [검토 기록](artifacts/learning/step04-review.json), [검산 기록](artifacts/learning/step04-real-dice-audit.json). 준비 당시69통과/20skip은 과거 기록입니다. 사용자도 로컬 빈 함수 오류 복구 안내 후 검산을 재실행해42/42·6/6 일치 출력을 제출했습니다. [사용자 실행 보고 검토](artifacts/learning/step05-review.json).
- 사용자가 NMS 반례 테스트 본문과 **1 passed in 0.01s**를 제출했습니다. 독립 실행에서도1개 통과했고 기본 전체 검사에 편입했습니다. [검토 기록](artifacts/learning/step02-review.json). 준비 당시68통과/1skip은 과거 기록입니다.
- 사용자가 좌표 함수와 **12 passed in 0.31s**를 제출했습니다. 별도 검증에서도 같은12개가 통과했고, 이제 기본 전체 테스트에 포함됩니다. [검토·실행 구분](artifacts/learning/step01-review.json).
- 실제 모델 추론·학습·평가·C++ 정합성·정적 UI 파일과 실제 결과 연결 검사 완료.
- 공개 데모는 [Sites](https://pathology-edge-lab.ykh13571.chatgpt.site)에 배포했습니다.
- 공개 버전7에서 Chromium·WebKit 각각 실제 조작 **46 tests**, 기존 화면 좌표 **5 tests** 통과. 데스크톱·태블릿·모바일 크기와 로딩/오류/빈 상태·지연 복구를 확인했습니다. [확장 근거](docs/WSI_REVIEW.md). 과거 공개 버전5의 각26개 검사 기록은 [기존 보고서](docs/INTERVIEW_UI.md)에 유지했습니다.
- 사용자가 WSI R1 이동·경계 차이·후보 출처를 확인했고 드래그·스크롤 요청에 이동 정상 보고를 보냈습니다([U07·U33·U34·U36·U37](docs/CONTRIBUTIONS.md)). 개별 입력 로그·다른 ROI/배율·브라우저 버전은 별도 미확인입니다. 좌표 함수의12개 테스트 통과는 사용자 보고로 확인했으며, 상세 실행 환경 로그는 받지 않았습니다.
- GitHub Actions: [CPU 검사 이력](https://github.com/sokldjs554/pathology-edge/actions/workflows/ci.yml), [checkout UI 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/42462829668), [공개 URL UI 검사](https://github.com/sokldjs554/pathology-edge/actions/runs/42463547474) 성공. UI 소스 `b5024b0` 기준이며 후속 문서·증거 추가는 UI 파일을 바꾸지 않습니다. 공개2,188개 파일의 저장소 정합성은 `artifacts/ui/wsi/production-files.json`에 있습니다.

[![CPU checks](https://github.com/sokldjs554/pathology-edge/actions/workflows/ci.yml/badge.svg)](https://github.com/sokldjs554/pathology-edge/actions/workflows/ci.yml)

```bash
# 저장소 루트, 개발 환경 설치 후: 제공 모델의 실제 추론
python -m pathology_edge.cli infer --image dist/assets/10_1.png --backend cpp --threads 4
# 저장소 루트: 일반 테스트 (검토 완료한 사용자 좌표 함수 포함)
python -m pytest -q
# 저장소 루트: 사전 계산 결과를 로컬 웹에서 검토
python -m http.server 8000 --directory dist --bind 127.0.0.1
```

상세한 환경·데이터·학습·평가·Docker 명령은 [RUNBOOK](docs/RUNBOOK.md)에 있습니다.
무료 CPU만 사용했으며 유료 API, 외부 사전학습 모델, 의료 영상 업로드 기능은 사용하지 않았습니다.

## 직접 수행한 작업

- 코드 작성: 좌표 변환, NMS 반례 테스트, Dice 계산, 그룹 누수 검사, PyTorch soft Dice 손실, WSI ROI 메타데이터 연결.
- 실행: 각 작성 코드의 테스트, 저장 Dice42개·평균6개 검산, 데이터 분리 검사, Codespaces 학습·두 손실 비교·3개 seed 반복 실험, 고정 소스 Ubuntu 재현.
- 검토: 경계의 개선·악화 사례, 후보 억제의 한계, WSI·IHC 분석 범위, 처리 시간과 점수 해석.
- Git 작업: 재현 로그9개 commit·push, PR #1 생성·설명 등록·병합.
- 결과 화면 확인: [Docker 재현](docs/STEP_50.md)의 두 성공 항목 확인 완료.

[기여 기록](docs/CONTRIBUTIONS.md)에 직접 수행한 범위와 확인 근거를 정리했습니다.
[검토 현황](docs/NEXT_STEPS.md)에서 완료·보류·미배정 항목을 확인할 수 있습니다. 면접 문장 작성은 보류 중입니다.

## 남은 한계

WSI 전체 모델 처리, 자동 IHC 핵 윤곽 분할·Ki67 임상 지수 검증, 사전학습 모델 비교, 공개 경계 비교의 다중 seed·신뢰구간,
병리 전문가·임상 검증은 미수행입니다. 외부 ROI 평가는 후속 MoNuSeg·PanopTILs·BCData 보고서에서 범위를 한정해 수행했습니다. 별도 BCE-only/soft Dice 손실 비교는 3개 seed·6회 학습을 완료했으며, 같은 validation에서 선택한 점수의 반복 결과입니다. CMU WSI에는 핵 정답이 없고, 공개 IHC 데모는 단일 기관·제공 중심점 조건입니다. 전체 WSI JPEG 타일을 포함해 저장소 용량이 증가했습니다. 사용자 좌표·메타데이터 연결 함수는 실제 ROI 읽기·패치 영역 생성 경로에서 검증했습니다. 원래 공개 추론 exporter는 유지하며 일반 배율 모델 추론·중심점 보정은 별도 미수행입니다.
단순 핵 foreground만으로 임상 세포 수를 정할 수 없고, 두 테스트 그룹의 성능 차이가 큽니다.
현재 test를 보며 모델을 다시 선택하면 새 평가 설계가 필요합니다.

데이터·모델·의존성 출처와 조건은 [THIRD_PARTY.md](THIRD_PARTY.md)에 있습니다.
TNBC 예제의 CC BY 4.0을 유지하며, 자체 코드의 일괄 오픈소스 라이선스는 사용자 결정 전이라 선언하지 않았습니다.

별도 환경의 반복 실험: 새 seed 20261110·20261111·20261112의 BCE-only/사용자 Dice 포함 총 6회 학습을 고정 조건으로 실행했습니다. 선택된 validation Dice 평균±표본 SD는 **0.508521±0.012424 → 0.546342±0.006688**, 같은 seed의 B−A 평균은 **+0.037821**(3개 모두 상승)입니다. 같은 validation 10장에서 epoch/threshold를 고른 결과이고 독립 test·임상 근거가 아닙니다. 기존 공개 모델·UI 결과에 덮어쓰지 않았고 사용자 반복 실행은 이후 [42단계](docs/STEP_42.md)에서 별도로 보고받았습니다. [모든 seed와 비용](artifacts/learning/step42-codex/summary.json).

사용자 Codespaces의 별도 6회 실행은 선택된 validation Dice 평균±표본 SD **0.518215±0.005288 → 0.546238±0.007100**, 같은 seed의 차이 평균 **+0.028023**(3개 모두 상승)으로 보고됐습니다. 제출 JSON의 집계값 재계산도 일치했습니다. 학습 시간 평균은 **92.93→88.89초**이나 통제된 속도 비교가 아닙니다. 위 별도 호스트 결과와 섞지 않았으며 보고 모델 해시와 점수 차이의 원인은 분리 검증하지 않았습니다. 사용자 모델 파일에 대한 직접 접근과 새 test 평가는 없습니다. [사용자 근거](artifacts/learning/step42-review.json).

사용자는 Codespaces Ubuntu 환경에서 고정 소스 `9c55480`의 C++ 재빌드·191개 테스트(skip 0)·저장 Dice42개/평균6개·정적 데모 검사와 원본 파일 보존 성공을 보고했습니다. 기존 패키지를 사용한 재현이며 Docker 빌드·새 데이터 실험·브라우저 검사는 아닙니다. [사용자 재현 보고](artifacts/learning/step45-review.json).

[50단계](docs/STEP_50.md)에서는 GitHub Actions에서 소스 `20cc5ac`의 Ubuntu Docker 이미지를 실제 빌드하고 컨테이너201개 테스트(skip 0)·저장 Dice42/6·C++·정적 데모·HTTP 응답을 검증했습니다. [실행 기록](artifacts/learning/step50-review.json). 사용자는 실행 결과 화면의 `Docker build: success`와 `Checks inside image: success` 두 항목을 확인했습니다.
