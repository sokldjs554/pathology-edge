#!/usr/bin/env python3
"""Frozen36-FOV supplement to the immutable NuCLS15-FOV evidence.

Input --base is an extracted earlier evidence archive (or original work root).
This executable never writes under base, edits raw data, or retunes a model.
"""
import argparse,csv,hashlib,importlib.util,json,os,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from PIL import Image

MODELS={'small_vit':'0bb2af67ca4d4e403e5789359feb6b284f9207e6c7eb9bf4e521b7d0972f5898','small_vit_refined':'b9d3892a257a06ed0b67bd4e8717a331d457272531b3501fadf1fbacd70f004f'}
BASE_PROTOCOL_SHA='0623d24445f886733f02fe81d17a808d330e6f23fe599c55a2f99c6e85b60b63'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False))
def support_module(base,expected):
 path=base/'evaluation/support.py'
 if sha(path)!=expected:raise ValueError('Base annotation policy changed')
 spec=importlib.util.spec_from_file_location('frozen_nucls_support',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def freeze(base,out):
 from pathology_edge.annotation_grid import AnnotationGrid
 if out.exists() or out.is_relative_to(base):raise ValueError('Use a fresh output outside the base evidence')
 oldp=json.loads((base/'evaluation/protocol.json').read_text());oldr=json.loads((base/'evaluation/results.json').read_text())
 if sha(base/'evaluation/protocol.json')!=BASE_PROTOCOL_SHA or oldp['models']!=MODELS or oldp['threshold']!=.35:raise ValueError('Unexpected base experiment')
 if oldr['protocol_sha256']!=BASE_PROTOCOL_SHA or not json.loads((base/'evaluation/status.json').read_text())['completed']:raise ValueError('Base run incomplete')
 support=support_module(base,oldp['support_sha256'])
 for a,digest in MODELS.items():
  if sha(base/'evaluation/models'/f'{a}.pt')!=digest:raise ValueError('Checkpoint changed')
 manifest=json.loads((base/'annotation-acquisition.json').read_text())
 for a in manifest:
  if sha(base/a['path'])!=a['sha256']:raise ValueError('Raw asset changed')
 acq=json.loads((base/'original-acquisition.json').read_text())
 if len(acq['cases'])!=5 or any(not c['original_stream']['reference_md5_verified'] for c in acq['cases']):raise ValueError('Original provenance incomplete')
 links={r['id']:r for c in acq['cases'] for r in c['rows']}
 olditems={r['id']:r for r in oldp['images']};oldrows={r['id']:r for r in oldr['rows']}
 out.mkdir(parents=True)
 for name in ['labels','annotations','predictions','source/pathology_edge']:(out/name).mkdir(parents=True)
 for p in (base/'evaluation/source/pathology_edge').glob('*.py'):
  if sha(p)!=oldp['source_sha256'].get(p.name):raise ValueError('Frozen model source differs')
  shutil.copy2(p,out/'source/pathology_edge'/p.name)
 grid_path=Path(__file__).resolve().parents[1]/'src/pathology_edge/annotation_grid.py'
 shutil.copy2(grid_path,out/'source/pathology_edge/annotation_grid.py');shutil.copy2(__file__,out/'runner.py')
 rows=[]
 for key,name in enumerate(sorted(links)):
  link=links[name];image_path=base/link['original_path']
  if sha(image_path)!=link['original_sha256']:raise ValueError('Original crop changed')
  mask=np.asarray(Image.open(base/'raw/mask'/(name+'.png')));csvpath=base/'raw/csv'/(name+'.csv');anns=list(csv.DictReader(csvpath.open()))
  wh=Image.open(image_path).size
  if wh!=Image.open(base/'raw/rgb'/(name+'.png')).size:raise ValueError('Original/provided RGB frame differs')
  if link['rgb_correlation']<.99 or max(map(abs,link['phase_shift_xy']))>1:raise ValueError('Unverified source alignment')
  grid=AnnotationGrid((mask.shape[1],mask.shape[0]),wh)
  target,valid,base_valid,coverage=support.annotation_support(mask,anns)
  aligned_mask,at,av,ab=[grid.resample(x) for x in (mask,target,valid,base_valid)]
  source_tuples=set(map(tuple,np.unique(mask.reshape(-1,3),axis=0)));new_tuples=set(map(tuple,np.unique(aligned_mask.reshape(-1,3),axis=0)))
  if not new_tuples<=source_tuples:raise ValueError('New categorical tuple')
  fg=lambda a:(a[...,0]>=1)&(a[...,0]<=12)
  ids=lambda a:set(map(tuple,np.unique(a[fg(a)],axis=0)))
  if ids(mask)!=ids(aligned_mask) or not np.array_equal(at,fg(aligned_mask)):raise ValueError('Nuclear identity lost or inconsistent target')
  if np.any(av&np.isin(aligned_mask[...,0],[0,99])):raise ValueError('Ignored code became evaluated')
  label=f'labels/{key:02d}.npz';np.savez_compressed(out/label,target=at,valid=av,base_valid=ab)
  transformed=[]
  for a in anns:
   x=[float(v) for v in a['coords_x'].split(',')];y=[float(v) for v in a['coords_y'].split(',')]
   # CSV integer image indices are treated as pixel centers for display only.
   points=grid.to_target_edges(np.column_stack([x,y])+.5)-.5
   transformed.append(dict(type=a['type'],raw_classification=a['raw_classification'],coords_xy_centers=points.tolist()))
  annpath=f'annotations/{key:02d}.json';save(out/annpath,dict(source_csv_sha256=sha(csvpath),mapping='target_index=(source_index+0.5)*target_size/source_size-0.5',rows=transformed,metrics_use='Same sampled original support masks, not a second rasterization of display vertices'))
  reuse=None
  if grid.is_identity:
   if name not in olditems:raise ValueError('Equal-shape case missing from old15')
   old=olditems[name]
   if link['original_sha256']!=old['inputs']['original']['sha256']:raise ValueError('Reused input differs')
   with np.load(base/'evaluation'/old['label'],allow_pickle=False) as z:
    if any(not np.array_equal(arr,z[k]) for k,arr in [('target',at),('valid',av),('base_valid',ab)]):raise ValueError('Identity changed old labels')
   reuse={a:{'path':'evaluation/'+oldrows[name]['inputs']['original'][a]['probability'],'sha256':oldrows[name]['inputs']['original'][a]['sha256']} for a in MODELS}
   for item in reuse.values():
    if sha(base/item['path'])!=item['sha256']:raise ValueError('Reused predictions changed')
  elif name in olditems:raise ValueError('Old15 unexpectedly transformed')
  rows.append(dict(key=f'{key:02d}',id=name,case_id=link['case_id'],input=link['original_path'],input_sha256=link['original_sha256'],grid=grid.metadata(),level0_bounds=link['bounds_level0'],label=label,label_sha256=sha(out/label),display_annotations=annpath,display_annotations_sha256=sha(out/annpath),source_coverage=coverage,valid_pixels=int(av.sum()),foreground_pixels=int((at&av).sum()),reuse=reuse))
 if len(rows)!=51 or sum(r['grid']['identity'] for r in rows)!=15:raise ValueError('Unexpected dataset membership')
 p=dict(created_utc=datetime.now(timezone.utc).isoformat(),models=MODELS,threshold=.35,mode='no_overlap',patch_size=128,boundary_radius=8,images=rows,image_count=51,case_count=5,new_inference_fovs=36,reused_fovs=15,base_protocol_sha256=BASE_PROTOCOL_SHA,base_results_sha256=sha(base/'evaluation/results.json'),base_original_acquisition_sha256=sha(base/'original-acquisition.json'),base_annotation_acquisition_sha256=sha(base/'annotation-acquisition.json'),support_sha256=oldp['support_sha256'],source_sha256={p.name:sha(p) for p in sorted((out/'source/pathology_edge').glob('*.py'))},runner_sha256=sha(out/'runner.py'),primary='Author-guided categorical grid normalization to fixed RGB; sampled existing support policy',historical_exporter_reproduced=False,registration_optimized_using_predictions=False,training_run=False,clinical_validation=False,whole_wsi_validation=False,previous_external_patient_overlap=['TCGA-A1-A0SP'])
 save(out/'protocol.json',p)
 return p

def aggregate(rows):
 result={}
 for subset,group in [('all51',rows),('previous15',[r for r in rows if r['reused']]),('new36',[r for r in rows if not r['reused']])]:
  result[subset]={}
  for region in ['all','boundary','interior','mask_only_support']:
   case_ids=sorted({r['case_id'] for r in group});cases={c:{a:float(np.mean([r['models'][a]['metrics'][region]['dice'] for r in group if r['case_id']==c])) for a in MODELS} for c in case_ids}
   means={a:float(np.mean([r['models'][a]['metrics'][region]['dice'] for r in group])) for a in MODELS}
   delta=[r['models']['small_vit_refined']['metrics'][region]['dice']-r['models']['small_vit']['metrics'][region]['dice'] for r in group]
   result[subset][region]=dict(fovs=len(group),cases=len(case_ids),fov_macro=means,delta=means['small_vit_refined']-means['small_vit'],case_means=cases,case_macro={a:float(np.mean([cases[c][a] for c in case_ids])) for a in MODELS},wins_ties_losses=[sum(x>0 for x in delta),sum(x==0 for x in delta),sum(x<0 for x in delta)])
 return result

def worker(base,out):
 import torch,cv2,scipy
 from pathology_edge.model_comparison import build_model
 from pathology_edge.experiment import predict,environment
 from pathology_edge.metrics import binary_metrics
 from pathology_edge.patches import boundary_mask
 if (out/'results.json').exists() or any((out/'predictions').iterdir()):raise ValueError('Refuse to overwrite an existing or partial inference run')
 p=json.loads((out/'protocol.json').read_text())
 if p['models']!=MODELS or p['threshold']!=.35 or sha(out/'runner.py')!=p['runner_sha256']:raise ValueError('Frozen run changed')
 if {x.name:sha(x) for x in (out/'source/pathology_edge').glob('*.py')}!=p['source_sha256']:raise ValueError('Frozen sources changed')
 if sha(base/'evaluation/protocol.json')!=p['base_protocol_sha256'] or sha(base/'evaluation/results.json')!=p['base_results_sha256']:raise ValueError('Base evidence changed')
 torch.set_num_threads(4);cv2.setNumThreads(1);torch.use_deterministic_algorithms(True)
 models={}
 for a,digest in MODELS.items():
  path=base/'evaluation/models'/f'{a}.pt'
  if sha(path)!=digest:raise ValueError('Model changed')
  m=build_model(a);m.load_state_dict(torch.load(path,map_location='cpu',weights_only=True));models[a]=m.eval()
 rows=[];new=0
 for item in p['images']:
  if sha(base/item['input'])!=item['input_sha256'] or sha(out/item['label'])!=item['label_sha256']:raise ValueError('Input changed')
  image=np.asarray(Image.open(base/item['input']).convert('RGB')).copy()
  with np.load(out/item['label'],allow_pickle=False) as z:t,v,b=z['target'],z['valid'],z['base_valid']
  seam=boundary_mask(t.shape);regions={'all':v,'boundary':v&seam,'interior':v&~seam,'mask_only_support':b}
  row=dict(id=item['id'],key=item['key'],case_id=item['case_id'],reused=item['reuse'] is not None,models={})
  for a,m in models.items():
   if item['reuse']:
    asset=item['reuse'][a]
    if sha(base/asset['path'])!=asset['sha256']:raise ValueError('Cached probability changed')
    with np.load(base/asset['path'],allow_pickle=False) as z:prob=z['probability']
    reference=dict(root='base',path=asset['path'],sha256=asset['sha256']);seconds=None
   else:
    prediction=predict(m,image,mode='no_overlap',threshold=.35);prob=prediction['probability'];seconds=prediction['seconds'];new+=1
    filename=f"predictions/{item['key']}-{a}.npz";np.savez_compressed(out/filename,probability=prob);reference=dict(root='supplement',path=filename,sha256=sha(out/filename))
   if prob.shape!=t.shape or not np.isfinite(prob).all() or (prob<0).any() or (prob>1).any():raise ValueError('Invalid probability')
   row['models'][a]=dict(probability=reference,metrics={name:binary_metrics(prob>=.35,t,reg) for name,reg in regions.items()},descriptive_seconds=seconds)
  rows.append(row);print(json.dumps(dict(completed=len(rows),new_inferences=new,case=item['case_id'])),flush=True)
 result=dict(protocol_sha256=sha(out/'protocol.json'),rows=rows,summary=aggregate(rows),new_inference_runs=new,reused_predictions=30,environment=dict(**environment(),scipy=scipy.__version__),training_run=False,clinical_validation=False,whole_wsi_validation=False,timing_scope='Single execution of newly admitted36 original crops, not a controlled speed benchmark')
 save(out/'results.json',result);save(out/'status.json',dict(completed=True,new_inference_runs=new,reused_predictions=30))
 print(json.dumps(result['summary']['all51']),flush=True)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--worker',action='store_true');a=parser.parse_args();base=a.base.resolve();out=a.output.resolve()
 if a.worker:worker(base,out);return
 freeze(base,out)
 env=dict(os.environ,PYTHONPATH=str(out/'source'),PYTHONDONTWRITEBYTECODE='1')
 result=subprocess.run([sys.executable,str(out/'runner.py'),'--base',str(base),'--output',str(out),'--worker'],env=env)
 if result.returncode:save(out/'status.json',dict(completed=False,returncode=result.returncode))
 raise SystemExit(result.returncode)
if __name__=='__main__':main()
