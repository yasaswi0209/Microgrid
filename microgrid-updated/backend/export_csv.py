import argparse,csv,json,sqlite3
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--device',required=True);p.add_argument('--source',choices=['live','simulation'],default='live');p.add_argument('--output',default='training.csv');a=p.parse_args()
c=sqlite3.connect(Path(__file__).parent/'telemetry.sqlite3')
fields=['timestamp','device_id','solar','load','temperature','soc']
rows=[json.loads(r[0]) for r in c.execute('SELECT data FROM readings WHERE device=? AND source=? ORDER BY ts',(a.device,a.source))]
with open(a.output,'w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for r in rows:
  if r['quality']=='good' and all(r.get(k) is not None for k in fields):w.writerow({k:r[k] for k in fields})
print('Exported',a.output)
