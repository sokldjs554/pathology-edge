# AIVIS 직무 근거와 IHC/Ki67 확장 가능성

확인일: 2026-11-08 UTC. 이 문서는 [기존 조사](RESEARCH.md)의 후속 조사다.
PathologyEdge는 AIVIS와 무관한 독립 연구·교육 프로젝트이며 회사 제품을 재현하거나 임상 검증한 작업이 아니다.

**2026-11-10 후속 확인:** 지정 사람인 공고 55507517의 모바일 본문에서 자격·우대·접수 일정을 읽었다. 아래 출처 표를 갱신했으며 현재 프로젝트·사용자 기여와의 대조는 [공고 대조 보고](JOB_MATCH_2026-11-10.md)에 있다. 데이터 조사·실험 이력의 원래 확인 날짜는 유지한다.

## 결론과 현재 범위

**추가 Ki67 실험의 가장 유력한 후보는 Patherea Breast-P1이다.** 저자가 연결한 공개 저장소에
명시적 데이터 라이선스, 실제 IHC 세포 유형 주석, 약 134 MB 하위집합, 환자별 fold가 있다.
실제 다운로드·주석·case별 분리 검사를 통과했다. 비상업 연구로 작은 CPU 기준선을 만드는 것은 현실적이다.
후속으로 정답 중심점 조건의 CPU 기준선을 실행했다. 결과는 [IHC 실험 기록](IHC_EXPERIMENT.md)에 있으며,
테스트 macro-F1은 0.601이다. 자동 검출이나 임상 Ki67 assay 성능이 아니다.
환자 명부 독립 확인의 한계는 아래에 기록한다.

기존 TNBC 실험은 H&E 이진 핵 분할이다. 종양 여부·Ki67 발현 정답이 없으므로 그 결과에
Ki67 양성률이나 바이오마커 분류라는 이름을 붙일 수 없다. IHC 추가 실험을 수행하더라도 데이터,
모델, 평가와 화면 설명을 별도로 두어야 한다.

## 채용 출처와 해석

