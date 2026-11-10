# 39단계: 비교 학습 결과의 해석 범위 설명

상태: **완료 — 사용자 설명 확인**. 38단계의 12개 검사와 `all_passed: true` 보고를 받아 저장 조건·파일 대조를 완료했습니다. 확인 근거는 사용자 실행 출력이며 Codex가 Codespaces 파일에 직접 접근한 것은 아닙니다. [검사 보고](../artifacts/learning/step38-review.json).

## 확인한 사용자 설명

“PyTorch로 soft Dice 손실 함수를 직접 구현하고 BCE만 사용한 모델과 비교한 결과, 검증 Dice가 0.521171에서 0.535783으로 상승했지만, 학습 seed 1개와 검증 이미지 10장에서 epoch와 threshold를 선택한 결과이므로 성능 개선의 일반화 여부는 추가 검증이 필요합니다.”

직접 작성한 계산·관찰 점수·검증 선택과 한 seed의 한계를 정확히 구분했습니다. 모델 전체 설계·새 test 성능 개선으로 확대하지 않았습니다. [검토 기록](../artifacts/learning/step39-review.json). 다음은 [40단계 WSI ROI 좌표 연결](STEP_40.md)입니다.

## 완료한 질문

**이번 실험을 면접에서 설명한다면 어떻게 말하겠어요? 직접 작성한 부분, 관찰한 검증 점수 변화, 결과 해석의 한계를 포함해 한 문장으로 정리해 주세요.**

답변 검토를 마쳤으며 이 해석을 반복 제출할 필요는 없습니다.

## 참고할 사실

| 항목 | 확인한 내용 |
|---|---|
| 학습 조건 | seed 20261107 하나, train 33장, validation 10장, 같은 손실 외 설정·기록된 환경 |
| 모델 선택 | 두 방식 각각 validation 10장으로 epoch와 threshold를 선택 |
| BCE-only 선택 결과 | epoch 12, threshold 0.5, validation Dice 0.521171 |
| BCE + 사용자 Dice 선택 결과 | epoch 13, threshold 0.35, validation Dice 0.535783 |
| 관찰한 차이 | 선택된 validation Dice +0.014612, 이번 학습 소요 시간 +5.66초 |
| 파일·기록 확인 | 두 실행의 manifest·소스 기록·파일 해시·16 epochs·최선 선택 검사가 모두 true |
| 추가 평가 | 이 비교에서 새로운 test 평가·다중 seed 반복·외부 데이터 검증을 수행하지 않음 |

자료·질문과 검사 명령은 Codex가 제공했습니다. 사용자 U51은 본인의 해석 답변을 받아 완료로 기록했습니다. U47은 직접 작성한 soft Dice 계산, U48·U49는 두 학습 실행, U50은 저장 기록·파일 대조로 구분합니다.

[두 학습 결과](STEP_38.md) · [기여 기록](CONTRIBUTIONS.md)
