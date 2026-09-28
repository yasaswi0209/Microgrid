from dataset_chat import answer as dataset_answer
from question_bank import catalog
import argparse,json,math,os,sqlite3,threading,time,hmac,csv,io
from functools import lru_cache
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from engine import Engine,validate
ROOT=Path(__file__).resolve().parent
DB=Path(os.getenv('MICROGRID_DB',str(ROOT/'telemetry.sqlite3')))
STARTED=time.time()
CHANGED=threading.Condition()
REVISION=0
CACHE={}
LOCK=threading.RLock()
ENGINES={}; MODELS={}; MODEL_ERROR=None
try:
 import joblib
 if (ROOT/'model.joblib').exists(): MODELS=joblib.load(ROOT/'model.joblib')
except Exception as e: MODEL_ERROR=str(e)
SCENARIO='normal'
def connect():
 c=sqlite3.connect(DB,timeout=10); c.execute('PRAGMA busy_timeout=10000'); c.row_factory=sqlite3.Row; return c
with connect() as c:
 c.execute('PRAGMA journal_mode=WAL')
 c.executescript('CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY, device TEXT, source TEXT, ts REAL, data TEXT, UNIQUE(device,source,ts)); CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, device TEXT, source TEXT, factor TEXT, status TEXT, opened REAL, updated REAL, data TEXT); CREATE INDEX IF NOT EXISTS readings_source_device_ts ON readings(source,device,ts DESC); CREATE INDEX IF NOT EXISTS alerts_source_device_status ON alerts(source,device,status);')
LIVE_RULES=None
if os.getenv('MICROGRID_RULES'):
 LIVE_RULES=json.loads(Path(os.environ['MICROGRID_RULES']).read_text())
 Engine(LIVE_RULES)
