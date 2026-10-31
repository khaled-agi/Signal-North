"use strict";
(() => {
 const el=id=>document.getElementById(id);
 const out=el("usFdicRows");
 if (!out) return;
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const urls={
  institutions:"./data/us_fdic_institutions.json",
  failures:"./data/us_fdic_failures.json",
 };
 const state={snapshots:{},health:null};
 function render(){
  const dataset=el("usFdicDataset").value, source=state.snapshots[dataset], query=el("usFdicSearch").value.trim().toLowerCase();
  if(!source||!Array.isArray(source.records)){
    el("usFdicStatus").textContent="FDIC "+dataset+" not yet available";
    out.innerHTML='<div class="empty">The last official FDIC collection is unavailable. This does not indicate zero institutions or failures.</div>';return;
  }
  const records=source.records, matches=records.filter(r=>!query||
    [r.institution,r.city,r.state,r.fdic_cert,r.ncua_charter,r.acquirer].some(x=>String(x||"").toLowerCase().includes(query)));
  el("usFdicStatus").textContent=records.length.toLocaleString("en-US")+" source rows · fetched "+String(source.retrieved_at||"").slice(0,10);
  out.innerHTML=matches.slice(0,90).map(r=>{
   const head='<article class="world-reporting-record"><div class="world-reporting-date">'+
    esc(r.state||"United States")+' · '+(dataset==="ncua"?'NCUA charter '+esc(r.ncua_charter):'FDIC certificate '+esc(r.fdic_cert))+' · '+(dataset==="institutions"?"Insured bank register":dataset==="ncua"?"Insured credit union register":"Bank lifecycle event")+'</div><strong>'+esc(r.institution)+'</strong>'+
    '<div class="world-reporting-details">'+esc(r.city||"")+
    (dataset==="failures"?' · Failure date: '+esc(r.failure_date||"Unknown")+' · Resolution: '+esc(r.resolution_type||"Not specified")+
      (r.acquirer?' · Acquirer: '+esc(r.acquirer):'') :dataset==="ncua"?' · NCUA quarterly cycle '+esc(r.cycle||"Unknown"):' · Active insured institution')+
    '</div>';
   return head+'<a href="'+(dataset==="failures"?'https://banks.data.fdic.gov/bankfind-suite/failures':dataset==="ncua"?'https://ncua.gov/analysis/credit-union-corporate-call-report-data/quarterly-data':'https://banks.data.fdic.gov/bankfind-suite/')+
    '" target="_blank" rel="noopener noreferrer">Official FDIC source ↗</a></article>';
  }).join("")+'<p class="supporting-disclaimer">Showing '+Math.min(90,matches.length)+' of '+
  matches.length.toLocaleString("en-US")+' matching original records; use institution search to narrow results.</p>';
 }
 el("usFdicDataset").addEventListener("change",render);
 el("usFdicSearch").addEventListener("input",render);
 for(const [dataset,url] of Object.entries(urls)){
  fetch(url+"?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json()})
   .then(d=>{if(!Array.isArray(d.records)||d.records.length<2500)throw Error("Invalid FDIC snapshot");state.snapshots[dataset]=d;render()})
   .catch(()=>{if(dataset===el("usFdicDataset").value)render()});
 }
 fetch("./data/us_fdic_source_health.json?v="+Date.now(),{cache:"no-store"})
  .then(r=>{if(!r.ok)throw Error("No collector health");return r.json()})
  .then(d=>{state.health=d;el("usFdicHealth").textContent=Object.entries(d.sources||{})
   .map(([k,v])=>k+": "+v.status+" · "+(v.last_success||v.last_attempt||"not collected")).join(" | ")})
  .catch(()=>{el("usFdicHealth").textContent="FDIC source health has not yet been published.";});
})();
