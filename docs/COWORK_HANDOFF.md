# PathologyEdge — 자소서·포트폴리오 작성을 위한 Cowork 전달 자료

[Cowork 전달 ZIP 직접 다운로드](https://raw.githubusercontent.com/sokldjs554/pathology-edge/main/artifacts/handoff/PathologyEdge-Cowork.zip) · [파일 목록·SHA256](../artifacts/handoff/manifest.json). 문서와 실제 오류 그림 8개를 포함한 약2.1MB 묶음입니다. ZIP 안의 근거 링크는 커밋 `540b6e3`에 고정되어 있습니다.

기존 근거 기준: 커밋 `ad739fd`. 최신 추가 실험은 아래 별도 보고서와 원본 SHA로 연결합니다. 원본 감사 문서의 날짜 표기는 해당 기록을 유지했습니다. 이 문서는 확인된 프로젝트 결과와 개인 기여를 정리한 작성 자료입니다. 외부 서비스 전송이나 지원서 제출은 수행하지 않았습니다.

## Cowork에 전달할 작성 요청

아래 근거로 에이비스 AI 연구원 지원용 한국어 자기소개서와 포트폴리오 초안을 작성해 주세요. 이력서에 넣을 프로젝트 요약도 함께 정리해 주세요. 핵심은 **작은 핵심 구성요소의 직접 구현, 실제 비교 실험 실행, 결과·실패·비용·재현성의 구분**입니다. 프로젝트에 존재하는 전체 구현을 지원자가 모두 단독 작성했다고 표현하지 말고, 각 항목의 직접 작성·제공 구현 활용·실행·검토 범위를 유지해 주세요. 별도의 도구 기여 제목을 만들 필요는 없습니다.

숫자에는 데이터 분할과 실행 주체를 붙여 주세요. 기존 TNBC test 7장 결과, 후속 validation 10장 결과, WSI의 정답 없는 ROI 예측, IHC의 정답 중심점 조건 분류를 서로 합치지 마세요. 실패 사례와 처리 비용을 남기고, 학위·경력·논문·임상 경험 등 확인되지 않은 개인정보는 빈칸으로 두세요. 이번 자료 작성은 최신 요청에 따른 것이므로 과거 기록의 면접 문장 작성 보류를 작성 중단 사유로 삼지 않습니다. 다만 지원자가 면접 답변을 직접 작성·검토 완료했다는 의미는 아닙니다.

## 프로젝트 한눈에 보기

**PathologyEdge는 병리 이미지의 패치 처리 방식에 따른 핵 분할 차이를 원본 좌표, 예측, 오류 픽셀, 처리 비용까지 추적하는 연구·교육용 작업대입니다.** 같은 모델의 무겹침/겹침 추론 비교에서 출발해 실제 WSI 탐색과 제한된 ROI 예측, 별도 IHC 분류 기준선, 손실 함수 비교, CNN–소형 ViT 비교, 직접 작성한 공간 보정 모듈 비교로 확장했습니다.

| 항목 | 확인된 내용 |
|---|---|
| 저장소 | [github.com/sokldjs554/pathology-edge](https://github.com/sokldjs554/pathology-edge) |
| 데모 | [TNBC 정답 경계 비교](https://pathology-edge-lab.ykh13571.chatgpt.site/) · [실제 WSI 탐색](https://pathology-edge-lab.ykh13571.chatgpt.site/wsi.html) · [IHC 분류](https://pathology-edge-lab.ykh13571.chatgpt.site/ihc.html) |
| 기술 | Python, NumPy, PyTorch, OpenCV, OpenSlide, scikit-learn, C++/pybind11, Ubuntu, Docker, Git/GitHub Actions, 웹 결과 뷰어 |
| 개인 구현의 중심 | 좌표 변환·ROI 연결, Dice 지표·soft Dice 손실, 그룹 누수 검사, NMS 반례 테스트, 153파라미터 잔차 보정 head |
| 개인 실행의 중심 | CPU 학습, BCE/soft Dice 3개 seed 비교, CNN/ViT 비교, 보정 head 비교, C++ 패치 추출 측정, Ubuntu 재현, GitHub PR 작업 |
| 성격 | 에이비스와 무관한 독립 프로젝트. 진단·치료 의사결정용 제품이나 임상 검증 프로젝트가 아님 |
| 전체 기여 근거 | [직접 수행한 작업 U01–U73](CONTRIBUTIONS.md), [실행 안내](RUNBOOK.md), [프로젝트 README](../README.md) |

기술 목록은 프로젝트에 사용한 기술입니다. C++ 추출기·Transformer 전체 구조·학습 루프·WSI 뷰어·Docker 도구 전체를 지원자가 직접 구현했다는 뜻으로 바꾸지 않습니다.

## 개인이 직접 작성한 코드

아래 코드는 사용자가 제출한 계산 본문을 검토·반영한 범위입니다. 함수 틀, 입력 검사, 과제 요구사항, 테스트 fixture·대부분의 계약 테스트, 실행 도구와 통합 작업은 제공된 내용을 활용했습니다. 테스트 수는 사용자 실행 보고이며, 별도로 수행된 전체 프로젝트 검사 수와 합산해 개인 테스트 작성 실적으로 쓰지 않습니다.

| 직접 작성한 부분 | 구현·확인 내용 | 사용자 실행 보고 | 코드·근거 |
|---|---|---:|---|
| `local_to_level0` | 축별 리사이즈 비율과 downsample·원점을 반영해 국소 좌표를 원본 좌표로 변환 | 12 passed | [코드](../src/pathology_edge/learner_coordinates.py), [검토](../artifacts/learning/step01-review.json) |
| NMS 합성 반례 테스트 본문 | 서로 다른 두 핵이 IoU 0이어도 중심 거리 조건으로 하나 억제되는 경우를 검증 | 1 passed | [테스트](../tests/learner/test_merge_counterexample.py), [검토](../artifacts/learning/step02-review.json) |
| `dice_score` | 이진 분할 Dice 계산과 계약 조건 처리 | 20 passed | [코드](../src/pathology_edge/learner_metrics.py), [검토](../artifacts/learning/step04-review.json) |
| `find_group_leaks` | split을 넘는 그룹 ID를 찾아 보고 | 18 passed | [코드](../src/pathology_edge/learner_split.py), [검토](../artifacts/learning/step09-review.json) |
| `soft_dice_loss` 계산 본문 | sigmoid, 이미지별 교집합·합계, soft Dice, batch 평균을 PyTorch로 구현 | 8 passed | [코드](../src/pathology_edge/learner_losses.py), [검토](../artifacts/learning/step35-review.json) |
| `roi_points_to_level0` 연결 본문 | 모델 입력 크기와 실제 읽은 ROI 크기로 축별 scale을 계산해 기존 좌표 함수에 전달 | 8 passed | [코드](../src/pathology_edge/learner_wsi.py), [검토](../artifacts/learning/step40-review.json) |
| `LocalResidualHead.__init__/forward` | 3×3 Conv 1→8→1, ReLU, 마지막 층 0 초기화, 원 logits에 잔차 합산. 총 153파라미터 | 13 passed | [코드](../src/pathology_edge/learner_refinement.py), [제출·통합 검사](../artifacts/learning/step57-accepted-review.json) |

보정 head는 제공된 설계·계약을 따라 작성한 모델 구성요소입니다. 입력 검증 helper와 ViT backbone·학습 실행기는 제공 구현이며, 전체 모델을 독자 설계했다고 쓰지 않습니다. 여기서 보정은 공간 잔차를 더하는 처리이며 예측 점수의 확률 보정을 뜻하지 않습니다. head는 각 128px 입력 타일 안에서 동작하므로 인접한 별도 타일을 직접 연결하지 않습니다.

## 개인이 실행하고 제출한 실험·재현 작업

### 학습과 손실 비교

사용자는 Codespaces CPU 환경에서 기존 TinyUNet 학습을 실행하고 checkpoint·epoch·threshold·환경·해시를 제출했습니다. 모델 구조와 학습 루프는 제공 구현을 사용했습니다. 검증 10장의 이미지별 평균 Dice로 epoch와 threshold를 선택하고 test 7장은 선택에 쓰지 않는 절차를 설명했습니다. 최초 재현 실행은 epoch 13, threshold 0.35, validation Dice 0.535783이며 개발 환경의 수치와 정확히 동일한 재현으로 주장하지 않습니다. [기록](../artifacts/learning/step34-review.json).

직접 작성한 soft Dice를 연결해 BCE-only와 BCE+soft Dice를 별도 실행했습니다. 첫 비교의 검증 Dice는 **0.521171→0.535783**이며, 후속 고정 seed 20261110·20261111·20261112에서 총 6회 학습을 실행하고 조건·원본 보존 검사 성공을 보고했습니다.

| 사용자 손실 비교 · validation 10장 | BCE-only | BCE+사용자 soft Dice |
|---|---:|---:|
| 3개 seed Dice 평균 ± 표본 SD | 0.518215 ± 0.005288 | 0.546238 ± 0.007100 |
| 동일 seed 간 차이 평균 ± 표본 SD | — | +0.028023 ± 0.006058 |
| seed별 상승/동일/하락 | — | 3/0/0 |

이는 같은 검증 데이터에서 선택한 점수의 반복 결과입니다. 독립 test 개선이나 통계적 유의성·외부 일반화를 입증하지 않습니다. 원본 파일 전체를 직접 다시 감사한 후속 ViT·보정 실험과 달리, 이 손실 반복 실험은 제출 요약과 사용자 로컬 감사 성공 보고가 핵심 근거입니다. [6회 사용자 수치](../artifacts/learning/step42-user-summary.json) · [확인 범위](../artifacts/learning/step42-review.json) · [단일 비교의 본인 해석](../artifacts/learning/step39-review.json).

### CNN–소형 ViT 비교

사용자가 비교 방향으로 ViT를 선택하고 제공된 TinyUNet·SmallViTSegmenter 및 실행 도구로 **seed 20261113, 두 모델 각 16epoch**를 실행했습니다. 학습·증강·선택 조건을 고정했으며 두 모델 모두 128px 무겹침 추론입니다. 외부 사전학습 가중치는 사용하지 않았습니다. TinyUNet 29,761파라미터, SmallViT 33,632파라미터로 모델 크기·연산량이 동일한 비교는 아닙니다.

| 사용자 Codespaces · validation 10장/2그룹 | TinyUNet | SmallViT | 차이 |
|---|---:|---:|---:|
| 전체 Dice | 0.503768 | 0.557644 | +0.053876 |
| 128px 패치 경계 Dice | 0.453280 | 0.530161 | +0.076881 |
| 내부 Dice | 0.504595 | 0.550867 | +0.046272 |

전체 Dice는 7장 상승·3장 하락했습니다. 사용자는 전체 10행과 집계를 제출하고 입력 토큰 shape `(8, 256, 32)`, 토큰 수 `(128÷8)×(128÷8)=256`을 설명했습니다. Transformer 전체 구현·이론 숙련이나 공식 ViT 논문 재현으로 확대하지 않습니다.

후속 원본 ZIP 112파일을 제출했고 모델 SHA, 저장 확률과 정답에서 재계산한 60개 평가 영역, 기존 요약·이미지별 표시 수치의 일치가 확인됐습니다. 이 독립 감사는 새 학습이나 새 추론을 뜻하지 않습니다. [사용자 SUMMARY](../artifacts/learning/step53-user-summary.json) · [10행](../artifacts/learning/step54-user-rows.json) · [원본 감사](USER_RESEARCH_AUDIT.md) · [모델별 재계산](../artifacts/learning/step56-user-evidence/vit-re-audit.json).

프로젝트에는 **개발 참고 환경의 CNN–ViT 3개 seed·6모델 비교**도 완료되어 있습니다. 전체 Dice 평균은 0.537512→0.565899, 쌍별 평균 차이는 +0.028387이며 3개 seed 모두 상승했습니다. 이 실행은 사용자 직접 실행으로 기록하지 않습니다. 사용자 단일 실행과 합쳐 평균을 내거나, 같은 10장을 30개의 독립 검증 이미지로 세지 않습니다. [반복 실험 원본·조건](../artifacts/experiments/cnn-vit-repeats-20261111/README.md) · [재감사 요약](../artifacts/experiments/cnn-vit-repeats-20261111/re-audited-summary.json).

### 직접 작성한 보정 head의 비교

사용자는 작성한 LocalResidualHead를 연결한 SmallViT와 기준 SmallViT를 **seed 20261116**에서 학습·비교했습니다. validation 10장·2그룹을 사용했고 두 모델 모두 128px 무겹침 추론입니다. 기준 epoch 12, 보정 epoch 14를 선택했으며 threshold는 모두 0.35입니다.

| 사용자 보정 비교 | 기준 ViT | 보정 추가 | 차이 |
|---|---:|---:|---:|
| 전체 Dice | 0.570565 | 0.590386 | +0.019820 |
| 경계 Dice | 0.558802 | 0.559040 | +0.000238 |
| 내부 Dice | 0.560475 | 0.582999 | +0.022525 |
| warm CPU 파이프라인 중앙값 | 43.672ms | 55.680ms | +12.009ms, 약 +27.50% |

차이는 반올림 전 값으로 계산합니다. 전체 Dice는 9장 상승·1장 하락, 경계는 6장 상승·4장 하락했습니다. **전체 평균은 상승했지만 경계 평균 변화는 매우 작고 처리 비용이 증가했습니다.** 경계 문제 해결·뚜렷한 경계 성능 개선·모든 이미지 개선으로 쓰지 않습니다. 최대 하락 `09_1`의 전체 Dice는 0.519999→0.501994, 경계 차이는 −0.094202입니다.

원본 ZIP 70파일과 두 모델 SHA, 동결 Python 소스 21개·실행기, 저장 확률 20개에서 60개 평가 영역·6개 평균, 동일 초기 가중치·crop/증강 순서·원본 보존 기록을 대조했습니다. 원본 수신·독립 감사가 완료됐으며 본인의 후속 화면 검토·면접 해석 답변 완료와는 구분합니다. [최종 감사 보고](USER_REFINEMENT_AUDIT.md) · [정확한 요약](../artifacts/experiments/user-vit-refinement-20261112/re-audited-summary.json) · [전체 이미지별 수치](../artifacts/experiments/user-vit-refinement-20261112/per-image.json) · [원본 ZIP](../artifacts/experiments/user-vit-refinement-20261112/evidence.zip).

개발 참고 환경의 같은 seed 결과는 전체 0.570565→0.583877, 경계 0.558802→0.550175로 다릅니다. 사용자 실행을 대신하거나 추가 독립 seed로 세지 않습니다. [개발 참고 원본](../artifacts/experiments/vit-refinement-reference-20261112/README.md).

### C++ 측정, Ubuntu 재현, GitHub 작업

사용자는 제공된 패치 추출기와 측정 도구로 Python/C++ 1·2·4스레드, 입력 512²·2048²의 8조건을 실행했습니다. 환경은 AMD EPYC 7763, 보이는 CPU/affinity 2개입니다. 후속 제출 원본에서 **8조건×9회=72개 원시 시간**과 출력 일치·표시값이 대조됐습니다.

| 사용자 측정 · 중앙값 ms | Python | C++ 1스레드 | C++ 2스레드 | C++ 4스레드 |
|---|---:|---:|---:|---:|
| 512² | 0.509 | 0.265 | 0.844 | 1.071 |
| 2048² | 22.418 | 12.425 | 13.594 | 11.453 |

2048²의 C++ 4스레드는 Python 대비 약 1.96배였지만 작은 입력에서는 스레드 증가가 느려졌습니다. 사용자는 이 값이 allocation·crop·padding을 포함한 **패치 추출 구간**이며 모델 forward·확률 합산·후처리를 포함한 전체 추론 가속률이 아니라고 설명했습니다. C++/GIL/atomic 작업 분배 코드 전체를 직접 작성했다는 근거는 없습니다. [사용자 표](../artifacts/learning/step51-user-measurements.json) · [원시값 후속 감사](USER_RESEARCH_AUDIT.md) · [본인 해석](../artifacts/learning/step52-review.json).

사용자는 Ubuntu 환경에서 제공된 고정 소스 재현 도구로 C++ 재빌드, **191개 테스트/skip 0, 저장 Dice 42개·평균 6개 일치, 정적 데모 검사**를 실행하고 결과를 제출했습니다. 이어 재현 로그 9개를 commit·push하고 [PR #1](https://github.com/sokldjs554/pathology-edge/pull/1)을 생성·설명 등록·병합했습니다. PR 제목·본문은 제공된 초안을 사용했습니다. 실제 Git/PR 작업 경험이며 다인 팀 협업이나 Jira 실무 이력으로 확대하지 않습니다. [Ubuntu 원본 요약](../artifacts/reproductions/ubuntu-9c55480/summary.json) · [사용자 실행 보고](../artifacts/learning/step45-review.json) · [병합 확인](../artifacts/learning/step49-review.json).

Docker는 GitHub Actions에서 실행됐고 사용자는 성공 Summary 화면을 확인했습니다. 직접 로컬 Docker 실행과 구분합니다. 프로젝트의 후속 고정 소스 `1744544`는 **컨테이너 366개 검사/skip 0, Dice 42/6, 정적·HTTP 검사**를 통과했습니다. 데이터셋 재학습·브라우저 조작은 이 Docker 검사에 포함되지 않습니다. [사용자 화면 확인](STEP_50.md) · [후속 Docker 실행](https://github.com/sokldjs554/pathology-edge/actions/runs/43070288195) · [로그·소스 대조](../artifacts/reproductions/docker-1744544/review.json).

## 완성된 작업대와 평가 범위

이 절은 프로젝트 산출물의 설명입니다. 앞 절에서 확인한 개인 실행 범위와 별개로, 원래 학습·IHC 기준선·WSI exporter·웹 구현 전체를 개인 직접 작성·직접 실행 실적으로 돌리지 않습니다.

### 원래 TNBC 경계 실험과 데모

TNBC v1.1의 512×512 이미지·이진 핵 마스크 50쌍을 폴더 그룹 단위 train 33/validation 10/test 7로 나눴습니다. 총 11그룹이며 test는 2그룹입니다. 공식 설명의 환자 수와 별개로 독립 환자 명부가 없어 `Slide_01..11` 그룹을 사용한 한계가 있습니다. 원래 모델의 epoch·threshold는 validation으로 선택했습니다.

| 원래 TNBC test 7장/2그룹 | 전체 Dice | 경계 Dice | 내부 Dice | CPU ms/장 |
|---|---:|---:|---:|---:|
| TinyUNet 무겹침 | 0.5580 | 0.4918 | 0.5729 | 57.2 |
| 같은 모델 겹침+병합 | 0.5608 | 0.5273 | 0.5696 | 309.3 |

경계 Dice는 약 +0.0355, 전체는 +0.0028이지만 내부는 하락했고 시간은 약 5.4배였습니다. 그룹 10의 전체 Dice는 0.5187→0.5003으로 하락, 그룹 11은 0.6104→0.6415로 상승했습니다. 공개 데모는 사전 계산 결과를 표시하며 브라우저에서 새 학습·추론을 하지 않습니다. [전체 평가](../artifacts/evaluation.json) · [원래 프로토콜](../artifacts/protocol.json) · [연구 기록](RESEARCH.md).

사용자는 직접 작성한 Dice로 저장 점수 **42/42·평균 6/6 일치**를 확인했습니다. 그룹 함수로 실제 50레코드·11그룹에서 누수 없음도 확인했고, 별도 제공 명령으로 저장된 이미지 해시 50개가 split을 넘지 않는지 검사했습니다. 후자는 원본 이미지를 새로 해싱하거나 해시 검사 코드를 직접 작성한 작업은 아닙니다. [Dice 실행 보고](../artifacts/learning/step05-review.json) · [그룹 검사](../artifacts/learning/step10-review.json) · [해시 문자열 검사](../artifacts/learning/step12-review.json).

### 실제 WSI 탐색과 제한된 ROI 예측

CC0 `CMU-1-JP2K-33005.svs`, **46,000×32,893, 0.499µm/px** 원본을 대상으로 전체 다중 해상도 탐색 화면을 제공하고, 모델은 사전 선택한 **3개 1024² ROI**에만 실행했습니다. 분석 영역은 원본 파일 면적의 약 **0.2079%**이며 조직 면적 비율이 아닙니다. 정답 핵 마스크가 없어 이 WSI의 Dice·정확도 개선은 평가하지 않았습니다.

원본 좌표→분석 ROI→같은 위치의 두 예측→경계의 추가/제거 픽셀→억제/유지 후보와 원 패치를 추적할 수 있습니다. ROI warm CPU 중앙값은 무겹침 0.297–0.329초, 겹침 1.249–1.899초였습니다. 전체 WSI 처리 시간으로 환산하지 않습니다. [실험·좌표·원본](WSI_EXPERIMENT.md) · [WSI 실행 결과](../artifacts/wsi/experiment.json).

### IHC 정답 중심점 조건 분류

Patherea Breast-P1의 실제 Ki67 자료 **29case·1,330patch·19,972점**을 사용한 별도 기준선입니다. 제공된 정답 중심의 반경 3·7px에서 RGB/HSV/OD의 **색상 통계 40개**를 추출하고, training-only 표준화와 로지스틱 회귀로 종양+/종양−/비종양+/비종양−를 분류합니다. 화면의 48px crop을 입력으로 학습하는 CNN이 아닙니다.

저자 fold 1 test를 고정하고 train/validation/test를 15/4/10case로 분리했습니다. **test 10case·6,419세포의 macro-F1 0.600906, accuracy 0.703692**, 양성 비종양 F1 0.205650입니다. 정답 중심의 주석 세포에서 계산한 종양 양성률의 case별 평균 절대오차는 **7.686%p**입니다. 자동 세포 검출·검출 누락·전체 WSI Ki67 지수·임상 assay 정확도는 평가하지 않았습니다. 모델 점수는 보정된 임상 신뢰도가 아닙니다. [실험 보고](IHC_EXPERIMENT.md) · [원시 결과](../artifacts/ihc/results.json) · [데이터 출처](https://huggingface.co/datasets/ds2268/patherea), CC BY-NC 4.0.

## 최신 추가 검증 — 사용자 직접 실행과 구분

요청에 따라 개발 환경에서 자동 실행하고 원본을 독립 검산한 결과입니다. 사용자가 직접 실행하거나 새 결과를 검토 완료한 것으로 기록하지 않습니다.

| 추가 작업 | 실제 결과 | 근거·해석 |
|---|---|---|
| 보정 head 3개 paired seed, 총6모델 새 학습 | TNBC validation10장 전체 평균0.555994→0.576699, 쌍별+0.020706; 전체3상승, 경계2상승·1하락 | [3개 seed 보고서](REFINEMENT_REPEATS_RESULTS.md). 사용자 Codespaces 단일 seed와 합산하지 않음 |
| 고정 사용자 모델의 MoNuSeg 외부 추론 | 공식test14ROI·14TCGA case 전체0.551974→0.534943, 경계0.563794→0.546988; 전체13장 하락 | [외부 평가·실패 그림](EXTERNAL_MONUSEG_VALIDATION.md). TNBC에서 고른 threshold0.35 고정, 외부 재학습/조정 없음 |
| 외부 결과 감사 | 28개 원본 TIFF/XML,14개 정답 변환,84평가 영역·6평균·차이·상하락 집계 확인 | [원본·검증](../artifacts/experiments/external-monuseg-20261111/audit.json). XML rasterization은 공식 MATLAB 동등성 주장 없음 |
| 전체 WSI·임상 검증 자원 대조 | 공개 데이터 주석 범위와 기존 WSI의 정답 부재를 확인하고 실행 조건 문서화 | [현재 상태](CLINICAL_WSI_VALIDATION_STATUS.md). **두 검증 모두 미실시**; 완료 성과로 쓰지 않음 |
| PanopTILs 실제 WSI 연결 ROI 평가 | 공개 WSI에서3case의 영역을 읽고 고정 모델 평가, 유효 영역 Dice0.479080→0.435576 | [좌표·부분 주석·실패 보고](PANOPTILS_WSI_PROBE.md). 평가 가능 픽셀은 각1024²의2.96–3.75%, 픽셀 정렬·MPP 차이 있음 |
| BCData 외부 IHC 전이 점검 | 10ROI·제공 종양 중심1,376개, accuracy31.61%, ROI 양성률 MAE24.26%p | [실패·조건 보고](EXTERNAL_BCDATA_VALIDATION.md). 자동 검출·환자 독립성·임상 검증 아님. 데이터 재배포 제외 |

이 추가 근거를 포함하면 연구 결론은 “같은 TNBC 검증셋의 여러 seed에서 전체 Dice가 개선됐지만, 외부 MoNuSeg에서는 성능이 낮아졌다”입니다. 외부 검증을 성공적인 일반화 입증으로 바꾸지 말고, 검증을 확대해 한계를 발견한 사례로 설명해 주세요. 외부14장은 전체 WSI가 아닌1000×1000 주석 ROI이며, TNBC와 동일한 전체RGB 파일은 없지만 환자 대응표가 없어 환자 수준 독립성을 완전히 증명하지는 못했습니다.

## 사용자가 직접 확인·설명한 범위

사용자는 안내된 화면과 질문을 바탕으로 아래 내용을 확인했습니다. 제품 전체 UX 검증, 모든 브라우저·배율 검증, 전문가 병리 판독으로 확대하지 않습니다. 상세 원문과 받은 도움은 [기여 기록](CONTRIBUTIONS.md)의 연결된 step별 JSON에 남아 있습니다.

- TNBC `10_1`의 같은 위치에서 국소 경계 Dice 0.546→0.433의 악화, `11_1`의 0.626→0.854 개선, 변경 픽셀 강조 끄기/켜기, 확대 화면의 드래그·두 손가락 스크롤 동기 이동을 보고했습니다.
- 전체 평균 상승과 개별 이미지 악화가 동시에 가능하고, 경계/내부 결과를 구분해야 한다고 설명했습니다. 픽셀 변화 수를 추가 검출 핵 개수로 해석하지 않았습니다.
- NMS의 두 핵 과소 집계 반례와 OR→AND 변경 시 같은 핵의 조각이 남는 과대 집계 가능성을 설명했습니다. 화면의 억제/유지 대응만으로 실제 같은 핵임을 확정할 수 없다고 구분했습니다.
- WSI R1 이동, 같은 위치 경계, 후보 `#1302→#1107`와 원 패치 `144→128`, 확대 이동을 확인했습니다. R1의 추가 전경 347px를 정확도 개선으로 주장할 수 없고 전체 탐색과 ROI 분석이 다르다고 설명했습니다.
- IHC 첫 사례의 종양→비종양 분류 오류, 양성 종양 1개가 양성 비종양으로 바뀔 때 양성률 분자·분모가 함께 1씩 줄어드는 점, 7.686%p의 주석 세포 조건, 보정되지 않은 모델 점수의 의미를 설명했습니다.

후속 사용자 CNN/ViT 저장 결과로 최대 하락 `09_1`, 최대 상승 `09_6`의 동일 ROI 오류 그림과 FP/FN 수치를 생성·감사했습니다. 전체 `09_1`은 FP 감소·FN 증가로 전체 Dice가 하락했고, `09_6`은 FP/FN이 모두 감소했습니다. 이 보고서는 완료했지만 **사용자가 새 오류 그림을 직접 검토·해석했다는 응답은 아직 확인되지 않았습니다.** [실제 사용자 오류 보고서](USER_RESEARCH_AUDIT.md) · [동일 ROI HTML](../artifacts/experiments/user-cnn-vit-errors-20261112/index.html). 토큰화가 오류의 원인이라는 인과 결론도 없습니다.

## 이력서에 사용할 수 있는 문장 초안

아래 문장은 근거가 있는 범위의 초안입니다. 원하는 분량에 맞춰 3–4개를 선택하되 validation 조건과 제공 구현 활용을 삭제해 단독 개발·독립 성능 검증으로 읽히게 만들지 않습니다.

- **병리 핵 분할 연구 프로젝트:** 제공된 학습·평가 파이프라인을 활용하고 좌표 변환, Dice 평가, 그룹 누수 검사, soft Dice 손실, WSI ROI 좌표 연결과 153파라미터 잔차 보정 모듈을 직접 작성·검증.
- **손실 함수 비교 실험:** 직접 구현한 soft Dice를 BCE와 결합해 CPU에서 3개 seed·6회 학습 수행. 같은 검증 10장의 선택 Dice 평균 0.518215→0.546238, 쌍별 평균 +0.028023을 확인하고 독립 test 평가와 구분.
- **CNN–ViT 비교와 결과 보존:** 제공된 TinyUNet·소형 ViT를 고정 조건에서 비교해 검증 전체 Dice 0.503768→0.557644, 10장 중 7장 상승·3장 하락 확인. 원본 로그·모델·예측을 제출해 60개 평가 영역 재계산과 해시 대조 근거 확보.
- **모델 구성요소 구현·비교:** 작은 공간 잔차 head를 작성해 기준 ViT와 한 seed에서 비교. 검증 전체 Dice 0.570565→0.590386, 경계는 0.558802→0.559040이며 CPU 파이프라인 비용 약 27.50% 증가를 함께 기록.
- **성능·재현성 검토:** Python/C++ 패치 추출 8조건·72회 측정, Ubuntu 고정 소스 재현과 191개 테스트 통과 보고, 재현 로그의 GitHub PR 생성·병합 수행. 2048² 입력에서 관찰한 패치 추출 1.96배를 전체 추론 가속과 구분.

포트폴리오는 문제와 데이터 → 직접 작성 범위 → 사용자 실행 비교표 → 좋아진/나빠진 실제 사례 → 비용과 재현 근거 → 한계 순서가 적합합니다. 가장 강한 개인 구현 사례는 soft Dice와 LocalResidualHead이며, WSI 좌표 연결과 누수 검사를 보조 사례로 연결할 수 있습니다.

## 작성 시 반드시 유지할 한계와 현재 미확인 항목

- **원래 TNBC test는 7장·2그룹입니다.** 후속 손실·CNN/ViT·보정 비교는 이미 반복 사용한 validation 10장·2그룹의 epoch/threshold 선택 결과입니다. 원래 test도 이후 결과를 상세히 열람했으므로 새 미열람 최종 검증으로 부르지 않습니다.
- **실험별 seed를 분리합니다.** 사용자 손실 비교 3개 seed, 사용자 CNN/ViT 1개 seed, 개발 참고 CNN/ViT 3개 seed, 사용자 보정 head 1개 seed, 별도 개발 환경의 보정 head 3개 seed가 확인 범위입니다. 같은 seed의 다른 환경 실행을 독립 seed로 추가하지 않습니다.
- **후속 범위를 구분합니다.** 추가 보정3개 seed, MoNuSeg 외부14ROI, PanopTILs WSI 연결3ROI, BCData 외부10ROI 평가는 개발 환경에서 실제 실행·감사했습니다. 사용자 업로드는 조사 문서였으며 실제 공개 입력은 별도 확보했습니다. 사용자는 현재 보유 자료가 그 조사 문서뿐이라고 확인했습니다. 임상 검증과 전체 WSI 핵 정답 기반 검증은 필요한 자료를 확보하지 못해 미실시입니다. 새 후속 결과의 사용자 직접 검토도 아직 확인하지 않았습니다.
- **전체 WSI 탐색과 분석은 다릅니다.** 현재 모델 분석은 3개 ROI뿐이며 GT 없는 예측 차이입니다. IHC는 제공 중심의 색상 통계 분류이고 자동 핵 검출·딥러닝 IHC·전체 슬라이드 임상 정량이 아닙니다.
- **시간·메모리 수치는 측정 구간과 환경의 관찰값입니다.** 공유 CPU에서 얻은 순차 실행 결과이며 모델 로딩·I/O·정답 평가 등의 포함 여부를 확인해야 합니다. RSS는 전체 프로세스 최대값이지 모듈 단독 추가 메모리가 아닙니다.
- **개인 정보는 미확인입니다.** 이름·연락처·학위·전공·졸업 여부·논문·기존 고용 경력·지원 자격·프로젝트 전체 시작/종료일은 이 저장소만으로 확정할 수 없습니다. 관련 전공·학력·전문연구요원 자격을 추정해 쓰지 않습니다.
- **공고 조건은 서로 섞지 않습니다.** [사람인 55507517](https://m.saramin.co.kr/job-search/view?cn=job-industry&cns=recently-list&rec_idx=55507517&referNonce=&t_category=job_recruit&t_content=generic)의 확인된 마감은 2026-12-06 23:59입니다. C++/Ubuntu 등 상세 기술 목록의 추가 근거인 [병역일터 별도 공고](https://work.mma.go.kr/caisBYIS/search/cygonggogeomsaekView.do?byjjeopche_cd=&cygonggo_no=2000001538893&menu_id=m_m7_1)의 전문연구요원 조건·마감은 사람인 공고에 적용하지 않습니다. [공고 대조와 출처](JOB_MATCH_2026-11-10.md).

현재 확인된 장점은 작은 구성요소를 직접 구현하고, 실제 실행 결과를 제출하며, 평균과 실패 사례·속도 비용·데이터 분리·주장 범위를 함께 설명할 수 있는 근거를 쌓았다는 점입니다. 연구 경력·임상 전문성·전체 시스템 단독 개발 실적으로 바꾸지 않습니다.

최신 코드 검증: [Ubuntu CI405개 통과](https://github.com/sokldjs554/pathology-edge/actions/runs/43082861969), 기존 Dice42개·평균6개 재계산 일치, 기존 보호 파일2731개 SHA변경0. 새 브라우저 검사·배포나 사용자 직접 실행 실적으로 바꾸지 않습니다. [정확한 검증 범위](../artifacts/experiments/additional-validation-review.json).
