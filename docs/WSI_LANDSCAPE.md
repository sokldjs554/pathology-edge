# WSI·핵 분할·경계 QA 선행 프로젝트 조사

조사일: 2026-11-08 · 조사 담당: Codex · 설계 전 조사 자료.

이 문서는 공식 저장소, 저자 논문, 프로젝트 문서·공개 데모 주소를 비교한다. 아래 타사 성능은 **저자가 보고한 값**이며 이번 조사에서 재현한 값이 아니다. 타사 모델을 설치·학습·추론하지 않았다. GitHub 원문은 연결 도구로 읽었고, 논문·문서는 웹 검색/열기로 확인했다. 개인 계정 저장소라는 사실을 1인 개발이나 완성도를 보증하는 근거로 삼지 않았다.

## 조사 당시 프로젝트와 비교 기준

[README](../README.md)와 [UI_REVIEW](UI_REVIEW.md)를 읽고 확장 전 버전5 상태를 기준으로 삼았다. 이후 완료한 WSI 원점·MPP 검증과 별도 IHC GT-center 분류는 [WSI_EXPERIMENT](WSI_EXPERIMENT.md), [IHC_EXPERIMENT](IHC_EXPERIMENT.md)에 구분해 기록했다. PathologyEdge는 TNBC의 512×512 H&E PNG에 작은 TinyUNet을 학습해 무겹침 128/128과 겹침 128/64를 비교한 **이진 핵 foreground 연구 작업대**다. 경계/내부 Dice, 확률 합산, 별도 연결 성분 NMS, 억제→유지 후보 추적, 개선·악화 사례와 CPU 비용을 공개한다. 7장/2그룹/1 seed의 결과이며 WSI 원점·MPP, 진짜 instance GT, 종양 분류, Ki-67 양성률은 검증하지 않았다. 현재 화면은 고정 결과를 읽으며 새 추론을 실행하지 않는다.

조사 결과, 확대 가능한 WSI, 동기 탐색, 핵 overlay, ROI, patch metadata, 겹침 합산, 경계/내부 평가, 처리 이력 각각은 이미 선행 구현이 있다. **이 요소들이 처음이라는 주장은 성립하지 않는다.** 적절한 목표는 작은 CPU baseline에서 발생한 오류·비용을 실제 WSI 위치와 연결하여, 다른 사람이 같은 결과와 실패를 재확인할 수 있는 좁고 완결된 QA 사례다.

## 비교 요약

`문서`는 공식 설명·그림 확인, `코드`는 해당 기능의 소스도 읽음, `논문`은 저자 보고 확인이다. `공개 주소`는 실시간 조작 성공을 의미하지 않는다. 모든 타사 추론은 미실행이다.

