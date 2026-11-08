# 실제 IHC 라벨을 이용한 CPU 세포 분류 기준선

실행일: 2026-11-08 UTC. **정답 세포 중심점이 주어진 조건**에서 Patherea Breast-P1의 네 세포 유형을
분류했다. 고정 테스트 10 case / 407 패치 / 6,419개 세포에서 **macro-F1 0.601, accuracy 0.704**였다.
이는 자동 세포 검출, 핵 경계 분할, 전체 슬라이드 Ki67 지수나 임상 assay의 성능이 아니다.

기존 TNBC TinyUNet은 H&E 핵 분할이며 Ki67 라벨이 없다. 이번 IHC 실험은 별도 데이터·모델·평가다.
[회사·데이터 조사](AIVIS_IHC_FEASIBILITY.md), [실제 결과 JSON](../artifacts/ihc/results.json),
[구현](../src/pathology_edge/ihc_baseline.py)을 함께 확인할 수 있다.

## 데이터와 정답

- 저자 제공 [Patherea 데이터](https://huggingface.co/datasets/ds2268/patherea),
  [논문](https://doi.org/10.1016/j.media.2025.103868). 데이터 라이선스 **CC BY-NC 4.0**.
- 저장소 revision `eb8a6c38cb1df3381b22385ed7b6175091c87ea5`의
  `Patherea_Breast_P1_224_v1.1.zip`, 134,068,022 bytes.
- ZIP SHA-256: `1194dbfb145ca3aee1a27fcff9d92799d73d34b5da972118424a7b67047034e7`.
- 실제 224×224 RGB 패치 1,330장, case ID 29개, mask 6,650장. 클래스마다 0/255 point-mask이며
  각 255 연결 성분이 **정확히 1픽셀**임을 검사했다. 세포 경계 mask가 아니다.
- `normal_cell` mask는 모두 비어 있어 평가 클래스에서 제외했다. 나머지 클래스별 중심점은
  종양 양성 5,556, 종양 음성 9,530, 비종양 양성 465, 비종양 음성 4,421이다.
- 논문·ZIP의 전체 `stats.txt`는 36,673개를 적고 있으나 **현재 파일에서 실제 센 수는 19,972개**다.
  fold별 통계는 실제 수와 일치한다. 원인 미확인이므로 이 실험은 19,972개라고 보고한다.

원 ZIP·전체 원영상은 공개 코드나 사이트에 복사하지 않았다. 화면에 제공하는 16개 실제 소스 패치와
국소 crop에는 [출처·조건](../dist/ihc/attribution.json)을 붙였다. 원소스 픽셀과 crop 범위를 검증했다.
생성 이미지·인위적 발현 정답은 사용하지 않았다.

## 사전에 고정한 분리와 모델 선택

저자의 **fold 1 test**를 유지했다. 나머지 19 case를 seed `20261108`의 Python `random.Random`으로
섞어 앞의 4 case를 validation, 나머지 15 case를 train으로 정했다. 새 패치나 세포를 만들기 전에
case 단위 배정을 고정했고 이미지·case·동일 픽셀 해시의 분할 간 중복이 없음을 검사했다.

| 부분 | case 수 | 패치 수 | 세포 수 | 종양 + | 종양 − | 비종양 + | 비종양 − |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 15 | 696 | 10,751 | 3,118 | 5,434 | 193 | 2,006 |
| Validation | 4 | 227 | 2,802 | 483 | 1,292 | 112 | 915 |
| Test | 10 | 407 | 6,419 | 1,955 | 2,804 | 160 | 1,500 |

Validation은 `case_0003, 0005, 0007, 0019`다. Test는
`case_0004, 0006, 0008, 0009, 0011, 0014, 0015, 0020, 0023, 0024`다.
전체 배정과 원 fold 파일 해시는 [split.json](../artifacts/ihc/split.json)에 있다.
저자는 환자 단위 fold라고 설명한다. 여기서 직접 검사한 것은 공개 파일의 case ID다.
별도의 임상 환자 명부·slide-to-patient 표가 없어 환자 신원을 독립 확인했다고 주장하지 않는다.

사전학습 모델을 사용하지 않았다. GT 중심의 반경 3·7픽셀 원 안에서 RGB, HSV의 hue sin/cos·채도·명도,
RGB optical density의 평균·표준편차 **40개 고정 색상 특징**을 얻었다. 영상 경계에서는 원을 영상 내부로
잘라 사용하며 세포 경계를 추정하지 않는다. Optical density는 `−log((RGB+1)/256)`이다.

`StandardScaler`는 **training 세포만**으로 맞췄다. `class_weight="balanced"`인 multinomial logistic
regression, L-BFGS, `max_iter=2000`, `tol=1e-6`을 사용했다. C 후보는 0.1·1·10으로 고정하고
validation macro-F1만으로 선택했다. 동점이면 작은 C를 선택한다. Validation을 합친 재학습은 하지 않았다.

| C | Validation macro-F1 |
|---:|---:|
| 0.1 | 0.653770 |
| 1 | 0.658591 |
| **10 (선택)** | **0.661112** |

모델과 정규화 계수를 JSON으로 저장·해시 고정한 뒤 테스트 코호트를 한 번 평가했다.
최대 softmax 값의 클래스를 선택하며 test로 threshold를 조정하지 않았다. 별도 확률 보정은 하지 않았으므로
화면의 확률은 **보정되지 않은 모델 점수**다. Pickle이나 실행 가능한 가중치 파일을 배포하지 않았다.

## 실제 테스트 결과와 오류

| 정답 클래스 | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Ki67 양성 종양 세포 | 0.862 | 0.738 | 0.795 | 1,955 |
| Ki67 음성 종양 세포 | 0.790 | 0.722 | 0.755 | 2,804 |
| Ki67 양성 비종양 세포 | 0.126 | 0.569 | **0.206** | 160 |
| Ki67 음성 비종양 세포 | 0.657 | 0.639 | 0.648 | 1,500 |

**Macro-F1 0.600906**, accuracy 0.703692. Macro-F1은 네 클래스 F1의 동일 가중 평균이며,
세포 수가 많은 클래스가 지배하는 accuracy와 의미가 다르다. 작은 양성 비종양 클래스의 precision이 낮다.

혼동행렬은 행이 정답, 열이 예측이다.

| 정답 ↓ / 예측 → | 종양 + | 종양 − | 비종양 + | 비종양 − |
|---|---:|---:|---:|---:|
| 종양 + | 1,443 | 29 | **479** | 4 |
| 종양 − | 152 | 2,024 | 134 | **494** |
| 비종양 + | 64 | 3 | 91 | 2 |
| 비종양 − | 15 | **505** | 21 | 959 |

색상만으로 같은 염색 상태의 종양·비종양을 구분하는 데 한계가 드러난다. 양성 종양을 양성 비종양으로,
음성 종양을 음성 비종양으로 바꾸는 오류가 많다. 이 기준선은 실제 핵 모양이나 넓은 조직 구조를 학습한
신경망이 아니다. 이 결과가 고급 모델의 우열이나 임상 정확도를 증명하지 않는다.

case별 macro-F1은 0.530~0.747이었다. 상세 혼동행렬·클래스 support와 case 결과는 JSON에 모두 남겼다.
case별 macro-F1도 네 클래스 정의를 유지하며, 정답·예측 모두 없는 클래스의 F1은 0으로 둔다.
단일 출처·단일 고정 분할 실험이며 외부 기관 검증이나 다중 seed 신뢰구간은 수행하지 않았다.

GT 중심 세포만 대상으로 `양성 종양 / (양성 종양 + 음성 종양)` 비율을 case별로 비교하면
평균 절대오차는 **7.686 percentage points**였다(10 case, 분모 0 제외 0 case).
예측 분모는 예측된 종양 세포 수이므로 종양 여부 혼동도 반영한다. 그러나 검출 누락·가짜 검출이 없고
선택된 주석 영역만 대상으로 하므로 **전체 슬라이드의 임상 Ki67 지수 오차가 아니다**.

예시는 정답 8개·오답 8개로 구성했다. 실제 정답 클래스별 순환 선택에 다른 case를 우선하며,
가능한 경우 중복 소스 영상을 피한다. 학습·평가 점수는 그대로 두고 저장된 예측으로 화면용 표본만
뽑았다. 이렇게 고른 16개는 성능·빈도를 추정하는 표본이 아니다. 전체 오류 수는 위 혼동행렬을 사용한다.

## CPU 비용과 재현

Linux x86_64, Python 3.12.14, NumPy 2.5.4, SciPy 1.18.1, Pillow 13.0.0,
scikit-learn 1.8.0에서 실행했다. 보이는 논리 CPU는 5개였고 fit의 BLAS thread는 1로 제한했다.
유료 GPU·외부 추론 서비스·네트워크 모델 호출은 사용하지 않았다.

| 측정 항목 | 관찰값 |
|---|---:|
| 전체 1회 벽시계 시간 | 26.60초 |
| 전체 split 영상·라벨 읽기/검사/해시/특징 계산 | 22.38초 |
| C 후보 3개 학습·선택 | 3.79초 |
| 이미 추출된 test 특징의 모델 계산 | 0.00130초 |
| 프로세스 최대 RSS | 146.70 MiB |

모델 계산 시간에는 영상 읽기·특징 계산이 빠져 있다. 이 값을 WSI 처리 시간으로 해석하면 안 된다.
공유 개발 환경의 한 번 관찰값이며 동시 테스트 등 다른 작업이 있었으므로 전용 장비 벤치마크가 아니다.

재실행에는 원 데이터 라이선스를 유지하고, 위 SHA-256과 일치하는 ZIP을 준비한다.
학습 환경에는 `scikit-learn==1.8.0`이 추가로 필요하다. 다음은 저장소 루트의 예시다.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src \
python -m pathology_edge.ihc_baseline \
  --data-dir /workspace/work/aivis-ihc/Patherea_Breast_P1_224_v1.1 \
  --archive /workspace/work/aivis-ihc/Patherea_Breast_P1_224_v1.1.zip \
  --artifacts /tmp/pathologyedge-ihc-reproduction \
  --public /tmp/pathologyedge-ihc-public
```

이미 평가한 artifact 디렉터리를 다시 쓰면 평가 lock으로 중단한다. 재현 확인에는 새 디렉터리를 쓴다.
재실행 결과로 모델 선택이나 보고할 seed를 바꾸지 않는다.

## 검증과 산출물

- [테스트](../tests/test_ihc_baseline.py)는 case 누출, 좌표 x/y 순서, 면적 mask 오용, 빈 normal 클래스,
  클래스 충돌·값 오류, 가장자리 특징, training-only 표준화, JSON 예측, 혼동행렬·분모와 실제 crop을 검사한다.
- [원자료 manifest](../artifacts/ihc/source-manifest.json)는 이미지·점 라벨 각각의 SHA-256과 case 배정을 저장한다.
- [선택 기록](../artifacts/ihc/selection.json), [평가 lock](../artifacts/ihc/evaluation-lock.json),
  [JSON 계수](../artifacts/ihc/model.json), [모든 test 세포 예측](../artifacts/ihc/test-predictions.json)을 보존했다.
- [추가 감사](../artifacts/ihc/verification.json)는 원 ZIP과 실제 입력 파일의 일치,
  공개 이미지·crop의 실제 픽셀, GT point, 저장된 JSON 모델의 예측 재현을 확인한다.

이 결과의 포트폴리오 가치는 유효한 실제 IHC 라벨, 분리된 실험, 실패 유형과 재현 가능한 CPU 기준선이다.
AIVIS 제품의 성능·허가나 병리의사의 판단을 대신한다는 주장은 포함하지 않는다.