def _ingest(r):
 validate(r)
 if r['source']=='live' and r['timestamp']<time.time()-30:raise ValueError('Live reading is older than 30 seconds; synchronize device clock')
 if r['timestamp']>time.time()+30: raise ValueError('Timestamp too far in future')
 with LOCK,connect() as c:
  old=c.execute('SELECT data,ts FROM readings WHERE device=? AND source=? ORDER BY ts DESC LIMIT 1',(r['device_id'],r['source'])).fetchone()
  if old and r['timestamp']<=old['ts']: raise ValueError('Duplicate or out-of-order reading')
  previous=json.loads(old['data']) if old else None
  rules= None if r['source']=='simulation' else LIVE_RULES or []
  engine=ENGINES.setdefault((r['device_id'],r['source']),Engine(rules))
  valid=r['quality']=='good'
  r['threshold_status']='Unvalidated demonstration limits' if r['source']=='simulation' else 'Configured equipment limits' if LIVE_RULES else 'Equipment limits not configured'
  dt=r['timestamp']-previous['timestamp'] if previous else 0
  energy=previous.get('energy_kwh',0) if previous else 0
  integrated=bool(previous and valid and previous['quality']=='good' and 0<dt<=30 and r.get('load') is not None and previous.get('load') is not None)
  r['energy_kwh']=energy+(r['load']+previous['load'])/2*dt/3600 if integrated else energy
  r['energy_status']='Integrated over valid contiguous intervals' if integrated else 'Gap or insufficient samples; interval not integrated'
  ks=['solar','wind','grid','battery','load','losses']
  r['balance_residual']=round(r['solar']+r['wind']+r['grid']+r['battery']-r['load']-r['losses'],3) if valid and all(r.get(k) is not None for k in ks) else None
  r['soc_decline_per_min']=round((previous['soc']-r['soc'])*60/dt,3) if previous and previous['quality']=='good' and valid and dt>0 and dt<=30 and previous.get('soc') is not None and r.get('soc') is not None else None
  predictions=[]
  for target in ['solar','load']:
   if valid and r.get(target) is not None:
    model=MODELS.get(target)
    features=[r.get(k) for k in ['solar','load','temperature','soc']]
    usable=model is not None and MODELS.get('device_id')==r['device_id'] and all(v is not None for v in features)
    value=float(model.predict([features])[0]) if usable else r[target]
    predictions.append(dict(target=target,value=round(max(0,value),3),issued_at=r['timestamp'],target_at=r['timestamp']+60,horizon_seconds=60,method='Random Forest' if usable else 'Persistence baseline',model_version=MODELS.get('version') if usable else None))
  r['predictions']=predictions
  # Compare an actual measurement only with forecasts issued before its target time.
  forecast_row=c.execute('SELECT data FROM readings WHERE device=? AND source=? AND ts<=? ORDER BY ts DESC LIMIT 1',(r['device_id'],r['source'],r['timestamp']-60)).fetchone()
  past=json.loads(forecast_row[0]) if forecast_row else None
  actual_prediction=next((p for p in past.get('predictions',[]) if p['target']=='solar'),None) if past else None
  shortfall=None
  if valid and actual_prediction and abs(r['timestamp']-actual_prediction['target_at'])<=10 and r.get('solar') is not None:
   expected=actual_prediction['value']
   if expected>.1:shortfall=max(0,(expected-r['solar'])/expected*100)
  deficit=max(0,predictions[1]['value']-predictions[0]['value']) if len(predictions)==2 else None
  r['generation_shortfall_pct']=shortfall
  r['forecast_deficit_kw']=deficit
  r['converter_loss_pct']=max(0,(r['converter_input_kw']-r['converter_output_kw'])/r['converter_input_kw']*100) if valid and r.get('converter_input_kw',0)>.1 and r.get('converter_output_kw') is not None else None
  risk=engine.assess(r if valid else {**r,**{rule[0]:None for rule in engine.rules}})
  risk['assessment_timestamp']=r['timestamp']
  risk['source']='Measured telemetry compared with configured equipment rules' if r['source']=='live' else 'Simulation with unvalidated demonstration limits'
  risk['formula']='100 × sum(weight × severity) / sum(available weights); critical factor overrides status'
  r['risk']=risk
  r['ml_anomaly']=None
  if valid and MODELS.get('device_id')==r['device_id'] and MODELS.get('anomaly') is not None and all(r.get(k) is not None for k in ['solar','load','temperature','soc']):
   features=[[r[k] for k in ['solar','load','temperature','soc']]]
   r['ml_anomaly']={'unusual':bool(MODELS['anomaly'].predict(features)[0]==-1),'decision_score':float(MODELS['anomaly'].decision_function(features)[0]),'method':'Isolation Forest','note':'Statistical deviation, not a fault probability'}
  # Additional factors enter the index only if their necessary measurements exist.
  if r['source']=='simulation':
   additional=[('soc_decline_per_min','SOC decline','%/min',None,None,1,3,1,'Inspect sustained discharge and SOC measurements.'),('generation_shortfall_pct','Generation shortfall','%',None,None,20,50,1,'Inspect shading, weather and PV output; baseline errors can also cause deviation.'),('forecast_deficit_kw','Forecast supply deficit','kW',None,None,2,5,1,'Review available grid and battery capacity.'),('converter_loss_pct','Converter losses','%',None,None,10,20,2,'Inspect converter input/output metering and thermal condition.')]
   optional=ENGINES.setdefault((r['device_id'],r['source'],'derived'),Engine(additional))
   extra=optional.assess(r if valid else {**r,**{a[0]:None for a in additional}})
   combined=risk['factors']+[f for f in extra['factors'] if f['value'] is not None]
   den=sum(f['weight'] for f in combined if f['value'] is not None)
   for f in combined:f['contribution']=round(100*f['weight']*f['severity']/den,1) if den and f['value'] is not None else None
   risk['factors']=combined
   if risk['score'] is not None:risk['score']=round(sum(f['contribution'] or 0 for f in combined),1)
   if any(f['severity']>=1 for f in combined):risk['level']='Critical'
   elif risk['score'] is not None and any(f['active'] for f in combined):risk['level']='Warning'
  r['recommendations']=['Rule-based advisory only; no hardware commands are sent.']
  if r.get('soc') is not None and r['soc']<25: r['recommendations'].append('Review grid charging and defer noncritical demand while preserving battery reserve.')
  if valid and r.get('solar') is not None and r.get('load') is not None:
   r['recommendations'].append('Evaluate battery charging within configured BMS limits.' if r['solar']>r['load'] else 'Evaluate available storage or grid supply to cover demand.')
  for f in risk['factors']:
   a=c.execute("SELECT id FROM alerts WHERE device=? AND source=? AND factor=? AND status!='resolved'",(r['device_id'],r['source'],f['key'])).fetchone()
   if f['active']:
    if a:c.execute('UPDATE alerts SET updated=?,data=? WHERE id=?',(r['timestamp'],json.dumps(f),a['id']))
    else:c.execute('INSERT INTO alerts(device,source,factor,status,opened,updated,data) VALUES(?,?,?,?,?,?,?)',(r['device_id'],r['source'],f['key'],'active',r['timestamp'],r['timestamp'],json.dumps(f)))
   elif a and f['status']=='Normal': c.execute("UPDATE alerts SET status='resolved',updated=? WHERE id=?",(r['timestamp'],a['id']))
  c.execute('INSERT INTO readings(device,source,ts,data) VALUES(?,?,?,?)',(r['device_id'],r['source'],r['timestamp'],json.dumps(r)))
 return r

