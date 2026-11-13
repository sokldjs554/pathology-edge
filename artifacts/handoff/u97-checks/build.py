import io, json, hashlib, subprocess, zipfile, re, posixpath, html
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit, unquote, quote

ROOT=Path.cwd()
SOURCE=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
RAW=f'https://raw.githubusercontent.com/sokldjs554/pathology-edge/{SOURCE}/'
BLOB=f'https://github.com/sokldjs554/pathology-edge/blob/{SOURCE}/'
NAME='PathologyEdge-Cowork-U97-20261113.zip'
OUT=ROOT/'artifacts/handoff'/NAME
files={}; origins={}; archives=[]
def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return subprocess.check_output(['git','show',f'{SOURCE}:{p}'])
def add(p,b,origin):
    if p.startswith('/') or '..' in p.split('/'): raise ValueError(p)
    files[p]=b; origins[p]=origin

def open_archive(name):
    path='artifacts/handoff/'+name; b=read(path); z=zipfile.ZipFile(io.BytesIO(b))
    assert z.testzip() is None
    a={'path':path,'source_commit':SOURCE,'bytes':len(b),'sha256':sha(b),'members':len(z.namelist()),'url':RAW+path}
    archives.append(a); return z,a

base,base_info=open_archive('PathologyEdge-Final-Handoff-20261113.zip')
for n in base.namelist(): add(n,base.read(n),{'archive':base_info['path'],'member':n})
for n in ['manifest.json','START_HERE.html','START_HERE.txt','docs/COWORK_HANDOFF.md','docs/FINAL_PROGRESS.md','docs/JOB_MATCH_2026-11-10.md']:
    add('historical/U86/'+n,files[n],origins[n])

snapshots=[
 ('automatic','PathologyEdge-AutoKi67-Addendum-20261113.zip',''),
 ('filter','PathologyEdge-CandidateFilter-20261113.zip',''),
 ('centers','PathologyEdge-LearnedCenters-20261113.zip','PathologyEdge-LearnedCenters-20261113/'),
 ('recall','PathologyEdge-RecallReview-20261113.zip','')]
for key,name,strip in snapshots:
    z,a=open_archive(name); included=[]; excluded=[]
    for orig in z.namelist():
        n=orig.removeprefix(strip); path=Path(n)
        # Writing/review package: keep published aggregate results, selection,
        # audits, frozen source/tests, desktop figures and offline review pages.
        # Full model/replay payloads remain in the immutable linked originals.
        omit=(path.suffix in {'.pt','.gz','.md'} or
              path.name in {'MANIFEST.json','ARCHIVE_MANIFEST.json','SHA256SUMS.txt','README.txt','START_HERE.txt','COWORK_READ_FIRST.txt','predictions.json','inference-bundle.json'} or
              (path.suffix=='.png' and any(x in path.name for x in ['mobile','390','heatmap'])))
        entry={'member':orig,'bytes':z.getinfo(orig).file_size,'sha256':sha(z.read(orig))}
        if omit: excluded.append(entry); continue
        dest=f'evidence/{key}/{n}'; included.append({**entry,'path':dest})
        add(dest,z.read(orig),{'archive':a['path'],'member':orig})
    add(f'evidence/{key}/SCOPE.txt',(
        'Published experiment evidence excerpt, not a runnable inference bundle.\n'
        'Current interpretation and user status: ../../docs/HANDOFF_U97.md.\n'
        'Model checkpoints, compressed replay data, historical Markdown and mobile screenshots are linked in the original ZIP.\n'
        f'Original: {a["url"]}\nSHA256: {a["sha256"]}\n'
        'This subset does not claim the original archive manifest is satisfied.\n').encode(),{'generated':'subset scope'})
    add(f'evidence/{key}/SUBSET.json',json.dumps({'original':a,'included':included,'excluded_available_in_original':excluded},ensure_ascii=False,indent=2).encode(),{'generated':'subset inventory'})

# Load current docs and all small learning records directly from the committed tree.
tree={}
for line in subprocess.check_output(['git','ls-tree','-r','-l',SOURCE],text=True).splitlines():
    left,p=line.split('\t',1); size=left.split()[-1]
    if size.isdigit():tree[p]=int(size)
