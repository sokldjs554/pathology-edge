# 권리와 출처

## 데이터·공개 예제

TNBC v1.1: Naylor Peter Jack, Walter Thomas, Laé Marick, Reyal Fabien.
“Segmentation of Nuclei in Histopathology Images by deep regression of the distance map”.
DOI: https://doi.org/10.5281/zenodo.2579118

공식 API `https://zenodo.org/api/records/2579118`의 license.id는 `cc-by-4.0`입니다.
스냅샷: `artifacts/data-source.json`. 조건: https://creativecommons.org/licenses/by/4.0/
출처·저자를 표시하고 변형 내용을 기록합니다. 원본 전체 ZIP은 Git에 포함하지 않습니다.
`dist/assets`의 7개 예제는 원본 RGBA→RGB 변환, GT 시각화, 모델 overlay이며 원본 저자의
추천이나 검증을 뜻하지 않습니다. 오류 그림·축약 지표는 이번 실험에서 생성했습니다.

BCData, SHIDC, NuCLS, MoNuSeg, 회사의 그림·포스터는 데모에 복제하지 않았습니다.
참고 링크만 사용합니다. 코드 라이선스가 데이터에도 자동 적용된다고 가정하지 않습니다.

## 모델

TinyUNet은 이 저장소에서 새로 작성한 작은 U-Net 계열 네트워크입니다.
외부 사전학습 가중치나 유료 모델을 사용하지 않았습니다. 저장된 `model.pt`는 공개 TNBC
train/validation만 이용해 선택한 연구용 checkpoint입니다. 모델 hash와 학습 설정을 함께 제공합니다.
U-Net 구조 참고: Ronneberger et al., 2015, https://arxiv.org/abs/1505.04597

## 주요 소프트웨어

| 패키지 | 역할 | 권리 확인 경로 |
|---|---|---|
| PyTorch | 학습·추론·직렬화 | https://github.com/pytorch/pytorch/blob/main/LICENSE |
| NumPy | 배열·좌표·확률 합산 | https://numpy.org/doc/stable/license.html |
| SciPy | 일대일 매칭 | https://github.com/scipy/scipy/blob/main/LICENSE.txt |
| OpenCV | RGB/HSV/gray, 조직 마스크, 연결 성분 | https://opencv.org/license/ |
| pybind11 | Python/C++ 바인딩 | https://github.com/pybind/pybind11/blob/master/LICENSE |
| Pillow | 이미지 읽기·저장·결과 시각화 | https://github.com/python-pillow/Pillow/blob/main/LICENSE |
| pytest | 실행 가능한 테스트 | https://github.com/pytest-dev/pytest/blob/main/LICENSE |
| IBM Plex Sans KR | 웹 글꼴, 미로드 시 시스템 글꼴 | https://github.com/IBM/plex/blob/master/LICENSE.txt |

설치된 정확한 버전은 `requirements-lock.txt`, 해당 배포판의 license/notice가 우선합니다.
이 목록은 의존성 전체의 라이선스를 하나로 변경하지 않습니다. 모델·데이터·코드 권리를 분리합니다.

## 프로젝트 자체 코드

사용자가 프로젝트 코드의 공개 라이선스를 아직 선택하지 않았으므로 일괄 MIT 또는 다른
오픈소스 라이선스를 선언하지 않았습니다. GitHub 공개 열람과 제3자 재사용 허가는 구분합니다.
데이터에 적용되는 CC BY 4.0은 그대로 유지됩니다. 코드 라이선스 결정은 이후 사용자 검토 항목입니다.