def signal_change():
 global REVISION
 with CHANGED:
  REVISION+=1
  CACHE.clear()
  CHANGED.notify_all()

def ingest(r):
 # Commit measurements before notifying clients. Each new event invalidates shared snapshots.
 with LOCK:
  result=_ingest(r)
  signal_change()
 return result

@lru_cache(maxsize=1)
def dataset_files():
 folder=ROOT/'data'
 return (json.loads((folder/'holdout.json').read_text()),json.loads((folder/'evaluation.json').read_text()))


def _snapshot(mode,device=None):
 if mode=='dataset':
  rows,metrics=dataset_files()
  return dict(history=rows,alerts=[],devices=['CoSSMic-residential3'],device='CoSSMic-residential3',server_time=time.time(),evaluation=metrics)
 source='live' if mode=='live' else 'simulation'
 cache_key=(str(DB),mode,device)
 with LOCK:
  cached=CACHE.get(cache_key)
  if cached and time.monotonic()-cached[0]<5:return cached[1]
 with LOCK,connect() as c:
  devices=[x[0] for x in c.execute('SELECT DISTINCT device FROM readings WHERE source=?',(source,))]
  device=device or (devices[0] if devices else '')
  rows=c.execute('SELECT data FROM readings WHERE source=? AND device=? ORDER BY ts DESC LIMIT 240',(source,device)).fetchall()
  history=[json.loads(x[0]) for x in rows][::-1]
  alerts=[{**dict(x),'data':json.loads(x['data'])} for x in c.execute('SELECT * FROM alerts WHERE source=? AND device=? ORDER BY id DESC LIMIT 50',(source,device))]
 result=dict(history=history,alerts=alerts,devices=devices,device=device,server_time=time.time(),model_error=MODEL_ERROR,model_device=MODELS.get('device_id'),model_version=MODELS.get('version'),rules_configured=bool(LIVE_RULES))
 CACHE[cache_key]=(time.monotonic(),result)
 return result

def snapshot(mode,device=None):
 with LOCK:return _snapshot(mode,device)

def simulate():
 global SCENARIO
 while True:
  t=time.time(); solar=18+2*math.sin(t/90); load=13+.6*math.sin(t/12); battery=-min(4,max(0,solar-load)); losses=.2
  r=dict(device_id='demo-01',component_id='microgrid-bus',source='simulation',timestamp=t,quality='good',voltage=231+2*math.sin(t/10),current=load*1000/(231*.95),temperature=32+math.sin(t/45),converter_temperature=49,soc=82+2*math.sin(t/120),solar=solar,wind=0,load=load,battery=battery,grid=load+losses-solar-battery,losses=losses,humidity=52+math.sin(t/30),wind_speed=3.4)
  if SCENARIO=='overheat':r['temperature']=58
  if SCENARIO=='low-soc':r['soc']=12
  if SCENARIO=='overload':r['current']=105
  if SCENARIO=='missing':r['voltage']=None;r['temperature']=None;r['soc']=None
  r['units']={'voltage':'V','current':'A','temperature':'C','converter_temperature':'C','soc':'%','solar':'kW','wind':'kW','load':'kW','grid':'kW','battery':'kW','losses':'kW','humidity':'%','wind_speed':'m/s'}
  if SCENARIO!='offline':ingest(r)
  time.sleep(2)

