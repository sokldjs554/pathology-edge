# C++ 성능 검토와 소형 ViT 비교 설계

사용자는 두 보완의 진행과 ViT 방향을 선택했습니다. 직접 수행하는 과제는 한 번에 하나씩 배정하며, 첫 과제는 C++ 성능 측정입니다. 면접 문장 작성은 보류합니다.

## 접근 선택

- C++: 기존 측정 스크립트 수정 대신 별도 실행기를 제공합니다. 원래 benchmark.json과 사용자 수정 코드를 보존합니다.
- ViT: CPU에서 실행할 수 있는 작은 ViT 기반 핵 분할 모델을 독립 구현합니다. 대형 사전학습 가중치를 받거나 IHC CNN으로 과제를 바꾸지 않습니다. 외부 가중치·새 의존성 없이 PyTorch의 attention 모듈을 사용합니다.
- 기존 TinyUNet과 같은 TNBC train33/validation10·128px crop·BCE+사용자 soft Dice·증강·Adam0.001·batch8·16epochs×20steps 조건을 사용합니다. seed20261113 하나를 사전에 고정합니다. 선택한 validation 점수의 탐색적 구조 비교이며 test 예측을 실행하지 않습니다.

## C++ 측정

새 `scripts/benchmark_cpp_review.py`는 기존 설치를 사용해 별도 `work/my-cpp-review.*` 폴더에 기록합니다. 합성 RGB512²/2048², 패치128/겹침64, Python과 C++1/2/4스레드를 비교합니다. 출력 일치 검사, 원본 코드·바이너리 해시, CPU/할당 정보, 원시 시간·집계·프로세스 메모리 범위를 보존합니다. 실패는 로그와 함께 비정상 종료하며 성공 수치를 임의로 생성하지 않습니다.

## ViT 모델과 비교

`SmallViTSegmenter`: 8px 토큰, 차원32, attention4heads, encoder2층, MLP64, dropout0. 128px 입력은256토큰입니다. 학습 위치 임베딩과 픽셀 로짓 복원 head를 사용합니다. 작은 크기 차이는 padding/좌표 복원으로 처리하며1024토큰을 넘는 입력은 거절합니다. 원논문의 대규모 분류 모델·최신 병리 foundation model을 재현했다고 부르지 않습니다.

별도 trainer·runner에서 기존 함수 `predict`, 데이터 무결성 검사, 사용자 손실을 재사용합니다. 원래 `train/evaluate/export`와 공개 모델·UI는 변경하지 않습니다. 양쪽 모델의 데이터 crop/augmentation 순서는 모델 초기화 RNG와 분리하며 추적 해시를 기록합니다. 모델 크기는 같다고 가정하지 않고 실제 파라미터 수·시간·메모리를 보고합니다.

최종 score는 각 모델의 모든 epoch×threshold(.35/.5/.65) 중 validation 이미지 평균 Dice의 최댓값입니다. 같은 점수라면 기존 규칙대로 먼저 관찰한 조합을 선택합니다. 두 모델 모두 총16epochs 학습합니다. 선택 checkpoint의 validation 전체·경계·내부 점수와 warmed pipeline 시간을 별도로 기록합니다. test7장은 기존 무결성 검사에서만 해시를 읽고 예측·평가하지 않습니다. 학습 시간은 학습·매epoch validation·checkpoint 쓰기이며 최종 상세 검토는 별도입니다.

결과가 더 나쁘더라도 구조·seed·epoch·threshold를 바꿔 좋은 결과를 고르지 않습니다. 이 조건에서의 작은 모델 비교이며 CNN/ViT 전반의 우열을 뜻하지 않습니다.

## 완료 기준

- 원래 모델·실험·데모 파일의 해시 보존.
- C++ 실제 측정과 실패/원본 보존 검증, 사용자는 실행·결과 제출 전까지 예정.
- ViT 좌표 복원·gradient·저장/복원·입력 계약 테스트와 전체 기존 테스트 통과.
- 합성 소규모 trainer 검사, 실제 고정한 한 쌍 학습과 저장 결과 감사. 테스트셋 예측 파일을 만들지 않음.
- 기존 Codespaces를 덮어쓰지 않는 SHA 고정 실습 수신 안내. 첫 과제만 안내하고 다음 단계는 보고를 받은 뒤 배정.

## 참고

[ViT 원논문](https://arxiv.org/abs/2010.11929), [PyTorch TransformerEncoder](https://docs.pytorch.org/docs/2.15/generated/torch.nn.TransformerEncoder.html). 논문은 이미지 패치를 토큰화하는 구조의 근거이며 작은 TNBC 학습에서의 성능 개선을 보장하지 않습니다.