extra_docs=['HANDOFF_U97.md','STEP_84.md','AUTO_KI67_EXPERIMENT.md','AUTO_KI67_EXTERNAL_PROTOCOL.md','AUTO_KI67_REVIEW.md','AUTO_KI67_REVIEW_LOG.md','KI67_CANDIDATE_FILTER.md','KI67_LEARNED_CENTERS.md','KI67_RECALL_DIAGNOSIS.md']
paths={n for n in files if n.startswith('docs/') and n in tree}
paths.update('docs/'+n for n in extra_docs)
paths.update(p for p,size in tree.items() if p.startswith('artifacts/learning/') and size<2_000_000 and Path(p).suffix in {'.json','.txt','.md','.py'})
paths.update(p for p in tree if p.startswith('docs/STEP_') and re.search(r'STEP_(7[3-9]|8[0-4])\.md$',p))
paths.add('README.md')
for p in sorted(paths): add(p,read(p),{'git_commit':SOURCE,'path':p})

# Source archives and dataset licenses stay distinct.
old_downloads=files['EVIDENCE_DOWNLOADS.md'].decode()
extra='\n## U87–U97 후속 실험의 전체 재현 원본\n\n이 통합 ZIP에는 집계·선택·감사·검토 화면을 발췌했습니다. 모델과 모든 압축 예측/피크, 모바일 캡처, 당시 README를 포함한 실행용 원본은 아래에 그대로 보존했습니다. 통합 ZIP을 완전한 추론 설치 묶음으로 사용하지 마세요.\n\n'
for a in archives:
    extra+=f'- [{Path(a["path"]).name}]({a["url"]}) — {a["bytes"]:,} bytes, SHA256 `{a["sha256"]}`\n'
