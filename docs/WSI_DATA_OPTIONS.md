# PathologyEdge 실제 WSI 데이터와 타일 뷰어 조사

확인일: 2026-11-08 UTC. 원본 배포자의 데이터별 권리 표시, 원격 파일 헤더, 공식 도구 문서와 실제 overview/macro 이미지를 확인했다. 초기 자료 조사에서는 대형 WSI 전체를 내려받지 않았다. 이후 구현 단계에서는 선택 원본 전체를 내려받아 checksum을 검증했고, 아래 배포 결정은 그 원본에서 자체 타일을 생성하는 방향으로 갱신했다. 아래 크기는 **압축 원본 바이트 수**이며, DZI 변환 결과의 크기와 다르다.

## 권고

**첫 선택은 `CMU-1-JP2K-33005.svs`, 두 번째는 `JP2K-33003-1.svs`이다.** 두 파일 모두 작은 패치를 확대하는 데모가 아니라, 조직 전체 형상이 보이는 원본 스캔의 overview에서 native pixel까지 이어지는 타일 뷰어를 만들 수 있다. CMU 파일은 CC0로 명확하며 약 133 MB, 대동맥 파일은 수정·재배포를 명시적으로 허용하며 약 64 MB이다. 작은 파일이 필요할 때 발견한 Huron 샘플은 실제 scanner pyramid이지만 **큰 조직의 일부만 촬영한 scan ROI**여서 이번 주 데모 원본으로 권하지 않는다.

