"""Check completed center-training records/locks without fitting or inference."""
import argparse
from datetime import datetime
import math
from pathlib import Path
from pathology_edge.ki67_center_experiment import checked,verify_selection
from pathology_edge.ki67_experiment import read_json,fresh_json,sha


def audit(run):
    run,p=checked(run);lock=verify_selection(run)
    models=read_json(run/'selection.json')['models']
    if [m['seed'] for m in models]!=p['seeds']:raise ValueError('Seed set/order changed')
    checked_trials=0
    for model in models:
        report=read_json(run/f'training-{model["seed"]}.json');history=report['history']
        if [e['epoch'] for e in history]!=list(range(1,17)):raise ValueError('Incomplete epoch history')
        for e in history:
            if len(e['trials'])!=12:raise ValueError('Incomplete configuration grid')
            found=set()
            for trial in e['trials']:
                cfg=trial['config'];found.add((cfg['threshold'],cfg['min_distance']))
                cases=list(trial['cases'].values())
                if len(cases)!=4:raise ValueError('Validation case count changed')
                if sum(c['tp']+c['fn'] for c in cases)!=2802:raise ValueError('Validation reference count changed')
                for key in ('f1','recall'):
                    actual=math.fsum(c[key] for c in cases)/4
                    if not math.isclose(actual,trial['case_macro_'+key],rel_tol=0,abs_tol=1e-12):raise ValueError('Case macro changed')
                checked_trials+=1
            if found!={(t,d) for t in p['thresholds'] for d in p['min_distances']}:raise ValueError('Grid changed')
            best=max(e['trials'],key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],t['config']['threshold'],t['config']['min_distance']))
            if any(e[k]!=best[k] for k in ('config','cases','case_macro_f1','case_macro_recall')):raise ValueError('Within-epoch selection mismatch')
        chosen=max(history,key=lambda e:(e['case_macro_f1'],e['case_macro_recall'],-e['epoch'],e['config']['threshold'],e['config']['min_distance']))
        if chosen['epoch']!=model['best_epoch'] or chosen['config']!=model['config'] or chosen['case_macro_f1']!=model['validation_case_macro_f1']:
            raise ValueError('Best epoch mismatch')
        if {k:v for k,v in report.items() if k!='history'}!=model:raise ValueError('Selection report mismatch')
        if sha(run/model['checkpoint'])!=model['sha256']:raise ValueError('Checkpoint hash changed')
    locktime=datetime.fromisoformat(lock['created_utc'])
    stage_times={}
    for tag in ('internal','external'):
        started=read_json(run/(tag+'-started.json'))['created_utc'];stage_times[tag]=started
        if datetime.fromisoformat(started)<=locktime:raise ValueError('Evaluation started before selection lock')
    return dict(all_checks_passed=True,seed_count=len(models),epochs_per_seed=16,configuration_trials=checked_trials,
                validation_cases=4,validation_centers=2802,selection_lock_created_utc=lock['created_utc'],evaluation_starts=stage_times,
                new_training=False,new_inference=False,scope='Stored history arithmetic, policy, hashes and stage timestamps; not a replay of every training epoch')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=audit(a.run);fresh_json(a.output,r);print(r)
