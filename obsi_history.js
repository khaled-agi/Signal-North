"use strict";
(() => {
 const el=id=>document.getElementById(id),root=el("obsiHistoricalSeries");
 if(!root)return;
 const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const get=name=>fetch("./data/"+name+"?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()});
 get("obsi_annual_banking.json").then(d=>{
  const rows=d.rows||[];
  if(!rows.length)throw Error("No annual totals");
  el("obsiHistoricStatus").textContent=rows.length+" fiscal years in the published annual report";
  root.innerHTML=rows.slice().reverse().map(r=>'<article class="world-reporting-record"><strong>Fiscal '+esc(r.year)+'</strong>'+
   '<div class="world-reporting-details">'+Number(r.banking_cases_opened).toLocaleString("en-CA")+' OBSI banking cases opened'+
   (r.fraud_cases_opened==null?'':' · '+Number(r.fraud_cases_opened).toLocaleString("en-CA")+' fraud-category investigations')+'</div>'+
   '<a target="_blank" rel="noopener noreferrer" href="'+esc(r.source_url)+'">OBSI historical chart ↗</a></article>').join("");
 }).catch(()=>{el("obsiHistoricStatus").textContent="No validated sector history";root.textContent="The banking-sector historical report is unavailable; no missing year is treated as zero.";});
 const out=el("obsiReportLinks");
 get("obsi_public_report_catalog.json").then(d=>{
  const rows=d.documents||[],good=Object.values(d.source_health||{}).filter(x=>x.status==="success").length;
  el("obsiReportCount").textContent=rows.length+" reports · "+good+"/2 feeds";
  out.innerHTML=rows.slice(0,70).map(r=>'<article class="world-reporting-record"><strong>'+esc(r.label)+'</strong><div class="world-reporting-details">'+esc(r.type)+'</div>'+
   '<a href="'+esc(r.source_url)+'" rel="noopener noreferrer" target="_blank">Official OBSI PDF ↗</a></article>').join("")||
   '<p class="supporting-disclaimer">No validated report links yet. Official source collection may have failed.</p>';
 }).catch(()=>{el("obsiReportCount").textContent="Report collection unavailable";out.textContent="OBSI report catalog has not yet passed source verification.";});
})();
