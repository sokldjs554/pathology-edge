# 후보 통합 실험 전 자료 점검

이 폴더는 구현 전 입력·기존 후보의 탐색 결과다. 새 CNN 성능 결과가 아니다. 실제 새 gate 학습은 실행하지 않았다.

- `preflight.json`: 기존 manifest의 split/케이스/클래스 수, train/validation923개 원본 RGB와 점 마스크를 기존 `load_sample`로 읽어 대조한 결과,6px 이내 다른 정답 중심의 존재 수, 저장 raw피크의 일대일 대응 수.
- `candidate-feasibility.json`: validation227장에 기존 LoG0.1/8px를 실행하고, 기존3seed 저장 raw피크를0.01/4px로 추출한 후보와 정확 좌표 합집합을 만든 탐색 결과. raw피크 근처 정답 존재와 합집합의 일대일 대응을 구분했다. 새 신경망 추론·학습·test/외부 영상 추론은 없다.
- `input-check.json`: train/validation의923 RGB·4615점 마스크 원파일 SHA를 기존 manifest와 대조했다. 사용하는 manifest/split/LoG 선택/가중치 선택 lock/저장 validation피크의 해시도 보존한다.
- `design-review.json`: 별도 검토자의 설계 읽기 결과. 사용자 실행 승인이나 구현 완료 검사가 아니다.

재집계 규칙: 기존 `pathology_edge.ki67_evaluation.match_points`의6px 일대일 대응을 사용했다. 피크 근처 정답 존재 상한은 각 정답과 모든 원피크의 유클리드 거리 중 최소값≤6인지를 센 것이다. 이 상한은 실제 선택된 후보의 정밀도·F1이 아니다. 합집합은 `np.unique(vstack([learned,log]),axis=0)`로 정확 좌표만 중복 제거했으며 새 CNN이나 최종 억제를 적용하지 않았다.

같은 validation을 이미 여러 차례 분석한 뒤 만든 설계다. 신규 미노출 검증이나 일반화 개선이라고 쓰지 않는다. 연구용 미대응 대리 라벨을 전문가가 확인한 배경으로 해석하지 않는다. 사용자 U101은 연구 방향 선택이며 위 데이터 점검·코드 작성·실험 실행은 사용자 수행이 아니다.

[실행 전 설계](../../../docs/superpowers/specs/2026-11-13-ki67-union-gate-design.md). 기존 결과·모델·사용자 파일·발행 ZIP은 수정하지 않았다.
