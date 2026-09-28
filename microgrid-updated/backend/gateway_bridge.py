"""Forward measurements from YOUR existing HTTP sensor gateway; generates no values.
Source must return one JSON object matching example-payload.json, with actual measurement
timestamps and units. Existing timestamps are preserved. No API or hardware is preconnected.
"""
import argparse,json,os,time,urllib.request,urllib.error
p=argparse.ArgumentParser();p.add_argument('--source',required=True,help='Your sensor gateway URL');p.add_argument('--target',default='http://127.0.0.1:8000/api/ingest');p.add_argument('--interval',type=float,default=2);a=p.parse_args()
token=os.environ.get('MICROGRID_DEVICE_TOKEN')
if not token:raise SystemExit('Set MICROGRID_DEVICE_TOKEN to the same token used by the backend')
last={}
while True:
 try:
  headers={};source_token=os.environ.get('MICROGRID_GATEWAY_TOKEN')
  if source_token:headers['Authorization']='Bearer '+source_token
  with urllib.request.urlopen(urllib.request.Request(a.source,headers=headers),timeout=8) as response:r=json.load(response)
  if not isinstance(r,dict):raise ValueError('Gateway must return one reading object')
  key=r['device_id'];timestamp=r['timestamp']
  if last.get(key)!=timestamp:
   req=urllib.request.Request(a.target,data=json.dumps(r).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
   with urllib.request.urlopen(req,timeout=8) as response:response.read()
   last[key]=timestamp;print('Forwarded reading for',key,flush=True)
 except urllib.error.HTTPError as e:print('HTTP status',e.code,'check timestamp, units and authentication',flush=True)
 except (ValueError,KeyError,urllib.error.URLError,TimeoutError) as e:print('Gateway unavailable or invalid reading:',type(e).__name__,flush=True)
 time.sleep(max(.5,a.interval))