권리의 근거는 [OpenSlide 원본 데이터 index.json](https://openslide.cs.cmu.edu/download/openslide-testdata/index.json)과 [Aperio 데이터별 라이선스 표](https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/)이다. OpenSlide 소프트웨어의 LGPL 라이선스를 이미지에 적용한 판단이 아니다. CC0는 복사·수정·배포를 허용한다. 출처를 남기되 제공 기관의 보증 또는 승인을 암시하지 않는다. [CC0 원문 설명](https://creativecommons.org/publicdomain/zero/1.0/)

## 원본 후보 비교

| 후보 / 원본 링크 | 크기 | native 크기, MPP | 파일에 들어 있는 범위 / 판정 | 이미지 권리 |
|---|---:|---|---|---|
| [CMU-1-JP2K-33005.svs](https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1-JP2K-33005.svs) | 132,565,343 B, 126.42 MiB | 46,000 × 32,893; 0.499 µm/px; 20× | CMU-1의 JPEG2000 export. 4개 조직 절편이 있는 스캔 전체. 3개 원본 pyramid level. **권고 1** | CC0-1.0 |
| [JP2K-33003-1.svs](https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/JP2K-33003-1.svs) | 63,847,265 B, 60.89 MiB | 15,374 × 17,497; 0.2498 µm/px; 40× | 공식 설명은 aorta tissue. 원형 대동맥 절편 전체와 주변 유리가 보임. **권고 2** | 공식 표: “Free to use and distribute, with or without modification”; JSON의 `distributable`을 CC0로 바꿔 부르면 안 됨 |
| [CMU-1.svs](https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1.svs) | 177,552,579 B, 169.33 MiB | 46,000 × 32,914; 0.499 µm/px; 20× | JPEG 원본. JP2K보다 21행 많고 압축이 다름. 엄밀한 provenance에서는 별개 자산 | CC0-1.0 |
| [Huron-1.tif](https://openslide.cs.cmu.edu/download/openslide-testdata/Huron/Huron-1.tif) | 35,568,452 B, 33.92 MiB | 6,022 × 10,503; 0.40 µm/px; 20× | H&E, Huron LE176, BigTIFF/JPEG. 2.41 × 4.20 mm의 scanner ROI. 전체 조직 overview 요건에는 제외 | CC0-1.0; Huron Digital Pathology |
| [Huron-1-40x.tif](https://openslide.cs.cmu.edu/download/openslide-testdata/Huron/Huron-1-40x.tif) | 115,718,398 B, 110.36 MiB | 12,040 × 21,006; 0.20 µm/px; 40× | 위와 같은 물리 크기의 scan ROI. 높은 배율이어도 전체 조직이 되지 않음 | CC0-1.0; Huron Digital Pathology |
| [Hamamatsu CMU-1.ndpi](https://openslide.cs.cmu.edu/download/openslide-testdata/Hamamatsu/CMU-1.ndpi) | 198,030,965 B, 188.86 MiB | 51,200 × 38,144; 약 0.4564 × 0.4551 µm/px | 2009년경 brightfield scan. 후보 범위보다 큼. SVS와 다른 스캐너 좌표계이므로 ROI 좌표를 공유하면 안 됨 | CC0-1.0 |
| [CMU-1-Small-Region.svs](https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1-Small-Region.svs) | 1,938,955 B | 원본 표가 단일 pyramid level의 exported region이라고 명시 | 작은 파일 또는 `.svs` 확장자만으로 WSI라 판단하면 안 됨. 이번 전체 조직 데모에서는 제외 | CC0-1.0 |

`native`는 **제공된 파일의 최고 해상도 픽셀**이라는 뜻이다. JPEG 또는 JPEG2000 압축이 없는 원시 센서 데이터라는 뜻은 아니다. 또한 스캔 파일의 전 영역을 보여 주는 것과, 유리 위의 모든 조직 또는 환자의 전체 검체를 완전히 촬영했다는 것은 다른 주장이다. CMU-1/대동맥의 macro와 overview는 시각적으로 전체 절편 형상이 들어 있음을 지지하지만, 원 배포처가 제공하지 않은 임상적 완전성까지 보증하지 않는다. CMU의 정확한 기관·종·질환·염색 명칭은 해당 배포 설명만으로 확정하지 않는다. H&E처럼 보인다는 시각적 판단을 확정 metadata로 쓰지 않는다.

### Huron을 제외한 실제 근거

[공식 Huron macro](https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/huron/huron-1/macro_files/9/0_0.jpeg)에는 두 큰 조직 조각과 아래쪽의 작은 파란 촬영 사각형이 보인다. [scan thumbnail](https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/huron/huron-1/thumbnail_files/9/0_0.jpeg)은 조직이 프레임 경계에서 잘린 직사각형 영역이다. 원격 TIFF `ImageDescription`도 `Scan Size = 2.41x4.20 mm`를 기록한다. 따라서 이 파일은 native ROI를 확대하는 별도 예제에는 정직하게 사용할 수 있지만, 사용자 요청의 “조직 전체 → 세포” 예제로 바꾸어 설명할 수 없다.

반면 [CMU-1 overview](https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/aperio/cmu-1/slide_files/9/0_0.jpeg)와 [macro](https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/aperio/cmu-1/macro_files/9/0_0.jpeg), [대동맥 overview](https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/aperio/jp2k-33003-1/slide_files/9/0_0.jpeg)와 [macro](https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/aperio/jp2k-33003-1/macro_files/9/0_0.jpeg)는 조직 윤곽과 주변 유리를 함께 보여 준다.

## 검증한 원본 정보

CMU JP2K, 대동맥 SVS, 두 Huron 파일의 HEAD 요청은 HTTP 200, 위 표와 일치하는 `Content-Length`, `Accept-Ranges: bytes`를 반환했다. 각 TIFF의 IFD와 description만 1.7–2.6 KB씩 HTTP Range로 읽어 크기와 MPP를 확인했다. TIFF의 해상도 단위가 centimeter이면 `MPP = 10000 / pixels_per_centimeter`이다. Huron의 25,000 px/cm는 0.40 µm/px이며, 40× 파일의 50,000 px/cm는 0.20 µm/px이다. Aperio 파일은 description의 `MPP` 값을 직접 제공한다.

| 파일 | 공식 SHA-256 |
|---|---|
| CMU-1-JP2K-33005.svs | `9a1923cd9bcb260ba4d99d64f8d6e32550648c332ba48817f920662f3a513420` |
| JP2K-33003-1.svs | `6205ccf75a8fa6c32df7c5c04b7377398971a490fb6b320d50d91f7ba6a0e6fd` |
| CMU-1.svs | `00a3d54482cd707abf254fe69dccc8d06b8ff757a1663f1290c23418c480eb30` |
| Huron-1.tif | `295506f9872becce44033baa830dfd7a7644d104a832e6a7f73565be990c465d` |
| Huron-1-40x.tif | `8ff6a75066d6325b1df2ecdeaaa2adf026b13082dc3673319a1788ef12978094` |
| Hamamatsu CMU-1.ndpi | `edf4a1ccf395c7000ae93ad3b44c07d97043810e00be0c1d167dd09bbe436e46` |

이 표는 **배포자가 공표한 checksum**이다. metadata range 조회만으로 전체 파일 checksum을 검증했다고 말하면 안 된다. 구현 단계에서 전체 다운로드 후 직접 SHA-256을 계산하고 일치 여부를 기록해야 한다. 서버 ETag는 SHA-256 대체물이 아니다.

## 정적 DZI와 원격 타일 비교

권고 경로는 원본을 한 번 다운로드하고 checksum을 확인한 다음, native 해상도를 끝 level로 유지한 DZI를 만들어 기존 정적 사이트에 배포하는 것이다. 정적 타일 생성 후 Python/OpenSlide 서버를 상시 운영할 필요가 없다. 소스 원본 자체를 사이트 아카이브에 함께 넣을 필요도 없다. 원본 링크와 checksum, 실제 사용한 해상도를 provenance에 기록하면 된다.

| 배포 방식 | 장점 | 실제 제약 |
|---|---|---|
| 자체 생성 DZI + OpenSeadragon | 픽셀 범위, 배포 버전, ROI 좌표, 타일 가용성을 직접 고정. 기존 Sites 정적 호스팅으로 동작 | native pyramid 타일 파일 수와 전체 JPEG 바이트 수를 실제 생성 후 측정해야 함 |
| 공식 OpenSlide demo 타일 | 원본 해상도까지 이미 제공. 새로운 서버·계정·유료 리소스 없음 | 외부 demo의 주소·버전·CORS·가용성에 의존. SLA나 영속 호스팅 계약은 확인되지 않음 |
| 동적 OpenSlide/IIIF 서버 | 큰 슬라이드의 임의 영역을 요청 시 생성 | 실행 서버, 캐시와 운영 필요. 현재 무료 정적 데모에는 불필요 |

타일 한 변을 512/1024로 정했을 때의 이론상 파일 수를 모든 DZI level에 대해 계산했다. overlap은 타일 이미지 가장자리 크기에 영향을 주며 이 계산의 격자 수를 바꾸지 않는다. 아래는 빈 타일을 생략하지 않는 수치이며 저장 용량 측정값이 아니다.

| native 이미지 | 512 px 타일 | 1024 px 타일 | level 수 |
|---|---:|---:|---:|
| CMU JP2K 46000×32893 | 7,887 | 2,038 | 17 |
| 대동맥 15374×17497 | 1,483 | 399 | 16 |
| Huron 6022×10503 | 354 | 103 | 15 |

파일 제한이 문제이면 타일 크기를 조정하거나 용량이 작은 대동맥 파일을 택할 수 있다. 조직 전체 이미지를 작은 JPEG로 축소한 뒤 그것을 확대하는 방식은 native 상세 탐색의 대체가 아니다. JPEG 품질을 조정했다면 re-encoding 사실도 기록한다.

### 조사 당시 공식 원격 타일 검증 — 공개 배포에서는 미채택

[공식 demo](https://openslide.org/demo/)가 사용하는 [info.json](https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/info.json)과 [status.json](https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/status.json)을 직접 확인했다. 2026-11-08 확인 시 `dirty=false`, stamp=`88ddfdd0`이며, 임의 Origin 헤더가 있는 GET에 `Access-Control-Allow-Origin: *`를 반환했다. native level 16의 `45_32.jpeg`와 overview level 9의 `0_0.jpeg`도 HTTP 200/CORS `*`였다.

다음은 초기 조사에서 확인한 공식 원격 JP2K descriptor의 기록이다. 로컬 브라우저의 200/CORS 확인과 달리 공개 배포에서는 S3가 `AccessDenied` XML/HTTP403을 반환했다. CORS 헤더가 `*`여도 객체 접근이 허용되는 것은 아니다. 접근 제한 우회나 Referrer 변경은 수행하지 않았고, 현재 배포는 이 외부 URL을 사용하지 않는다. 동일 CC0 원본으로 모든 level의 정적 DZI를 생성해 같은 사이트에서 제공한다.

```json
{
  "Image": {
    "xmlns": "http://schemas.microsoft.com/deepzoom/2008",
    "Url": "https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/aperio/cmu-1-jp2k-33005/slide_files/",
    "Format": "jpeg",
    "TileSize": 510,
    "Overlap": 1,
    "Size": {"Width": 46000, "Height": 32893}
  }
}
```

CMU JPEG 원본은 URL이 `/aperio/cmu-1/slide_files/`, 높이는 **32914**이다. 원본을 JP2K에서 분석했다면 full CMU JPEG 타일과 혼용하지 않는다. 유사 영상이라도 재압축과 마지막 21행 차이가 있어 출처·픽셀 일치 주장을 깨뜨린다.

[공식 생성 코드](https://github.com/openslide/openslide.github.io/blob/main/demo/_synctiles.py)는 배포 index를 읽고 원본 SHA-256을 검증한 뒤 OpenSlide `DeepZoomGenerator`로 JPEG 품질 75 타일을 만든다. 코드의 CORS 설정은 `['*']`이다. 이 근거는 원본과 파생 타일의 연결을 설명한다. 코드 LGPL과 이미지 CC0는 별도 권리이다. 관련 CMU 두 source의 sparse map은 확인 시 비어 있었다. 다른 슬라이드의 sparse map은 빈 타일 요청을 생략해야 할 수 있으므로 단순히 모든 URL이 존재한다고 가정하지 않는다.

## 도구별 역할과 라이선스

| 도구 | 담당 기능 | 소프트웨어 권리 / 주의점 |
|---|---|---|
| [OpenSlide](https://openslide.org/) + [Python API](https://openslide.org/api/python/) | SVS/NDPI/TIFF 디코딩, level0 좌표의 ROI 읽기, thumbnail, MPP, DeepZoom 생성 | LGPL-2.1. 이미지 또는 모델 가중치 라이선스가 아님 |
| [OpenSeadragon](https://openseadragon.github.io/) | 브라우저 타일 요청, pan/zoom, navigator, overlay; DZI/IIIF 등 지원 | [BSD-3-Clause 형태의 공식 LICENSE](https://github.com/openseadragon/openseadragon/blob/master/LICENSE.txt). SVS를 직접 분석하는 AI 엔진이 아님 |
| [TIAToolbox](https://tia-toolbox.readthedocs.io/en/latest/) | WSI 읽기·patch 추출·stain 처리·모델 inference 및 결과 처리 | [코드 BSD-3-Clause](https://github.com/TissueImageAnalytics/tiatoolbox/blob/develop/LICENSE). 가중치는 [모델별 별도 권리](https://tia-toolbox.readthedocs.io/en/latest/pretrained.html) |

Huron vendor 지원은 [OpenSlide 4.0.1](https://github.com/openslide/openslide/releases/tag/v4.0.1)에 추가되었다. 단순히 OpenSlide “4.x”라고만 확인하면 부족하다. [Huron 형식 문서](https://openslide.org/formats/huron/)의 구조와 확인한 3-level pyramid를 실제 library 출력과 비교해야 한다. 오래된 library가 generic TIFF로 파일을 열었다고 해서 모든 level과 MPP를 올바르게 해석했다는 뜻이 아니다.

TIAToolbox를 쓰더라도 기존 분석 파이프라인을 통째로 바꿀 필요는 없다. 필요한 경우 ROI 추출·좌표·모델 입력 resolution 관리에만 사용할 수 있다. 공식 문서는 PanNuke 가중치를 CC BY-NC-SA 4.0, CoNSeP 가중치를 Apache 2.0 등으로 구분한다. 코드 BSD를 근거로 모든 가중치가 자유 재배포된다고 주장하지 않는다.

## 실제 분석 ROI와 정직한 결과 표시

추천 원본 목록에는 nuclear instance GT mask 또는 핵 유형 GT가 함께 제공되지 않는다. 따라서 이 원본에 실행한 결과는 **unlabelled WSI ROI inference**로 표시해야 한다. nuclear Dice/IoU/PQ, precision/recall, 진단 정확도, 실제 핵 개수에 대한 오차를 측정했다고 주장할 근거가 없다. 별도 데이터셋에서 얻은 benchmark는 데이터셋·split·조건을 명시하고 이 WSI 결과와 구분한다.

ROI 산출물에는 적어도 다음 lineage를 저장한다.

- 원본 파일명, 다운로드 URL, source SHA-256, native width/height, MPP x/y.
- `level0` 좌표계의 `x,y,width,height`, 추출 level과 실제 downsample, 추출 RGB의 checksum.
- 모델 이름·가중치 checksum·버전, 입력 MPP, resize/padding/crop/색 처리, 출력 pixel과 level0 사이의 affine mapping.
- 입력 ROI·확률 또는 mask·instance contour·카운트·실행시간. 카운트는 “모델이 검출한 수”로, 시간은 해당 ROI 크기와 실행 환경을 함께 표시.

[OpenSlide API](https://openslide.org/api/python/#openslide.OpenSlide.read_region)는 `read_region`의 location이 **level0 좌표**임을 명시한다. Viewer rectangle, crop 파일, inference mask가 동일한 ROI를 가리키도록 이 기준을 통일한다. DeepZoom level 번호는 OpenSlide pyramid level 번호와 다르다. 필요하면 `get_tile_coordinates`로 연결할 수 있다. ROI를 모델 입력 크기로 resize했다면 원본 polygon으로 역변환할 때 scale과 padding offset을 모두 반영한다.

조직 영역 선택은 저해상도 overview에서 배경·접힘·찢김을 먼저 보고, native crop을 확인한 뒤 고정한다. 작은 예쁜 영역만 골라 일반화 성능처럼 제시하지 않는다. CMU0.499 µm/px를 0.25 µm/px 모델에 넣기 위해 확대했어도 새로운 native 상세가 생기지 않는다. 대동맥은 0.2498 µm/px여서 0.25 입력 해상도에는 더 가깝지만, 조직·세포 형태의 domain 차이는 별도로 남는다.

## 추가 원천을 우선하지 않은 이유

- **OME 공개 SVS:** [원본 디렉터리](https://downloads.openmicroscopy.org/images/SVS/)의 `77917.svs` 704,041,277 B, `77928.svs` 609,174,117 B. [데이터 readme](https://downloads.openmicroscopy.org/images/SVS/readme.txt)가 Paul Felts의 이미지이며 CC BY 4.0이라고 명시하고 [COPYING](https://downloads.openmicroscopy.org/images/SVS/COPYING)도 제공한다. 합법적 대안이지만 이번 약 5–150 MB 범위를 크게 초과한다. 임의의 OME 파일 모두에 이 폴더 권리를 일반화하지 않는다. native 치수·MPP·checksum은 이번 조사에서 검증하지 않았다.
- **Zenodo 실제 breast WSI:** [Digital Pathology Dataset for Breast Cancer Diagnosis, 14131968](https://zenodo.org/records/14131968)는 H&E/IHC `.svs`를 담은 실제 WSI 자료이다. [공식 API](https://zenodo.org/api/records/14131968)의 record license=`cc-by-4.0`를 확인했다. 최소 H&E archive `BAU_HE_22.zip`은 352,913,240 B, MD5=`a9e2f7a659afb3f87aa31c8cb6fc8b4d`. 최소 IHC archive `BAU_IHC_13.zip`은 161,139,161 B, MD5=`b6f70aa84a0358a2307d3fa4fb71d483`. 각 zip 안에 여러 슬라이드가 들어 있어 원본 하나의 크기·MPP와 nuclear GT 유무는 archive 조사 전 미확정이다. landing page가 이 조사 도구에서 429였지만 API metadata는 응답했다. 대형 파일은 다운로드하지 않았다.
- **TCGA/GDC:** [공식 안내](https://gdc.cancer.gov/access-data/gdc-data-portal)는 원본 SVS 다운로드를 지원한다. [공개 데이터 정책](https://gdc.cancer.gov/access-data/data-access-policies)과 [분석 정책](https://gdc.cancer.gov/analyze-data/data-analysis-policies)은 출처 표시와 재식별 금지 등을 정한다. open access와 CC0는 같지 않다. 현재 더 단순한 데이터별 권리와 작은 원본을 확보했으므로 추가 환자 자료 또는 대형 파일을 먼저 채택할 이유가 없다. 구체적 GDC 파일의 현재 공개 상태·크기·checksum을 조회하지 않은 상태에서 사용 가능한 파일이라고 제시하지 않는다.
- Zenodo에서 “WSI”라는 단어가 발견되어도 원본 WSI가 포함된 것은 아니다. 패치 archive, annotation-only record, Gaussian-splat 파생 렌더링은 native tissue WSI 원본 후보에서 제외했다.

## 구현 단계에서 확인할 사항

다운로드 checksum 일치, 최고 DZI level의 native 치수 일치, 전체 화면→native zoom에서 실제 타일 교체, ROI로 이동한 위치와 분석 입력 crop의 일치, 외부 타일 사용 시 배포 origin의 실제 브라우저 CORS를 확인한다. 코드가 돌아간 것과 unlabeled 데이터의 임상 정확도가 검증된 것은 구분한다.

조사 원시 자료는 작업 환경의 `/workspace/work/wsi-source-research/`에 있다. 원본 index JSON/HTML, metadata range-reader와 결과 JSON, official demo info/status JSON, 실제 overview/macro JPEG, Zenodo API JSON을 포함한다. source checksum의 전체 다운로드 검증은 구현 담당 단계에 남겨 두었다.

### 추론 전에 고정한 ROI 제안

아래 3개는 overview에서 조직이 차지하는 위치만 보고 선택했다. 모델 출력·count·confidence를 보고 선택하지 않았다. 대상은 `CMU-1-JP2K-33005.svs`, 좌표는 native level0의 top-left이고 크기는 모두 1024×1024이다.

| ROI | x | y | width | height | 선택 이유 |
|---|---:|---:|---:|---:|---|
| A | 5888 | 20608 | 1024 | 1024 | 왼쪽 큰 절편 내부 |
| B | 29440 | 9728 | 1024 | 1024 | 위쪽 가운데 큰 절편 내부 |
| C | 15872 | 26112 | 1024 | 1024 | 아래쪽 가운데 절편 내부 |

level9 overview의 중심점 `(50,165)`, `(234,80)`, `(128,208)`에 native factor128을 적용하고 512px를 뺀 top-left이다. 눈에 띄는 접힘이 있는 오른쪽 위 작은 절편을 피하고 3개 다른 절편을 포함했다. 추론 전 실제 native RGB를 한 번 확인하여 유리·뚜렷한 찢김 여부를 기록할 수 있다. 결과가 기대보다 나쁘다는 이유로 ROI를 바꾸지 않는다. 이 좌표 제안은 **보고서 작성 시점의 사전 선택**이며 실제 추론 실행·품질 검증 완료 주장이 아니다.