| 프로젝트 / 유형 | 주 목적·데이터/모델 | UI·출력에서 확인한 내용 | 평가와 현재 범위의 차이 | 확인 수준 |
|---|---|---|---|---|
| [KatherLab WSI Viewer](https://github.com/KatherLab/wsi-viewer) / 연구실 도구 | 서버의 OpenSlide 호환 WSI 탐색; 지정 학습 모델 없음 | 폴더·썸네일·DZI·metadata·물리 눈금 | 핵 분할 benchmark가 아니라 조회 인프라 | 문서 |
| [TIAToolbox/TIAViz](https://github.com/TissueImageAnalytics/tiatoolbox) / 대학 연구 도구 | WSI 처리·HoVer-Net 등 추론·결과 시각화 | nuclei/graph/heatmap/WSI overlay, ROI 모델 탐색 | 범용 연구 도구; 비교할 모델·평가는 별도로 고정해야 함 | 문서·논문·공개 주소 |
| [QuPath](https://github.com/qupath/qupath) / 대학 기반 오픈소스 | H&E/IHC/형광, 세포 검출·분류 | ROI, 개별 세포 측정, histogram·CSV, Ki-67 tutorial | 종양과 양성 세포를 실제 구분하는 정량 workflow | 문서·논문 |
| [Digital Slide Archive](https://github.com/DigitalSlideArchive/digital_slide_archive) / 연구 플랫폼 | WSI 저장·관리·분석·annotation | HistomicsUI + HistomicsTK + Girder | dataset/annotation/job 관리까지 포함; 하나의 모델 점수로 평가 불가 | 문서·공개 주소 |
| [caMicroscope](https://github.com/camicroscope/caMicroscope) / 연구 플랫폼 | WSI와 사람·기계 annotation | layer, side-by-side, shared view, nuclei count/export | review 기능 선행; 방문한 웹사이트는 정상 demo로 확인 못함 | 문서 |
| [EOV](https://github.com/eosin-platform/eov) / 작은 범위의 데스크톱 도구 | 로컬 WSI + patch export + plugin | linked panes, MPP, ROI, QC, patch/run metadata | provenance와 QA 기능도 이미 존재; README 주장과 실측 구분 필요 | 문서 |
| [TissUUmaps](https://tissuumaps.github.io/) / 대학·공동체 시각화 | 공간 omics·다중 해상도 영상·세포/전사체 | 이미지·label·point·shape layer와 공개 gallery | 대량 overlay 탐색 도구; 핵 분할 정확도 자체는 별도 | 문서·공개 주소 |
| [Slideflow/Studio](https://github.com/slideflow/slideflow) / 대학 기반 라이브러리 | WSI 모델 개발, MIL/feature/segmentation | WSI→tile preview→예측·QC·성능 패널 | 모델 훈련부터 탐색까지 넓은 범위; 자체 조건 재현 필요 | 문서·논문 링크 |
| [PathoQuant](https://github.com/shekharaj0007/PathoQuant) / 개인 계정 | MoNuSeg, residual U-Net, Gaussian blend | CLI mask/overlay/metrics | 직접적인 소규모 비교군; 전체 RAM은 영상 면적에 비례 | 문서·코드 |
| [hd_wsi](https://github.com/impromptuRong/hd_wsi) / 개인 계정에 공개된 연구실 코드 | HD-Yolo, 폐/유방/대장 모델, TME | DeepZoom viewer + segmentation + export | 단순 binary보다 세포 유형·TME까지 넓음; GPU 중심 | 문서·논문 링크 |
| [CellViT](https://github.com/TIO-IKIM/CellViT) / 연구실 논문 코드 | PanNuke, ViT encoder + U-Net 형태 decoder | patch metadata, nuclei feature, GeoJSON→QuPath | instance/type task; TNBC binary Dice와 직접 순위 비교 불가 | 문서·논문 |
| [HoVer-NeXt](https://github.com/digitalpathologybern/hover_next_inference) / 연구실 논문 코드 | Lizard-Mitosis/PanNuke, ConvNeXtV2 | WSI instance map, centroids, QuPath TSV | 추론/후처리 병렬화와 WSI 속도까지 평가 | 문서·논문 |
| [Hann window 연구](https://doi.org/10.1371/journal.pone.0229839) / Uppsala 논문 | H&E, U-Net, 128px patch | 무겹침·평균·4종 window 비교 그림 | 경계/중앙 Dice까지 이미 수행한 직접 선행연구 | 논문·저자 코드 링크 |
| [tiler](https://github.com/the-lay/tiler) / 개인 계정 라이브러리 | 임의 N차원 NumPy array | iterator·batch·padding·window merge | 병리 특화 데이터/검증이 아닌 재사용 tiling 기능 | 문서 |
| [Smoothly-Blend-Image-Patches](https://github.com/Vooban/Smoothly-Blend-Image-Patches) / 소규모 공개 구현 | 위성영상 예시, 모델 독립 blending | 50% overlap·spline window·D4 averaging | 메모리 제한을 명시; WSI나 핵 정답 검증은 아님 | 문서 |
| [ASHLAR](https://github.com/labsyspharm/ashlar) / Harvard 연구실 도구 | 다중 round 현미경 원시 tile·CyCIF/CODEX | 촬영 tile 정합→pyramidal OME-TIFF | 추론 patch 병합이 아닌 촬영 위치 정합 문제 | 문서·논문 링크 |

## 핵심 1차 출처와 구체적인 관찰

### 1. KatherLab WSI Viewer

[공식 README](https://github.com/KatherLab/wsi-viewer/blob/main/README.md)는 FastAPI·Vue·OpenSeadragon, OpenSlide 형식, DZI endpoint, metadata 기반 µm/mm 눈금, associated image, 폴더 검색·썸네일 lazy loading, Redis/LRU cache를 설명한다. grid와 viewer 그림이 있으며 설치 후 localhost:8010을 여는 구조다. 확인한 README에 핵 segmentation 모델·학습 데이터·정량 segmentation benchmark는 없다. `Production Ready`라는 문구는 저자의 설명이며 보안·처리량 인증이 아니다. clone 예시에는 현재 저장소명과 다른 `wsi-browser` 이름이 남아 있어 명령 재현 시 확인이 필요하다.

**배울 점:** 실제 slide metadata와 tiled serving을 먼저 갖추고, 원본 파일/ROI/결과의 역할을 구분한다. **차이:** PathologyEdge의 후보 억제 근거·정답 오류 분석을 대신하는 도구가 아니라 WSI 탐색 기반이다.

### 2. TIAToolbox / TIAViz

[저자 논문](https://arxiv.org/html/2402.09990v1)은 zoom 가능한 segmentation·annotation·graph·heatmap·다른 WSI overlay, Python/Bokeh 기반 원격·로컬 탐색을 설명한다. [공식 핵 instance tutorial](https://tia-toolbox.readthedocs.io/en/stable/_notebooks/jnb/08-nucleus-instance-segmentation.html)은 `hovernet_fast-pannuke`, 출력 DB를 `Add Overlay`로 추가하는 흐름을 제공한다. 논문은 많은 annotation의 최초 로딩이 느릴 수 있다고 명시한다. 논문에 연결된 [공개 데모](https://tiademos.dcs.warwick.ac.uk/)는 이번 웹 열기에서 접근 실패해 동작 여부를 확정하지 않았다.

**배울 점:** 임의 overlay를 받는 것보다 geometry·속성·해상도 계약을 분명히 해야 한다. **차이:** TIAViz만으로 모든 모델이 정확하거나 모든 핵 overlay가 Ki-67를 의미하지 않는다. 우리 쪽에서도 foreground mask, component 후보, GT, suppression 연결선을 서로 다른 layer로 표시해야 한다.

### 3. QuPath — Ki-67를 말하려면 무엇이 더 필요한가

[공식 tutorial](https://qupath.readthedocs.io/en/stable/docs/tutorials/cell_detection.html)은 OpenSlide의 OS-2.ndpi Ki67 영상에서 tumor ROI를 수동으로 정하고, 핵 DAB optical density로 positive/negative를 나눈다. 개별 객체와 측정 표가 연결되고 histogram·CSV를 제공한다. 문서 예시의 1,088 detections/12.4%는 해당 설정의 예시이며 임상 정확도 수치가 아니다. stain vector 변경 후에는 detection을 다시 수행해야 한다고 설명한다. [저장소](https://github.com/qupath/qupath)와 [원 논문](https://www.nature.com/articles/s41598-017-17204-5)은 연구용 bioimage analysis의 범위를 확인해 준다.

**배울 점:** 총 핵 수가 아니라 **어떤 세포를 분모로 삼았는지**, staining·threshold·검출 조건을 함께 보여 준다. **조사 당시 부족:** 확장 전 PathologyEdge에는 IHC, 종양/비종양, 양성/음성 GT가 없었다. H&E 핵 foreground를 Ki-67 score로 바꾸어 부를 근거가 없다.

### 4. Digital Slide Archive / HistomicsUI / HistomicsTK

[공식 개요](https://digitalslidearchive.github.io/digital_slide_archive/)는 HistomicsUI(보기·annotation), HistomicsTK(영상 분석), Mongo/Girder(관리·API), algorithm job 실행을 분리한다. 로컬/S3 assetstore, 접근권한, 전체 또는 일부 영상 처리, 자동 UI 확장을 설명한다. [문서](https://digitalslidearchive.github.io/digital_slide_archive/documentation/)는 annotation style/template과 multi-resolution `large_image` 접근을 안내한다. [공식 demo](https://demo.kitware.com/histomicstk/histomicstk#?image=5c74528be62914004b10fd1e)는 웹 추출에서 HistomicsUI 제목만 읽혔다. 분석·annotation 조작을 성공했다고 기록하지 않는다.

**배울 점:** 이미지 ID·annotation ID·실행 결과를 별도 자원으로 취급한다. **차이:** 기관 규모 관리 플랫폼을 작은 포트폴리오에 재구현할 필요는 없다. source manifest와 저장 결과를 제한된 범위에서 연결하면 된다. 범용 플랫폼에 단일 Dice를 붙여 우열 비교하지 않는다.

### 5. caMicroscope

[공식 README](https://github.com/camicroscope/caMicroscope)는 viewport navigator, 확대/이동, annotation/layer manager, side-by-side, 공유 view URL, 핵 segmentation 표시·개수·export, ROI에서 pretrained TensorFlow 모델 결과 표시를 설명한다. review 완료 표시와 화면 캡처도 포함된다. 모델/학습 데이터와 임상 검증은 배포 instance와 연결된 모델별로 확인해야 한다. 조사 시 `camicroscope.org` 열기는 관련 없는 다른 사이트로 이동하여 이 주소를 정상 demo 근거로 사용하지 않았다. 원인을 단정하지 않는다.

**배울 점:** view state를 링크로 재현하고 검토 대상을 명시하는 기능은 이미 있다. **차이:** 같은 기능을 넣었다는 이유만으로 새 QA 접근이라고 주장하지 말고 실제 seam 오류와 대응 후보를 검토할 수 있는지로 평가한다.

### 6. EOV — provenance도 이미 있는 비교군

[공식 README](https://github.com/eosin-platform/eov/blob/master/README.md)는 Rust/Slint 로컬 WSI viewer, linked panes, calibration, ROI, heatmap 위치·downsample, patch extraction을 기술한다. metadata에는 level-0 좌표·원본/출력 크기·읽은 level/downsample·MPP·source fingerprint가 포함되고 batch manifest는 plugin/model hash·매개변수·결과 상태를 기록한다고 설명한다. 일부 edge patch를 생략하는 규칙도 명시한다. 범위가 작은 도구라는 포지셔닝이지만 현재 기능은 넓다. 이 기능·속도는 README 확인이며 이번에 앱을 설치하거나 benchmark하지 않았다.

**배울 점:** source→변환→output 이력은 기본 품질 요구사항이다. **차이:** PathologyEdge만 provenance를 제공한다는 주장은 불가능하다. “이 실험의 후보가 어느 패치에서 생성·억제됐는지 직접 확인할 수 있다”처럼 실제 구현으로 입증 가능한 문장이 적절하다.

### 7. TissUUmaps — 대량 결과를 공유하는 공개 웹 사례

[공식 사이트](https://tissuumaps.github.io/)와 [gallery](https://tissuumaps.github.io/gallery/)는 browser 기반 image/label/point/shape/table 탐색과 공유 프로젝트를 제공한다. 현재 사이트는 4 beta와 3 예제를 구분한다. gallery에는 Xenium 인간 폐암의 H&E·핵/세포 segmentation·12.2M transcripts, 2GB QPTIFF multiplex scan, CAMELYON17 기반 DEPICTER가 제시되어 있다. 이는 데이터/예제 설명이지 해당 환경에서의 로딩 성능 재현이 아니다. [3.x 문서](https://tissuumaps.github.io/TissUUmaps-docs/docs/intro/about.html)는 다중 해상도와 대량 marker 탐색을 설명한다.

**배울 점:** slide overview에서 물체·표로 들어가는 탐색과 layer 구분. **한계:** spatial omics viewer의 marker 수나 GPU 렌더링 성능을 핵 segmentation 정확도로 해석할 수 없다. 3/4 기능과 배포 상태도 섞지 않아야 한다.

### 8. Slideflow / Slideflow Studio

[공식 README](https://github.com/slideflow/slideflow)는 WSI tile 추출, stain normalization, supervised/MIL, pretrained features, heatmaps·uncertainty를 포함하는 모델 개발 라이브러리다. [Studio 문서](https://slideflow.dev/studio/)는 WSI main view·tile preview·control panel의 연결, 선택 위치에 모델이 요구하는 px/µm tile 추출, QC·tile filter, 모델 설정, 예측·saliency·heatmap, frametime 표시를 설명한다. Studio는 OpenGL 로컬 앱이며 단순 브라우저 demo로 소개하지 않는다. 문서의 속도 표현은 이번에 측정하지 않았다.

**배울 점:** “어느 위치를 어떤 물리 크기로 모델에 넣었는가”를 시각적으로 보여 준다. **차이:** PathologyEdge는 광범위한 모델 개발 플랫폼이 아니라 경계 처리 조건을 고정한 비교에 집중할 수 있다.

### 9. PathoQuant — 가장 가까운 개인 계정 비교군

[README](https://github.com/shekharaj0007/PathoQuant/blob/main/README.md)는 MoNuSeg, residual U-Net, 256/128 overlap, Gaussian blending, 연결 성분·AJI·count/density, Otsu+watershed를 제공한다. 저자 보고 test 14 tiles Dice 0.794/AJI 0.521, watershed AJI 0.318, RTX 3050 4GB/40 epoch다. 데이터·split·metric이 우리 TNBC 실험과 달라 수치를 직접 비교할 수 없다. 확인한 자료에서 웹 seam QA 화면이나 live demo는 찾지 못했다.

[tiling.py](https://github.com/shekharaj0007/PathoQuant/blob/main/src/pathoquant/tiling.py)는 전체 출력 크기의 float32 누적·가중치 배열을 만든다. [infer.py](https://github.com/shekharaj0007/PathoQuant/blob/main/src/pathoquant/infer.py)는 PIL로 영상을 RGB NumPy array로 읽는다. 따라서 **constant VRAM을 constant total RAM으로 해석하면 안 된다.** 50,000² 출력에 누적·가중치 두 배열만 약 20GB(18.6GiB)라는 값은 코드에서 계산한 이론값이며 실측 RSS가 아니다. native WSI region streaming은 이 파일에서 확인하지 못했다.

**배울 점:** 작은 모델도 데이터·훈련·instance metric·baseline을 명확하게 제시할 수 있다. **보완 목표:** 우리 WSI 확장은 제한된 ROI와 실제 peak RSS/I/O까지 검증해 “gigapixel” 표현을 실제 처리 범위와 일치시켜야 한다.

### 10. hd_wsi / HD-Yolo

[공식 README](https://github.com/impromptuRong/hd_wsi/blob/master/README.md)는 patch/WSI nuclei detection·segmentation·세포 유형, 밀도·Delaunay 기반 TME feature, DeepZoom 웹 UI를 제공한다. 유방/폐 HD-Yolo와 대장 YOLOv8 weights 링크, 0.25 MPP 정렬과 원래 크기로 되돌리는 흐름이 있다. UI는 slide/model/device 선택→Run→overlay toggle이며 연구 demo라고 명시한다. 최적 성능을 위한 기본 모델 메모리 약 16GB 설명과 CPU 명령도 있다. 이 값을 우리 CPU 지연과 직접 비교하지 않는다. 연결 논문은 Rong et al., Modern Pathology 2023이다.

**배울 점:** 좌표·MPP 변환과 class/score/mask를 결과 파일에 같이 담는다. **한계:** 실시간 추론 demo의 작동 여부·정확도는 이번에 재현하지 않았다. 개인 계정 저장소여도 연구실·논문 기반인 사례로 구분해야 한다.

### 11. CellViT

[논문 초록](https://arxiv.org/abs/2306.15350)은 PanNuke 약 20만 annotated nuclei, 5 classes/19 tissue types, pretrained ViT encoder 기반 instance segmentation을 다룬다. 저자 보고 mPQ 0.50, detection F1 0.83이다. [README](https://github.com/TIO-IKIM/CellViT/blob/main/README.md)는 1024px patch/64px overlap, metadata와 GeoJSON→QuPath export, 평가 checkpoint 선택 주의를 설명하며 새 CellViT++/Inference 저장소로의 이동도 공지한다.

**배울 점:** semantic mask와 instance/type 평가를 분리하고 dataset·fold·checkpoint 조건을 고정한다. **한계:** 우리 binary foreground Dice를 이 mPQ/F1과 비교해서 좋고 나쁨을 판정할 수 없다. 구버전 README를 최신 pipeline의 성능으로 일반화하지 않는다.

### 12. HoVer-NeXt

[PMLR 원문](https://proceedings.mlr.press/v250/baumann24a.html)은 Lizard에 mitosis를 추가한 H&E nuclei segmentation/classification, PanNuke 비교와 WSI 처리속도를 보고한다. 저자 조건의 0.5MPP 1.8s/mm², 0.25MPP 3.2s/mm², binary F1 0.84는 논문 수치이지 이 환경의 측정이 아니다. [inference 저장소](https://github.com/digitalpathologybern/hover_next_inference)에는 Lizard/PanNuke ConvNeXtV2 weights, OpenSlide 입력, inference와 후처리의 분리·worker/tiling 설정, instance map/centroid/QuPath TSV가 있다. OpenReview 주소는 browser verification 화면으로 막혔고 PMLR 원문으로 확인했다.

**배울 점:** throughput은 MPP·면적·장치·후처리 범위를 같이 써야 한다. **보완 목표:** 추론이 빨라도 dense stitching·후처리·출력이 병목일 수 있으므로 단계를 나눠 기록한다.

### 13. Hann window 논문 — 직접적인 방법 선행연구

[Pielawski와 Wählby, PLOS ONE 2020](https://doi.org/10.1371/journal.pone.0229839)은 H&E U-Net 128px patch, 1024px 영상, half-stride에서 no overlap·average·Pyramidal·Hann·Bartlett-Hann·Triangular를 비교한다. SSIM뿐 아니라 **patch centre와 edge 주변의 Dice**를 따로 평가한다. 단순 average가 항상 개선되는 것도 아니었다. 가장자리·모서리의 weight 처리를 별도로 설명한다. [저자 publication page](https://pielawski.fr/publications/)는 논문과 Code gist 링크를 연결한다; 이번에 그 gist의 실행은 확인하지 않았다.

**배울 점:** Hann overlap, 경계 점수 자체는 새 방법이 아니다. **필요 실험:** 동일 checkpoint와 동일 평가 격자에서 평균/Gaussian/Hann/valid-centre 등의 소규모 ablation, 외곽 padding/coverage 점검, 개선과 악화의 동시 보고. 논문의 유의성을 우리 2그룹 결과에 빌려 쓰지 않는다.

### 14. tiler

[공식 README](https://github.com/the-lay/tiler/blob/master/README.md)는 N차원 array의 iterator/getter/batch, overlap, padding, tapering merge를 제공한다. 작성자의 반복적인 3D patch 작업에서 출발한 일반 라이브러리이며 napari-tiler 연동을 안내한다. WSI는 사용 가능한 예 중 하나이고 자체 병리 모델·세포 GT·clinical validation이 붙는 것은 아니다.

**배울 점:** patch extraction/merge 구현은 이미 재사용 가능한 기반 기능이다. **차이:** PathologyEdge가 직접 구현하는 이유는 새 tiler를 발명해서가 아니라 경계 처리·좌표·후보 추적의 작은 실험을 설명하고 Python/C++ parity를 검증하기 위해서라고 적는 편이 정확하다.

### 15. Vooban Smoothly-Blend-Image-Patches

[공식 README](https://github.com/Vooban/Smoothly-Blend-Image-Patches/blob/master/README.md)는 2017년 Guillaume Chevalier의 공개 구현으로, 50% overlap과 2차 spline window·mirror padding·8방향 D4 평균을 설명한다. 위성영상 U-Net 결과와 mock prediction/reconstruction 예를 구분한다. 전체 patch batch가 큰 NumPy 배열을 만들기 때문에 큰 영상에서 CPU RAM 문제가 생길 수 있음을 직접 밝힌다.

**배울 점:** smoothing의 겉모양, identity reconstruction error, 실제 GT segmentation 정확도는 다른 지표다. **한계:** 이 예시의 수치를 병리 성능 근거로 쓸 수 없고, D4까지 넣으면 overlap 효과와 test-time augmentation 효과가 섞인다.

### 16. ASHLAR — 다른 의미의 stitching

[공식 저장소](https://github.com/labsyspharm/ashlar)와 [방법 설명](https://labsyspharm.github.io/ashlar/overview/DetCompMethods.html)은 microscope stage 위치와 overlap을 이용해 촬영 tile을 정합하고, imaging cycle 사이를 정렬해 pyramidal OME-TIFF를 만든다. [예제 데이터 설명](https://labsyspharm.github.io/ashlar/dataset.html)은 정상 인간 colon의 609 overlapping tiles와 junction 확대를 제시한다. 입력은 unstitched tile이므로 scanner가 이미 합친 WSI만 내보내면 이 입력 문제와 맞지 않는다.

**배울 점:** seam이라는 단어만으로 같은 연구라고 묶지 않는다. 촬영 정합 오차, CNN context 경계 오차, instance 중복은 각각 원인·입력·평가가 다르다. 이번 PathologyEdge 범위는 이미 합쳐진 WSI에서 추출한 추론 패치의 경계 문제다.

## 개인 프로젝트에서 주장과 근거를 구분한 추가 사례

[saiyam-jain0/Deep-Learning-Medical-Imaging README](https://github.com/saiyam-jain0/Deep-Learning-Medical-Imaging/blob/main/README.md)는 WSI tiling→inference→heatmap→Flask/OpenSeadragon을 소개하지만 Results에는 채워 넣으라는 지시와 예시 Dice/IoU가 있다. 실제 [inference_and_stitch.py](https://github.com/saiyam-jain0/Deep-Learning-Medical-Imaging/blob/main/inference_and_stitch.py)를 읽으면 EfficientNet-B0 scalar tile score를 평균하여 dense heatmap으로 만드는 코드다. nuclei segmentation이나 HoVer-Net가 구현됐다고 볼 수 없다. root directory에서 viewer HTML·tiling/inference 파일은 확인했으나 README의 Flask server 파일과 검증된 WSI checkpoint/benchmark는 확인하지 못했다. **완성된 임상/segmentation 경쟁 제품으로 계산하지 않았다.** 이 사례는 보기 좋은 기능 목록보다 실제 파일·weights·실행 결과를 확인해야 함을 보여 준다.

## 공개 데모 접근 근거

2026-11-08에 문서 열기와 별도의 Chromium 접근을 시도했다. raw notes는 작업 공간 `/workspace/work/wsi-landscape/`에 있다. 타사 캡처는 저장소에 재배포하지 않았다.

| 대상 | 관찰 | 결론의 한계 |
|---|---|---|
| KatherLab | README의 grid/fullscreen/slide-viewer 이미지와 설치 명령 확인 | 외부 live server를 찾았다고 주장하지 않음 |
| TIAViz | 저자 논문이 Warwick demo 링크를 제공; 웹 열기는 접근 실패 | 서버 장애인지 이 환경의 접근 문제인지 확정 불가 |
| DSA | 공식 demo 주소의 HistomicsUI HTML shell 확인 | 슬라이드 렌더링·zoom·annotation을 검증하지 않음 |
| TissUUmaps | 공식 gallery와 Xenium project app 링크 확인 | large data 로딩·렌더링 완료를 검증하지 않음 |
| caMicroscope | 연결 홈페이지가 조사 시 무관 사이트로 redirect | 공식 GitHub 자료만 채택; 정상 demo라고 소개하지 않음 |
| Chromium 공통 | DSA/TIAViz/TissUUmaps 접근에서 `NET::ERR_CERT_AUTHORITY_INVALID` | 이 환경의 브라우저 CA 신뢰 문제와 구분 필요; 타사 서비스 고장 근거가 아님 |

이번 조사에서 재현한 것은 출처 접근과 정적 코드 읽기다. 외부 모델의 실제 실행 성능이나 demo 사용성을 실측했다고 쓰지 않는다.

## WSI 확장에서 방어 가능한 방향

권장 설명은 **“실제 WSI의 출처·좌표를 보존한 제한된 ROI에서, 같은 CPU 모델의 경계 처리 전후와 후보 병합 근거를 추적하는 재현 가능한 연구 QA 데모”**다. 다음 항목은 신규성 주장이 아니라 구현·검증 요구사항이다.

1. WSI 전체와 분석 ROI를 같은 장면에서 구분한다. 전체 thumbnail/pyramid 위에 ROI bounds를 표시하고 확대해 같은 좌표의 prediction을 연다. ROI만 추론했다면 WSI 전체 분석이라고 표시하지 않는다.
2. source URL·license·checksum·원본 dimensions·level/downsample·MPP의 원천을 기록한다. `WSI level-0 → 읽기 level → resize → ROI → patch → 화면` 변환을 명시하고 MPP가 없으면 px로 표시한다.
3. 출력 이미지의 pyramid tile 경계와 모델 patch seam을 다른 개념으로 다룬다. viewer tile 선을 CNN 경계 효과처럼 보이지 않게 한다.
4. raw candidate마다 patch ID·좌표·유효영역·score·경계 접촉을 보존하고, suppressed 후보→kept 후보의 ID·규칙·IoU/거리·임계값을 연결한다. 이는 같은 세포라는 GT 판정과 구분한다.
5. 전체/ROI/현재 viewport/GT가 있는 부분의 지표 적용 범위를 구분한다. 화면을 확대했다고 저장된 성능 수치가 그 영역의 score로 변하지 않게 한다.
6. 사례는 개선·악화·차이 적음·겹친 다른 핵의 잘못된 병합을 포함한다. 사후 선택한 보기 좋은 사례를 평균 성능 대표로 설명하지 않는다.

## 필요한 실험과 아직 답할 수 없는 질문

| 질문 | 최소 검증 | 통과해도 주장할 수 없는 것 |
|---|---|---|
| 실제 WSI 좌표가 맞는가 | native metadata 보존; non-power-of-two downsample와 비정수 resize; ROI corners·round-trip·marker를 viewer에서 대조 | 새 slide/모든 scanner 지원 |
| 실제 tile serving인가 | 큰 이미지 전체 다운로드 없이 zoom별 tile 요청·오류/빈 tile 확인; overview→ROI 이동과 좌표 대조 | 전체 slide 추론 완료 |
| overlap이 이 모델에 도움이 되는가 | 같은 checkpoint/threshold/평가 격자; no-overlap, average, Hann/Gaussian, 큰 context 또는 valid-centre 대조; per-image·경계·내부·외곽 | 다른 데이터/모델에서 보편적 개선 |
| 중복 제거가 진짜 핵 수를 개선하는가 | instance GT가 있는 held-out 자료에서 detection/instance 지표·split/merge·중복률; NMS 전후 및 dense touch 사례 | binary CC 기반 proxy로 임상 세포 수 보증 |
| WSI용 메모리 처리인가 | ROI 크기·tile 수별 peak RSS와 I/O; dense accumulator 크기 기록; chunk/streaming이면 실제 큰 입력에서 측정 | VRAM 일정만으로 total memory 일정 |
| 외부 WSI에서도 정확한가 | 별도 외부 GT·scale/stain shift·환자/slide 단위 split, 여러 seed 또는 불확실성 보고 | GT 없는 WSI overlay가 정확도 입증 |
| Ki-67에 연결되는가 | IHC 자료, 종양/비종양+양/음 labels, 분모 정의, 전문가 검토·별도 검증 설계 | H&E nucleus foreground에서 양성률 추정 |

현재 GT 없는 외부 WSI를 추가할 경우 **좌표·뷰어·처리 이력·scale sensitivity를 확인하는 engineering case**로 명명하는 것이 맞다. seam disagreement나 큰 context와의 MAE는 일관성 지표이며 정확도를 대신하지 않는다. 기존 TNBC test를 본 뒤 설계를 조정했다면 새 성능 주장은 별도 holdout 또는 탐색 실험 표기로 구분해야 한다.

## 설계 전에 결정할 우선순위

무료 CPU 범위에서는 거대한 모델·새 임상 task보다, 배포 가능한 실제 WSI pyramid와 제한된 ROI 하나를 먼저 완결하는 편이 근거를 만들기 쉽다. ROI에서 native 좌표→확대→패치→후보 근거가 일치하고 메모리·시간이 기록된 다음, instance GT 데이터의 비교 실험을 별도로 확장한다. 기존 사용자 작성 과제인 일반 좌표 함수는 구현 주체와 완료 상태를 유지해야 한다.

이 조사로 확인한 공백은 **PathologyEdge 자신의 실험/WSI 근거**의 공백이다. 타사 도구 전체에 해당 기능이 없다는 exhaustive novelty claim이 아니다.