add('EVIDENCE_DOWNLOADS.md',(old_downloads+extra).encode(),{'generated':'prior and new immutable archive index'})
licenses=files['LICENSES_AND_SCOPE.txt'].decode()+'''\n\nU97 후속 통합 추가:\n자동 Ki-67 검토 영상은 Patherea P1 공개 파생 그림이며 CC BY-NC 4.0 조건과 원출처를 유지합니다.\nhttps://huggingface.co/datasets/ds2268/patherea\nhttps://creativecommons.org/licenses/by-nc/4.0/\nBCData 원본 PNG/HDF5 및 개별 세포 좌표는 추가하지 않았습니다. 외부 집계·입력 해시·감사 결과만 포함합니다.\n후속 자동 분석은 별도 연구 패치 실험이며 임상 또는 전체 WSI 검증이 아닙니다.\n'''
add('LICENSES_AND_SCOPE.txt',licenses.encode(),{'generated':'prior license plus Patherea scope'})
start='''PathologyEdge Cowork 통합 자료 — U97 / 2026-11-13 UTC

START_HERE.html을 열어 최신 요약과 화면으로 이동하세요.
1. docs/HANDOFF_U97.md: 최신 완료 범위, 직접 수행과 실험 한계
2. docs/COWORK_HANDOFF.md: 작성 요청, 전 과정·직접 코드·실행 근거
3. docs/CONTRIBUTIONS.md: 실제 응답 U00–U97, U98 예정
4. docs/FINAL_PROGRESS.md: 전체 경과
5. EVIDENCE_DOWNLOADS.md: 큰 원본 및 후속 전체 재현 ZIP의 고정 링크·SHA

Cowork는 위 근거로 자기소개서·포트폴리오 초안을 작성할 수 있습니다.
사용자 직접 작성 7범위와 제공 구조 활용, 본인 실행, 화면/해석 확인을 구분하세요.
U87–U97은 안내된 후속 화면·결과 해석입니다. 자동 검출기·CNN 학습 전체를
사용자 직접 구현/실행으로 바꾸지 마세요. 도구 기여라는 별도 제목은 필요 없습니다.
U98(본인 CNN–ViT 09_1 오류 그림)은 아직 확인 대기입니다.

자동 Ki-67 패치 분석은 구현·평가됐지만 임상 Ki-67 분석기가 아닙니다.
재현율 조건은 세 seed 중 하나만 충족했고, 누락 감소와 FP/F1 악화를 함께 보존합니다.
외부 성능 개선 성공·새 미노출 검증·임상·전체 WSI 정답 검증은 완료하지 않았습니다.
BCData 정답 중심 조건 test402장과 자동 분석 validation133장을 합치지 마세요.

새 구현은 draft PR #2이며 main 병합/공개 데모 배포는 하지 않았습니다.
연구 HTML은 저장 결과 검토용입니다. 여는 동작은 새 추론이 아닙니다.
이 ZIP은 자료 전달용이며 완전한 설치·재현 패키지가 아닙니다.
historical/는 발행 당시 기록이고 현재 상태보다 우선하지 않습니다.
'''
add('START_HERE.txt',(start+'\nDocument source commit: '+SOURCE+'\n').encode(),{'generated':'current read-first'})
links=[('docs/HANDOFF_U97.md','현재 완료 범위·실패·남은 과제'),('docs/COWORK_HANDOFF.md','Cowork 작성 지침과 상세 근거'),('docs/CONTRIBUTIONS.md','직접 작성·실행·검토 기록'),('docs/FINAL_PROGRESS.md','전체 진행 경과'),('docs/JOB_MATCH_2026-11-10.md','기존 공고와 현재 근거 대조'),('artifacts/experiments/user-cnn-vit-errors-20261112/index.html','이번 확인: CNN–ViT 09_1'),('evidence/automatic/viewer.html','자동 패치 기준선 결과'),('evidence/filter/review.html','후보 제거 전후'),('evidence/centers/review.html','학습 중심 검출 결과'),('evidence/recall/review.html','재현율 조건·누락과 오검출 비교'),('EVIDENCE_DOWNLOADS.md','전체 원본 ZIP과 SHA'),('LICENSES_AND_SCOPE.txt','자료 출처·이용 조건')]
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PathologyEdge U97 전달 자료</title><style>body{font:16px/1.65 system-ui;color:#23333e;margin:24px;max-width:950px}li{margin:12px 0}a{color:#086b98}code{overflow-wrap:anywhere}p{max-width:78ch}</style><h1>PathologyEdge · U97 전달 자료</h1><p>기존 과정과 최신 자동 Ki-67 연구를 함께 읽는 자료입니다. <b>개인 작성·실행·화면 확인을 구분</b>하며 실패 결과도 포함합니다.</p><p>현재 사용자 과제는 <b>09_1 동일 영역 확대 그림 표시 확인</b> 한 가지입니다. 아래 ‘이번 확인’에서 09_1을 찾으세요. U98은 확인 대기이며 새 학습·추론은 없습니다.</p><ol>'''
page+=''.join(f'<li><a href="{href}">{html.escape(label)}</a></li>' for href,label in links)
page+='''</ol><p>자동 패치 분석은 구현·평가했지만 안정적 성능 개선·임상·전체 WSI 핵 정답 검증은 완료하지 않았습니다. 후속 검토 화면은 저장 결과이며 공개 데모와 별개입니다.</p><p>큰 모델·압축 예측은 원본 ZIP 링크로 보존했습니다. 이 묶음은 설치 패키지가 아닙니다. historical/의 예정 상태보다 최신 요약과 직접 수행 기록을 우선하세요.</p>'''
page+=f'<p>문서 기준 커밋 <code>{SOURCE}</code> · <a href="https://github.com/sokldjs554/pathology-edge/pull/2">draft PR #2</a></p></html>'
add('START_HERE.html',page.encode(),{'generated':'current navigation'})

# Package-local handoff index avoids pointing back to an older publication index.
add('artifacts/handoff/README.md', ('# U97 통합 전달 자료\n\n이 폴더의 최신 묶음을 열고 있습니다. [시작 화면](../../START_HERE.html), [현재 요약](../../docs/HANDOFF_U97.md), [전체 원본 ZIP](../../EVIDENCE_DOWNLOADS.md)을 사용하세요.\n\n자동 분석 후속은 draft PR #2이며 공개 데모와 별도입니다. 과거 U86 ZIP과 후속 원본은 고정 링크와 SHA로 보존합니다. 본인 CNN–ViT 오류 그림 확인 U98은 예정입니다.\n').encode(), {'generated':'package-local current index'})
add('SCREENSHOTS.md', files['SCREENSHOTS.md'] + ('\n\n## U87–U97 후속 화면\n\n- [자동 패치 분석](evidence/automatic/viewer.html) · [데스크톱 캡처](evidence/automatic/desktop.png)\n- [후보 제거](evidence/filter/review.html) · [데스크톱 캡처](evidence/filter/screenshots/desktop.png)\n- [학습 중심](evidence/centers/review.html) · [데스크톱 캡처](evidence/centers/screenshots/desktop.png)\n- [재현율 조건 비교](evidence/recall/review.html) · [데스크톱 캡처](evidence/recall/screenshots/review-1440.png)\n\n이 화면들은 저장된 연구 결과를 표시합니다. 모바일 캡처를 포함한 전체 원본은 EVIDENCE_DOWNLOADS.md에 연결했습니다.\n').encode(), {'generated':'prior figures and current review index'})

# Current docs get local targets where bundled; otherwise pin to the exact source.
# Original archived Markdown is historical and remains byte-for-byte intact.
repo_dirs={posixpath.dirname(p) for p in tree}
for p in list(tree):
    par=posixpath.dirname(p)
    while par: repo_dirs.add(par);par=posixpath.dirname(par)
rewritten=[];unresolved=[]
def target_for(owner,url):
    if urlsplit(url).scheme or url.startswith(('#','//','data:')): return url
    parts=urlsplit(url); target=posixpath.normpath(posixpath.join(posixpath.dirname(owner),unquote(parts.path)))
    if target in files:return url
    if target in tree or target in repo_dirs:
        fixed=BLOB+quote(target,safe='/')+('#'+parts.fragment if parts.fragment else '')
        rewritten.append({'document':owner,'old':url,'new':fixed}); return fixed
    unresolved.append({'document':owner,'target':url});return url
for p in list(files):
    if p.endswith('.md') and (p.startswith('docs/') or p=='README.md'):
        s=files[p].decode(); chunks=re.split(r'(```[\s\S]*?```)',s); s=''.join(chunk if chunk.startswith('```') else re.sub(r'(\]\()([^\s)]+)(\))',lambda m:m[1]+target_for(p,m[2])+m[3],chunk) for chunk in chunks)
        files[p]=s.encode()
if unresolved:
    print(json.dumps({'unresolved':unresolved[:30]},ensure_ascii=False));raise SystemExit('unresolved current document link')

# Frozen counts and seven learner files must agree with the exact committed source.
r=json.loads(read('artifacts/experiments/ki67-recall-20261113/selection.json'))
feasible=[m['seed'] for m in r['models'] if m.get('selected') is not None]
assert feasible==[20261117]
assert [m['feasible_trials'] for m in r['models']]==[3,0,0]
old=json.loads(read('artifacts/experiments/ki67-recall-20261113/baseline/internal-results.json'))['arms']['lr']['localization']
new=json.loads(read('artifacts/experiments/ki67-recall-20261113/seed-20261117/internal/results.json'))['arms']['lr']['localization']
assert [old[x] for x in ['tp','fp','fn']]==[2531,5297,3888]
assert [new[x] for x in ['tp','fp','fn']]==[3890,30134,2529]
for metrics in [old,new]:
    tp,fp,fn=(metrics[x] for x in ['tp','fp','fn'])
    assert abs(metrics['recall']-tp/(tp+fn))<1e-12
    assert abs(metrics['precision']-tp/(tp+fp))<1e-12
    assert abs(metrics['f1']-2*tp/(2*tp+fp+fn))<1e-12
ids=re.findall(r'^\| (U\d+) \|',files['docs/CONTRIBUTIONS.md'].decode(),re.M)
assert len(ids)==99 and len(set(ids))==99
assert json.loads(files['artifacts/learning/step84-review.json'])['user_response'] is None
learner=[p for p in tree if p.startswith('src/pathology_edge/learner_')]+['tests/learner/test_merge_counterexample.py']
assert len(learner)==7
preserved={}
for p in learner:
    b=read(p);assert files[p]==b;preserved[p]=sha(b)

manifest={'name':NAME,'created_utc':datetime.now(timezone.utc).isoformat(),'document_source_commit':SOURCE,'experiment_state_commit':'8b7f6a2d76d989a2c7311ab50a78cb4be8619f0d','latest_tested_code_commit':'fda5695cac0312889e1355539c475d9d6fcad70d','latest_ci_tests':571,'user_record_range':'U00-U97 (statuses preserved)','pending_user_review':'U98 / STEP84','new_training_run':False,'new_inference_run':False,'user_new_tests_run':False,'public_demo_changed':False,'pr_merged':False,'clinical_validation':False,'whole_wsi_ground_truth_validation':False,'contains_bcdata_raw_inputs_or_cell_coordinates':False,'archive_sources':archives,'learner_files_unchanged':preserved,'metrics_checked':{'recall_A':old,'recall_B':new},'rewritten_missing_local_links':rewritten,'historical_scope':'historical/U86 and individual evidence are publication snapshots; current docs govern user status. Full source/replay archives linked, not duplicated.','members':[]}
files.pop('manifest.json',None);origins.pop('manifest.json',None)
for p,b in sorted(files.items()): manifest['members'].append({'path':p,'bytes':len(b),'sha256':sha(b),'origin':origins[p]})
add('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode(),{'generated':'integrated inventory; excludes own hash'})
OUT.parent.mkdir(exist_ok=True,parents=True)
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p,b in sorted(files.items()): z.writestr(p,b)
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    for row in manifest['members']: assert sha(z.read(row['path']))==row['sha256']
report={'file':NAME,'bytes':OUT.stat().st_size,'sha256':sha(OUT.read_bytes()),'members':len(files),'document_source_commit':SOURCE,'zip_crc':'passed','all_member_hashes':'passed','user_authored_files_unchanged':7,'pending_user_review':'U98','new_training_run':False,'new_inference_run':False}
Path('work/u97-handoff/build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
