# 연구·검증 이력

README에는 목적·역할·대표 결과와 시작 경로를, RUNBOOK에는 현재 실행 절차를 둡니다. 이 문서는 누적 연구와 과거 검사 근거를 찾기 위한 색인입니다. **실행 완료와 성능 기준 통과, 직접 수행과 후속 자동 실행을 구분합니다.**

## 버전과 공개 범위

| 범위 | 기준 소스 | 상태·근거 |
|---|---|---|
| 공개 작업대·main의 이전 상태 | `ff486a3be0f01fcdc98e9aad5dd67d6a7424d39e` | TNBC·WSI·정답 중심 조건 IHC, NuCLS·U86 전달 자료까지. 아래 원문에 당시 전체 내용 보관 |
| 후속 연구의 고정 상태 | `095b0196585c05b256942bfe6bf889c3668a136c` | 자동 패치 검출·분류, 사전학습·새 외부 평가, U106까지의 확인. [Draft PR #2](https://github.com/sokldjs554/pathology-edge/pull/2) |
| 공개 UI 배포 기준 | `b5024b0`의 UI 파일 | [WSI/UI 배포 검증](WSI_REVIEW.md). 이후 연구·문서 커밋을 새 화면 배포로 해석하지 않음 |

2026-11-15의 문서 정리는 소스·모델·측정 결과·공개 `dist/` 파일을 변경하지 않습니다. 현재 브랜치 CI 상태는 [main](https://github.com/sokldjs554/pathology-edge/actions/workflows/ci.yml?query=branch%3Amain)과 [research](https://github.com/sokldjs554/pathology-edge/actions/workflows/ci.yml?query=branch%3Afeat%2Fauto-ki67)에서 각각 확인합니다.

## 연구 흐름

| 단계 | 수행한 일·결과 해석 | 상세 근거 |
|---|---|---|
| 병리 경계 기준 실험 | TNBC50장·11그룹 분리, 같은 모델의 무겹침/겹침·전체/경계/내부·비용 비교. test7장·2그룹·한 seed의 제한 | [초기 검토](REVIEW.md), [저장 평가](../artifacts/evaluation.json) |
| 작업대 UI | 원본 위치와 오버레이·후보 출처·개선/악화·처리 비용 연결, 확대 후 이동 오류 수정 | [UI 조사](UI_REVIEW.md), [경계 사례](INTERVIEW_UI.md), [이동 수정](PAN_FIX.md) |
| WSI/IHC | 실제 WSI 다중 해상도 탐색과 ROI3개 예측, 별도 Patherea 정답 중심 조건 분류 | [WSI](WSI_EXPERIMENT.md), [IHC](IHC_EXPERIMENT.md) |
| 개인 구현·반복 학습 | 핵심 코드7개, 사용자 BCE/soft Dice 세 paired seed, Ubuntu 재현과 Git 로그 | [직접 수행 기록](CONTRIBUTIONS.md), [손실 실행 요약](../artifacts/learning/step42-user-summary.json) |
| C++·CNN/ViT | 사용자8조건·72회 추출 측정, 소형 CNN/ViT 및153파라미터 잔차 head 비교, 원본 ZIP 감사 | [사용자 연구 감사](USER_RESEARCH_AUDIT.md), [보정 감사](USER_REFINEMENT_AUDIT.md) |
| 분할 외부 평가 | MoNuSeg14 ROI·NuCLS51시야에서 보정 효과 악화, 원본 WSI/주석 연결·36쌍 격자 처리 | [MoNuSeg](EXTERNAL_MONUSEG_VALIDATION.md), [원본 대조](ORIGINAL_ANNOTATION_EVALUATION.md), [NuCLS51](NUCLS_GRID_ALIGNMENT.md) |
| IHC 외부 평가 | BCData402장 정답 중심 조건 분류 실패와 원자료 감사, 본인109/367 두 장 재실행·해석 | [BCData](BCDATA_FULL_TEST.md), [직접 수행 기록](CONTRIBUTIONS.md) |
| 자동 후보·CNN·학습 중심 | RGB에서 후보를 만들고 분류, 제거·재현율 조건·후보 통합·중심 재학습 비교. 일부 지표 개선과 FP/FN·seed 조건 미달을 함께 보존 | [자동 분석](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/AUTO_KI67_EXPERIMENT.md), [재현율 진단](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_RECALL_DIAGNOSIS.md), [후보 통합](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_UNION_GATE.md) |
| 위치·정렬·추가 학습 | uint8 점수 정렬 수정, 위치 보정·추가 학습·정규화·감독 신호 진단. 각 연구의 진행/채택 조건을 유지 | [위치 보정](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_LOCALIZATION.md), [재학습](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_CENTER_REFIT.md), [정규화](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_NORMALIZED.md), [감독 신호](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_SUPERVISION.md) |
| 최종 고정 비교 | ImageNet 특징/무작위 고정 특징×3seed, 실제 검출 중심의 분류, 새 DeepLIIF597장 평가. 내부 채택0/3·기존test1/3·BCData 재평가3/3·새 외부1/3. 안정적 종합 개선 미달로 종료 | [최종 조건·전체 수치](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_FINAL_TRANSFER.md) |

사전학습 미사용이라는 초기 설명은 공개 TNBC·소형 ViT 실험의 범위입니다. 최종 SqueezeNet 연구에서는 실제 ImageNet 가중치를 사용했습니다. 임상 검증·전체 WSI의 모든 핵 정답 기반 검증은 수행하지 않았습니다. WSI와 연결한 **주석 ROI** 평가를 전체 WSI 검증으로 확대하지 않습니다.

<a id="verification"></a>
## 검증 이력 — 버전별 결과

테스트 개수는 서로 다른 소스·환경의 기록입니다. 합계나 현재 버전의 검사 수로 사용하지 않습니다. 아래 최신 두 소스의 통과 수는 GitHub 원본 job 로그에서 확인했습니다.

| 소스·시점 | 검사 결과 | 수행·근거 |
|---|---|---|
| main `ff486a3` | **462 passed**, Dice42/42·평균6/6, JS·정적 데모 검사 성공 | [CPU CI43269595759](https://github.com/sokldjs554/pathology-edge/actions/runs/43269595759) |
| research `095b019` | **799 passed**, Dice42/42·평균6/6, JS·정적 데모 검사 성공 | [CPU CI43625358925](https://github.com/sokldjs554/pathology-edge/actions/runs/43625358925) |
| 클래스 대조 검사 수정 당시 | 374 passed | [당시 근거](../artifacts/learning/step58-class-match-fix.json) |
| 보정 모듈 연결 / 고정 소스1744544 Docker | 일반366개, 사용자 계약13개는 별도 기록 | [연결 감사](../artifacts/learning/step57-accepted-review.json), [후속 연구](RESEARCH_FOLLOWUP.md) |
| 반복·원본 보관·오류 분석 확장 | 331 passed | [당시 근거](../artifacts/experiments/final-followup-checks/summary.json) |
| C++·ViT 첫 확장 | 269 passed | [당시 근거](../artifacts/experiments/cpp-vit-checks/summary.json) |
| 소스20cc5ac Docker | 컨테이너201개·skip0, 저장 Dice·C++·정적/HTTP 확인 | [원격 실제 실행](../artifacts/learning/step50-review.json). 본인 수행은 CI 성공 화면 확인 |
| 소스9c55480 Ubuntu | 본인191개·skip0, C++ 재빌드·저장 Dice·정적 데모 | [원본 재현 summary](../artifacts/reproductions/ubuntu-9c55480/summary.json). 로컬 Docker 빌드와 구분 |
| 공개 UI 버전7 | Chromium·WebKit 각각46개 실제 조작, 기존 좌표5개 검사 | [WSI/UI 보고](WSI_REVIEW.md). 정적 검사·개인 화면 확인과 구분 |

초기 Docker 공간 부족·명령 부재와 후속 원격 Docker 성공도 [당시 실행 안내 원문](history/main-RUNBOOK-20261115.txt)에 남아 있습니다. 과거의 실패를 지우거나 현재 실패로 오해하지 않도록 버전·실행 주체를 함께 봅니다.

개별 코드의 12·1·20·18·8·8·13개 테스트는 각각 해당 시점의 사용자 실행 보고입니다. 함수 본문 작성, 제공 테스트 실행, 독립 검산을 구분한 원문은 [CONTRIBUTIONS](CONTRIBUTIONS.md)와 `artifacts/learning/`에 보존합니다. 문서를 읽거나 새 검사 명령을 안내했다는 이유로 개인 완료 기록을 늘리지 않습니다.

## 수정 전 문서 원문

아래 `.txt`는 Markdown 원문을 **바이트 그대로 보관한 파일**입니다. 문장·수치·진행 보고를 삭제하지 않았습니다. 당시 ‘최신’·‘예정’·‘미실시’는 해당 버전의 표현이며, 현재 사용법은 [RUNBOOK](RUNBOOK.md), 현재 범위는 [README](../README.md)를 따릅니다. 원문의 상대 경로는 아래 고정 커밋의 저장소 루트 기준입니다.

| 원문 | 고정 소스의 렌더링된 문서 |
|---|---|
| [main README](history/main-README-20261115.txt) | [ff486a3 README](https://github.com/sokldjs554/pathology-edge/blob/ff486a3be0f01fcdc98e9aad5dd67d6a7424d39e/README.md) |
| [main RUNBOOK](history/main-RUNBOOK-20261115.txt) | [ff486a3 RUNBOOK](https://github.com/sokldjs554/pathology-edge/blob/ff486a3be0f01fcdc98e9aad5dd67d6a7424d39e/docs/RUNBOOK.md) |
| [research README](history/research-README-20261115.txt) | [095b019 README](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/README.md) |
| [research RUNBOOK](history/research-RUNBOOK-20261115.txt) | [095b019 RUNBOOK](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/RUNBOOK.md) |

[원문별 크기·SHA256](history/manifest-20261115.json). 기존 실험 원본 ZIP과 본인 제출 코드는 변경하지 않았습니다.

## 문서 구성에서 참고한 프로젝트

사용자가 제시한 비교에 따라 개요·예제·역할·실행 경로를 앞에 배치했습니다. 아래는 연구 도구의 구성 참고 링크이며 회사 합격자의 저장소라는 의미가 아닙니다. 이번 변경에서 이들 모델을 설치·재현한 것도 아닙니다.

[HoVer-Net](https://github.com/vqdang/hover_net) · [StarDist](https://github.com/stardist/stardist) · [TIAToolbox](https://github.com/TissueImageAnalytics/tiatoolbox) · [MONAI](https://github.com/Project-MONAI/MONAI) · [CellViT](https://github.com/TIO-IKIM/CellViT) · [Cellpose](https://github.com/MouseLand/cellpose) · [HistoQC](https://github.com/choosehappy/HistoQC) · [QuPath](https://github.com/qupath/qupath).
