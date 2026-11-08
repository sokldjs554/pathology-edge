# 실제 WSI ROI 실험 기록

2026-11-08. `CMU-1-JP2K-33005.svs` 원본 전체 SHA-256을 검증하고, 사전에 정한 3개 native level0 ROI에 기존 TinyUNet 체크포인트를 실행했다. 모델·threshold·기존 TNBC 결과·사용자 좌표 과제는 수정하지 않았다.

## 범위와 사전 선택

- 원본: 46,000×32,893, 0.499 µm/px, CC0-1.0. 분석 범위: 3×1024×1024 = 3,145,728 pixel, 원본 파일 면적의 약 0.2079%. 이는 조직 면적 비율이 아니다.
- R1=(5888,20608), R2=(29440,9728), R3=(15872,26112). overview에서 고정한 뒤 `--prepare-only`로 추출한 RGB를 추론 전에 직접 확인했다. 모두 조직과 핵을 포함하여 원 좌표를 유지했다. 성능 결과를 보고 ROI를 바꾸지 않았다.
- 원본 제공 설명은 brightfield이며 조직형·정확한 염색·진단은 문서화하지 않는다. TNBC H&E 패치로 학습한 모델의 탐색적 적용이다.
- 핵 GT가 없으므로 WSI Dice/PQ/precision/recall 또는 개선·악화 판정은 없다. 파란색은 무겹침에서만 나온 예측 픽셀, 주황색은 겹침에서만 나온 예측 픽셀이다.

## 실행 조건

- 고정 모델 SHA-256: `62ac28ffe5d9851e91770b0fe13a92caf028092995cae50327fbc85a400e12b6`; threshold=0.5.
- `predict` 원래 구현을 그대로 호출했다. 무겹침은 128px 패치/128px step, 겹침은 128px 패치/64px step과 Hann probability blending. RGB/255 외 resize·stain normalization 없음.
- ROI×방식마다 새 Python 프로세스. torch 4 threads, OpenCV 1 thread, CPU. 같은 ROI 1회 warmup 후 3회 측정. 3회 probability byte hash가 동일함을 검사했다.
- 시간은 patch 추출·tissue gate·forward·stitch·components·NMS를 포함한 `predict` 내부 시간이다. WSI 다운로드·OpenSlide 읽기·모델 load·PNG/JSON 저장은 제외하고 읽기와 warmup 시간은 따로 기록했다.
- peak RSS는 각 독립 worker 프로세스의 절대 high-water mark이다. runtime/model/WSI읽기/warmup/반복 inference를 포함하고 산출물 직렬화 전에 읽었다. 모델 증분 메모리 또는 전체 WSI 메모리로 해석하지 않는다.
- 파일 OS cache 및 공유 host 부하는 통제하지 않았다. `read_seconds`는 cold storage 측정이 아니다.

| ROI | 방식 | warm 중앙값(s) | warmup(s) | native 읽기(s) | peak RSS(MiB) | raw→kept 후보 | 억제 |
|---|---|---:|---:|---:|---:|---:|---:|
| R1 | no_overlap | 0.2966 | 0.3091 | 0.0683 | 446.04 | 639→639 | 0 |
| R1 | overlap | 1.8990 | 2.0083 | 0.0693 | 471.46 | 2370→996 | 1374 |
| R2 | no_overlap | 0.3148 | 0.3278 | 0.0685 | 448.11 | 187→187 | 0 |
| R2 | overlap | 1.2485 | 1.3258 | 0.0614 | 473.61 | 722→348 | 374 |
| R3 | no_overlap | 0.3295 | 0.3284 | 0.0691 | 451.35 | 429→429 | 0 |
| R3 | overlap | 1.6191 | 1.7197 | 0.0690 | 471.83 | 1616→758 | 858 |

segmentation mask는 최종 probability를 threshold한 픽셀 결과이고, 후보 수는 patch별 connected component와 NMS의 별도 분기이다. 서로 다른 정의의 두 결과를 같은 정답 핵 개수로 표현하지 않는다.

