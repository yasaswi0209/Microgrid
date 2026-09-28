"""Transparent operational index. Demo thresholds are not equipment specifications."""
import math
RULES = [
 ('voltage','Bus voltage','V',207,195,253,265,2,'Inspect supply and converter regulation.'),
 ('current','Load current','A',None,None,85,100,2,'Inspect overload and load distribution.'),
 ('temperature','Battery temperature','°C',None,None,45,55,3,'Inspect cooling and battery condition.'),
 ('soc','Battery SOC','%',25,15,None,None,2,'Review charging schedule and noncritical loads.'),
 ('converter_temperature','Converter temperature','°C',None,None,65,80,2,'Inspect converter cooling.')]
class Engine:
 def __init__(self, rules=None):
  self.rules=rules if rules is not None else RULES
  for rule in self.rules:
   if not isinstance(rule,list) and not isinstance(rule,tuple): raise ValueError('Rule must be an array')
   if len(rule)!=9: raise ValueError('Rule requires nine fields')
   key,label,unit,lo,lc,hi,hc,weight,action=rule
   if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in [weight,*[v for v in [lo,lc,hi,hc] if v is not None]]):raise ValueError('Rule limits and weights must be finite numbers')
   if lo is None and hi is None:raise ValueError('Rule requires at least one bound')
   if weight<=0 or not math.isfinite(weight): raise ValueError('Rule weight must be positive and finite')
   if (lo is None)!=(lc is None) or (hi is None)!=(hc is None): raise ValueError('Bounds require warning and critical pairs')
   if lo is not None and not lc<lo: raise ValueError('Lower critical bound must be below warning')
   if hi is not None and not hi<hc: raise ValueError('Upper critical bound must exceed warning')
  self.states={}
 def assess(self,r):
  factors=[]
  for key,label,unit,lo,lc,hi,hc,weight,action in self.rules:
   value=r.get(key); raw=0
   if value is not None:
    if hi is not None and value>hi: raw=max(raw,min(1,(value-hi)/(hc-hi)))
    if lo is not None and value<lo: raw=max(raw,min(1,(lo-value)/(lo-lc)))
   state=self.states.setdefault((r['device_id'],key),{'start':None,'active':False,'severity':0})
   last=state.get('last')
   if last is not None and r['timestamp']-last>10:state.update(start=None,active=False,severity=0)
   state['last']=r['timestamp']
   if value is None:
    state.update(start=None,active=False,severity=0)
   elif raw>0:
    if state['start'] is None: state['start']=r['timestamp']
    if raw>=1 or r['timestamp']-state['start']>=5: state.update(active=True,severity=raw)
   else:
    # Recover only after crossing 2% of warning-to-critical span back into normal range.
    recovered=(hi is None or value<=hi-.02*(hc-hi)) and (lo is None or value>=lo+.02*(lo-lc))
    if recovered: state.update(start=None,active=False,severity=0)
   sev=state['severity'] if state['active'] else 0
   factors.append(dict(key=key,label=label,unit=unit,value=value,warning_low=lo,critical_low=lc,warning_high=hi,critical_high=hc,weight=weight,severity=sev,raw_severity=raw,active=state['active'],duration=0 if state['start'] is None else round(r['timestamp']-state['start'],1),action=action,status='Unavailable' if value is None else 'Critical' if sev>=1 else 'Warning' if sev>0 else 'Pending' if raw>0 else 'Normal'))
  present=[f for f in factors if f['value'] is not None]
  coverage=len(present)/len(factors) if factors else 0
  den=sum(f['weight'] for f in present)
  score=round(100*sum(f['weight']*f['severity'] for f in present)/den,1) if den and coverage>=.8 else None
  for f in factors: f['contribution']=round(100*f['weight']*f['severity']/den,1) if den and f['value'] is not None else None
  level='Critical' if any(f['severity']>=1 for f in present) else 'Insufficient data' if score is None else 'Warning' if any(f['active'] for f in present) else 'Normal'
  return dict(score=score,level=level,coverage=round(coverage*100),factors=factors)

def validate(r):
 if not isinstance(r,dict): raise ValueError('Payload must be an object')
 for k in ['device_id','component_id','timestamp','source','units','quality']:
  if k not in r: raise ValueError('Missing '+k)
 if not isinstance(r['device_id'],str) or not r['device_id'] or len(r['device_id'])>128 or not isinstance(r['component_id'],str) or not r['component_id']: raise ValueError('IDs must be strings')
 if r['source'] not in ['live','simulation']: raise ValueError('Invalid source')
 if r['quality'] not in ['good','invalid']: raise ValueError('Invalid quality')
 if not isinstance(r['units'],dict): raise ValueError('units must be an object')
 if isinstance(r['timestamp'],bool) or not isinstance(r['timestamp'],(int,float)) or not math.isfinite(r['timestamp']): raise ValueError('Invalid timestamp')
 units={'voltage':'V','current':'A','temperature':'C','converter_temperature':'C','soc':'%','solar':'kW','wind':'kW','load':'kW','grid':'kW','battery':'kW','losses':'kW','humidity':'%','wind_speed':'m/s','converter_input_kw':'kW','converter_output_kw':'kW','irradiance':'W/m2','efficiency':'%'}
 for k,u in units.items():
  if r.get(k) is not None:
   v=r[k]
   if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v): raise ValueError('Invalid '+k)
   if r['units'].get(k)!=u: raise ValueError('Expected '+k+' unit '+u)
 for k in ['solar','wind','load','losses','irradiance','converter_input_kw','converter_output_kw']:
  if r.get(k) is not None and r[k]<0:raise ValueError(k+' must be nonnegative')
 for k in ['soc','humidity','efficiency']:
  if r.get(k) is not None and not 0<=r[k]<=100: raise ValueError(k+' out of range')
 return r