class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT.parent/'dist'),**kw)
 def handle(self):
  try:super().handle()
  except (ConnectionError,TimeoutError):
   # Browser refresh/close can abort a response on Windows (WinError 10053).
   self.close_connection=True
 def end_headers(self):
  self.send_header('Cache-Control','no-store')
  super().end_headers()
 def log_message(self,*a):pass
 def json(self,data,status=200):
  b=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):
  p=urlparse(self.path);q=parse_qs(p.query);mode=q.get('mode',['dataset'])[0];device=q.get('device',[None])[0]
  if p.path=='/api/questions':return self.json([{'id':v['id'],'category':v['category'],'question':v['question']} for v in catalog()])
  if p.path=='/api/state':return self.json(snapshot(mode,device))
  if p.path=='/api/health':return self.json({'ok':True,'uptime_seconds':round(time.time()-STARTED),'model_loaded':bool(MODELS),'model_device':MODELS.get('device_id'),'rules_configured':bool(LIVE_RULES),'stream':'event-driven SSE','database':'SQLite WAL','model_error':MODEL_ERROR})
  if p.path=='/api/rules':return self.json({'rules':LIVE_RULES or [],'configured':bool(LIVE_RULES),'source':'MICROGRID_RULES equipment profile','formula':'100 × sum(weight × severity) / sum(available weights)','coverage_required':80,'warning_duration_seconds':5,'critical_override':True})
  if p.path=='/api/export':
   state=snapshot(mode,device);fields=(['timestamp','issued_at','solar','load','grid','solar_prediction','load_prediction'] if mode=='dataset' else ['timestamp','solar','load','grid','voltage','current','temperature','soc','irradiance','efficiency'])
   buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields);writer.writeheader()
   writer.writerows({k:r.get(k) for k in fields} for r in state['history'])
   payload=buf.getvalue().encode();self.send_response(200);self.send_header('Content-Type','text/csv');self.send_header('Content-Disposition','attachment; filename=microgrid-readings.csv');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
  if p.path=='/api/events':
   self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Cache-Control','no-cache');self.end_headers()
   last_ts=None
   try:
    while True:
     with LOCK:
      revision=REVISION
      state=dict(snapshot(mode,device))
     history=state['history']
     if last_ts is not None:
      state['history']=[r for r in history if r['timestamp']>last_ts]
      state['delta']=True
     if history:last_ts=history[-1]['timestamp']
     self.wfile.write(('data: '+json.dumps(state)+'\n\n').encode());self.wfile.flush()
     with CHANGED:CHANGED.wait_for(lambda:REVISION!=revision,timeout=10)
   except (ConnectionError,TimeoutError):pass
   return
  if p.path.startswith('/api/'):return self.json({'error':'Not found'},404)
  return super().do_GET()
 def do_POST(self):
  global SCENARIO
  # Mutations require same-origin browser calls, or a device token for ingestion.
  origin=self.headers.get('Origin')
  if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.json({'error':'Origin rejected'},403)
  try:
   size=int(self.headers.get('Content-Length',0))
   if size<=0 or size>32768:raise ValueError('Invalid payload size')
   r=json.loads(self.rfile.read(size))
   if not isinstance(r,dict):raise ValueError('Payload must be an object')
   if self.path=='/api/chat':
    rows,metrics=dataset_files()
    return self.json(dataset_answer(r.get('question'),rows,metrics,r.get('index'),r.get('window',48),r.get('threshold',.5)))
   if self.path=='/api/ingest':
    token=os.getenv('MICROGRID_DEVICE_TOKEN','')
    if not token or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):return self.json({'error':'Device token required'},401)
    r['source']='live';return self.json(ingest(r),201)
   if self.path=='/api/scenario':
    if r.get('scenario') not in ['normal','overheat','low-soc','overload','missing','offline']:raise ValueError('Unknown scenario')
    SCENARIO=r['scenario'];return self.json({'scenario':SCENARIO})
   if self.path=='/api/ack':
    with LOCK,connect() as c:c.execute("UPDATE alerts SET status='acknowledged' WHERE id=? AND status='active'",(int(r['id']),))
    signal_change()
    return self.json({'ok':True})
   return self.json({'error':'Not found'},404)
  except (ValueError,KeyError,TypeError) as e:return self.json({'error':str(e)},400)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8000);ap.add_argument('--host',default=os.getenv('MICROGRID_BIND','127.0.0.1'));args=ap.parse_args()
 if os.getenv('MICROGRID_ENABLE_SIMULATION')=='1':threading.Thread(target=simulate,daemon=True).start()
 print(f'Microgrid running at http://localhost:{args.port}',flush=True)
 ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
