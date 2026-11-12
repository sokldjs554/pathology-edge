# BCData 외부 점검: 고정 IHC 모델의 전이 실패

실행·출처 확인일: **2026-11-12 Asia/Seoul**. 기존 Patherea CPU 색상 분류기를
BCData의 사전 선택 **10 ROI / 정답 종양 세포 중심 1,376개**에 적용했다.
Accuracy는 **31.61%**, ROI별 종양 양성률 평균 절대오차는 **24.26 percentage points**였다.
제한된 외부 자료에서도 안정적으로 전이되지 않았다. **임상 검증이나 전체 WSI 검증을 완료한 결과가 아니다.**

[집계 산출물](../artifacts/experiments/external-bcdata-20261112/README.md),
[실제 결과](../artifacts/experiments/external-bcdata-20261112/results.json),
[기존 실험](IHC_EXPERIMENT.md)을 함께 확인할 수 있다. 기존 모델·학습·테스트 결과는 변경하지 않았다.

## 원자료와 사전 고정 조건

[BCData 공식 배포 페이지](https://sites.google.com/view/bcdataset)는 Ki67 양성·음성 **종양** 세포의
좌표를 HDF5로 제공한다. [원 논문](https://link.springer.com/chapter/10.1007/978-3-030-59722-1_28)은
비상업 연구 용도로 사용을 제한한다. 공개 ZIP의 파일 목록을 직접 읽어 train 803 / validation 133 /
test 402 영상과 영상마다 두 HDF5 파일을 확인했다. 환자·슬라이드 대응표, 핵 경계 mask,
비종양 세포 정답, 임상 결과는 이 ZIP에 없다.

예측 전에 공식 test 경로의 사전식 정렬 앞 10개를 고정했다:
`0, 1, 10, 100, 101, 102, 103, 104, 105, 106`. 모든 제공 중심점을 평가했고 표본을 교체하지 않았다.
이 선택은 전체 402장이나 환자 모집단을 대표하는 무작위 표본이 아니다. 사전 점검에서는 0번 영상과 좌표 형식만 확인했다.
[프로토콜](../artifacts/experiments/external-bcdata-20261112/protocol.json)의 SHA-256은
`6052d56a11b70271608a56500229651d3ae2da3321526919607d490332cbb4dd`다.

30개 파일은 6,765,000 bytes의 부분 다운로드로 확보했다. CRC32·크기·SHA-256, 좌표 범위·정수 여부,
중복·클래스 충돌을 검사했다. 선택 영상의 동일 픽셀 중복과 기존 Patherea의 동일 파일 해시는 없었다.
이 검사는 부분 영상 중복이나 환자 독립성을 증명하지 않는다.

기존 모델의 40개 RGB/HSV/optical-density 특징, 반경 3·7 **픽셀**, 네 클래스 argmax를 그대로 유지했다.
재학습, 매개변수 선택, 확률 보정, 리사이즈, 염색 정규화는 하지 않았다. 비종양 예측도 오류로 남겼다.

영상은 640×640 RGB이고 PNG/HDF5에 물리 해상도 정보가 없었다.
[Patherea 논문 §2.2/Table 1](https://arxiv.org/html/2412.16425v2)은 BCData를 40× 현미경·카메라 자료로 설명한다.
후속 문헌의 0.2239 μm/pixel 값은 원자료에서 확인하지 못했다. 따라서 **원본 픽셀 조건의 전이 점검**이며,
물리 해상도를 맞춘 비교나 394개 WSI를 확인한 실험으로 해석할 수 없다.

## 실제 오류

| 지표 | 결과 |
|---|---:|
| 정답 양성 / 음성 종양 세포 | 803 / 573 |
| 네 클래스 argmax accuracy | 0.316134 |
| 양성 종양 F1 / 음성 종양 F1 | 0.625095 / 0.070278 |
| 정답이 존재하는 두 종양 클래스 평균 F1 | 0.347687 |
| 네 클래스 macro-F1 | 0.173843 |
| 정답 종양인데 비종양으로 예측 | 754 / 1,376 |
| ROI별 종양 양성률 MAE | 24.260319 pp |
| 비율 비교 가능 ROI / 정답·예측 분모 0 | 10 / 0·0 |

BCData에는 두 비종양 클래스의 정답 support가 0이다. 네 클래스 macro-F1은 기존 구현의
분모 0이면 F1=0 규칙을 유지한 값이며, **네 클래스 모두 있는 Patherea macro-F1과 직접 비교할 수 없다.**

혼동행렬의 행은 정답, 열은 예측이다.

| 정답 ↓ / 예측 → | 종양 + | 종양 − | 비종양 + | 비종양 − |
|---|---:|---:|---:|---:|
| 종양 + | 411 | 86 | 154 | 152 |
| 종양 − | 101 | 24 | 185 | 263 |
| 비종양 + | 0 | 0 | 0 | 0 |
| 비종양 − | 0 | 0 | 0 | 0 |

각 ROI에서 `양성 종양 / (양성 종양 + 음성 종양)`을 계산했다. 예측 비율의 분모에는
**예측상 종양인 세포만** 들어가므로 종양 여부 오류도 반영한다. 제공된 정답 중심을 사용해 검출 누락·가짜 검출은
평가하지 않았고, ROI 선택·침윤암 영역 결정·전체 슬라이드 샘플링도 평가하지 않았다.
색상, 물리 해상도, 형태 또는 주석 관행 중 무엇이 실패를 일으켰는지는 이 실험만으로 분리할 수 없다.

## 임상 검증에 대한 판단

[ACROBAT](https://researchdata.se/en/catalogue/dataset/2022-190-1/1/)의 CSV를 실제 확인했지만,
Ki67 점수·세포 정답은 없었다. 등록용 landmark는 Ki67 정답이 아니다.
환자 키는 `(set, anon_id)`로 결합해야 한다. `anon_id`는 split 사이에서 재사용된다.
[BCNB 공식 자료](https://github.com/bupt-ai-cz/BALNMP/blob/main/download_dataset.md)는 H&E 영상과 환자표를 제공한다.
Ki67 값은 수치 1,003개와 구간·부등호 문자열 55개가 섞여 있으며, 현재 IHC 색상 모델을 바로 평가할 정답은 아니다.
접근 실패와 자료 자체 부재는 구분해 [출처 기록](../artifacts/experiments/external-bcdata-20261112/sources.json)에 남겼다.

[IKWG 권고](https://pmc.ncbi.nlm.nih.gov/articles/PMC8487652/)는 분석적 타당성, 임상적 타당성과
임상적 유용성을 구분한다. 실제 검증에는 목적·성공 기준을 사전 고정하고, 대표성 있는 검체,
교육된 평가자의 독립·눈가림 점수, 적절한 기준 정답과 임상 설계가 필요하다.
이번 작업에 새 임상 코호트나 병리의사의 독립 판독은 포함되지 않았다.

## 재현 및 공개 범위

원영상·HDF5·세포별 좌표/정답/예측·환자표는 공개 산출물에 넣지 않았다.
원자료는 사용 조건을 확인하고 공식 출처에서 별도로 확보한다. 아래 `BCDATA_PARENT`는
그 안에 `BCData/images/test/`와 `BCData/annotations/test/{positive,negative}/`가 있는 디렉터리다.
선택된 30개 파일은 공개 manifest의 SHA-256과 같아야 한다.

저장소 루트에서 Python **3.12.14**를 사용한 재현 명령:

```bash
python3.12 -m venv work/bcdata-repro-venv
work/bcdata-repro-venv/bin/python -m pip install -r artifacts/experiments/external-bcdata-20261112/requirements.txt
BCDATA_PARENT=/absolute/path/to/independently_acquired_data
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  work/bcdata-repro-venv/bin/python artifacts/experiments/external-bcdata-20261112/reproduce.py \
  --data-dir "$BCDATA_PARENT" --output work/bcdata-reproduction/aggregate-results.json
```

재현 스크립트는 고정된 모델·특징 코드·선택 입력의 해시를 확인하고 **집계 결과만** 저장한다.
기존 출력 파일은 덮어쓰지 않는다. 확인한 의존성은 NumPy 2.5.4, SciPy 1.18.1, Pillow 13.0.0,
h5py 3.15.1이다. 학습용 scikit-learn이나 외부 모델 코드는 필요하지 않다.

최초 실행의 혼동행렬·precision/recall/F1·accuracy·비율을 별도 카운트 계산으로 확인했다.
공개용 재현 스크립트로 모든 영상별·전체 집계 결과가 원 결과와 일치함을 확인했고,
모델·프로토콜·입력 해시가 유지됐다. 지정된 데이터와 조건에서 검증한 연구용 코드이며
범용 입력·운영 환경까지 검증했다는 의미는 아니다.
