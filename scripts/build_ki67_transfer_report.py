#!/usr/bin/env python3
"""Build a factual closeout from completed, audited experiments only."""
import argparse
import json
from pathlib import Path
from pathology_edge.ki67_experiment import read_json,fresh_json,sha
from pathology_edge.ki67_union_experiment import read_rows
from pathology_edge.ki67_transfer_experiment import checked,primary_models
from pathology_edge.ki67_transfer_evaluation import validate_audited


def build(root):
    root=Path(root);p=checked(root,selected=True);audit=validate_audited(root);selection=read_json(root/'selection.json');primary=primary_models(selection)
    browser=read_json(root/'browser-review.json')
    if not browser['all_checks_passed'] or browser['review_sha256']!=sha(root/'review.html'):raise ValueError('Actual browser review of the current artifact required before closeout')
    stages={s:read_json(root/'evaluation'/s/'summary.json') for s in ('validation','test','bcdata','deepliif')}
    if not all(v['all_checks_passed'] for v in stages.values()):raise ValueError('All evaluations required')
    adopted=sum(m['selected'] is not None for m in primary);external=stages['deepliif']['passes'];internal=stages['test']['passes']
    palette=read_json(root/'external-input-review/palette-normalization-summary.json')
    f=lambda v:'—' if v is None else f'{v:.4f}'
    lines=['# 마지막 성능 보완: 실제 사전학습과 고정 외부 평가','',
           f'**내부 검출기 채택 {adopted}/3, 재사용 내부 test 종합 기준 {internal}/3, 새 DeepLIIF 외부 종합 기준 {external}/3.** 아래 숫자는 자동 검산을 완료한 실제 결과다. 평가 완료와 성능 목표 달성을 구분한다. 이번 고정 실험으로 성능 보완 반복을 종료하며, 기존 배포 모델은 교체하지 않았다.','',
           '## 1~4번에서 완료한 작업','',
           '1. **실제 외부 사전학습 비교:** 공식 ImageNet SqueezeNet1.1 가중치를 로드했다. 동일 구조의 무작위 고정 encoder와 세 seed를 짝지어 비교했다. 이전의 자체 체크포인트 재학습·정규화·손실·평활화와 다른 실험이다.',
           '2. **학습 자료·방법 보완:** 학습 이미지 696장·15케이스의 영상/주석/분할 해시를 확인하고, 케이스를 균등 추출했다. 케이스당 원본 이미지 수는 9~109장이며 원래 좌표·클래스·분할은 유지했다. 새 임의 라벨이나 외부 학습 자료를 추가하지 않았다.',
           '3. **자동 Ki-67 과정 평가:** 사람이 제공한 중심 대신 실제 검출 중심에서 고정 CNN 분류기를 실행했다. 검출·세포 분류·양성률을 함께 집계했다. 검출기 seed17/18/19에 기존 분류기 seed13/14/15를 고정 대응시켜 분류기를 사후 선택하지 않았다.',
           '4. **새 외부 평가:** DeepLIIF 597장 전체에서 원영상과 제공 주석을 대조한 뒤 같은 고정 모델들을 평가했다. 기존 Patherea test407장과 BCData133장은 재사용 평가이며 새 외부 검증으로 부르지 않는다.','',
           '임상 검증과 전체 WSI 핵 정답 기반 검증은 실시한 것으로 기록하지 않는다. 이번 외부 과제는 폐·방광 IHC 패치의 전체 세포 양음성/중심 검출이며 종양 세포만의 임상 Ki-67 지수가 아니다.','',
           '## 이전 실험을 반복하지 않은 부분','',
           '- 공식 가중치 SHA-256과 50개 feature tensor를 대조하고, 공식 구현과 encoder 출력의 완전 일치를 확인했다. 외부 사전학습을 사용했다고 말할 수 있는 근거다.',
           '- encoder는 고정하고 21,665개 decoder 파라미터만 학습했다. 총 파라미터는 744,161개다. 무작위 대조군도 encoder가 고정되어 있으므로 전체 모델 from-scratch 학습 대조군이나 병리 foundation model 비교는 아니다.',
           '- 같은 seed의 두 arm은 decoder 초기값·추출 순서·증강을 동일하게 했다. 새 구조와 케이스 추출을 함께 적용했으므로 기존 A 대비 차이 전체를 사전학습 하나의 효과로 돌리면 안 된다. 사전학습 자체의 비교는 같은 구조의 random/pretrained 행을 본다.',
           '- 이전에는 내부 기준 미달이면 외부 단계를 건너뛰었다. 이번에는 결과를 보기 전에 **미달 모델도 진단 목적으로 고정 평가**하도록 정했다. 채택 기준을 완화하거나 이전 실패를 소급 변경한 것은 아니다.','',
           '## 고정한 학습·선택 조건','',
           'seed20261117/18/19 × pretrained/random, 각24epochs. Adam0.001,batch8,작업당1thread. epoch마다696회 복원 추출하므로 새로운696장을 매번 추가한 것이 아니다. 기존 maxGaussian sigma2/radius6와 center focal loss, 회전/반전/RGB0.9~1.1 증강을 유지했다. ImageNet mean/std 정규화만 적용하고 원영상 좌표를 바꾸는 resize/crop은 하지 않았다.',
           '',
           'validation227장·4케이스에서 epoch와12임계값×3거리를 비교했다. FP·FN 동시 비증가(하나 이상 감소), 케이스 평균 재현율≥0.479795, 양성 종양 위치 재현율≥270/483, 음성 종양 위치 재현율≥439/1292, 각 케이스 재현율≥기존A의90%를 유지했다. 적격 설정이 있으면 그중 최고 case-F1, 없으면 최고 case-F1 진단 설정을 선택했다. 여섯 모델을 모두 봉인한 뒤 heldout을 실행했고 결과를 보고 재학습/임계값 조정하지 않았다.','',
           '## 검증 자료 — 케이스 평균 검출 F1','',
           '분할 Dice가 아니라 중심의6px 이내 일대일 위치 대응이다. FP/FN은227장 합계이며 F1과 전체 재현율은4케이스 평균이다. 종양 클래스별 재현율은 위치 검출 결과이고 세포 분류 정확도가 아니다.','',
           '|seed|방식|case-F1|FP|FN|case 재현율|양성 종양 위치 재현율|채택|','|---|---|---:|---:|---:|---:|---:|---|']
    for seed in p['seeds']:
        records=[m for m in selection['models'] if m['seed']==seed];baseline=records[0]['baseline']
        lines.append(f"|{seed}|기존 A|{f(baseline['case_macro_f1'])}|{baseline['localization']['fp']}|{baseline['localization']['fn']}|{f(baseline['case_macro_recall'])}|{f(baseline['tumor_recalls'][0])}|기준|")
        for arm in ('random','pretrained'):
            m=next(r for r in records if r['arm']==arm);r=m['evaluation_trial']
            lines.append(f"|{seed}|{arm}|{f(r['case_macro_f1'])}|{r['localization']['fp']}|{r['localization']['fn']}|{f(r['case_macro_recall'])}|{f(r['tumor_recalls'][0])}|{'통과' if m['selected'] is not None else '미달·진단'}|")
    lines += ['', '## 재사용 내부 test407장·10케이스 — 실제 검출 중심의 자동 분석','',
              '검출 F1은407장 합계, 세포 F1은4클래스 macro-F1, 양성률 오차는케이스 평균 절대오차(%p)다. 종양 양성률의 분모가 있는 케이스 수를 함께 표시한다.','',
              '|seed|방식|검출 F1|세포 F1|케이스 양성률 MAE(%p)|유효 케이스|','|---|---|---:|---:|---:|---:|']
    for m in primary:
        scores=read_rows(root/'evaluation/test'/str(m['seed'])/'scores.json.gz')[0]
        for arm in ('A','B'):
            r=scores[arm];lines.append(f"|{m['seed']}|{arm}|{f(r['localization']['f1'])}|{f(r['macro_f1'])}|{f(r['case_ratio_mae_pp'])}|{r['case_ratio_valid']}/10|")
    for dataset,title in [('bcdata','재사용 BCData133장 — 종양 주석만 있는 과제'),('deepliif','새 DeepLIIF597장 — 전체 세포 양음성 과제')]:
        lines += ['', '## '+title,'',
                  'BCData에서는 종양 예측만 참조 종양 좌표와 대응한다. DeepLIIF에서는 종양·비종양 예측을 양음성으로 합치며 모든 예측 세포를 유지한다. 서로 다른 과제의 절대 F1을 직접 비교하지 않는다.','',
                  '|seed|방식|검출 F1|검출+양음성 macro-F1|동일 모집단 양성률 MAE(%p)|유효 A/B/공통 이미지|','|---|---|---:|---:|---:|---|']
        for m in primary:
            c=read_json(root/'evaluation'/dataset/str(m['seed'])/'comparison.json')
            if dataset=='deepliif':c=c['6']
            frac=c['fractions'];coverage=f"{len(frac['A_valid_ids'])}/{len(frac['B_valid_ids'])}/{len(frac['common_ids'])}"
            for arm in ('A','B'):
                r=c[arm];lines.append(f"|{m['seed']}|{arm}|{f(r['localization']['f1'])}|{f(r['two_class_macro_f1'])}|{f(frac[arm+'_mae_pp'])}|{coverage}|")
        lines += ['',f"고정한 종합 기준 통과: **{stages[dataset]['passes']}/3**. A에서 정답/예측 분모가 유효한 동일 이미지 집합에서 MAE를 비교한다. B의 분모가 사라지면 해당 이미지를 빼고 좋은 평균만 내지 않으며 비교 미달로 처리한다."]
    lines += ['', '### DeepLIIF 보조 반경12px — 주 분석6px를 대체하지 않음','', '|seed|A 검출 F1|B 검출 F1|A 양음성 F1|B 양음성 F1|보조 기준|','|---|---:|---:|---:|---:|---|']
    for m in primary:
        c=read_json(root/'evaluation/deepliif'/str(m['seed'])/'comparison.json')['12']
        lines.append(f"|{m['seed']}|{f(c['A']['localization']['f1'])}|{f(c['B']['localization']['f1'])}|{f(c['A']['two_class_macro_f1'])}|{f(c['B']['two_class_macro_f1'])}|{'통과' if c['passed'] else '미달'}|")
    lines += ['', '## 외부 자료 연결과 한계','',
              '- 공식 test598개 중 이전 형식 점검에 사용한1개를 결과 이전에 제외하고597개를 고정했다. 이후 점수나 영상 크기에 따라 사례를 골라내지 않았다.',
              '- 512×3072 PNG의첫512px RGB와여섯번째512px 참조 마스크를 연결했다. 빨강/파랑 내부의8연결 성분 중면적>4px만 사용하고 색상 다수결과 무게중심으로 양음성/좌표를 유도했다. 경계 성분 수와 혼합색 성분도 기록했다. SciPy와별도 OpenCV 계산을 대조했다. 이것은 공식 DeepLIIF 평가 프로토콜의 재현이나 전문가 중심점의 직접 주석을 뜻하지 않는다.',
              '- 개별 ZIP항목 CRC·SHA·응답 범위를 확인하고 기존 자료/새 자료 안의 완전 동일 RGB 해시 중복을 검사했다. 원본1GB ZIP 전체 checksum은 확인한 것으로 기록하지 않는다. 환자·슬라이드·기관 독립성 및 MPP가 보장되지는 않는다.',
              '- 처음 받은 HTTP429는 원자료 오류가 아니라 요청 제한이었다. 실패한 시도를 보존하고 요청당 한 범위·분당최대30회·Retry-After 대기로 복구했다. 자료 집합이나 성능 기준은 바꾸지 않았다.',
              f"- 원자료 점검409장 이후 참조 마스크의1픽셀 `(253,0,2)`를 발견해, 모델 외부 추론 전에 별도 형식 보완 규칙을 기록했다. 공식 코드의 양성 채널 해석과 대조하고 표준 색상과의 최대 채널 차이2까지만 정규화했다. 실제 적용은{palette['images_changed']}장·{palette['pixels_changed']}픽셀이다. 더 큰/모호한 차이는 거부하며 원본RGB와597장 구성은 유지했다. 원래 규칙부터 완전히 동일했다고 표현하지 않으며 `reference-amendment.json`에 근거·시점·원본 해시를 남겼다.",
              '- seed3개·작은 내부 케이스 수·재사용 validation 선택의 한계가 남는다. 외부 성공 여부도 이 전체 세포 과제의 결과이지 종양 Ki-67 임상 정확도나 전체WSI 성능의 근거가 아니다.','',
              '## 실행·검산·본인 작업 구분','',
              f"별도 검산에서 **{audit['trial_checks']}개 설정**, 선택 체크포인트 **{audit['checkpoint_replay_images']}건의 영상 재실행**, **{audit['metric_summaries']}개 지표 요약**을 대조했다. NMS·선택·집계는 별도 코드이며 일부 검증된 peak/matching 기본 함수는 공유한다. heldout 전체를 별도 모델로 다시 추론한 검증이라고 부르지 않는다.",
              '',
              '이번 학습·자동 평가·코드 검사·브라우저 확인은 자동 실행 작업이다. 사용자가 새 모델을 직접 학습/검토했다고 추가하지 않았다. 기존 사용자 작성7개 파일의 해시를 유지했으며 앞선 사용자 확인 기록도 소급 변경하지 않았다. 새 검토 화면의 사용자 확인은 아직 예정이다.',
              '',
              '## 직접 확인할 순서','',
              '증거 ZIP의 review.html을 브라우저로 열고 예시0 → seed20261117을 선택한다. 세 패널이 같은 원영상을 보여주는지 본다. 중심 표시를 끄고 켜도 TP/FP/FN·F1·양성률은 유지되어야 한다. 참조 중심/대응선을 켜면 위치 대응을 볼 수 있다. 다른 seed와여섯 예시를 선택해 비교한다. 화면의 양성률은 전체 세포 비율이며 종양 임상 지수가 아니다. 선택한 여섯 예시를 전체597장 평균으로 해석하지 않는다.','',
              '## 재현 및 출처','',
              f"학습 소스 커밋: `{p['source_commit']}`. 실행 설정·입력/가중치/소스 해시는 `protocol.json`, 여섯 모델 선택은 `selection-lock.json`, 평가 코드는 `evaluation-lock.json`에 고정했다. 실제 환경은 `resource-environment.json`에 있다. 학습 시간은 검증/설정 탐색과동시 실행을 포함하므로 통제된 속도 벤치마크가 아니다.",
              '',
              '- SqueezeNet1.1: https://github.com/pytorch/vision/blob/3ac97aa9120137381ed1060f37237e44485ac2aa/torchvision/models/squeezenet.py ; 소스 BSD3Clause 공지 포함. ImageNet 공개 가중치 사용이며 병리 사전학습 모델이 아니다.',
              '- Patherea Breast-P1: https://huggingface.co/datasets/ds2268/patherea ; CC BY-NC4.0.',
              '- DeepLIIF: Ghahremani et al., DOI10.1038/s42256-022-00471-x ; https://zenodo.org/records/4751737 ; CC BY4.0.',
              '- BCData: https://sites.google.com/view/bcdataset ; 비상업 연구용. 원영상과 개별 주석 좌표는 공개 증거 ZIP에 재배포하지 않는다.',
              '',
              '원자료와 이전 고정 실행 폴더가 있는 저장소 루트에서 `scripts/run_ki67_transfer.py`의prepare/fit/seal, `scripts/run_ki67_transfer_evaluation.py`의references/validation/test/bcdata/deepliif, `scripts/audit_ki67_transfer.py`를 순서대로 사용한다. 경로·원자료 해시가 다른 실행을 기존 결과 위에 덮어쓰지 않는다. 모델과결과는 연구·교육용이다.','']
    report='\n'.join(lines)
    with (root/'final-report.md').open('x') as fobj:fobj.write(report)
    result=dict(training_source_commit=p['source_commit'],all_steps_executed=True,internal_adopted=adopted,stages=stages,audit=audit,live_model_changed=False,user_new_execution_or_review_claimed=False,clinical_validation=False,whole_wsi_validation=False,stop_after_this_fixed_attempt=True)
    fresh_json(root/'final-summary.json',result);print(json.dumps(dict(internal_adopted=adopted,reused_test_passes=internal,new_external_passes=external,report=str(root/'final-report.md'))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);a=p.parse_args();build(a.run)
