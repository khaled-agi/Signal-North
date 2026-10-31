"use strict";
/* Source-labeled CAFC publicly reported FRAUD aggregates, not incident map. */
(() => {
 const el=id=>document.getElementById(id);
 const html=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const data={rows:[],status:{status:"not_attempted"},scope:{}};
 const money=n=>Number(n).toLocaleString("en-CA",{maximumFractionDigits:0});
 function render(){
  if(!el("cafcRows"))return;
  const dimension=el("cafcDimension").value;
  const year=el("cafcYear").value;
  const q=el("cafcSearch").value.toLocaleLowerCase().trim();
  const matches=data.rows.filter(x=>x.dimension===dimension &&
    (!year||x.year===year)&&(!q||[x.label,x.province,x.year].some(t=>
     String(t||"").toLocaleLowerCase().includes(q))))
   .slice().sort((a,b)=>b.report_rows-a.report_rows);
  el("cafcHealth").textContent="Collection: "+(data.status.status||"not_attempted")+
   " · Source through "+(data.status.dataset_end_date||"2025-09-30");
  el("cafcSummary").textContent=(data.status.canada_rows||0).toLocaleString()+
   " Canada-labeled source rows · "+(data.status.status||"not attempted")+
   " · Published through September 2025";
  el("cafcStats").innerHTML=
    '<div class="cfpb-sample-count"><strong>'+money(data.status.canada_rows||0)+
    '</strong><span>Canadian report rows processed from the official file</span></div>'+
    '<div class="cfpb-mini-stat"><strong>'+money(matches.length)+
    '</strong><span>Visible category/year aggregate groups (≥5 reports)</span></div>';
  el("cafcRows").innerHTML=matches.length?matches.slice(0,100).map(x=>{
   const dollars=x.reported_dollar_loss_sum;
   const loss=dollars===null?"Known reported subtotal $"+money(x.known_reported_dollar_loss_subtotal||0)+"; "+(x.rows_without_loss||0)+" rows missing loss; total unknown":
      "$"+money(dollars)+" reported dollar loss (not verified)";
   return '<article class="world-reporting-record cafc-row">'+
    '<div class="world-reporting-date">'+html(x.year)+' · '+html(x.dimension)+
    '</div><strong>'+html(x.label)+'</strong>'+
    '<div class="world-reporting-details">'+money(x.report_rows)+
    ' report rows · '+html(loss)+'</div>'+
    (x.rows_without_loss?'<div class="world-reporting-details">'+
      html(x.rows_without_loss)+' records with missing loss amounts; no zero-loss inference</div>':"")+
    '<div class="world-reporting-details">CAFC reported allegations · Not independently confirmed offences</div>'+
    '</article>';
  }).join(""):'<div class="empty">'+(data.rows.length?
   "No aggregated categories match these filters.":
   "No CAFC report aggregates collected yet. This does not mean Canada had no reported fraud.")+'</div>';
  el("cafcShown").textContent=Math.min(matches.length,100)+" of "+matches.length+
   " matching categories shown · Source-labeled and privacy-aggregated";
 }
 async function fetchData(){
  if(!el("cafcOpenData"))return;
  const paths=["cafc_aggregates.json","cafc_source_status.json"];
  const results=await Promise.allSettled(paths.map(async file=>{
   const response=await fetch("./data/"+file+"?v="+Date.now(),{cache:"no-store"});
   if(!response.ok)throw new Error(file+" HTTP "+response.status);
   return response.json();
  }));
  if(results[0].status==="fulfilled")
   data.rows=(results[0].value.rows||[]).filter(x=>
    Number.isInteger(x.report_rows)&&x.report_rows>=5 &&
    ["year","category","province","method"].includes(x.dimension));
  if(results[1].status==="fulfilled")data.status=results[1].value||{};
  else data.status={status:"unavailable"};
  const years=[...new Set(data.rows.map(x=>x.year))].sort().reverse();
  const picker=el("cafcYear");
  picker.innerHTML='<option value="">All available years</option>'+
   years.map(x=>'<option value="'+html(x)+'">'+html(x)+'</option>').join("");
  for(const id of ["cafcDimension","cafcYear","cafcSearch"]){
   el(id)?.addEventListener(id==="cafcSearch"?"input":"change",render);
  }
  render();
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",fetchData);
 else fetchData();
})();