| 출처 | 직접 확인 결과 | 사용할 수 있는 근거 |
|---|---|---|
| [사용자 제공 사람인 공고 55507517 모바일 본문](https://m.saramin.co.kr/job-search/view?cn=job-industry&cns=recently-list&rec_idx=55507517&referNonce=&t_category=job_recruit&t_content=generic) | 11월8일 접근 실패 후 11월10일 자격·우대·접수 일정 확인 성공. PC·짧은 모바일 URL은 여전히 접근 실패 | 해당 번호의 자격·우대·12월6일 마감 확인. 업무·기술 목록은 아래 별도 공고로 보완 |
| [병무청 병역일터 AIVIS AI연구원 공고](https://work.mma.go.kr/caisBYIS/search/cygonggogeomsaekView.do?byjjeopche_cd=&cygonggo_no=2000001538893&menu_id=m_m7_1) | 본문 확인. 등록 2026-10-12, 접수 2026-11-30 표기 | 별도 공식 채용 공고로 직무·기술을 확인할 수 있음. 사람인 번호와 동일 공고라고 단정하지 않음 |
| [AIVIS 게시 LinkedIn AI연구원 공고](https://kr.linkedin.com/jobs/view/ai%EC%97%B0%EA%B5%AC%EC%9B%90-at-aivis-4303750862) | 본문 확인, 마감된 과거 공고 | 이전 직무의 기술 스택을 보조 확인. 과거의 경력·우대 조건을 현재 사람인 조건으로 옮기지 않음 |
| [채용 공고에서 연결한 회사 Notion](https://aivis-ai.notion.site/AIVIS-232d6f0c42f480ca8256cc531abc14b0) | 직접 열기 실패 | 내용을 추정하지 않음 |

병역일터의 현재 공개 본문은 WSI를 포함한 병리 영상 모델 연구, classification/segmentation/detection,
전처리·패치·학습 데이터 구성, 학습·성능 평가·오류 분석, 최신 연구 적용, 재현성·협업을 업무로 설명한다.
Python/PyTorch 구현과 영상 모델링 및 연구 설계·구현·검증, GitHub/Jira 경험을 자격에 포함한다.
기술 목록에는 Python, PyTorch, C++, Docker, multi-threading, Ubuntu, OpenCV, Computer Vision이 있다.
이 문서의 프로젝트 대응은 이제 사용자 요약뿐 아니라 **이 별도 공식 공고**에도 근거한다.

병역일터의 전문연구요원 고용조건·학력·급여 표기는 일반 채용 전체의 조건으로 확대하지 않는다.
과거 LinkedIn 조건을 현재 공고에 옮기지 않는다. 다만 11월10일에는 지정 사람인 본문에서 관련 석박사·WSI 경험·ViT 연구/구현·학술 실적 우대를 직접 확인했다. 자세한 자격과 우대의 구분은 후속 대조 보고를 따른다.

## 사업 방향과 프로젝트의 연결

[회사 홈페이지](https://www.aivis.kr/)는 병리의사·임상의를 위한 Qanti IHC와 제약사·연구자를 위한
Qanti Discovery를 구분한다. 유방 ER/PR·HER2·Ki67, NET·갑상선 Ki67, 위 HER2와 신규 약물 표적의
IHC 정량을 안내한다. 이는 일반 영상 분류보다 **세포 유형, 염색 상태, 정량의 재현성**을 보여 주는
포트폴리오가 회사 업무와 연결된다는 근거다. 채용의 필수 요구사항으로 역추론하지 않는다.

[Qanti Breast Ki67](https://www.aivis.kr/product/qanti-breast-ki-67)의 지수는 양성 종양 세포 / 전체 종양 세포다.
모든 갈색 핵 / 모든 핵은 같은 정의가 아니다. 제품의 허가·상관계수 표시는 회사의 제품 설명이며
본 프로젝트의 성능·임상 적합성을 뒷받침하지 않는다.

[공개 연구 목록](https://www.aivis.kr/technology/publication)에는 2026년 공개 데이터 기반 Ki67 검증,
2025년 세포 수준 Ki67 벤치마크와 종양 세포 검출 관련 연구가 있다. 제목만으로 모델 상세나 성능을 추정하지 않았다.
기존 조사에서 읽은 QuaCCa-BRS Ki67 포스터는 합리적 요청에 의한 제공으로 기록되어 있다.
이번 [동일 PDF 직접 조회](https://www.aivis.kr/images/product/PV2025_A_Comprehensive_Cell-Level_Ki-67_Quantification_Benchmark_Dataset_for_Breast_Cancers.pdf)는 실패했으며,
자유 다운로드·재배포 조건이 새로 확인된 것은 아니다. 회사에 연락하거나 데이터를 요청하지 않았다.

## 데이터와 코드 비교

| 자료 | 염색·정답·실제로 평가 가능한 과제 | 분리 정보 | 접근·권리·CPU 판단 |
|---|---|---|---|
| [Patherea Breast-P1/P2 데이터](https://huggingface.co/datasets/ds2268/patherea), [논문](https://arxiv.org/html/2412.16425v2) | Ki67 IHC 유방암, 224×224 패치. 종양/비종양 × 양성/음성의 점 주석. 검출·세포 유형 분류·주석 영역 양성률 평가 후보. 핵 경계 분할 정답은 없음 | 논문은 환자별 3-fold 공개를 명시. P1/P2는 같은 29 샘플과 ROI를 두 병리의사가 주석한 것이므로 서로 독립 평가셋이 아님 | 데이터 카드 **CC BY-NC 4.0**. P1 ZIP 134,068,022 bytes; P2 134,052,865 bytes. CPU 색상/형태 기준선 후보. 공식 모델은 별도 CUDA 의존성 존재 |
| [BCData 공식](https://sites.google.com/view/bcdataset) | 유방암 Ki67 IHC. positive/negative **tumor** 중심점 HDF5. 검출·계수·양성률 가능, 경계 분할 GT 없음 | 공식 train/validation/test 구조 확인. 환자/슬라이드 매핑과 독립성은 미검증 | Google Drive 다운로드 링크 있음. 공식 페이지에서 데이터 라이선스·재배포 허가 미확인. 공개 링크만으로 MIT/CC를 추정하지 않음 |
| [SHIDC-B-Ki67 / PathoNet](https://github.com/SHIDCenter/PathoNet), [원 논문](https://doi.org/10.1038/s41598-021-86912-w) | 유방암 Ki67 IHC, 양성·음성·TIL 세포 주석 연구. 검출/분류 목적 | 원 파일 미검증. 환자별 집계가 논문에 있어도 내려받은 split의 독립성 검증을 대신하지 못함 | 데이터 사이트 두 경로 모두 접근 실패. **코드 MIT와 데이터 권리는 별개**. 오래된 Python/Keras/TensorFlow 환경을 CPU에 곧바로 재현 가능하다고 주장하지 않음 |
| [NuCLS 공식](https://sites.google.com/view/nucls/home), [corrected single-rater](https://sites.google.com/view/nucls/single-rater) | TCGA 유방암 **H&E**. 핵 검출·유형 분류·일부 경계. corrected 1,744 FOV / 59,485 nuclei / 19,680 boundaries | 공식 원 슬라이드 목록 링크 존재. TCGA slide/case로 분리할 수 있는지 실제 파일을 검사해야 함 | 데이터 **CC0 1.0** 명시. 핵 분류 확장 후보이나 Ki67 양성·음성 정답이 아님. 주석 없는 경계를 배경 GT로 처리하면 안 됨 |
| [IHCScoreGAN 코드](https://github.com/WenchaoHan0718/IHCScoreGAN), [공개 자산](https://zenodo.org/records/11396999) | IHC 입력과 합성 target을 이용한 비지도 방법. 120.7 MB ZIP은 TCGA 23개 H&E에서 얻은 **trainB 합성 target**. 실제 IHC/임상 정답셋이 아님 | 공개 외부 평가에는 별도 BCData가 필요. 내부 임상 코호트의 공개 여부를 이 ZIP으로 대신할 수 없음 | 코드 README **CC BY-NC 4.0**, Zenodo 레코드 자산 메타데이터 **CC BY 4.0**로 구분. BCData 가중치 487,943,205 bytes. CPU 옵션은 있으나 재학습은 비용·시간상 비권장, 성능 측정 안 함 |
| [DeepLIIF 공개 데이터](https://zenodo.org/records/4751737), [논문](https://doi.org/10.1038/s42256-022-00471-x) | 같은 조직의 IHC와 다중 IF를 이용한 세포 경계/발현 정답. Ki67 세포 분류·분할 후보. 종양 여부를 별도 확인해야 함 | train/validation/testing ZIP 제공. 환자·슬라이드 연결과 클래스 인코딩 미검사 | 데이터 레코드 **CC BY 4.0**, 코드 Apache 2.0 + Commons Clause는 별개. test 1,011,233,522 bytes, validation 161,416,136 bytes. 공식 설명은 로컬 GPU 필요. 이번 CPU 작업에는 Patherea가 더 작고 직접적 |
| [PathoQuant](https://github.com/shekharaj0007/PathoQuant) | H&E MoNuSeg 핵 분할·계수·타일 합성 예시. Ki67 GT 없음 | README의 환자 분리·결과 주장은 저자 주장. 이번 조사에서 코드 실행으로 검증하지 않음 | 코드 MIT. 코드 허가가 MoNuSeg 원영상 허가로 이어지지 않음. 타일링·분할 평가 참고용이며 IHC 확장 데이터는 아님 |
| [기존 TNBC v1.1](https://doi.org/10.5281/zenodo.2579118) | H&E 50 PNG와 이진 핵 마스크. 실제 핵 분할 가능, 종양/세포유형/Ki67 GT 없음 | 기존 7 test 이미지 / 2 Slide 폴더 그룹. 환자 명부로 검증한 환자 split이라고 부르지 않음 | CC BY 4.0, 기존 파일 검사 완료. 현재 실행된 TinyUNet 범위 |

BCData의 널리 쓰이는 803/133/402 분할과 640px·1,338 이미지 수는
[CellRegNet의 자료 기술](https://www.mdpi.com/2306-5354/11/8/814)에서도 확인되지만,
이는 원 파일·환자 매핑·데이터 권리를 직접 검사한 결과가 아니다.

## Patherea를 실행하기 전 확인할 사항

저자 [README](https://github.com/patherea/patherea-p2p/blob/main/README.md)가 위 Hugging Face 데이터로 연결된다.
HF 카드에는 라이선스가 YAML 메타데이터가 아닌 본문 `license: cc-by-nc-4.0`로 적혀 있다.
웹 viewer의 자동 생성 오류는 관찰했지만 원 ZIP이 손상되었다는 뜻은 아니다.
[코드 라이선스](https://github.com/patherea/patherea-p2p/blob/main/LICENSE.md)는 **CC BY-NC-SA 4.0**다.
데이터·코드·논문 권리를 하나로 합치지 않는다. 독립 기준선 작성에는 원 모델 코드를 복제할 필요가 없다.

공식 [loader](https://github.com/patherea/patherea-p2p/blob/main/src/p2p/datasets/aikinet_multiple.py)는
`folds/fold_{n}_train.txt`와 `fold_{n}_test.txt`를 읽는다. 코드에는
`positive_tumor_cell`, `negative_tumor_cell`, `normal_cell`, `others_positive`, `others_negative` 다섯 키가 있어,
논문의 네 범주와 실제 파일에서 `normal_cell`이 어떻게 대응하는지 확인해야 한다.
실제 P1 검사에서 `normal_cell`은 전부 0이었고 나머지 네 범주에 주석이 있었다.
따라서 P1 실험은 빈 범주를 제외한 네 범주로 명시할 수 있다.

1. ZIP 체크섬과 저장소 revision, 이미지·주석 수, 좌표 범위·중복·결측을 기록한다.
2. 제공 fold의 이미지 겹침뿐 아니라 파일명/메타데이터의 원 환자·슬라이드 그룹 겹침을 검사한다.
   P1/P2와 같은 영상의 다른 주석을 별개 환자로 세지 않는다.
3. 원 주석이 적용된 영역만 평가한다. 주석 밖 세포나 point-mask의 주변 픽셀을 임의의 음성 GT로 만들지 않는다.
4. 비상업·출처표시 조건을 지키며 큰 원 ZIP을 코드 저장소나 공개 배포물에 복사하지 않는다.
   공개 예시 이미지를 포함하면 데이터 저자·출처·라이선스와 변경 여부를 함께 표시한다.

파일 접근·분리·라벨 검증이 실패하면 IHC 실험은 보류하고 확인된 이유를 기록한다. 다른 데이터의
공개 논문·코드 라이선스를 빌려 누락된 데이터 권리를 채우지 않는다.

## 비용 없이 가능한 실험과 주장할 수 있는 수준

첫 실험으로는 **정답 중심 좌표가 주어진 세포의 유형 분류**가 적절하다. 각 중심 주변 RGB/HSV 또는
염색 분리 색상 요약과 작은 국소 형태 특징을 계산하고 CPU 로지스틱 회귀 등의 단순 기준선을 평가할 수 있다.
이는 실제 IHC 양성/음성·종양 여부 라벨을 쓰는 실험이지만 검출 누락과 가짜 검출이 없는 조건부 평가다.
표기명은 `GT-center cell classification` 또는 `정답 중심점 조건의 세포 분류`로 한다.

권장 평가는 클래스별 precision/recall/F1, confusion matrix, macro-F1와 환자/슬라이드 그룹별 결과다.
중심 좌표를 GT에서 가져왔다면 자동 세포 검출 F1이나 end-to-end Ki67 분석 성능으로 표시하지 않는다.
양성률을 계산하는 경우 종양 양성 / (종양 양성 + 종양 음성)으로 정의하고 분모 0은 제외 사유와 수를 남긴다.
평가 단위가 패치/주석 ROI인 결과를 임상 전체 슬라이드의 Ki67 지수로 확대하지 않는다.

공식 fold 중 테스트를 먼저 고정하고, 나머지 그룹에서 validation을 확보하거나 training 내부 그룹 교차검증만
사용한다. 색상 threshold·특징 선택·정규화·확률 보정·모델 선택은 training/validation만으로 결정한다.
test 결과를 보면서 threshold를 바꾸지 않는다. 공식 논문의 3-fold 평균과 단일 고정 fold 결과는 구분한다.
CPU 시간·메모리를 측정하기 전에는 처리 속도를 보장하지 않는다.

정식 검출까지 확장하려면 클래스별 point matching, 거리 허용값, 중복 매칭 방지, 경계 세포 처리 등을
추가해야 한다. 점 주석으로 만든 Gaussian target은 학습 표현이며 실제 세포 경계 GT가 아니다.
분할 Dice나 AJI를 그 인공 target에 대해 계산해서 실제 핵 분할 성능처럼 제시하지 않는다.

## 직무 대응에서 남는 차이

| 직무와의 연결 | 기존/추가로 보여 줄 수 있는 근거 | 남는 차이 |
|---|---|---|
| 병리 영상 전처리·패치·재현성 | 기존 H&E 패치 파이프라인, 출처·체크섬·좌표·분리 관리 | 작은 PNG 타일 실험 자체는 실제 WSI 처리 증거가 아님 |
| segmentation | 실제 이진 마스크로 학습·평가한 TinyUNet | 세포 instance 경계·세포 유형 정답과 별개 |
| classification | Patherea 파일 검증 후 가능한 실제 IHC 세포 분류 | 정답 중심 조건이면 자동 detection을 검증하지 않음 |
| detection·Ki67 정량 | 실제 point GT와 종양/발현 유형을 이용할 수 있는 확장 경로 | 별도 실험 없이 구현 완료·임상 assay로 주장할 수 없음 |
| 오류 분석 | 유형별 혼동, 그룹별 오차, 염색/경계 오류와 데이터 누출 점검 | 소규모 단일 출처 성능은 외부 기관 일반화 근거가 아님 |

## 원자료 확인 기록

무료 웹 검색·공개 GitHub 읽기와 공개 메타데이터 HTTP 조회만 사용했다. 유료 GPU/서비스,
회원가입·연락·데이터 신청은 하지 않았다. 현재 조사 중 파일 확인 전 상태와 이후 실행 결과는 분리해 기록한다.

- IHCScoreGAN Zenodo API: <https://zenodo.org/api/records/11396999> — 데이터/가중치 라이선스와 바이트 크기 확인.
- DeepLIIF Zenodo API: <https://zenodo.org/api/records/4751737> — 레코드 라이선스와 파일 크기 확인.
- Patherea 파일 API: <https://huggingface.co/api/datasets/ds2268/patherea/tree/main?recursive=true&expand=false> — P1/P2와 NET ZIP 크기 확인.
- 위 API 응답의 로컬 조사 스냅샷: `/workspace/work/aivis-ihc/`.

## Patherea Breast-P1 실제 파일 검사

공식 링크에서 비상업 연구용으로 P1 ZIP 하나만 내려받았다. 공개 코드 저장소에 원 ZIP을 추가하지 않았다.
검사 시각은 2026-11-08 07:22 UTC다.

- 파일: `Patherea_Breast_P1_224_v1.1.zip`, **134,068,022 bytes**.
- SHA-256: `1194dbfb145ca3aee1a27fcff9d92799d73d34b5da972118424a7b67047034e7`.
- ZIP CRC 검사 통과. RGB 224×224 PNG **1,330장**, 대응 point-mask PNG **6,650장**.
- 파일명 `case_0001`~`case_0029`의 **29 case**. 각 이미지에 다섯 클래스 mask가 존재하며 값은 0/255.
- 같은 좌표의 복수 클래스 충돌, 손상·누락·잘못된 크기, 동일 이미지 바이트/픽셀 해시 중복을 발견하지 못했다.
- macOS 메타데이터와 숨김 파일은 학습 이미지로 세지 않고 추출에서 제외했다.

| 클래스 | 현재 ZIP의 실제 255 중심점 수 |
|---|---:|
| positive_tumor_cell | 5,556 |
| negative_tumor_cell | 9,530 |
| normal_cell | 0 |
| others_positive | 465 |
| others_negative | 4,421 |
| **합계** | **19,972** |

**원자료 통계 불일치:** ZIP `stats.txt`와 논문 P1 표에는 36,673개가 있으나,
현재 1,330장의 point-mask를 직접 센 값은 19,972개다. `folds/stats_fold_*`의 수는
실제 파일과 일치한다. 차이의 원인은 확인하지 못했으며 다운샘플·필터링 때문이라고 추정하지 않는다.
실험의 표본수는 현재 파일을 센 값으로 보고하고, 논문 전체 수치를 이 ZIP의 실제 수로 옮기지 않는다.

| 제공 fold | train 이미지 / case | test 이미지 / case | train–test case·이미지 겹침 | train–test 동일 픽셀 해시 |
|---|---:|---:|---:|---:|
| 1 | 923 / 19 | 407 / 10 | 0 / 0 | 0 |
| 2 | 854 / 19 | 476 / 10 | 0 / 0 | 0 |
| 3 | 883 / 20 | 447 / 9 | 0 / 0 | 0 |

각 fold의 train/test는 전체 1,330장을 빠짐없이 나누며, 세 test 집합은 서로 겹치지 않고 합쳐서 전체를 덮는다.
논문은 환자별 fold라고 설명한다. 실제로 확인한 것은 파일명 case ID의 분리와 해시 중복 부재다.
ZIP에 별도의 임상 환자 명부·slide-to-patient 표가 없어 **환자 신원을 독립 대조했다고 주장하지 않는다**.
P1/P2의 동일 영상 관계도 유지되므로 P2를 외부 테스트 환자처럼 추가해서는 안 된다.

검사 결과 JSON과 이미지별 SHA-256·case·클래스 수 manifest는
`/workspace/work/aivis-ihc/patherea-p1-validation.json`과
`/workspace/work/aivis-ihc/patherea-p1-manifest.json`에 있다.
원영상은 `/workspace/work/aivis-ihc/Patherea_Breast_P1_224_v1.1/`에만 추출했다.
이 검사에 근거하여 **정답 중심점 조건의 CPU 세포 분류 실험을 수행했다**.
모델 성능·시간·오류 분석은 [별도 실험 문서](IHC_EXPERIMENT.md)에 기록했다.
완전 자동 Ki67 지수나 임상적 유효성은 검증하지 않았다.
