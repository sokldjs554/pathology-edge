# NuCLS 격자 정규화 보충 증거

[방법·결과·한계 보고서](../../../docs/NUCLS_GRID_ALIGNMENT.md) · [정렬 그림](figures/alignment-example.png) · [36쌍 전체 비교](figures/normalized36-sheet-1.png)

보류36쌍을 최근접 categorical 격자로 대응시킨51시야·5케이스 평가다. 기존15시야의 라벨·확률·지표와 원자료를 보존했다.72회 추가 추론이며 사용자 직접 실행으로 기록하지 않는다.

[evidence-v2.zip](evidence-v2.zip): 37,542,882bytes, 288members. SHA256 `5cbcb9b667484870c2e6ce64ae109576f2b57d35afbb58339bbd6c90633cf5b0`.

이 ZIP은 [선행 NuCLS 증거](../nucls-sp3-20261113/evidence.zip)에 의존한다. 두 파일은 서로 다른 폴더에 푼다. [base-reference.json](base-reference.json)에 고정 다운로드 링크와 SHA가 있다. 기존모델·원자료·15시야 예측은 선행 ZIP에, 새 확률72개·정렬 mask51개·좌표·코드·검산·그림은 보충 ZIP에 있다.

전체 Dice0.628150→0.613006,8상승·43하락. 고정 threshold0.35, 모델 재학습0회. 과거 SP.3 exporter의 정확한 소수점 좌표 복원, intended-FOV 확보, 전체 WSI·임상 검증은 주장하지 않는다.

[ZIP CRC·구성 파일 SHA 검사](archive-audit.json) · [새 폴더에 푼 파일 재검산](extracted-audit.json) · [86개 관련 테스트](regression.log).

버전2는 참고 코드의 [MIT/BSD 고지](UPSTREAM_LICENSES.txt)를 ZIP 내부에도 포함했다. 이전 발행본은 커밋6744ee5에 보존되며 평가 결과·예측은 같다.
