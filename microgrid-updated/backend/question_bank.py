"""Curated questions and grounded numerical answers; not a generative LLM."""
import json,re,math
from pathlib import Path
from functools import lru_cache
from datetime import datetime,timezone
@lru_cache(maxsize=1)
def catalog():return json.loads((Path(__file__).parent/'data/questions.json').read_text())
def normalize(s):return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()
def find_question(q):
 n=normalize(q)
 ident=re.fullmatch(r'(?:q|question)?\s*(\d{1,3})',n)
 if ident:return next((v for v in catalog() if v['id']==int(ident[1])),None)
 return next((v for v in catalog() if normalize(v['question'])==n),None)
def values(rows,e,index,window,threshold):
 r=rows[index];w=rows[max(0,index-window+1):index+1]
 stamp=lambda t:datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
 f=lambda x:f'{x:.3f}'
 total=lambda key:sum(v[key] for v in w)
 solar=total('solar');load=total('load');coverage=sum(min(v['solar'],v['load']) for v in w)/load*100 if load else 0
 errors=[abs(v['solar']-v['solar_prediction']) for v in w];worst=max(range(len(w)),key=lambda i:errors[i]);flags=sum(x>threshold for x in errors)
 dep=max(0,r['load']-r['solar'])/r['load'] if r['load'] else 0;err=abs(r['solar']-r['solar_prediction']);score=math.floor(100*(.7*dep+.3*min(err/threshold,1))+.5)
 ps=max(w,key=lambda v:v['solar']);pl=max(w,key=lambda v:v['load'])
 d=dict(first_time=stamp(rows[0]['timestamp']),last_time=stamp(rows[-1]['timestamp']),selected_time=stamp(r['timestamp']),issued_time=stamp(r['issued_at']),measured_count=e['measured_rows'],total_count=len(rows),train_count=e['train_samples'],validation_count=e['validation_samples'],solar=f(r['solar']),load=f(r['load']),grid=f(r['grid']),grid_import=f(max(0,r['grid'])),grid_export=f(max(0,-r['grid'])),current_coverage=f(min(1,r['solar']/r['load'])*100 if r['load'] else 0),surplus=f(max(0,r['solar']-r['load'])),deficit=f(max(0,r['load']-r['solar'])),solar_error=f(err),window_count=len(w),solar_energy=f(solar),load_energy=f(load),import_energy=f(sum(max(0,v['grid']) for v in w)),export_energy=f(sum(max(0,-v['grid']) for v in w)),window_coverage=f(coverage),peak_solar=f(ps['solar']),peak_solar_time=stamp(ps['timestamp']),peak_load=f(pl['load']),peak_load_time=stamp(pl['timestamp']),mean_solar=f(solar/len(w)),mean_load=f(load/len(w)),flag_count=flags,threshold=f(threshold),worst_error=f(errors[worst]),worst_time=stamp(w[worst]['timestamp']),current_flag='Yes' if err>threshold else 'No',flag_percentage=f(flags/len(w)*100),score=score,risk_band='High' if score>=70 else 'Moderate' if score>=30 else 'Low',dependence=f(dep*100))
 for key in ('solar','load'):
  m=e['targets'][key]
  d.update({key+'_model':m['selected_model'],key+'_mae':f(m['test_mae']),key+'_rmse':f(m['test_rmse']),key+'_baseline':f(m['persistence_test_mae']),key+'_interval_coverage':f(100*m.get('interval_test_coverage',0)),'window_'+key+'_mae':f(sum(abs(v[key]-v[key+'_prediction']) for v in w)/len(w))})
 nxt=next((v for v in rows if v['issued_at']==r['timestamp']),None)
 for key in ('next_forecast','next_solar','next_load','next_timing','next_solar_interval','next_load_interval'):d[key]='No saved next-hour forecast is available at this selected timestamp. Missing intervals are not invented.'
 if nxt:
  timing=f"Issued {stamp(r['timestamp'])}; target {stamp(nxt['timestamp'])}."
  d.update(next_timing=timing,next_forecast=f"Solar estimate {nxt['solar_prediction']:.3f} kW; load estimate {nxt['load_prediction']:.3f} kW. {timing} Saved historical estimates, not today's forecast.")
  for key in ('solar','load'):
   d['next_'+key]=f"Next-hour {key}: {nxt[key+'_prediction']:.3f} kW. {timing}"
   d['next_'+key+'_interval']=f"{key.title()} interval: {nxt[key+'_lower']:.3f} to {nxt[key+'_upper']:.3f} kW. {timing} Based on validation residuals with nominal 90% coverage; no guarantee for this individual record."
 return d
