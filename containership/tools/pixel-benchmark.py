"""Deterministic observational microbenchmark, not a performance qualification."""
from pathlib import Path
import hashlib,json,platform,statistics,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'hull'),str(ROOT/'ship')]
from pa21studio import fabric_tif as T,fabric_gif as G,pixel_kernel as K
import PIL
slots=[b'benchmark',b'',bytes(range(64)),bytes(range(256)),bytes(range(256)),bytes(range(16)),b'',b'']
b=T.build_blob({'version':1,'monotonic':0,'clock':0,'slots':slots})
def measure(fn,n):
 samples=[]
 for _ in range(n):
  start=time.perf_counter_ns();fn();samples.append((time.perf_counter_ns()-start)/1e6)
 return {'iterations':n,'median_ms':statistics.median(samples),'p95_ms':sorted(samples)[int(.95*(len(samples)-1))],'total_ms':sum(samples)}
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'state.tif';g=Path(d)/'state.gif';q=Path(d)/'restored.tif';rows=[]
 for comp in ('raw','tiff_deflate','tiff_lzw','packbits'):
  T.write_tif(b,p,compression=comp);size=p.stat().st_size
  r=measure(lambda:T.read_tif(p),500);w=measure(lambda:T.write_tif(b,p,compression=comp),100)
  rows.append({'compression':comp,'bytes':size,'read':r,'write_verified_atomic':w})
 T.write_tif(b,p);G.export_tiff(p,g);G.restore_tiff(g,q)
 assert T.read_tif(q)['blob']==b
 kernel=measure(lambda:K.apply(b,[{'tile':0,'word':0,'op':'xor','value':255}]),1000)
 print(json.dumps({'schema':'UC/PIXEL_BENCH/1','platform':platform.platform(),'python':platform.python_version(),'Pillow':PIL.__version__,
  'blob_bytes':len(b),'tiff_bytes':p.stat().st_size,'gif_bytes':g.stat().st_size,'restored_exact':True,'measurements':rows,
  'kernel_xor':kernel,'qualification':'Single-host observation; no speedup claim against the prior codec; full histories cost more work.'},indent=2))
