"""Train one-minute forecasts from a single-device CSV using chronological splits."""
import argparse,csv,json,time
from pathlib import Path
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor,IsolationForest
from sklearn.metrics import mean_absolute_error,root_mean_squared_error
FEATURES=['solar','load','temperature','soc']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('csv');a=ap.parse_args()
 with open(a.csv,newline='') as f:rows=list(csv.DictReader(f))
 devices={r.get('device_id','single-device') for r in rows}
 if len(devices)>1:raise SystemExit('Use a CSV containing exactly one device.')
 rows=sorted(rows,key=lambda r:float(r['timestamp']))
 ts=np.array([float(r['timestamp']) for r in rows]);x=np.array([[float(r[k]) for k in FEATURES] for r in rows])
 if not np.isfinite(x).all() or not np.isfinite(ts).all() or (np.diff(ts)<=0).any():raise SystemExit('Finite values and unique ascending timestamps required.')
 future=np.searchsorted(ts,ts+60);mask=future<len(ts);idx=np.where(mask)[0];idx=idx[(ts[future[idx]]-ts[idx]<=65)]
 if len(idx)<500:raise SystemExit('Need at least 500 complete pairs at a 60–65 second forecast horizon.')
 aidx=int(len(idx)*.6);bidx=int(len(idx)*.8)
 # Purge training labels crossing the next split to avoid leakage.
 train=idx[:aidx];train=train[ts[future[train]]<ts[idx[aidx]]]
 val=idx[aidx:bidx];val=val[ts[future[val]]<ts[idx[bidx]]]
 test=idx[bidx:]
 if min(len(train),len(val),len(test))<30:raise SystemExit('Insufficient samples after chronological purging.')
 models={'version':str(int(time.time())),'device_id':next(iter(devices))};report={'horizon_seconds':60,'features':FEATURES,'split':'60/20/20 chronological with horizon purge','warning':'Validation applies only to the supplied data distribution. Simulation performance does not establish real-world accuracy.','targets':{}}
 for j,target in enumerate(['solar','load']):
  y=x[future[idx],j];best=None;best_mae=float('inf');depth=None
  for dep in [6,12]:
   m=RandomForestRegressor(n_estimators=120,max_depth=dep,min_samples_leaf=3,random_state=42,n_jobs=-1)
   m.fit(x[train],x[future[train],j]);mae=mean_absolute_error(x[future[val],j],m.predict(x[val]))
   if mae<best_mae:best=m;best_mae=mae;depth=dep
  models[target]=best
  pred=best.predict(x[test]);actual=x[future[test],j];base=x[test,j]
  report['targets'][target]={'unit':'kW','validation_mae':best_mae,'max_depth':depth,'test_mae':mean_absolute_error(actual,pred),'test_rmse':root_mean_squared_error(actual,pred),'baseline_mae':mean_absolute_error(actual,base),'baseline_rmse':root_mean_squared_error(actual,base),'train_samples':len(train),'validation_samples':len(val),'test_samples':len(test)}
 models['anomaly']=IsolationForest(n_estimators=100,contamination='auto',random_state=42).fit(x[train])
 report['anomaly']='Isolation Forest fit to training partition. Unsupervised deviation only; no labeled fault validation.'
 root=Path(__file__).parent;joblib.dump(models,root/'model.joblib');(root/'model-metrics.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
