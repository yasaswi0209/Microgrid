import rows from '../backend/data/holdout.json';
import evaluation from '../backend/data/evaluation.json';
import questions from '../backend/data/questions.json';
export const dataset={history:rows,evaluation};
export const questionList=questions.map(({id,category,question})=>({id,category,question}));
const norm=s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const stamp=t=>new Date(t*1000).toISOString().slice(0,16).replace('T',' ')+' UTC';
const f=n=>n.toFixed(3);
export function chat({question,index,window=48,threshold=.5}){
 if(!Number.isInteger(index)||index<0||index>=rows.length)throw Error('Select a valid dataset record.');
 const r=rows[index],w=rows.slice(Math.max(0,index-window+1),index+1),e=evaluation;
 const sum=k=>w.reduce((a,v)=>a+v[k],0),solar=sum('solar'),load=sum('load');
 const err=Math.abs(r.solar-r.solar_prediction),dep=r.load?Math.max(0,r.load-r.solar)/r.load:0,score=Math.round(100*(.7*dep+.3*Math.min(err/threshold,1)));
 const errors=w.map(v=>Math.abs(v.solar-v.solar_prediction)),worst=errors.indexOf(Math.max(...errors)),flags=errors.filter(x=>x>threshold).length;
 const ps=w.reduce((a,b)=>b.solar>a.solar?b:a),pl=w.reduce((a,b)=>b.load>a.load?b:a);
 const d={first_time:stamp(rows[0].timestamp),last_time:stamp(rows.at(-1).timestamp),selected_time:stamp(r.timestamp),issued_time:stamp(r.issued_at),measured_count:e.measured_rows,total_count:rows.length,train_count:e.train_samples,validation_count:e.validation_samples,solar:f(r.solar),load:f(r.load),grid:f(r.grid),grid_import:f(Math.max(0,r.grid)),grid_export:f(Math.max(0,-r.grid)),current_coverage:f(r.load?Math.min(1,r.solar/r.load)*100:0),surplus:f(Math.max(0,r.solar-r.load)),deficit:f(Math.max(0,r.load-r.solar)),solar_error:f(err),window_count:w.length,solar_energy:f(solar),load_energy:f(load),import_energy:f(w.reduce((a,v)=>a+Math.max(0,v.grid),0)),export_energy:f(w.reduce((a,v)=>a+Math.max(0,-v.grid),0)),window_coverage:f(load?100*w.reduce((a,v)=>a+Math.min(v.solar,v.load),0)/load:0),peak_solar:f(ps.solar),peak_solar_time:stamp(ps.timestamp),peak_load:f(pl.load),peak_load_time:stamp(pl.timestamp),mean_solar:f(solar/w.length),mean_load:f(load/w.length),flag_count:flags,threshold:f(threshold),worst_error:f(errors[worst]),worst_time:stamp(w[worst].timestamp),current_flag:err>threshold?'Yes':'No',flag_percentage:f(flags/w.length*100),score,risk_band:score>=70?'High':score>=30?'Moderate':'Low',dependence:f(dep*100)};
 for(const key of ['solar','load']){const m=e.targets[key];Object.assign(d,{[key+'_model']:m.selected_model,[key+'_mae']:f(m.test_mae),[key+'_rmse']:f(m.test_rmse),[key+'_baseline']:f(m.persistence_test_mae),[key+'_interval_coverage']:f(100*m.interval_test_coverage),['window_'+key+'_mae']:f(w.reduce((a,v)=>a+Math.abs(v[key]-v[key+'_prediction']),0)/w.length)})}
 for(const key of ['next_forecast','next_solar','next_load','next_timing','next_solar_interval','next_load_interval'])d[key]='No saved next-hour forecast is available at this selected timestamp. Missing intervals are not invented.';
 const next=rows.find(v=>v.issued_at===r.timestamp);
 if(next){const timing=`Issued ${stamp(r.timestamp)}; target ${stamp(next.timestamp)}.`;d.next_timing=timing;d.next_forecast=`Solar estimate ${f(next.solar_prediction)} kW; load estimate ${f(next.load_prediction)} kW. ${timing} Saved historical estimates, not today's forecast.`;for(const key of ['solar','load']){d['next_'+key]=`Next-hour ${key}: ${f(next[key+'_prediction'])} kW. ${timing}`;d['next_'+key+'_interval']=`${key[0].toUpperCase()+key.slice(1)} interval: ${f(next[key+'_lower'])} to ${f(next[key+'_upper'])} kW. ${timing} Based on validation residuals with nominal 90% coverage; no guarantee for this individual record.`}}
 const q=norm(question),id=q.match(/^(?:q|question)?\s*(\d{1,3})$/);
 let entry=id?questions.find(v=>v.id===+id[1]):questions.find(v=>norm(v.question)===q);
 if(!entry){const mappings=[[/anomal|alert|deviation|unusual/,51],[/battery|temperature|voltage|soc|sensor|maintenance|failure/,92],[/accuracy|accurate|mae|rmse|model|train/,41],[/predict|forecast|next hour/,31],[/risk|exposure|dependence/,61],[/source|dataset|data from/,1],[/energy|summary|summar|consumption|import|export|generation|load|solar/,21]];entry=questions.find(v=>v.id===mappings.find(([re])=>re.test(q))?.[1]);}
 const answer=entry?entry.reply.replace(/\{([^}]+)\}/g,(_,key)=>{if(!(key in d))throw Error('Unsupported question field');return d[key]}):'Choose one of the 100 questions in the question bank or enter Q1 to Q100. I answer supported dataset questions rather than open-ended general conversation.';
 return {answer,context:`Selected record: ${stamp(r.timestamp)}. Source: OPSD / CoSSMic residential3 (historical).`,question_id:entry?.id};
}