## 실제 예측 불일치

동일한 내부 무겹침 128px grid 주위 radius8 경계띠를 두 방식에 공통 적용했다. ROI당 경계 영역은 216,832 pixel이다. 다음은 GT 오차가 아니라 두 예측 간 불일치이다.

| ROI | 추가(B only) | 제거(A only) | 전체 변화 | 경계띠 변화 | 선택 case local bbox |
|---|---:|---:|---:|---:|---|
| R1 | 33427 | 6586 | 40013 | 26157 | `[608, 624, 672, 688]` |
| R2 | 26698 | 5087 | 31785 | 21489 | `[80, 608, 144, 672]` |
| R3 | 28553 | 6423 | 34976 | 23549 | `[96, 752, 160, 816]` |

case는 실제 내부 128px 경계에 64×64 window의 중심을 놓는다. 한 축은 경계 좌표에 고정하고 다른 축 중심은 16px 간격으로 탐색하며, ROI 내부에 완전히 들어오는 창 중 전체 변화≥16이고 ±8px 경계띠의 변화>0인 영역을 고려한다. 경계 변화 수 내림차순, 전체 변화 수 내림차순, y/x 오름차순으로 하나를 고른다. 차이가 큰 곳을 검토하는 규칙이며 모델의 정확도나 대표성을 주장하는 규칙이 아니다. ROI 자체 선정은 추론 전에 이루어졌고, case window 선정은 두 출력의 차이에 기반한다.

## 재현과 산출물

OpenSlide 4.0.1 / openslide-python 1.4.7이 설치된 환경에서 다음을 실행한다. 원본 다운로드는 CLI가 자동 수행하지 않는다. 준비 단계는 RGB만 만들고 추론을 실행하지 않는다.

```bash
PYTHONPATH=src python -m pathology_edge.wsi_export \
  --slide /path/to/CMU-1-JP2K-33005.svs --prepare-only

PYTHONPATH=src python -m pathology_edge.wsi_export \
  --slide /path/to/CMU-1-JP2K-33005.svs \
  --model artifacts/model.pt --training artifacts/training.json \
  --output-dist dist --artifacts artifacts/wsi
python -m pytest -q
```

- `artifacts/wsi/source.json`: 원본 checksum·native 크기·MPP·OpenSlide 버전·권리와 동일 JP2K 원격 tile source.
- `artifacts/wsi/protocol.json`: 추론 전 고정 ROI geometry와 pixel hash, 원 모델/threshold, 반복 측정/경계 규칙, 그리고 revision2 case 표시 규칙.
- `artifacts/wsi/R{1,2,3}_{no_overlap,overlap}.json`: 독립 worker의 실제 raw/kept/suppressed, patch manifest, 모든 반복 시간과 probability hash.
- `dist/wsi.json`, `artifacts/wsi/experiment.json`: 동일한 완성 실험 schema. `dist/wsi/provenance.json`은 공개 provenance 요약.
- `dist/wsi/*.png`: native RGB, 실제 binary mask, RGBA segmentation 및 XOR difference overlay. SHA-256을 payload에 기록한다. 160px JPEG thumbnail은 목록 표시용이며 분석 입력이 아니다.
- suppression의 `kept_index`와 `suppressed_index`는 원 구현대로 **raw 배열 인덱스**다. `kept_raw_index`/`suppressed_raw_index`도 명시하며 kept objects는 `raw_index`로 연결한다. IoU·거리·threshold 충족 여부·완전한 component 우선 규칙을 실제 결과에서 산출한다.
- patch ID는 실제 `predict` grid의 순서를 따른다. local/level0 origin, valid bbox, trailing padding을 제외한 valid size를 저장한다. bbox는 `[x0,y0,x1,y1)` 형식이다.

