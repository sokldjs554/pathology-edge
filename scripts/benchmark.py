"""Fresh process per case/backend; synthetic input is for engineering timing only."""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
from time import perf_counter
import numpy as np
from pathology_edge.patches import grid,extract


def worker(size,backend,threads):
    image=np.random.default_rng(42).integers(0,256,(size,size,3),dtype=np.uint8)
    patches=grid(size,size,128,64)
    expected=extract(image,patches)
    actual=extract(image,patches,backend,threads)
    assert np.array_equal(expected,actual)
    digest=hashlib.sha256(actual.tobytes()).hexdigest()
    del actual,expected; gc.collect()
    times=[]
    for _ in range(9):
        start=perf_counter(); a=extract(image,patches,backend,threads); times.append(perf_counter()-start)
        del a
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform=='darwin':rss/=1024
    return dict(size=size,backend=backend,threads=threads,patch_count=len(patches),
                median_ms=statistics.median(times)*1000,measurements_ms=[x*1000 for x in times],
                peak_process_rss_mib=rss/1024,sha256=digest,equal_to_python=True,
                memory_scope='absolute worker peak including parity check with both outputs resident')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--size',type=int);p.add_argument('--backend');p.add_argument('--threads',type=int);args=p.parse_args()
    if args.worker:
        print(json.dumps(worker(args.size,args.backend,args.threads)))
    else:
        rows=[]
        for size in [512,2048]:
            for backend,threads in [('python',1),('cpp',1),('cpp',2),('cpp',4)]:
                cmd=[sys.executable,__file__,'--worker','--size',str(size),'--backend',backend,'--threads',str(threads)]
                rows.append(json.loads(subprocess.check_output(cmd)))
        result=dict(rows=rows,platform=platform.platform(),cpu_count=os.cpu_count(),
                    input='seeded random uint8 RGB, not pathology accuracy evidence',
                    timing_scope='allocation + crop copy + white padding; no inference or disk I/O',
                    repeats=9,warmups=1)
        Path('artifacts').mkdir(exist_ok=True)
        Path('artifacts/benchmark.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
