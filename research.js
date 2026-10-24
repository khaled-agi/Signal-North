"use strict";
/* Curated public research layer: separate from incident & bank-loss records. */
(() => {
 const el=id=>document.getElementById(id);
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 let all=[],losses=[],wired=false;
 function safeLink(url,label){
  try{const u=new URL(url);if(u.protocol!=="https:")return "";return '<a href="'+esc(u.href)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' ↗</a>'}catch{return ""}
 }
 function renderReports(){
  const q=el("librarySearch").value.trim().toLowerCase(),topic=el("libraryTopic").value,year=el("libraryYear").value;
  const subset=all.filter(x=>(!topic||x.topic===topic)&&(!year||String(x.year)===year)&&
   (!q||[x.title,x.publisher,x.topic,x.why,x.type,x.coverage].join(" ").toLowerCase().includes(q)));
  el("libraryCount").textContent=subset.length+" of "+all.length+" primary-source resources";
  el("libraryRows").innerHTML=subset.length?subset.map(x=>'<article class="library-record"><div class="library-record-top"><span>'+esc(x.publisher)+'</span><span>'+esc(x.year)+' · '+esc(x.type)+'</span></div>'+
   '<h3>'+safeLink(x.url,x.title)+'</h3><div class="library-topic">'+esc(x.topic)+' · Covers '+esc(x.coverage)+'</div>'+
   '<p>'+esc(x.why)+'</p><div class="library-limit"><strong>Interpret carefully:</strong> '+esc(x.limitations)+'</div></article>').join(""):
   '<div class="empty">No reports match the selected research filters.</div>';
 }
 function renderTrend(){
  const max=Math.max(1,...losses.map(x=>x.cad_millions));
  el("lossTrend").innerHTML=losses.length?losses.map(x=>{
   const pct=(x.cad_millions/max*100).toFixed(1);
   return '<div class="loss-trend-row"><strong>'+esc(x.year)+'</strong><div class="loss-trend-bar"><span style="width:'+pct+'%"></span></div><div><strong>C$'+esc(Number(x.cad_millions).toLocaleString("en-CA",{maximumFractionDigits:1}))+'M'+'</strong><small>'+safeLink(x.source_url,"Source")+'</small></div></div>';
  }).join(""):'<div class="empty">Source-linked yearly loss figures are not available.</div>';
 }
 async function boot(){
  try{
   const r=await fetch("./data/research_library.json?v="+Date.now(),{cache:"no-store"});
   if(!r.ok)throw Error("HTTP "+r.status);
   const d=await r.json();
   all=d.reports||[];losses=d.victim_loss_series||[];
   all.sort((a,b)=>Number(b.year)-Number(a.year));
   const previousTopic=el("libraryTopic").value,previousYear=el("libraryYear").value;
   el("libraryTopic").innerHTML='<option value="">All topics</option>'+[...new Set(all.map(x=>x.topic))].sort().map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join("");
   el("libraryYear").innerHTML='<option value="">All years</option>'+[...new Set(all.map(x=>String(x.year)))].sort().reverse().map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join("");
   if(previousTopic)el("libraryTopic").value=previousTopic;
   if(previousYear)el("libraryYear").value=previousYear;
   if(!wired){
    el("libraryTopic").addEventListener("change",renderReports);
    el("libraryYear").addEventListener("change",renderReports);
    el("librarySearch").addEventListener("input",renderReports);
    wired=true;
   }
   renderReports();renderTrend();
  }catch(e){
   el("libraryCount").textContent="Research library unavailable";
   el("libraryRows").innerHTML='<div class="empty">Could not load curated official reports: '+esc(e.message)+'</div>';
   el("lossTrend").innerHTML='<div class="empty">Historical victim-loss trend unavailable.</div>';
  }
 }
 window.addEventListener("signalnorth:refresh",boot);
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
