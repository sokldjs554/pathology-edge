# 보정 모듈 추가 seed: 실제 3개 쌍 실행

**개발 환경에서 seed 20261116·20261117·20261118, 총 6개 모델을 새로 학습했다.** 기존 사용자 Codespaces의 한 seed 결과와 합산하지 않았다. 같은 초기 backbone에서 보정 head 유무를 비교하고 실행 순서는 기준→보정, 보정→기준, 기준→보정으로 교대했다. [사전 조건](REFINEMENT_REPEATS_PROTOCOL.md).

| 평가 영역 | 기준 ViT 평균 ± 표본 SD | 보정 ViT 평균 ± 표본 SD | 같은 seed 차이 평균 ± 표본 SD | 상승/동일/하락 |
|---|---:|---:|---:|---:|
| 전체 | 0.555994 ± 0.014420 | 0.576699 ± 0.007876 | +0.020706 ± 0.006752 | 3/0/0 |
| 경계 | 0.538927 ± 0.017215 | 0.555245 ± 0.007569 | +0.016318 ± 0.022384 | 2/0/1 |
| 내부 | 0.546571 ± 0.015602 | 0.567130 ± 0.009244 | +0.020558 ± 0.006975 | 3/0/0 |

차이는 반올림 전 수치로 계산했다. 같은 **validation 10장·2그룹**에서 epoch/threshold를 선택했다. 30개의 독립 이미지나 독립 test 결과가 아니다. 경계 차이의 표본 SD가 평균보다 크고 한 seed는 하락했다.

| seed | 기준 epoch / threshold | 보정 epoch / threshold | 전체 Dice 차이 | 경계 Dice 차이 |
|---|---|---|---:|---:|
| 20261116 | 12 / 0.35 | 13 / 0.35 | +0.013312 | −0.008627 |
| 20261117 | 11 / 0.35 | 11 / 0.5 | +0.026545 | +0.022929 |
| 20261118 | 13 / 0.35 | 16 / 0.35 | +0.022260 | +0.034652 |

## 근거와 재계산

[원시 실행 ZIP](../artifacts/experiments/refinement-repeats-20261111/evidence.zip)에는 각 모델, 확률60개, 학습 이력, 동결 소스, 원본 보존 기록을 포함했다. [파일별 SHA](../artifacts/experiments/refinement-repeats-20261111/file-manifest.json) · [ZIP SHA](../artifacts/experiments/refinement-repeats-20261111/archive.json) · [전체 요약](../artifacts/experiments/refinement-repeats-20261111/summary.json) · [별도 재계산](../artifacts/experiments/refinement-repeats-20261111/verification.json).

- 180개 이미지·영역 Dice를 원시 확률과 TNBC 정답에서 재계산했고, 세 쌍 모두 설정·모델·소스·manifest·crop/증강 순서·초기 backbone 조건 검사가 통과했다.
- 세 seed의 전체/경계/내부 평균 및 표본 SD, 이미지별 반복 차이 30개 요약을 별도 검산했다.
- 원본 파일의 실행 전후 기록이 같았다. 기존 사용자 결과를 다시 학습하거나 덮어쓰지 않았다.
- 실제 실행은 커밋 `7826601` 및 미커밋 외부 평가 helper를 포함하는 작업 소스에서 동결했다. **깨끗한 커밋 단독 재현이라고 주장하지 않으며**, ZIP의 Python22개·runner와 SHA가 정확한 실행 소스다. helper는 모델 학습에 사용되지 않았다.
- 환경은 EPYC9V74, CPU5, Python3.12.14, PyTorch2.15CPU, threads4이다. 사용자 EPYC7763 환경의 결과와 구분한다.

## 해석

이 조건에서 전체·내부 검증 Dice의 개선이 세 seed에서 관찰됐다. 경계 개선은 일관되지 않았다. 같은 검증셋을 반복 사용한 선택 편향은 해소하지 못했다. head는 각 128px 타일 안의 logits를 보정하며 서로 다른 타일의 문맥을 직접 연결하지 않는다.

별도 [MoNuSeg 외부 평가](EXTERNAL_MONUSEG_VALIDATION.md)에서는 **사용자 단일 seed의 보정 모델이 평균 성능을 낮췄다**. 새 3개 seed 모델을 외부 평가한 결과는 아니므로 두 실험을 합쳐 평균 내지 않는다. 모델 일반화나 임상적 유효성은 입증하지 않았다.
