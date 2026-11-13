"""Publish completed learned-center evidence, excluding BCData raw data/coordinates.

Run after all six independent audits and viewer export. The output must be new.
Screenshots, final review and documentation can then be added before sealing the ZIP.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from pathology_edge.ki67_center_experiment import checked,verify_selection
from pathology_edge.ki67_experiment import sha,read_json,fresh_json


USER_FILES=('src/pathology_edge/learner_coordinates.py','src/pathology_edge/learner_metrics.py',
    'src/pathology_edge/learner_split.py','src/pathology_edge/learner_losses.py',
    'src/pathology_edge/learner_wsi.py','src/pathology_edge/learner_refinement.py',
    'tests/learner/test_merge_counterexample.py')


def package(run,initial,output):
    run,p=checked(run);verify_selection(run)
    initial,output=Path(initial),Path(output)
    models=read_json(run/'selection.json')['models']
    for m in models:
        for tag in ('internal','external'):
            audit=read_json(run/f'seed-{m["seed"]}'/tag/'independent-audit.json')
            if not audit['all_checks_passed']:raise ValueError('Incomplete independent audit')
    if not read_json(run/'review-export.json')['all_replays_exact']:raise ValueError('Viewer replay failed')
    output.mkdir(parents=True,exist_ok=False)
    def copy(src,dest):
        dest=output/dest;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    for name in ('protocol.json','selection.json','selection-lock.json','review.html','review-export.json'):
        copy(run/name,name)
    for source in (run/'frozen_source/pathology_edge').glob('*.py'):copy(source,'frozen_source/pathology_edge/'+source.name)
    copy('src/pathology_edge/ki67_center_inference.py','frozen_source/pathology_edge/ki67_center_inference.py')
    for name in ('infer_ki67_centers.py','audit_auto_ki67.py','run_ki67_centers.py','export_ki67_centers_review.py'):
        copy('scripts/'+name,'scripts/'+name)
    parent=Path(p['parent']);previous=Path(p['external'])
    for scope,folder in [('internal',parent),('external',previous)]:copy(folder/'results.json','baseline/'+scope+'-results.json')
    copy('artifacts/experiments/ki67-candidate-filter-20261113/patherea-results.json','previous-filter/internal-results.json')
    copy('artifacts/experiments/ki67-candidate-filter-20261113/bcdata-results.json','previous-filter/external-results.json')
    classifiers={}
    for name in ('model.json','cnn-20261113.pt','cnn-20261114.pt','cnn-20261115.pt'):
        copy(parent/name,'models/'+name)
        arm='lr' if name=='model.json' else Path(name).stem
        classifiers[arm]=dict(file='models/'+name,sha256=sha(parent/name),kind='logistic' if arm=='lr' else 'cnn')
    for m in models:
        copy(run/m['checkpoint'],'models/'+m['checkpoint'])
        copy(run/f'training-{m["seed"]}.json',f'training-{m["seed"]}.json')
        for tag in ('internal','external'):
            folder=Path(f'seed-{m["seed"]}')/tag
            for name in ('results.json','independent-audit.json'):copy(run/folder/name,folder/name)
            # Patherea is CC BY-NC. Do not distribute individual BCData coordinates.
            if tag=='internal':copy(run/folder/'predictions.json',folder/'predictions.json')
    for name in ('protocol.json','selection.json','selection-lock.json',*[f'training-{s}.json' for s in p['seeds']]):
        copy(initial/name,'initial-relu-validation/'+name)
    for name in initial.glob('detector-*.pt'):copy(name,'initial-relu-validation/'+name.name)
    for name in (initial/'frozen_source/pathology_edge').glob('*.py'):
        copy(name,'initial-relu-validation/frozen_source/pathology_edge/'+name.name)
    for name in ('convergence-diagnostic.json','diagnose_convergence.py'):
        copy(Path('work/learned-centers-20261113')/name,'initial-relu-validation/'+name)
    example='case_0011_region_0_patch_1_O.png'
    copy(Path(p['data_dir'])/'images'/example,'examples/first-case.png')
    for m in models:
        rows=read_json(run/f'seed-{m["seed"]}/internal/predictions.json')
        row=next(r for r in rows if r['image']==example)
        # Example predictions are separable from annotations; CLI needs image only.
        fresh_json(output/f'examples/expected-{m["seed"]}.json',
                   {k:row[k] for k in ('image','points','scores','classes')})
    frozen=output/'frozen_source/pathology_edge'
    bundle=dict(schema='learned-centers-inference.v1',
        detectors=[dict(seed=m['seed'],file='models/'+m['checkpoint'],sha256=m['sha256'],config=m['config']) for m in models],
        classifiers=classifiers,source_hashes={f.name:sha(f) for f in sorted(frozen.glob('*.py'))},
        limits='Research patches only; no clinical or whole-WSI validation; no probability calibration',
        data='Patherea Breast-P1 v1.1; CC BY-NC 4.0; research/noncommercial artifacts')
    fresh_json(output/'inference-bundle.json',bundle)
    preservation=[]
    for name in USER_FILES:
        before=subprocess.check_output(['git','show','4246f020077fcaf707b0c76f55a07868714b4fe8:'+name])
        after=Path(name).read_bytes()
        if before!=after:raise ValueError('User file changed: '+name)
        preservation.append(dict(path=name,sha256=sha(name),unchanged=True))
    fresh_json(output/'user-file-preservation.json',dict(base_commit='4246f020077fcaf707b0c76f55a07868714b4fe8',files=preservation,
        current_experiment_user_implemented=False,current_experiment_user_executed=False,current_experiment_user_reviewed=False))
    # Include confirmed reviews through U93, not new unconfirmed work.
    for n in range(73,80):
        name=f'artifacts/learning/step{n:02d}-review.json'
        raw=subprocess.check_output(['git','show','HEAD:'+name])
        dest=output/'confirmed-user-reviews'/Path(name).name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(raw)
    fresh_json(output/'provenance.json',dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        training_source_commit='583be54b40876dd1ed02e6c80102e03a878cdf58',
        initial_training_source_commit='1465ec8e3a2d28d0d01e1557de5e29d68bdf8732',
        protocol_sha256=sha(run/'protocol.json'),selection_lock_sha256=sha(run/'selection-lock.json'),
        bcdata_coordinates_redistributed=False,clinical_validation=False,whole_wsi_validation=False,
        prior_user_reviews_through='U93; new viewer review pending'))
    (output/'requirements-inference.txt').write_text('numpy==2.5.4\nscipy==1.18.1\nPillow==13.0.0\ntorch==2.15.0\n')
    print(json.dumps(dict(output=str(output),detectors=len(models),classifiers=len(classifiers))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','initial','output'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();package(a.run,a.initial,a.output)
