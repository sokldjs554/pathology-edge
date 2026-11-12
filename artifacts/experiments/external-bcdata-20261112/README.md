# BCData 외부 자료에서의 고정 모델 점검

2026-11-12 Asia/Seoul. [실험 설명](../../../docs/EXTERNAL_BCDATA_VALIDATION.md).

BCData 공식 test의 사전 선택 10 ROI, 제공된 종양 세포 중심 1,376개에서 기존 모델을 그대로 실행했다.
Accuracy 0.316134, 양성/음성 종양 클래스 평균 F1 0.347687, ROI별 종양 양성률 MAE 24.260319 pp였다.
이 결과는 제한된 외부 자료에서의 전이 실패를 보여준다. 자동 검출, 전체 WSI 점수, 환자 단위 평가나 임상 검증이 아니다.

| 파일 | 내용 |
|---|---|
| `protocol.json`, `inference-lock.json` | 예측 전 고정한 선택 규칙·모델·특징·입력 해시 |
| `selected-manifest.json`, `input-audit.json` | 선택한 30개 파일의 크기·해시와 영상별 입력 집계 |
| `results.json`, `verification.json` | 집계 지표·혼동행렬·영상별 비율과 독립 계산 확인 |
| `sources.json` | 1차 출처·접근 조건·범위·원본 파일명 대응 |
| `runner-original.py` | 최초 실행 스크립트의 변경 없는 감사용 사본; 당시 작업 폴더 구조에 의존 |
| `reproduce.py`, `requirements.txt` | 독립적으로 확보한 로컬 원자료로 집계 결과만 재현하는 스크립트와 의존성 |
| `reproduction-verification.json` | 새 재현 스크립트로 원 집계 결과가 일치했는지 확인 |
| `publication-manifest.json` | 공개 대상 파일의 SHA-256 및 제외 자료 점검 |

원영상, HDF5, 세포별 좌표·정답·예측 기록, 환자 표, 논문·웹페이지 원문은 포함하지 않는다.
원자료는 [BCData 공식 페이지](https://sites.google.com/view/bcdataset)에서 별도로 확보해야 한다.
[원 논문](https://link.springer.com/chapter/10.1007/978-3-030-59722-1_28)은 비상업 연구 용도로 제한한다.
파일명과 SHA-256은 입력 식별을 위한 정보이며 원자료 사용·재배포 권리를 부여하지 않는다.

이 스크립트는 지정한 입력과 고정된 모델의 재현을 확인한 연구용 코드다. 범용 데이터 로더나 운영용 분석기로 검증한 것은 아니다.
