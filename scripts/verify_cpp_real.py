"""Check native backend on frozen model and all held-out real images, without retuning."""
import json
from pathlib import Path
import numpy as np
import torch
from pathology_edge.data import load_image
from pathology_edge.experiment import predict,load_records
from pathology_edge.model import TinyUNet

torch.set_num_threads(4)
model=TinyUNet();model.load_state_dict(torch.load('artifacts/model.pt',weights_only=True))
metadata=json.loads(Path('artifacts/training.json').read_text())
rows=[]
for row in load_records('data'):
    if row['split']!='test':continue
    image=load_image(Path('data')/row['image'])
    for mode in ['no_overlap','overlap']:
        expected=np.load(f'artifacts/predictions/{mode}/{row["id"]}.npy')
        actual=predict(model,image,mode,metadata['threshold'],'cpp',4)['probability']
        np.testing.assert_array_equal(expected,actual)
        rows.append(dict(id=row['id'],mode=mode,max_absolute_difference=float(np.abs(expected-actual).max())))
Path('artifacts/cpp_real_parity.json').write_text(json.dumps(dict(model_sha256=metadata['model_sha256'],images=7,comparisons=rows,passed=True),indent=2))
print('PASS: 14 real-image probability maps match bit for bit (Python vs C++ 4 threads).')
