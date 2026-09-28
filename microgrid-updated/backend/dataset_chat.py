"""Offline, deterministic dataset assistant. No external LLM or fabricated readings."""
from datetime import datetime, timezone
from question_bank import find_question, values

def answer(question, rows, evaluation, index, window=48, threshold=.5):
 if not isinstance(question,str) or not question.strip() or len(question)>1000:raise ValueError('Enter a question of 1–1000 characters.')
 if not isinstance(index,int) or isinstance(index,bool) or not 0<=index<len(rows):raise ValueError('Invalid dataset position.')
 if window not in (24,48,168):raise ValueError('Invalid analysis window.')
 if not isinstance(threshold,(int,float)) or not .01<=threshold<=100000:raise ValueError('Invalid deviation threshold.')
 q=question.lower();r=rows[index];selected=rows[max(0,index-window+1):index+1]
 stamp=lambda t:datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
 context=f"Selected record: {stamp(r['timestamp'])}. Source: OPSD / CoSSMic residential3 (historical)."
 entry=find_question(question)
 if entry:
  text=entry['reply'].format(**values(rows,evaluation,index,window,threshold))
  return {'answer':text,'context':context,'question_id':entry['id'],'method':'Supported question bank · dataset calculations','timestamp':r['timestamp']}
 if any(k in q for k in ('battery','temperature','voltage','soc','sensor','maintenance','failure')):
  text='This dataset subset does not contain battery SOC, temperature, voltage or labelled equipment failures. I cannot estimate those values or diagnose hardware faults. Available measurements are solar and grid energy; household demand is derived.'
 elif any(k in q for k in ('accuracy','accurate','mae','rmse','model','trained','training')):
  text='Validation-selected forecasting models predict solar generation and load one hour ahead. Chronological training/validation/test splits prevent future observations being used for earlier forecasts. '+ ' '.join(f"{key.title()}: test MAE {m['test_mae']:.3f} kW, RMSE {m['test_rmse']:.3f} kW." for key,m in evaluation['targets'].items())+' Large retained source outliers affect load RMSE. Accuracy is not guaranteed.'
 elif any(k in q for k in ('predict','forecast','next hour','next-hour')):
  upcoming=next((v for v in rows if v['issued_at']==r['timestamp']),None)
  if upcoming:text=f"Forecast issued at the selected record for {stamp(upcoming['timestamp'])}: solar {upcoming['solar_prediction']:.3f} kW; load {upcoming['load_prediction']:.3f} kW. These are saved held-out model estimates; target measurements are not used in this answer."
  else:text='No saved next-hour forecast issued at this selected timestamp is available. Choose another record; missing intervals are not invented.'
 elif any(k in q for k in ('risk','exposure','dependence')):
  dep=max(0,r['load']-r['solar'])/r['load'] if r['load'] else 0
  error=abs(r['solar']-r['solar_prediction']);score=round(100*(.7*dep+.3*min(error/threshold,1)))
  text=f"Energy exposure is {score}/100: grid dependence {dep*100:.1f}%, solar forecast error {error:.3f} kW, threshold {threshold:g} kW. Formula: 100 × (0.7 × dependence + 0.3 × min(error/threshold,1)). Weights are illustrative; this is retrospective energy analysis, not a fault probability. Grid dependence can be normal."
 elif any(k in q for k in ('anomal','alert','deviation','unusual')):
  flags=[v for v in selected if abs(v['solar']-v['solar_prediction'])>threshold]
  text=f"{len(flags)} of {len(selected)} selected records exceed the solar forecast-error threshold of {threshold:g} kW. These are historical review flags, not equipment alarms. "
  if flags:
   worst=max(flags,key=lambda v:abs(v['solar']-v['solar_prediction']))
   text+=f"Largest flagged error: {abs(worst['solar']-worst['solar_prediction']):.3f} kW at {stamp(worst['timestamp'])}."
 elif any(k in q for k in ('source','dataset','data from')):
  text='OPSD Household Data, release 2020-04-15, hourly CoSSMic residential3 counters. Solar and net grid powers are counter differences over one-hour intervals. Load = solar + import − export, assuming no unmetered storage. Missing/interpolated intervals are excluded. Original dates are retained.'
 elif any(k in q for k in ('energy','summary','summar','consumption','import','export','generation','load','solar')):
  solar=sum(v['solar'] for v in selected);load=sum(v['load'] for v in selected)
  imports=sum(max(0,v['grid']) for v in selected);exports=sum(max(0,-v['grid']) for v in selected)
  text=f"Across {len(selected)} valid hourly records: solar {solar:.3f} kWh; consumption {load:.3f} kWh; imported {imports:.3f} kWh; exported {exports:.3f} kWh. Missing hours are excluded, not interpolated. At the selected hour: solar {r['solar']:.3f} kW and load {r['load']:.3f} kW."
 else:text='I can answer questions about next-hour forecasts, model error, energy totals, grid dependence, anomalies and dataset provenance. Try “What is the next-hour forecast?” or “Summarize the energy window.” This offline assistant uses predefined intents and dataset calculations; it is not a general-purpose language model.'
 return {'answer':text,'context':context,'method':'Offline dataset assistant · deterministic calculations','timestamp':r['timestamp']}