검증: 전체 Python suite 54 passed / 12 learner tests skipped. WSI 검사에는 synthetic padding geometry, 실제 NMS trace의 두 trigger와 우선순위, 색 방향, 경계 중심을 포함하는 deterministic case와 mask-only 갱신 CLI, 실제 출력 파일 hash·mask·XOR·좌표·candidate 재계산 일치가 포함된다. CI에는 원본 WSI 다운로드나 native OpenSlide가 필요하지 않다. 체크인된 export가 없으면 실제 산출물 검사는 명시적으로 skip한다.

## 경계 중심 case 표시 갱신

revision2는 경계가 case 가장자리에 놓이는 문제를 고친 표시용 후처리이다. 저장된 두 binary mask의 SHA-256을 확인한 뒤 case 좌표·해당 창의 변화 수만 다시 산출했다. 원본 모델, native RGB, mask, segmentation/difference overlay, 여섯 worker 결과 JSON 등 25개 보호 파일의 checksum이 동일하고, 기록된 시간·NMS 결과도 그대로임을 검증했다. 추론은 재실행하지 않았다.

```bash
PYTHONPATH=src python -m pathology_edge.wsi_export \
  --refresh-cases --output-dist dist --artifacts artifacts/wsi
```

원래 추론 코드 hash는 `provenance.inference_pipeline_sha256`에 보존하고, 갱신 코드 hash는 `case_selection_pipeline_sha256`에 기록했다. public `wsi.json`은 같은 schema의 minified JSON으로 저장하여 8,929,315 → 3,934,683 bytes로 줄였다. 기록 보관용 `artifacts/wsi/experiment.json`은 읽기 쉬운 형태를 유지하며 내용은 동일하다.

## 공식 DZI와 native ROI 좌표 독립 확인

원본 SHA-256을 다시 확인하고, 3개 ROI의 저장 PNG가 해당 원본을 새 OpenSlide handle에서 읽은 native level0 RGB와 정확히 일치함을 확인했다. 이어 각 ROI의 고정 local 좌표 `(96,96)`, `(448,448)`, `(800,800)`에서 96×96 RGB 영역을 공식 JP2K DZI의 level16과 비교했다. 510px 격자와 내부 타일의 1px overlap을 반영했으며, 타일 경계를 가로지르는 표본은 격자 내부 영역을 이어 붙여 overlap 중복을 피했다. 원격 JPEG 10개가 HTTP200/CORS `*`로 응답했다.

| ROI | 표본 수 | 정렬된 RGB MAE 범위(0–255) | 기준을 각 축 +1px 이동한 MAE 범위 | 기준을 각 축 +16px 이동한 MAE 범위 |
|---|---:|---:|---:|---:|
| R1 | 3 | 2.946–4.232 | 13.142–19.275 | 35.992–49.395 |
| R2 | 3 | 3.069–4.782 | 14.971–24.491 | 39.480–45.159 |
| R3 | 3 | 3.483–4.472 | 16.439–24.768 | 36.041–48.666 |

9개 표본의 정렬된 평균 MAE는 **3.771/255**, 표본별 범위는 **2.946–4.782**였다. 모든 표본에서 의도적 offset 대조군보다 오차가 작았다. native PNG와 달리 원격 display tile은 공식 생성 코드에서 JPEG 품질75로 다시 저장하므로 RGB가 bit-exact하게 같다고 주장하지 않는다. 이 결과는 샘플링한 좌표에서의 정렬과 손실압축 차이에 대한 근거이며, WSI 전체 픽셀에 대한 완전 검사나 핵 분할 정확도 검증이 아니다.

[검증 기록](../artifacts/wsi/tile-alignment.json)에 각 source/ROI/원격 JPEG checksum, 실제 타일 URL·크기·HTTP 응답, native 좌표, 96×96 표본 hash, MAE/RMSE/오차 분위수·범위와 의도적 offset 결과를 남겼다. 원 모델·추론·소스 코드·공개 자산·기존 source manifest는 변경하지 않았다.
