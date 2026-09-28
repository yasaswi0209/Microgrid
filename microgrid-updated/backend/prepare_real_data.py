"""Reproducible measured-data extraction and honest chronological forecast evaluation."""
import argparse,csv,hashlib,json,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error,root_mean_squared_error
import joblib
ROOT=Path(__file__).parent
PREFIX='DE_KN_residential3_'
KEYS=[PREFIX+k for k in ['pv','grid_import','grid_export']]
URL='https://data.open-power-system-data.org/household_data/2020-04-15/household_data_60min_singleindex.csv'
def prepare(path):
 data=ROOT/'data';data.mkdir(exist_ok=True)
 raw=[]
 with open(path,newline='') as f:
  for r in csv.DictReader(f):
   if all(r.get(k) for k in KEYS):raw.append({k:r[k] for k in ['utc_timestamp',*KEYS,'interpolated']})
 with (data/'source_counters.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['utc_timestamp',*KEYS,'interpolated']);w.writeheader();w.writerows(raw)
 rows=[];excluded=0
 for prev,cur in zip(raw,raw[1:]):
  a=datetime.fromisoformat(prev['utc_timestamp'].replace('Z','+00:00')).timestamp();b=datetime.fromisoformat(cur['utc_timestamp'].replace('Z','+00:00')).timestamp()
  if b-a!=3600 or any(k in (prev['interpolated']+' '+cur['interpolated']) for k in KEYS):excluded+=1;continue
  vals=[float(cur[k])-float(prev[k]) for k in KEYS]
  if min(vals)<-1e-8:excluded+=1;continue
  solar,imp,exp=vals;load=solar+imp-exp
  if load<-.005:excluded+=1;continue
  rows.append(dict(timestamp=b,solar=round(solar,6),load=round(max(0,load),6),grid=round(imp-exp,6)))
 with (data/'measured_hourly.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['timestamp','solar','load','grid']);w.writeheader();w.writerows(rows)
 lookup={r['timestamp']:r for r in rows};samples=[]
 for r in rows:
  t=r['timestamp']
  if all(t+offset in lookup for offset in [-3600,-7200,-86400,3600]):
   dt=datetime.fromtimestamp(t+3600,timezone.utc);hour=dt.hour
   features=[r['solar'],r['load'],lookup[t-3600]['solar'],lookup[t-3600]['load'],lookup[t-7200]['solar'],lookup[t-7200]['load'],lookup[t-86400]['solar'],lookup[t-86400]['load'],math.sin(hour*math.pi/12),math.cos(hour*math.pi/12),dt.month,dt.weekday()]
   samples.append((r,lookup[t+3600],features))
 n=len(samples);a=int(n*.6);b=int(n*.8)
 # Purge the single-hour label crossing each chronological boundary.
 tr=[s for s in samples[:a] if s[1]['timestamp']<samples[a][0]['timestamp']]
 va=[s for s in samples[a:b] if s[1]['timestamp']<samples[b][0]['timestamp']];te=samples[b:]
 report={'source_url':URL,'source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'source':'Open Power System Data / CoSSMic residential3, southern Germany','license':'CC BY 4.0','horizon_seconds':3600,'units':'kW (hourly average)','excluded_interpolated_or_invalid_intervals':excluded,'measured_rows':len(rows),'features':'Current and 1h/2h/24h lagged solar/load, target hour sine/cosine, target month and weekday','split':'60/20/20 chronological, purged boundary labels','train_samples':len(tr),'validation_samples':len(va),'test_samples':len(te),'train_end':tr[-1][1]['timestamp'],'validation_start':va[0][0]['timestamp'],'validation_end':va[-1][1]['timestamp'],'test_start':te[0][0]['timestamp'],'targets':{}}
 models={};output=[{**s[1],'issued_at':s[0]['timestamp']} for s in te]
 for target in ['solar','load']:
  candidates={};fitted={}
  for depth in [8,16]:
   model=RandomForestRegressor(n_estimators=100,max_depth=depth,min_samples_leaf=4,random_state=42,n_jobs=-1)
   model.fit([s[2] for s in tr],[s[1][target] for s in tr]);name=f'Random Forest depth {depth}'
   fitted[name]=model;candidates[name]=model.predict([s[2] for s in va])
  # Fixed candidate set. Select using validation only, before test evaluation.
  extra={
   'Extra Trees depth 16':ExtraTreesRegressor(n_estimators=200,max_depth=16,min_samples_leaf=4,random_state=42,n_jobs=-1),
   'Histogram Boosting absolute error':HistGradientBoostingRegressor(loss='absolute_error',max_iter=180,max_leaf_nodes=15,l2_regularization=1,early_stopping=False,random_state=42),
  }
  for name,model in extra.items():
   model.fit([s[2] for s in tr],[s[1][target] for s in tr]);fitted[name]=model
   candidates[name]=np.maximum(0,model.predict([s[2] for s in va]))
  candidates['Persistence baseline']=[s[0][target] for s in va]
  candidates['Daily seasonal baseline']=[lookup[s[1]['timestamp']-86400][target] if s[1]['timestamp']-86400 in lookup else s[0][target] for s in va]
  actual=[s[1][target] for s in va];scores={k:float(mean_absolute_error(actual,v)) for k,v in candidates.items()};chosen=min(scores,key=scores.get)
  pred=fitted[chosen].predict([s[2] for s in te]) if chosen in fitted else [s[0][target] if chosen=='Persistence baseline' else lookup.get(s[1]['timestamp']-86400,s[0])[target] for s in te]
  pred=np.maximum(0,pred)
  # Validation residual interval; temporal distribution shift can reduce coverage.
  residuals=np.abs(np.asarray(actual)-np.asarray(candidates[chosen]))
  qlevel=min(1,math.ceil((len(residuals)+1)*.9)/len(residuals))
  radius=float(np.quantile(residuals,qlevel,method='higher'))
  test_actual=[s[1][target] for s in te];base=[s[0][target] for s in te]
  report['targets'][target]={'selected_model':chosen,'validation_mae_candidates':scores,'test_mae':float(mean_absolute_error(test_actual,pred)),'test_rmse':float(root_mean_squared_error(test_actual,pred)),'persistence_test_mae':float(mean_absolute_error(test_actual,base)),'persistence_test_rmse':float(root_mean_squared_error(test_actual,base))}
  report['targets'][target]['validation_interval_radius_kw']=radius
  report['targets'][target]['interval_nominal_coverage']=.9
  report['targets'][target]['interval_test_coverage']=float(np.mean((np.asarray(test_actual)>=np.maximum(0,pred-radius))&(np.asarray(test_actual)<=pred+radius)))
  for r,v in zip(output,pred):
   r[target+'_prediction']=round(max(0,float(v)),6)
   r[target+'_lower']=round(max(0,float(v)-radius),6)
   r[target+'_upper']=round(float(v)+radius,6)
  if chosen in fitted:models[target]=fitted[chosen]
 report['note']='Historical results for one German household; no guarantee on another microgrid. Missing physical sensors remain unavailable. Test forecasts are precomputed using only data available at each issue time.'
 (data/'evaluation.json').write_text(json.dumps(report,indent=2));(data/'holdout.json').write_text(json.dumps(output,separators=(',',':')));joblib.dump(models,data/'dataset_models.joblib',compress=3)
 print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('csv');prepare(p.parse_args().csv)
