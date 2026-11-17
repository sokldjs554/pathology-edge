"""Assemble the authorized full-progress handoff from immutable public evidence.

This packages existing results; it does not run training, inference, or user work.
"""
import hashlib
import html
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
SOURCE = 'fbc5f0d7e09f151c2790eca5e7463b41fdf279e7'
NAME = 'PathologyEdge-All-Progress-U106-20261115.zip'
OUT = ROOT / 'artifacts/handoff' / NAME
RAW = f'https://raw.githubusercontent.com/sokldjs554/pathology-edge/{SOURCE}/'
ROWS = json.loads((WORK / 'git-inventory.json').read_text())
TREE = {r['path']: r for r in ROWS}
FILES, ORIGINS, INVENTORY = {}, {}, []
USER_ZIPS = {
    'artifacts/learning/step56-user-evidence/research-evidence.zip':
        '136a3c0ebae3f32ee7970160700922179485b27fa40b6f07df791d4d965d3895',
    'artifacts/experiments/user-vit-refinement-20261112/evidence.zip':
        'a9d7a597e21528cbb81e07e881ed9f55fd13e6ef5fdcb299991c265ee65d17d1',
}
USER_CODE = [
    ('src/pathology_edge/learner_coordinates.py', 'local_to_level0', '좌표 변환·입력 검사', '12 passed'),
    ('tests/learner/test_merge_counterexample.py', 'test_distance_rule_can_suppress_distinct_nuclei', '서로 다른 핵을 하나로 억제하는 반례 테스트 본문', '1 passed'),
    ('src/pathology_edge/learner_metrics.py', 'dice_score', '영역 선택·입력 검사·Dice 계산', '20 passed'),
    ('src/pathology_edge/learner_split.py', 'find_group_leaks', 'split 간 그룹 누수 검사', '18 passed'),
    ('src/pathology_edge/learner_losses.py', 'soft_dice_loss', 'sigmoid·이미지별 soft Dice·batch 평균 본문', '8 passed'),
    ('src/pathology_edge/learner_wsi.py', 'roi_points_to_level0', '실제 읽기 크기와 모델 크기의 scale 연결', '8 passed'),
    ('src/pathology_edge/learner_refinement.py', 'LocalResidualHead', '두 convolution·ReLU·0 초기화·잔차 연결', '13 passed'),
]
UI_KEEP = {
    'artifacts/ui/before-desktop.png', 'artifacts/ui/after-desktop.png',
    'artifacts/ui/interview/after-first.png', 'artifacts/ui/interview/after-improved.png',
    'artifacts/ui/wsi/wsi-overview.png', 'artifacts/ui/wsi/ihc-desktop.png',
}
PHASES = [
    ('01', '회사·공고 조사와 프로젝트 범위', 'docs/JOB_MATCH_2026-11-10.md', 'docs/RESEARCH.md'),
    ('02', 'TNBC 데이터·기준 모델·경계 평가', 'docs/REVIEW.md', 'artifacts/evaluation.json'),
    ('03', '작업대 UI·동기 이동·개선/악화 경계', 'docs/INTERVIEW_UI.md', 'docs/PAN_FIX.md'),
    ('04', '사용자 코드·테스트·결정 기록', 'PERSONAL_WORK.md', 'docs/CONTRIBUTIONS.md'),
    ('05', 'WSI 탐색과 제한된 ROI 예측', 'docs/WSI_EXPERIMENT.md', 'docs/WSI_REVIEW.md'),
    ('06', '정답 중심 조건 IHC 분류', 'docs/IHC_EXPERIMENT.md', 'artifacts/ihc/results.json'),
    ('07', '직접 손실 구현·기준 학습·3 seed 비교', 'docs/STEP_34.md', 'docs/STEP_42.md'),
    ('08', 'Ubuntu 재현·C++ 빌드·Git·원격 Docker CI', 'docs/STEP_45.md', 'docs/STEP_51.md'),
    ('09', 'C++ 구간 벤치마크·CNN/ViT 비교', 'docs/CPP_VIT_COMPARISON.md', 'docs/USER_RESEARCH_AUDIT.md'),
    ('10', '직접 보정 head·제출 원본·추가 반복', 'docs/USER_REFINEMENT_AUDIT.md', 'docs/REFINEMENT_REPEATS_RESULTS.md'),
    ('11', 'MoNuSeg 외부 평가·실패 분석', 'docs/EXTERNAL_MONUSEG_VALIDATION.md', 'artifacts/experiments/external-monuseg-20261111/largest-decrease.png'),
    ('12', 'BCData 원본 대조·402장 평가·본인 109/367 재실행', 'docs/BCDATA_FULL_TEST.md', 'docs/STEP_69.md'),
    ('13', '공개 WSI/주석 연결·PanopTILs 평가', 'docs/ORIGINAL_ANNOTATION_EVALUATION.md', 'docs/PANOPTILS_WSI_PROBE.md'),
    ('14', 'NuCLS 36쌍 치수 해결·전체 51시야 평가', 'docs/NUCLS_GRID_ALIGNMENT.md', 'docs/NUCLS_SP3_EVALUATION.md'),
    ('15', '자동 Ki-67 패치 후보 검출·분류', 'docs/AUTO_KI67_EXPERIMENT.md', 'docs/AUTO_KI67_REVIEW_LOG.md'),
    ('16', '후보 제거·재현율 손실 분석', 'docs/KI67_CANDIDATE_FILTER.md', 'docs/KI67_LEARNED_CENTERS.md'),
    ('17', '학습 중심·재현율 진단·3 seed 안정성', 'docs/KI67_RECALL_DIAGNOSIS.md', 'docs/STEP_84.md'),
    ('18', 'CNN/ViT 실제 오류·FP/FN 검토', 'docs/STEP_86.md', 'artifacts/experiments/user-cnn-vit-errors-20261112/index.html'),
    ('19', '후보 통합·이진 CNN·점수 정렬 수정', 'docs/KI67_UNION_GATE.md', 'docs/STEP_90.md'),
    ('20', '예측 중심 재학습·중심 위치 보완', 'docs/KI67_CENTER_REFIT.md', 'docs/KI67_LOCALIZATION.md'),
    ('21', '정규화 검출기·감독 신호·마지막 사전 진단', 'docs/KI67_NORMALIZED.md', 'docs/KI67_SUPERVISION.md'),
    ('22', '최종 사전학습 대조·3 seed·새 DeepLIIF 외부 평가', 'docs/KI67_FINAL_TRANSFER.md', 'review/final-transfer/review.html'),
    ('23', '임상·전체 WSI 검증 미실시와 데이터 한계', 'docs/CLINICAL_WSI_VALIDATION_STATUS.md', 'docs/KI67_FINAL_TRANSFER.md'),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def add(path, b, origin):
    if Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError(path)
    if isinstance(b, str):
        b = b.encode()
    FILES[path], ORIGINS[path] = b, origin


def generated(path, text):
    add(path, text, {'generated': 'handoff packaging, no new experiment or user confirmation'})


def selection(path):
    suffix = Path(path).suffix.lower()
    if path.startswith('.openai/'):
        return False, 'internal work metadata; not project deliverable'
    if path.startswith('artifacts/handoff/'):
        if suffix == '.zip':
            return False, 'historical duplicate handoff; current reports and original links preserved'
        if suffix == '.png':
            return False, 'historical duplicate screenshot; fixed download available'
        return True, 'historical publication receipts, explicitly historical'
    if path.startswith('dist/wsi/'):
        return False, 'large WSI tiles/ROI assets; fixed download and live viewer available'
    if path.startswith('artifacts/predictions/'):
        return False, 'large original model predictions; fixed download available'
    if suffix in {'.zip', '.pt', '.npz', '.npy', '.gz'} and path not in USER_ZIPS and path != 'artifacts/learning/step57-exercise.zip':
        return False, 'large replay/checkpoint/evidence archive; fixed download available'
    if path.startswith('artifacts/ui/') and suffix == '.png' and path not in UI_KEEP:
        return False, 'additional historical screen size/state; fixed download available'
    if path.startswith('artifacts/experiments/') and suffix == '.png' and ('mobile' in path or '390' in path) and 'ki67-final-transfer' not in path:
        return False, 'additional mobile screenshot; fixed download available'
    return True, 'included verbatim from source commit'


proc = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
user_archive_checks = []
for r in ROWS:
    p = r['path']
    proc.stdin.write((r['oid'] + '\n').encode()); proc.stdin.flush()
    size = int(proc.stdout.readline().split()[2])
    b = proc.stdout.read(size)
    assert proc.stdout.read(1) == b'\n' and size == r['bytes']
    include, reason = selection(p)
    entry = {**r, 'sha256': sha(b), 'included': include, 'reason': reason, 'url': RAW + quote(p, safe='/')}
    INVENTORY.append(entry)
    if include:
        add(p, b, {'git_commit': SOURCE, 'git_blob': r['oid'], 'path': p})
    if p in USER_ZIPS:
        assert sha(b) == USER_ZIPS[p]
        z = zipfile.ZipFile(io.BytesIO(b)); assert z.testzip() is None
        user_archive_checks.append({'path': p, 'bytes': size, 'sha256': sha(b), 'crc_ok': True, 'members': len(z.infolist())})
    if p == 'artifacts/handoff/PathologyEdge-FinalTransfer-20261115.zip':
        z = zipfile.ZipFile(io.BytesIO(b)); assert z.testzip() is None
        for n in z.namelist():
            add('review/final-transfer/' + n, z.read(n), {'archive': p, 'archive_sha256': sha(b), 'member': n, 'git_commit': SOURCE})
    if p == 'artifacts/handoff/PathologyEdge-Cowork-U97-20261113.zip':
        z = zipfile.ZipFile(io.BytesIO(b)); assert z.testzip() is None
        for n in ['START_HERE.txt', 'EVIDENCE_DOWNLOADS.md', 'LICENSES_AND_SCOPE.txt', 'SCREENSHOTS.md']:
            add('historical/U97/' + n, z.read(n), {'archive': p, 'archive_sha256': sha(b), 'member': n, 'git_commit': SOURCE})
proc.stdin.close(); assert proc.wait() == 0

# Keep the public snapshot byte-exact; a new cover overrides historical pending labels.
contrib = FILES['docs/CONTRIBUTIONS.md'].decode()
record_ids = re.findall(r'^\| (U\d+) \|', contrib, re.M)
assert len(record_ids) == 107 and set(record_ids) == {f'U{i:02d}' for i in range(107)}
for p, fn, _, _ in USER_CODE:
    assert p in FILES and fn.encode() in FILES[p]
generated('PERSONAL_WORK.md', '''# 본인이 직접 수행한 부분 — 확인된 범위

이 목록은 실제 제출 코드·실행 출력·화면 확인 답변에 근거합니다. **전체 기록은 [U00–U106](docs/CONTRIBUTIONS.md)** 이며, 번호 107개에는 예정·보류 항목도 있습니다. 107개 모두 완료했다는 뜻이 아닙니다. 이 포장 작업에서 새 사용자 완료 기록을 만들지 않았습니다.

## 직접 작성한 7개 항목

각 파일의 틀·guard·fixture·학습기·기존 연결 코드에는 제공된 코드가 포함됩니다. 파일 전체나 모델 전체를 단독 작성했다고 표현하지 않습니다. 테스트 수는 당시 본인의 실행 보고이며 이번 포장 시 재실행한 결과가 아닙니다.

| 코드·함수 | 직접 작성 범위 | 당시 실행 보고 |
|---|---|---|
''' + ''.join(f'| [{p}]({p}) · `{fn}` | {scope} | {tests} |\n' for p, fn, scope, tests in USER_CODE) + '''
## 직접 실행·제출한 주요 작업

- 저장 Dice 42/42개·평균 6/6개 대조. 그룹 11개/이미지 50장, split 33/10/7 검사와 저장 이미지 해시 문자열 중복 검사.
- Codespaces CPU 기준 학습, BCE-only/직접 soft Dice 비교, 추가 세 seed의 여섯 학습 실행 및 로컬 감사 성공 출력.
- Ubuntu 고정 소스 재현(191개 테스트·C++ 재빌드·Dice·정적 데모), 원본 로그 commit·push·PR #1 생성·병합. Docker는 원격 CI 화면 확인이며 본인 로컬 Docker 빌드가 아닙니다.
- C++ 패치 추출 8조건·72개 시간 측정, CNN/ViT 단일 seed 비교, 직접 보정 head의 13개 테스트·학습 비교와 원본 ZIP 제출.
- BCData 공식 test 1,206파일 수신 보고, 109·367 두 이미지의 고정 모델 추론·기존 결과 대조와 화면 확인. BCData 전체 평가를 본인 실행으로 확장하지 않습니다.

## 직접 검토·해석한 내용

동기 이동과 경계 전후 비교, 개선·악화 사례, 후보 억제 반례, 픽셀 수와 핵 개수 구분, 전체/경계/내부/국소 점수 구분, WSI 전체 탐색과 일부 ROI 분석 구분, 정답 중심 조건 분류와 자동 검출 구분, 양성률 분모와 세포 분류 오류, 외부 악화·FP/FN·seed 안정성의 한계를 검토했습니다.

U101 방향 선택과 U102 설계 승인은 실험 실행 기록이 아닙니다. U103–U106은 안내된 화면과 표시/수치 유지 확인 범위이며, 독립 검산·전체 seed/영상 전수 검토·병리 전문가 판독으로 확대하지 않습니다. 마지막 사전학습·DeepLIIF 실험은 개발 환경의 자동 실행입니다.

## 본인이 제출한 원본 파일도 포함

- [C++·CNN/ViT 연구 원본 ZIP](artifacts/learning/step56-user-evidence/research-evidence.zip)
- [보정 head 원본 ZIP](artifacts/experiments/user-vit-refinement-20261112/evidence.zip) — 업로드명 `refinement-evidence.nvOJR4.zip`과 SHA256가 같습니다.

모든 개인 응답·출력 원문과 받은 도움: `artifacts/learning/step*-review.json` 및 관련 summary. 원본을 실제 수신한 실험은 원본 감사와 해시를, 채팅 출력만 받은 단계는 실행 보고라는 증거 범위를 유지합니다. [직접 연구 감사](docs/USER_RESEARCH_AUDIT.md), [보정 원본 감사](docs/USER_REFINEMENT_AUDIT.md).
''')

generated('CURRENT_STATUS.md', f'''# 전체 진행·최종 상태 — 2026-11-15 KST

소스 기준: `{SOURCE}` / `feat/auto-ki67`, [draft PR #2](https://github.com/sokldjs554/pathology-edge/pull/2). 최신 후속 실험은 main 병합·공개 작업대 배포와 구분합니다. [공개 데모](https://pathology-edge-lab.ykh13571.chatgpt.site/)는 기존 TNBC·WSI·IHC 작업대입니다. 후속 연구 화면은 이 ZIP의 검토 HTML에서 봅니다.

## 완료한 작업과 성능 결과

병리 경계 작업대, 실제 WSI 탐색/ROI 좌표 연결, 정답 중심 조건 IHC 분류, 사용자 핵심 코드 7개, 학습·비교·재현·C++ 측정, 원본 WSI와 주석 연결, 외부 평가, 자동 Ki-67 패치 후보 검출·분류와 후속 보완 실험을 구현·실행·검토했습니다. 성공한 비교와 악화·미달 결과를 모두 보존했습니다.

- 원래 TNBC test 7장·2그룹: 전체 Dice 0.558001→0.560790, 경계 0.491793→0.527261, 내부 0.572866→0.569630. CPU 파이프라인 57.2→309.3ms. 평균 경계 개선이 개별 영상/내부 개선을 보장하지 않습니다.
- 본인 BCE/soft Dice 추가 세 seed: 같은 validation 10장의 선택 점수 평균 0.518215→0.546238. 독립 test 개선 증명이 아닙니다.
- C++ 최고 1.96배는 2048² 패치 추출 구간입니다. 전체 추론 가속으로 확대하지 않습니다.
- 본인 보정 head 단일 비교: TNBC validation 전체 Dice 0.570565→0.590386. 외부 MoNuSeg 14 ROI에서는 0.551974→0.534943, 13장 악화. NuCLS 전체 51시야에서는 0.628150→0.613006, 8상승·43하락입니다.
- 최종 사전학습 실험: 세 seed × 사전학습/고정 무작위 특징 2군, 6회 학습. 내부 채택 조건 **0/3**, 재사용 내부 test 407장 종합 조건 **1/3**, 재사용 BCData 133장 조건 **3/3**, 새 DeepLIIF 597장 조건 **1/3**. BCData 재평가는 독립 미노출 외부 증명이 아닙니다. DeepLIIF는 전체 세포의 염색 분류 과제이며 종양 Ki-67 임상 지수 검증이 아닙니다.

**일부 성능 보완은 성공했지만 모든 seed에서 안정적인 종합 개선을 달성하지 못했습니다.** 같은 자료를 계속 조정해 성공으로 포장하지 않고 마지막 사전 고정 실험 결과로 종료합니다. 임상 검증과 전체 WSI의 모든 핵 정답 기반 검증은 수행하지 않았습니다. 연구용 패치·부분 주석 ROI 평가와 구분합니다.

## 근거와 상태 읽는 법

- 현재 종합 해석은 이 파일과 [최종 실험 보고서](docs/KI67_FINAL_TRANSFER.md)가 우선입니다.
- [전체 단계 기록](docs/FINAL_PROGRESS.md), [Cowork 작성 지침](docs/COWORK_HANDOFF.md), [직접 수행 원문](docs/CONTRIBUTIONS.md)을 함께 읽으세요. 옛 STEP/실험/ZIP의 예정·미실시 표시는 당시 기록입니다.
- 현재 소스 CI [43621940392](https://github.com/sokldjs554/pathology-edge/actions/runs/43621940392)는 799개 테스트 통과 기록입니다. 이번 자료 통합에서는 학습·추론을 재실행하지 않았고, 별도로 ZIP·해시·목차·브라우저 연결을 검사합니다.
- 본인 확인 최신 범위는 **U106**입니다. 최신 자동 실행·자료 포장·다운로드 검사를 본인 수행으로 추가하지 않았습니다.

## 이 ZIP의 범위

모든 프로젝트 단계의 문서·실험 집계·감사·개인 기록, 전체 소스/테스트/스크립트 스냅샷, 본인 제출 원본 ZIP 2개, 비교 그림·대표 화면·후속 검토 화면을 포함합니다. 모든 학습 가중치·전체 예측 배열·원자료를 한 파일에 넣은 설치 패키지는 아닙니다.

대용량 증거 ZIP·checkpoint·예측 배열·WSI 타일과 추가 화면은 `FILE_INVENTORY.json`에서 포함 여부·정확한 경로·크기·SHA256·고정 다운로드 URL을 확인할 수 있습니다. `DOWNLOADS.html` 및 `EVIDENCE_DOWNLOADS.md`에서 원본 증거 ZIP을 받을 수 있습니다. 공개 재배포하지 않는 BCData 원영상/HDF5/개별 세포 좌표, 보유하지 않은 임상 자료는 포함하지 않았습니다. 원자료 출처와 이용 조건은 `LICENSES_AND_SCOPE.txt`를 따릅니다.
''')

generated('PERSONAL_FOLLOWUP.md', '''# U106 이후 대화의 추가 해석·요청

기존 정식 기록 U00–U106을 변경하거나 새 실행 완료 번호를 만들지 않고, 현재 대화에서 실제로 받은 후속 문장을 보존합니다. 아래 답변은 당시 검토 과제에 관한 해석·요청이며 마지막 사전학습 실험의 채택 수치와 혼합하지 않습니다. 새 코드·테스트·학습·추론·최종 외부 화면 확인으로 확대하지 않습니다.

## 결과 해석 — 최초 답변과 수정 답변

최초 답변:

> FP와 FN이 모두 감소해 Dice가 개선됐지만, `09_1`에서는 FN이 증가하고 Dice가 하락하는 등 이미지마다 결과가 달랐으므로, 일부 사례의 개선만으로 이번 실험 전체에서 안정적인 성능 향상을 달성했다고 말할 수 없습니다.

이후 사용자가 다시 질문을 요청했고, 다음 수정 답변을 제출했습니다:

> FP와 FN이 모두 감소했지만, 전체 검증 자료에서 세 seed 중 하나만 재현율 유지 등의 채택 조건을 충족하고 나머지 두 seed는 충족하지 못했으므로, 학습 초기값이 달라도 안정적인 성능 개선이 재현됐다고 말할 수 없습니다.

첫 답변의 CNN/ViT `09_1`·Dice와 후속 자동 세포 검출 실험의 채택 조건은 서로 다른 실험입니다. 최초·수정 답변을 합쳐 한 실험 결과로 쓰지 않습니다. 위 문장은 받은 답변 원문이며, ‘1/3’을 최신 실험 전체의 채택 결과로 사용하지 않습니다. 검증 후보 선택·내부 test 조건·최종 사전학습 실험은 각각 해당 selection/stability 및 최종 보고서의 분모·조건을 따라야 합니다.

## 마지막 제한된 보완 시도에 대한 요청

> 그래 그렇게 진행하고 1~4번 마지막으로 보완 시도해보고 안되면 마무리하자 최대한 완료할 수 있게 해 근데 이거 아까전에도 똑같이 했던것 같은데.....일단 확실하게 할 수 있는 보완부터 진행해

이는 실행 방향·종료 조건에 대한 사용자 요청입니다. 실제 마지막 실험 실행·검산은 제공된 개발 환경에서 이루어졌습니다. 요청·승인을 본인 학습 실행으로 기록하지 않습니다.

## 이번 전달 요청

> 그럼 지금까지 진행했던것 완료했던것들 zip으로 해서 올려줘 내가 직접한것까지도 전부 다 포함해서

이번 ZIP은 이 요청에 따른 통합입니다. 사용자가 ZIP을 다운로드·열람·전체 검토했다고 기록하지 않았습니다.
''')

for p in ['docs/COWORK_HANDOFF.md', 'docs/FINAL_PROGRESS.md', 'artifacts/handoff/README.md', 'README.md']:
    # Do not alter immutable source bytes; the start page disambiguates old status.
    assert p in FILES

coverage_rows = []
for order, title, a, b in PHASES:
    # Some historical scopes have no second standalone page; all links must exist.
    if b not in FILES:
        b = a
    assert a in FILES, a
    coverage_rows.append({'order': order, 'scope': title, 'files': list(dict.fromkeys([a, b]))})
generated('COVERAGE.json', json.dumps({'source_commit': SOURCE, 'phases': coverage_rows, 'user_records': record_ids, 'user_code': [v[0] for v in USER_CODE], 'user_original_archives': user_archive_checks, 'new_user_completion_claimed': False}, ensure_ascii=False, indent=2))
generated('FILE_INVENTORY.json', json.dumps({'source_commit': SOURCE, 'scope': 'Every blob tracked at the frozen commit; .openai internal metadata is not a deliverable. Missing original datasets are not claimed present.', 'files': INVENTORY}, ensure_ascii=False, indent=2))

archives = [r for r in INVENTORY if r['path'].endswith('.zip')]
downloads = '# 원본 증거·이전 발행본 다운로드\n\n주요 원본과 과거 보관본의 고정 커밋 URL·SHA256입니다. 사용자 원본 2개는 이번 ZIP에도 들어 있습니다. 이전 전달본은 당시 상태이며 현재 판단은 CURRENT_STATUS.md를 따릅니다. 그 외 대용량 단일 파일과 추가 화면은 FILE_INVENTORY.json에서 찾습니다.\n\n'
for r in archives:
    downloads += f"- **{'ZIP 안 포함' if r['included'] else '별도 다운로드'}**: [{r['path']}]({r['url']}) — {r['bytes']:,} bytes\n  SHA256: `{r['sha256']}`\n"
generated('EVIDENCE_DOWNLOADS.md', downloads)

generated('LICENSES_AND_SCOPE.txt', '''자료별 이용 조건과 범위

1. 저장소의 THIRD_PARTY.md, 각 실험의 DATA-NOTICE/README 및 원출처 조건을 유지합니다. 프로젝트 코드의 조건이 데이터/모델 권리에 자동 적용되지 않습니다.
2. TNBC: CC BY 4.0, https://doi.org/10.5281/zenodo.2579118. OpenSlide CMU 공개 예제: CC0. Patherea P1 연구 파생 그림/검토 이미지: CC BY-NC 4.0, https://huggingface.co/datasets/ds2268/patherea. 상업 서비스 전용을 허가하는 묶음이 아닙니다.
3. DeepLIIF 연구 데이터/파생 예제: CC BY 4.0, https://github.com/nadeemlab/DeepLIIF. 최종 보고서의 공식 자료 URL/해시/변형 기록을 따릅니다. 검토 예제는 원본 첫 RGB 패널과 여섯 번째 주석 패널에서 만든 중심을 사용합니다. DeepLIIF 모델을 실행한 것이 아닙니다.
4. DeepLIIF 참고 코드 스냅샷은 Apache 2.0 + Commons Clause라는 별도 조건입니다. 데이터 CC BY 4.0과 혼동하지 않습니다. SqueezeNet/torchvision 코드의 BSD 3-Clause 고지는 third_party/torchvision-SQUEEZENET-LICENSE에 있습니다. 사전학습 가중치 출처와 고정 해시는 최종 실험 보고서/증거에 있습니다.
5. NuCLS/MoNuSeg/PanopTILs 및 원본 WSI 연결 자료는 해당 보고서/원본 증거의 출처·연구 이용 조건을 그대로 유지합니다. 공개 파일과 해시를 연결한다고 임상 사용 권리를 주장하지 않습니다.
6. BCData 원영상 PNG/HDF5·개별 GT/예측 세포 좌표·비공개 비교 SVG를 이 패키지에 새로 추가하지 않았습니다. 집계·입력 해시·제공된 다운로드/재현 코드만 포함합니다. 사용자가 로컬로 받은 원자료는 별도 보관합니다.
7. 조사 문서는 실제 임상 검체·전문가 판독·전체 WSI 핵 정답 자료가 아닙니다. 임상 검증/전체 WSI 정답 검증은 미실시입니다.
8. 본인 코드/실행/검토/결정과 제공된 구현/자동 실행을 구분합니다. 모든 기록을 본인 단독 구현·실험으로 바꾸지 않습니다. 개인정보·자격·학위·임상 경력은 추정하지 않습니다.
''')

def anchor(path, label=None):
    return f'<a href="{html.escape(path, quote=True)}">{html.escape(label or path)}</a>'


css = '''body{font:16px/1.65 system-ui,sans-serif;color:#183440;background:#f7f9fa;margin:0}main{max-width:1100px;margin:auto;padding:28px}h1{font-size:27px}h2{font-size:20px;margin-top:32px}p{max-width:1000px}a{color:#075f99;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;background:white}th,td{padding:10px;border-bottom:1px solid #d4e0e7;text-align:left;vertical-align:top;overflow-wrap:anywhere}code{overflow-wrap:anywhere}nav{display:flex;flex-wrap:wrap;gap:14px;padding:14px 0}.note{border-left:4px solid #bb731e;padding:12px 16px;background:#fff8e8}details{margin:14px 0}summary{cursor:pointer}img{max-width:100%;height:auto}.scroll{overflow:auto}@media(max-width:600px){main{padding:16px}h1{font-size:23px}th,td{padding:7px;font-size:13px}}'''
body = '''<h1>PathologyEdge 전체 진행 자료</h1><p>2026-11-15 KST · 개인 기록 U00–U106 · 마지막 고정 외부 평가까지</p>
<nav>''' + ' '.join(anchor(p, t) for p, t in [('CURRENT_STATUS.md', '현재 상태'), ('PERSONAL_WORK.md', '내가 직접 한 작업'), ('PERSONAL_RECORDS.html', '개인 기록 107행'), ('docs/COWORK_HANDOFF.md', 'Cowork 작성 근거'), ('DOWNLOADS.html', '대용량 근거 다운로드')]) + '''</nav>
<p>직접 작성한 코드·실행한 실험·검토한 화면과 자동 실행된 추가 실험을 구분했습니다. 아래 목차에서 초기 경계 분석부터 마지막 외부 평가까지 찾아볼 수 있습니다.</p>
<p>U106 이후의 수정 해석 답변과 마지막 시도 요청도 <a href="PERSONAL_FOLLOWUP.md">추가 대화 기록</a>으로 보존했습니다. 새 사용자 실행 완료 기록은 아닙니다.</p>
<p class="note"><strong>실험 완료와 성능 개선 성공은 다릅니다.</strong> 최종 내부 채택 0/3, 재사용 내부 test 종합 조건 1/3, 재사용 BCData 3/3, 새 DeepLIIF 1/3입니다. 모든 seed에서 안정적인 종합 개선은 달성하지 못했습니다. 임상·전체 WSI 핵 정답 검증은 미실시입니다.</p>
<h2>바로 볼 자료</h2><ul>''' + ''.join('<li>' + anchor(p,t)+'</li>' for p,t in [
    ('review/final-transfer/review.html','마지막 외부 평가: 같은 RGB·정답·두 예측 비교'),
    ('docs/KI67_FINAL_TRANSFER.md','최종 실험 수치·선정 조건·한계'),
    ('artifacts/experiments/ki67-normalized-20261114/review/index.html','본인이 표시를 확인한 정규화 검출기'),
    ('artifacts/experiments/ki67-union-20261113/review/index.html','후보 통합·제거·표시 전환 검토'),
    ('artifacts/experiments/user-cnn-vit-errors-20261112/index.html','본인 CNN/ViT 비교의 개선·악화 오류'),
    ('artifacts/ui/before-desktop.png','기존 작업대 화면'),('artifacts/ui/interview/after-first.png','개선한 작업대 화면'),
]) + '''</ul><p>연구 검토 HTML은 저장된 결과를 보여 줍니다. 여는 것만으로 새 분석을 실행하지 않습니다. 공개 데모와 후속 연구 화면의 배포 범위는 다릅니다.</p>
<h2>전체 과정 목차</h2><table><thead><tr><th>단계</th><th>수행 내용</th><th>문서·근거</th></tr></thead><tbody>'''
for row in coverage_rows:
    body += f"<tr><td>{row['order']}</td><td>{html.escape(row['scope'])}</td><td>" + '<br>'.join(anchor(p) for p in row['files']) + '</td></tr>'
body += '''</tbody></table><h2>압축을 푼 뒤</h2><p><code>START_HERE.html</code>부터 여세요. 브라우저가 로컬 파일을 제한하면 압축을 푼 폴더에서 <code>python3 -m http.server 8000</code> 실행 후 <a href="http://localhost:8000/START_HERE.html">http://localhost:8000/START_HERE.html</a>을 여세요. 화면 열람에는 모델 설치가 필요 없습니다.</p>
<p>모든 대용량 데이터·가중치를 내장한 설치본은 아닙니다. 포함/별도 파일 전수 목록은 <code>FILE_INVENTORY.json</code>, ZIP 내 파일 해시는 <code>MANIFEST.json</code>입니다. 추가 자료는 고정 URL·SHA256으로 연결했습니다. BCData 원자료·개별 좌표와 임상 자료는 포함하지 않았습니다.</p>
<p>옛 문서의 ‘예정’ 및 과거 ZIP의 ‘최신’은 발행 당시 상태입니다. 현재 판단은 CURRENT_STATUS.md를 우선합니다. U00–U106에는 보류·예정도 있어 107건 모두 완료라는 뜻은 아닙니다.</p>'''
generated('START_HERE.html', f'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>PathologyEdge 전체 진행 자료</title><style>{css}</style><main>{body}</main></html>')
generated('START_HERE.txt', '''PathologyEdge 전체 진행 자료 — 2026-11-15 KST

START_HERE.html → CURRENT_STATUS.md → PERSONAL_WORK.md → docs/COWORK_HANDOFF.md 순서로 읽습니다.
본인 확인 원문은 docs/CONTRIBUTIONS.md와 artifacts/learning/에 있습니다. U00–U106에는 예정/보류도 포함됩니다.
이전 README/STEP/전달본의 상태는 역사 기록입니다. 최신 요약이 우선합니다.
모든 주요 단계의 문서·코드·집계·감사·대표 화면, 본인 원본 ZIP 2개를 포함합니다.
대용량 모델·예측·원자료·추가 화면은 FILE_INVENTORY.json / DOWNLOADS.html에 고정 URL과 SHA를 제공합니다.
새 학습/추론/사용자 테스트를 수행한 것으로 기록하지 않았습니다.
''')
record_rows = []
for line in contrib.splitlines():
    if re.match(r'^\| U\d+ \|', line):
        cells = [s.strip() for s in line.strip('|').split('|')]
        record_rows.append('<tr>' + ''.join('<td>'+html.escape(s)+'</td>' for s in cells)+'</tr>')
generated('PERSONAL_RECORDS.html', f'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>직접 수행 기록</title><style>{css}</style><main><p>{anchor("START_HERE.html", "전체 목차")}</p><h1>개인 기록 U00–U106</h1><p>107개 번호에는 예정·보류도 있습니다. 각 행의 상태·범위·받은 도움을 유지합니다. 최신 자동 실험을 본인 수행으로 추가하지 않았습니다. 원문: {anchor("docs/CONTRIBUTIONS.md")}</p><div class="scroll"><table><tr><th>번호</th><th>주체</th><th>종류</th><th>수행 내용</th><th>상태</th><th>근거·범위</th></tr>{"".join(record_rows)}</table></div></main></html>')
dlbody = '<h1>추가 증거 다운로드</h1><p>'+anchor('START_HERE.html','전체 목차')+'</p><p>사용자 원본 두 개는 이 ZIP에 포함했습니다. 다른 대용량 묶음은 아래 고정 링크로 받습니다. 옛 전달본의 상태는 당시 기록입니다. 모든 단일 파일은 FILE_INVENTORY.json에서 찾을 수 있습니다.</p>'
for r in archives:
    dlbody += '<details><summary>'+html.escape(r['path'])+'</summary><p>'+anchor(r['path'] if r['included'] else r['url'], 'ZIP 안 파일 열기' if r['included'] else '원본 다운로드')+f" · {r['bytes']:,} bytes</p><p>SHA256: <code>{r['sha256']}</code></p></details>"
generated('DOWNLOADS.html', f'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>추가 증거</title><style>{css}</style><main>{dlbody}</main></html>')

# The manifest authenticates all payloads; the outer checksum authenticates the manifest.
generated('PACKAGING/build.py', Path(__file__).read_bytes())
if (WORK/'source-ci.json').exists():
    generated('PACKAGING/source-ci.json', (WORK/'source-ci.json').read_bytes())
manifest = {'source_commit': SOURCE, 'user_latest_confirmed_id': 'U106', 'new_user_completion_claimed': False, 'new_training_or_inference_run': False, 'files': [dict(path=p, bytes=len(b), sha256=sha(b), origin=ORIGINS[p]) for p,b in sorted(FILES.items())]}
FILES['MANIFEST.json'] = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUT, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as z:
    for p, b in sorted(FILES.items()):
        info = zipfile.ZipInfo(p, date_time=(2026,11,15,3,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
        z.writestr(info,b,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
assert OUT.stat().st_size < 100*1024*1024, OUT.stat().st_size
report = {'path': str(OUT.relative_to(ROOT)), 'bytes': OUT.stat().st_size, 'sha256': sha(OUT.read_bytes()), 'members': len(FILES), 'source_commit': SOURCE, 'tracked_files_included': sum(r['included'] for r in INVENTORY), 'tracked_files_linked_or_out_of_scope': sum(not r['included'] for r in INVENTORY), 'user_code_files': 7, 'user_record_ids': len(record_ids), 'user_latest_confirmed_id': 'U106', 'user_original_archives': user_archive_checks, 'new_training_or_inference_run': False, 'new_user_completion_claimed': False}
(WORK/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
