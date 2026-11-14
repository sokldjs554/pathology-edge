# 마지막 사전학습 중심 검출 비교

사용자는 1~4번을 마지막으로 시도하고 미달이면 마무리하도록 승인했다. 이전 재학습·정규화·손실·평활화 비교를 반복하지 않는다. 구현 선택은 아래와 같이 정하며 사용자 직접 설계·실행으로 기록하지 않는다.

## 범위와 선택

1. 실제 외부 사전학습: torchvision v0.20.1(commit3ac97aa9120137381ed1060f37237e44485ac2aa)의 SqueezeNet1.1 ImageNet1K_V1 공식 가중치. CPU·남은 저장 공간에 맞는 작은 모델이다. MobileNet/대형 foundation model 설치·fine-tuning은 자원과 새로운 의존성이 커 제외한다. 기존 자체 체크포인트 refit은 이미 했으므로 제외한다.
2. 학습 자료: 기존 Patherea train696/15케이스만 사용. 케이스를 균등 확률로 고르고 그 케이스 안에서 이미지를 균등 추출해 epoch당696회 학습한다. 원본 클래스·좌표·분할은 유지한다. 클래스/케이스 수·경계 근처 주석·가까운 주석 분포를 감사하되 임의로 주석을 삭제하거나 추가하지 않는다. 배경의 주석 완전성을 주장하지 않는다.
3. 자동 분석: 실제 검출 중심을 고정 CNN 분류기에 넣어 검출·4클래스 F1·케이스 양성률 MAE를 함께 평가한다. seed17/18/19는 기존 CNN13/14/15와 고정 대응한다. 이번에 분류기 선택/재학습은 하지 않는다.
4. 새 외부: 이미 형식만 조사한 DeepLIIF official test598 중 사전 제외한 형식 probe1을 뺀597장 전체. 512px 원영상과 제공 마스크의 연결을 재검증한다. all-cell Ki67 양음성 과제이며 종양 Ki67 임상 검증이나 WSI 전체 검증이 아니다. 기존 BCData133과 Patherea test407은 재사용 평가라고 표시한다.

## 실험 고정

- seed20261117/18/19, 두 arm(pretrained/random), 각24epochs. 무작위 arm도 encoder를 고정하므로 from-scratch full fine-tuning 대조군은 아니다.
- encoder는 공식 features와 동일하며 모든 가중치를 strict 검사한다. pretrained는 50개 feature tensor가 공식값과 같음을 기록한다. encoder 변화 없이 작은 FPN/원해상도 RGB decoder만 학습한다. 양쪽 decoder 초기값·표본 순서·증강은 seed별 동일하다.
- feature taps1/4/7/12(64/128/256/512channels), 각16채널 lateral Conv1x1+GroupNorm4+LeakyReLU.1; top-down bilinear 합산. 원해상도 RGB3→8 Conv3x3+GroupNorm2+LeakyReLU.1와 결합해24→16→16 Conv3x3/GN4/Leaky,Conv1x1→1. bias−2.19. ImageNet mean/std를 encoder에만 적용. 좌표 보존을 위해 RGB 리사이즈·center crop 없음.
- Adam.001,batch8,1thread/worker, pairedrot90/flips·perimageRGB.9~1.1. 기존 sigma2/radius6 maxGaussian와 center focal loss 유지. 학습 중 encoder 고정 및 유한성 확인.
- validation227/4케이스에서 각epoch 기존12threshold×3distance 설정 평가. 기존 FP/FN·재현율 채택 기준을 완화하지 않는다. eligible 최고 trial이 있으면 선택, 없으면 최고 case F1 diagnostic을 선택한다. tie 순서는 기존 trial_key.
- 선택과 가중치를 세 seed 모두 봉인한 뒤 validation/test/BCData/DeepLIIF 자동 분석을 실행한다. **채택 실패여도 diagnostic 평가를 실행**한다. 이것은 채택/성공을 뜻하지 않는다. 이전 실패 실험을 소급 변경하지 않는다.
- 외부 주 비교는 historicalA vs pretrainedB. random arm은 내부 validation에만 쓰는 사전학습 ablation이다. all3를 분모로 사용하고 실패 seed를 누락하지 않는다.
- DeepLIIF primary matching6px,secondary12px,참조 centroid/색상 규칙·597멤버 고정. 양성률은 GT+A 유효 동일 모집단; B 분모 소실은 실패로 기록. 두 반경을 사후 선택하지 않는다. 클래스 F1↑·검출F1↑·동일 모집단 MAE≤를 세 seed 모두 만족해야 이번 외부에서 일관된 개선으로 표현한다. 환자·기관 독립성/MPP 미확인 한계 표시.

## 종료와 보존

레시피 변경·추가 seed·새 threshold 탐색은 없다. 인프라/코드 오류는 원인을 기록하고 같은 고정 실험을 복구할 수 있다. 데이터 정합성 오류 시 임의 사례 제외 없이 중단/범위를 보고한다. 내부/외부 채택 미달이면 기존 배포 유지 후 최종 보고로 종료한다. 사용자7개 작성 파일과 기존 증거는 보존한다. 다운로드는 항목별 CRC/SHA 검증하며 원본1GB 전체 저장을 피한다. 임상 자료·전체WSI 핵 정답이 없으므로 해당 검증 완료를 주장하지 않는다.
