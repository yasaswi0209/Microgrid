// Descriptive historical energy indicators, not equipment-failure probabilities.
export function assess(row, threshold=.5) {
 const dependence=row.load>0?Math.min(1,Math.max(0,row.load-row.solar)/row.load):0;
 const error=Math.abs(row.solar-row.solar_prediction);
 const severity=Math.min(1,error/Math.max(.01,threshold));
 return {dependence,error,score:Math.round(100*(.7*dependence+.3*severity)),flagged:error>threshold};
}
export function summarize(rows){
 const total=key=>rows.reduce((a,r)=>a+r[key],0);
 const solar=total('solar'),load=total('load'),imports=rows.reduce((a,r)=>a+Math.max(0,r.grid),0),exports=rows.reduce((a,r)=>a+Math.max(0,-r.grid),0);
 return {solar,load,imports,exports,coverage:load?100*rows.reduce((a,r)=>a+Math.min(r.solar,r.load),0)/load:0};
}
export function csv(rows){return ['timestamp_utc,solar_kw,load_kw,net_grid_kw,solar_forecast_kw,load_forecast_kw',...rows.map(r=>[new Date(r.timestamp*1000).toISOString(),r.solar,r.load,r.grid,r.solar_prediction,r.load_prediction].join(','))].join('\n');}
