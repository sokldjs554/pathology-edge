# 에이비스 지원 공고 기준과 프로젝트 근거

기준 정정: **2026-11-18 KST**. 기준은 지원자가 제공한 **「AI연구원 채용 (전문연구요원 지원 가능)」의 주요업무·자격요건·우대사항·기술 스택 캡처**다. 아래는 그 캡처에서 읽은 항목이며, 다른 경력 공고·회사 논문·검색 요약의 조건을 합치지 않았다. 캡처 원본은 대화에 제공됐으며 저장소에 별도 보관돼 있다고 주장하지 않는다.

과거 [공고 대조](JOB_MATCH_2026-11-10.md), [C++·ViT 비교](CPP_VIT_COMPARISON.md), [회사·IHC 조사](AIVIS_IHC_FEASIBILITY.md)에는 ViT·석박사·학술 실적을 지정 공고의 명시적 우대사항으로 잘못 기재했다. 이 해석을 정정한다. 기존 실험·사용자의 선택 및 실행 기록은 유지한다. ViT 비교는 최초 요청의 조건부 모델 비교와 아래 업무 ⑤에 연결되는 경험이다. 당시 잘못된 안내를 따라 선택한 사실을 사용자의 오류로 돌리지 않는다.

## 주요업무와 근거

| 캡처의 주요업무 | 실제 프로젝트 근거 | 설명할 범위 |
|---|---|---|
| ① WSI를 포함한 병리 영상 데이터 기반 AI 모델 연구·개발 | [WSI ROI 읽기·좌표 연결](../src/pathology_edge/wsi_roi.py), [WSI 실험](WSI_EXPERIMENT.md), 공개 슬라이드 탐색·3개 ROI 예측 | WSI 전체 탐색과 일부 ROI 분석. 전체 WSI 모든 핵의 정답 검증은 미실시 |
| ② Classification, segmentation, detection 등 모델 설계 및 실험 | [TNBC 기준 모델](../src/pathology_edge/model.py), [정답 중심 IHC 분류](IHC_EXPERIMENT.md), [후속 자동 검출·분류 연구](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_FINAL_TRANSFER.md) | 공개 IHC는 색상 통계+로지스틱 회귀. 후속 CNN 검출·분류와 구분하며 전체를 본인 단독 구현으로 표현하지 않음 |
| ③ 전처리, 패치 추출, 학습 데이터 구성 | [데이터·조직 검사](../src/pathology_edge/data.py), [패치 생성·결합](../src/pathology_edge/patches.py), [직접 그룹 누수 검사](../src/pathology_edge/learner_split.py) | TNBC 33/10/7장 분리, 그룹·해시 검사. 그룹 ID만으로 환자·기관 독립성을 입증하지 않음 |
| ④ 학습, 성능 평가, 오류 분석 및 개선 | [직접 soft Dice](../src/pathology_edge/learner_losses.py), [직접 잔차 head](../src/pathology_edge/learner_refinement.py), [원본 비교 감사](USER_RESEARCH_AUDIT.md), [보정·외부 결과](USER_REFINEMENT_AUDIT.md) | 검증 점수 상승과 개별·외부 악화를 함께 설명. 선택에 쓴 검증 점수를 독립 test 결과로 바꾸지 않음 |
| ⑤ 최신 AI 연구 동향 조사 및 모델 적용 | [소형 ViT 비교와 논문 출처](CPP_VIT_COMPARISON.md), [ImageNet 고정 특징·무작위 특징 대조](https://github.com/sokldjs554/pathology-edge/blob/095b0196585c05b256942bfe6bf889c3668a136c/docs/KI67_FINAL_TRANSFER.md) | 논문 아이디어 적용·비교. 공식 논문 재현이나 공고의 특정 모델 필수조건으로 표현하지 않음 |
| ⑥ 재현성 확보를 위한 실험 관리 및 개발 협업 | [실행 안내](RUNBOOK.md), 모델·소스 해시, 고정 패키지, [사용자 PR #1](https://github.com/sokldjs554/pathology-edge/pull/1), [기여 기록](CONTRIBUTIONS.md) | 직접 실행·Git 작업과 원격 CI 화면 확인을 구분. 협업 사례는 [별도 근거 정리](COLLABORATION_EXPERIENCE.md) 참고 |

## 자격요건

| 캡처의 요건 | 연결되는 근거·확인 범위 |
|---|---|
| 컴퓨터공학·AI·전기전자·수학·통계·의공학 또는 관련 전공 | 전공·학력은 지원 서류로 확인하며 저장소 코드만으로 판정하지 않음 |
| Python 및 PyTorch 기반 딥러닝 모델 구현 경험 | 직접 작성한 soft Dice·잔차 head, 제공 학습기를 활용한 비교 학습 |
| 영상 데이터 기반 AI 모델의 기본 이해 | 좌표·배율·마스크·패치 경계·FP/FN·평가 범위 설명 기록 |
| Classification, segmentation, detection 등 모델링 과제 경험 | 위 업무 ②의 실제 모델·실험. 세 과제 모두를 새로 단독 구현해야 한다는 의미로 강화하지 않음 |
| 연구 설계·구현·실험·검증 과정 경험 | 조건 고정 비교, 세 seed 실행, 지표 검산, 실패 사례·일반화 한계 해석 |
| GitHub, Jira 등 개발 협업 도구 경험 | Git commit/push·PR 생성/병합 근거. Jira 사용 경험은 확인되지 않았으며 필수 추가 과제로 취급하지 않음 |

## 우대사항·기술 스택

캡처의 우대사항은 **Python·PyTorch / OpenCV·image processing 라이브러리 / Ubuntu·Docker / Git·GitHub**다. 기술 스택에는 **C++·multi-threading·Computer Vision**도 명시돼 있다. 각 기술의 실제 코드와 본인 수행 범위는 [기술 설명 자료](ENGINEERING_REVIEW.md)에 연결했다.

석박사·논문 실적·ViT를 명시적 우대사항으로, 임상 검증·전체 WSI 정답 기반 검증을 지원 전 필수조건으로 추가하지 않는다. 회사 제품·공개 연구는 업무의 맥락이며 지원자의 프로젝트에 제품 수준 정확도나 임상 유효성을 부여하지 않는다. 접수 일정·학위의 세부 지원 조건은 이 기술 대조표로 확정하지 않고 실제 지원 페이지에서 확인한다.

## 현재 보완 상태

| 작업 | 상태 | 본인 확인 여부 |
|---|---|---|
| 공고 기준·과거 설명 정정 | 문서 반영 | 문서 반영 완료. 본인의 문서 전체 재독 여부는 별도 확인하지 않음 |
| 공개 데모·저장소 버전 안내 | [현재 버전 안내](PUBLIC_DEMO_VERSION.md)와 README·RUNBOOK에 반영 | UI PR #3으로 main에 통합. 이번에 사용자가 다시 실행한 것으로 기록하지 않음 |
| C++·스레드·OpenCV·Docker 설명 | 자료 준비·세 핵심 설명 확인 | GIL/atomic, 연결 성분, Docker 재현성 설명 확인. 새 실행·전체 코드 검토는 아님 |
| 협업 경험 설명 | Git 근거·초안 정리, 역할 사실관계 확인 | 본인·동기 역할과 Notebook·오류 메시지 공유를 본인이 확인. 전체 문구 최종 승인·대회 자료 독립 검증은 아님 |

[이번 본인 응답과 확인 범위](USER_REVIEW_20261118.md)를 기록했다. 본인 직접 작성 7개 항목과 기존 완료 기록을 유지한다. 설명 자료 작성만으로 새 구현·실행·검토를 사용자 완료로 변경하지 않는다.
