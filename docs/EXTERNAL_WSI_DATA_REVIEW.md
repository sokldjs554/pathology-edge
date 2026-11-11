# 외부 H&E 핵 분할 자료·whole-WSI GT 검토

확인일: 2026-11-11 UTC. 이 문서는 공개 자료 조사, 실제 다운로드와 원본 검사 결과를 기록한다. 모델의 외부 성능이나 임상 유효성이 검증되었다는 보고가 아니다.

## 채택할 외부 자료

**MoNuSeg 2018 공식 test 14장을 고정 외부 평가셋으로 권고한다.** TNBC로 학습한 핵 foreground 모델에 학습·threshold 재조정 없이 적용할 수 있고, 원본·핵 경계 정답이 약 40 MiB archive에 들어 있다. 핵 instance polygon의 합집합을 이진 foreground GT로 변환하면 현재 과제와 맞는다. 핵 유형 분류나 instance 분리 성능은 이 이진 평가만으로 입증되지 않는다.

- [공식 데이터·권리 페이지](https://monuseg.grand-challenge.org/Data/)
- [공식 페이지가 연결한 MoNuSegTestData.zip](https://drive.google.com/file/d/1NKkSQ5T0ZNQ8aUhh0a8Dt2YKYCQXIViw/view)
- [논문: A Multi-organ Nucleus Segmentation Challenge](https://doi.org/10.1109/TMI.2019.2947628)
- [저자 XML 변환 코드](https://github.com/ruchikaverma-iitg/MoNuSeg/blob/master/he_to_binary_mask_final.m)
- 이미지·annotation 권리: **CC BY-NC-SA 4.0**. [원문](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en). 현재 연구용 평가에는 출처·변환 내용·조건을 남긴다. TNBC의 CC BY 4.0 또는 도구의 소프트웨어 라이선스로 바꾸어 표시하지 않는다. 공식 challenge의 외부 학습 데이터 금지 규칙을 준수한 대회 제출이라고 주장하지 않으며, TNBC 학습 모델의 별도 외부 평가라고 표시한다.

공식 링크는 public download form을 제공했다. Google Drive의 대용량 virus-scan 안내 뒤 공개 다운로드 버튼과 동일한 form을 사용하여 HTTP 200 application/octet-stream 응답을 받았다. 별도 계정·접근 제한 우회는 사용하지 않았다.

| 실제 검사 항목 | 결과 |
|---|---|
| archive | `MoNuSegTestData.zip` |
| 다운로드 크기 | 41,620,178 bytes = 약 39.69 MiB |
| 직접 계산한 archive SHA-256 | `13e522387ae8b1bcc0530e13ff9c7b4d91ec74959ef6f6e57747368d7ee6f88a` |
| 추출된 평가 원본 | 14 TIFF + 14 XML, 60,571,259 bytes |
| TIFF | 모두 RGB, 1 frame, 1000×1000 pixels |
| XML region 합계 | **6,697**. 공식 페이지의 “additional 7000”은 반올림 소개이며 실제 개수로 쓰지 않음 |
| case | 파일명에서 추출한 고유 TCGA case 14개 |
| XML의 MPP | 0.2457–0.2527 µm/pixel |
| GT 범위 | 제공된 1000×1000 image region 내부. 원 WSI 전체 GT가 아님 |
| 공간 단위 | image-local pixels. 전체 WSI의 원점·좌표 변환은 이 archive만으로 확보되지 않음 |

archive와 원본을 모두 보관해도 약 97.46 MiB이다. foreground mask·요약 수치는 작은 추가 용량으로 저장할 수 있다. 14장×모든 설정의 float32 probability를 모두 영구 저장하면 용량이 커지므로 원본·mask·프로토콜·metrics를 우선 보존한다. 이 원본 검사는 모델 추론 비용 측정이 아니다.

로컬 원시 근거는 `work/external-data-research/`에 있다. 이 폴더는 Git ignore 대상이다.

- `source-inspection.json`: archive와 28개 원파일 SHA-256, TIFF 크기·decoded RGB SHA-256, XML region/vertex 수·좌표 범위, case metadata.
- `gdc-case-metadata.json`: GDC 공개 cases API 원응답.
- `tnbc-rgb-hashes.json`: 기존 TNBC 50장 decoded RGB SHA-256.
- `source-license-evidence.json`: 공식 데이터 페이지와 CC BY-NC-SA 4.0 legalcode의 읽은 본문·URL.
- 원본 `MoNuSegTestData.zip` 및 추출한 `MoNuSegTestData/`.

공식 데이터 페이지와 license는 공개 웹 읽기 도구에서 정상 조회되었고, 동일 페이지에 대한 Python urllib 요청은 HTTP 403이었다. archive 다운로드와 GDC metadata 조회는 Python에서도 성공했다. 전체 archive SHA-256은 직접 계산한 고정값이며, 배포자가 별도로 서명한 checksum이라는 뜻은 아니다.

## case 구성과 TNBC 독립성의 한계

TCGA case ID는 slide filename의 앞 세 barcode 요소이다. 다음 장기·project는 [GDC cases API](https://api.gdc.cancer.gov/cases)에서 14개 `submitter_id`를 조회한 결과다. 다른 자료의 장기 목록을 파일에 추정 대입하지 않았다.

| Case | GDC project / primary site | XML regions | MPP µm/px |
|---|---|---:|---:|
| TCGA-2Z-A9J9 | KIRP / Kidney | 575 | 0.2527 |
| TCGA-44-2665 | LUAD / Bronchus and lung | 818 | 0.2468 |
| TCGA-69-7764 | LUAD / Bronchus and lung | 441 | 0.2520 |
| TCGA-A6-6782 | COAD / Colon | 441 | 0.2457 |
| TCGA-AC-A2FO | BRCA / Breast | 521 | 0.2480 |
| TCGA-AO-A0J2 | BRCA / Breast | 356 | 0.2485 |
| TCGA-CU-A0YN | BLCA / Bladder | 677 | 0.2485 |
| TCGA-EJ-A46H | PRAD / Prostate gland | 466 | 0.2480 |
| TCGA-FG-A4MU | LGG / Brain | 465 | 0.2468 |
| TCGA-GL-6846 | KIRP / Kidney | 355 | 0.2462 |
| TCGA-HC-7209 | PRAD / Prostate gland | 325 | 0.2462 |
| TCGA-HT-8564 | LGG / Brain | 249 | 0.2525 |
| TCGA-IZ-8196 | KIRP / Kidney | 533 | 0.2457 |
| TCGA-ZF-A9R5 | BLCA / Bladder | 475 | 0.2525 |

따라서 실제 archive는 kidney 3, colon 1, breast/lung/prostate/brain/bladder 각 2장이다. 연구 소개의 “7 organs”만 보고 장기별 2장이라고 가정하면 안 된다.

기존 [TNBC v1.1 원배포](https://zenodo.org/records/2579118)는 50개 annotated image / 11 patients를 명시한다. 현재 프로젝트는 공개 `Slide_01..11`을 case group으로 쓰고 train 33 / validation 10 / test 7을 유지한다. MoNuSeg는 TCGA 출처이고 TNBC는 별도 Naylor/Institut Curie 자료이다. **서로 다른 dataset 출처라는 근거는 있지만, TNBC 공개 ID에 TCGA case crosswalk가 없으므로 환자 신원을 대조해 중복이 없음을 확정했다고 말할 수 없다.**

실제 기존 TNBC RGB 50장과 외부 RGB 14장의 decoded pixel SHA-256을 대조했고 동일한 전체 이미지 hash는 0개였다. TNBC는 512×512, MoNuSeg는 1000×1000이므로 이 검사의 범위는 제한적이다. 공통 환자, 같은 WSI의 다른 crop, 부분 포함 영상, 회전·resize·색변환 중복은 이 검사가 배제하지 않는다. “외부 dataset 평가; 환자 ID crosswalk 미제공”으로 보고하고 임의의 완전 독립 cohort 증명으로 확대하지 않는다.

## XML 변환과 사전 고정 평가

실제 XML의 구조는 `Annotations/Annotation/Regions/Region/Vertices/Vertex`이며 `Vertex`의 `X,Y`는 부동소수점 좌표이다. root의 `MicronsPerPixel`을 별도로 보존한다. 모든 6,697 region의 `NegativeROA`는 0이다. 점 중에는 -1 또는 1001, 소수점 좌표도 있으므로 각 polygon을 그대로 유효한 이미지 canvas에 rasterize하고 바깥 부분을 잘라야 한다. 좌표가 범위를 조금 벗어났다는 이유로 nucleus 전체를 버리면 안 된다.

저자 MATLAB 코드는 X/Y를 `poly2mask`에 전달한다. Python의 반올림·pixel-center·경계 포함 규칙은 동일하다고 자동 가정할 수 없다. 실제 evaluator에서 채택한 변환, 예를 들어 nearest rounding 후 OpenCV polygon fill과 OR 합집합, 라이브러리 버전·소스·mask hash를 명시하고 작은 독립 fixture로 확인한다. 이것을 “저자 공식 rasterization과 pixel-exact 동일” 또는 공식 AJI 재현이라고 부르지 않는다. 서로 닿거나 겹치는 instance를 합쳐 평가하므로 instance 수·PQ·AJI는 foreground Dice로부터 유도할 수 없다.

모델 결과를 보기 전에 고정해야 할 항목은 다음과 같다.

1. 사용할 기존 기준 ViT/보정 ViT checkpoint의 실제 SHA-256, TNBC 학습 split·seed·code version. 외부 14장은 새 학습·early stopping·threshold 선택에 사용하지 않는다.
2. 이미지 크기를 유지한 tile size/stride/Hann window/padding/crop, 기존 threshold, stain preprocessing 여부, 채택한 XML rasterizer. native MPP를 기록하되 TNBC MPP가 미상인 상태에서 물리 해상도가 일치한다고 주장하지 않는다.
3. 제공 test 14장 모두를 평가하고 제외 기준은 처리 불가 파일·명백한 pairing 오류처럼 결과를 보지 않은 기술 기준으로 한정한다.
4. 전체 foreground Dice/IoU와 동일한 tile-grid seam band의 Dice, seam 외 영역 Dice를 per case 및 집계로 저장한다. seam band Dice는 핵 윤곽 surface Dice와 다른 지표다.
5. 실제 실행에서는 두 고정 모델 모두 no_overlap으로 처리하고 같은 이미지의 보정−기준 Dice를 비교했다. overlap−no_overlap 추가 비교와 case bootstrap은 수행하지 않았다. 이미지와 seed 수를 혼동하지 않으며 장기별 1–3 case를 독립된 충분한 장기별 검증으로 보지 않는다.
6. 원본, masks, model/protocol hashes, per-case 수치, 실패·제외 목록을 기록한다. 대표 예시는 성공/실패를 모두 사전 규칙으로 고르며 임의의 좋은 사례만 남기지 않는다.

이 평가는 “TNBC 학습 모델의 MoNuSeg test ROI zero-shot foreground segmentation”이다. 임상 유효성·핵 유형 분류·모든 기관의 일반화·WSI 전체 정확도는 별도 주장이다.

## 실제 WSI nuclear GT 후보 검토

| 자료 | 실제 annotation 범위와 사용 가능성 | 권리·접근 확인 및 판정 |
|---|---|---|
| [MoNuSeg](https://monuseg.grand-challenge.org/Data/) | TCGA H&E의 제공 ROI 안에 nuclear boundary. 이번 14장과 6,697 regions 직접 확인 | CC BY-NC-SA 4.0, 39.69 MiB 실제 다운로드. **즉시 외부 ROI 평가에 채택** |
| [CoNSeP 저자 repository](https://github.com/vqdang/hover_net) / [논문](https://doi.org/10.1016/j.media.2019.101563) | 41개 1000×1000 colorectal image tiles의 nuclear instance/type GT. 전체 WSI GT가 아님 | 공식 Warwick dataset 링크가 확인 시 university sign-in으로 이동. repository MIT와 data license를 혼동하지 않음. 이번 조사에서 데이터 원배포 license/file를 재확인하지 못해 우선 제외 |
| [NuCLS 공식 사이트](https://sites.google.com/view/nucls/home) / [논문](https://doi.org/10.1093/gigascience/giac037) | 220,000개 이상 annotation; single-rater 연구는 3,944 FOV/125 patients. bounding box·class·일부 segmentation/algorithmic suggestions·교정 여부를 구분해야 함 | 논문은 CC0 1.0 명시. WSI와 연결된 FOV 평가에 유용하지만 슬라이드 전 영역의 모든 nuclear contour 정답이 아님. annotation type/ignore-area/교정 여부 audit가 추가로 필요 |
| [Lizard 논문](https://arxiv.org/html/2108.11195v2) | 291 colon image regions, 495,179 nuclei, 약 0.5 µm/px. 여러 원천의 자동/반자동 결과에 expert refinement. 논문의 전체 WSI 그림은 별도 시각 예시 | 공식 Warwick dataset link는 확인 시 sign-in으로 이동하여 이번에 archive/license 재확인하지 않음. CoNSeP/PanNuke/TCGA와 원천 중복 주의. eosinophil은 cytoplasm도 annotation에 포함한다는 원논문 한계가 있어 순수 nuclear foreground와 label 정의도 다름 |
| [PanNuke 공식 자료](https://warwick.ac.uk/fac/cross_fac/tia/data/pannuke/) / [논문](https://arxiv.org/abs/2003.10778) | 다장기 image patches의 nuclear instance/type annotation. WSI inference를 위한 학습 자료가 될 수 있으나 전체 WSI GT가 아님 | 공식 페이지 research-only / CC BY-NC-SA 4.0와 fold archive 링크 확인. 이번 40 MiB 평가 자료보다 우선할 이유가 없어 대형 fold 미다운로드 |
| [PUMA 공식 challenge](https://puma.grand-challenge.org/) / [원자료](https://zenodo.org/records/14869398) | 155 primary + 155 metastatic melanoma ROI, 1024×1024, 40×. tissue+nuclei 두 목표가 있음 | 최신 대안도 ROI 자료. 이번 조사에서 archive/개별 권리를 재검증하거나 다운로드하지 않음 |
| [Pan-Cancer-Nuclei-Seg, TCIA](https://www.cancerimagingarchive.net/analysis-result/pan-cancer-nuclei-seg/) | 5,060 WSI의 **자동** nuclear segmentation + quality control. 수동 instance GT는 별도 1,365 patches | CC BY 3.0; 전체 배포 약 665.94 GB. 전체 슬라이드 segmentation을 독립 human GT로 사용하면 모델 대 모델 평가가 됨. 소개 본문은 1,356, 상세는 1,365로 불일치하므로 실제 파일 확인 전 정밀 개수 단정 금지 |
| [CAMELYON16 공식 자료](https://camelyon16.grand-challenge.org/Data/) | 실제 WSI와 metastasis contours/binary tumor masks | 정답 target이 종양 전이 영역이다. nuclear foreground GT로 대체 불가 |
| [현재 CMU WSI](WSI_EXPERIMENT.md) | 원본 전체 scan의 viewer 및 3개 1024×1024 ROI prediction | CC0 원본이나 nuclear GT 없음. 전체 tiled image 표시, 전체 model inference, GT accuracy는 각기 별개 |

이 조사에서 **현재 저장공간 내에 즉시 쓸 수 있고, 전체 조직의 모든 핵에 독립적으로 검수한 contour GT가 있는 공개 원본 WSI cohort는 확인하지 못했다.** 그러한 자료가 세계에 전혀 없다고 단정하는 결론은 아니다. 특히 “whole-slide segmentation results”라는 제목만으로 자동 결과를 GT라고 바꾸지 않는다.

## whole-WSI 및 임상 검증으로 이어질 조건

현재 CMU WSI를 전체 조직에 걸쳐 처리하면 범위·좌표·실행 비용·실패 복구를 검증할 수 있다. GT 없이 얻은 전체 결과의 nuclei count·seam consistency는 예측 통계이며 정확도나 진짜 세포 개수의 오차가 아니다. 제공된 3 ROI만 분석한 현재 기록은 그대로 보존한다.

실제 WSI 정확도 평가에는 원본 WSI, level0 좌표계, MPP, annotation coverage/ignore mask, annotator 검수 절차가 함께 필요하다. 실용적인 다음 단계는 별도 기관의 슬라이드에서 조직·염색·scanner·희귀 형태를 포함한 ROI를 모델 예측을 보지 않고 표본 추출하고, 전문가가 그 ROI 내부 모든 핵을 검수하는 것이다. 이 경우 얻는 것은 **WSI로부터 표본 추출한 ROI의 정확도**이며 exhaustive whole-WSI 정확도가 아니다. 슬라이드 전체의 추정치를 주장하려면 표본설계·포함확률·가중치와 case 단위 불확실성을 사전에 정해야 한다. exhaustive 평가를 원한다면 평가 대상 tissue 전체를 annotation하고 누락·artifact·불확실 영역을 기록해야 한다.

“임상 검증”은 공개 benchmark 성능의 다른 이름이 아니다. 아직 승인된 cohort, 전문가 판독 결과, 비교 reference standard, intended use, 임상 endpoint가 제공되지 않았다. 이를 없는 상태에서 진단 보조 효과·민감도·특이도·clinical usefulness를 계산하거나 이미 검증됐다고 표시할 수 없다. 필요한 다음 자료는 다음과 같다.

- 승인된 데이터 사용 범위와 de-identified 환자/검체/기관·scanner 단위 ID, TNBC/MoNuSeg 및 pretrained model과의 중복 확인 가능 metadata.
- 용도와 target population, 누가 어떤 결정을 지원받는지, 연구용 segmentation 지표 외 어떤 endpoint를 평가할지.
- 독립 전문가와 판독 지침, 불일치 adjudication, 필요 시 두 판독자와 inter-rater agreement.
- 시간·기관을 분리한 고정 evaluation cohort, 사전 제외 기준·실패 처리·표본 수 근거·case 단위 분석 계획.
- 실제 workflow/사용자 연구가 목적이면 읽기 시간·오류 변화 같은 endpoint를 정한 후 별도 승인된 평가.

이 항목들은 이번 조사에서 수행하지 않았다. 외부 공개 ROI benchmark와 임상 cohort 검증의 수행 여부를 실험 표에서 각각 따로 기록한다.
