"""Local API smoke test. Send only with real measurements in an actual integration."""
import json,time,os,urllib.request
from pathlib import Path
p=json.loads((Path(__file__).parent/'example-payload.json').read_text());p['timestamp']=time.time()
r=urllib.request.Request('http://localhost:8000/api/ingest',data=json.dumps(p).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['MICROGRID_DEVICE_TOKEN']})
print(urllib.request.urlopen(r).read().decode())
