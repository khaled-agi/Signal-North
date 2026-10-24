"use strict";
/* Signal North consultant worklist. Local-only browser storage, no external CRM sync. */
(() => {
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const el=id=>document.getElementById(id);
 const key="signalnorth.watchlist.v1";
 let institutions=[],records=[],cases=[],leads=[];
 function read(){
  try{const a=JSON.parse(localStorage.getItem(key)||"[]");return Array.isArray(a)?a.filter(x=>typeof x==="string").slice(0,100):[]}
  catch{return []}
 }
 function save(items){try{localStorage.setItem(key,JSON.stringify(items))}catch(e){console.warn("Watchlist storage unavailable",e)}}
 function normalize(v){return String(v||"").trim().toLowerCase()}
 function setNames(){
  institutions=[...new Set([...records.map(x=>x.institution),...cases.map(x=>x.institution),...leads.flatMap(x=>x.banks_mentioned_in_headline||[])].filter(Boolean))].sort((a,b)=>a.localeCompare(b));
  el("clientSuggestions").innerHTML=institutions.map(n=>'<option value="'+esc(n)+'"></option>').join("");
 }
 function metrics(name){
  const n=normalize(name);
  const r=records.filter(x=>normalize(x.institution)===n);
  const c=cases.filter(x=>normalize(x.institution)===n);
  const l=leads.filter(x=>(x.banks_mentioned_in_headline||[]).some(z=>normalize(z)===n));
  return {r,c,l};
 }
 function render(){
  setNames();const names=read();
  el("clientWatchlist").innerHTML=names.length?names.map((name,i)=>{
   const m=metrics(name);const latest=[...m.r.map(x=>({date:x.published_at,title:x.title,url:x.source_url,tier:"Regulator"})),...m.c.map(x=>({date:x.reported_at,title:x.title,url:x.source_url,tier:"Reported incident"})),...m.l.map(x=>({date:x.published_at,title:x.title,url:x.url,tier:"Unverified headline"}))].sort((a,b)=>(b.date||"").localeCompare(a.date||"")).slice(0,3);
   const recent=latest.map(x=>'<div class="watch-result"><span>'+esc(x.tier)+' · '+esc((x.date||"").slice(0,10))+'</span><a href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer">'+esc(x.title)+' ↗</a></div>').join("");
   return '<article class="client-item"><div class="client-head"><div><div class="eyebrow">INSTITUTION '+(i+1)+'</div><h3>'+esc(name)+'</h3></div><button data-remove-client="'+esc(name)+'" class="map-reset" aria-label="Stop tracking '+esc(name)+'">Remove</button></div><div class="client-metrics"><span><b>'+m.r.length+'</b> regulatory records</span><span><b>'+m.c.length+'</b> customer incident reports</span><span><b>'+m.l.length+'</b> headline mentions</span></div><div class="client-timeline">'+(recent||'<div class="small">No matching published records in the current data.</div>')+'</div><button class="client-map-link" type="button" data-client-focus="'+esc(name)+'">Focus map on mentioned institution →</button></article>';
  }).join(""):'<div class="empty">Your watchlist is empty. Add a bank or institution to see its related public-source activity.</div>';
 }
 function add(){
  const name=el("clientName").value.trim();if(!name)return;
  const known=institutions.find(x=>normalize(x)===normalize(name))||name;
  const next=read();if(!next.some(x=>normalize(x)===normalize(known))){next.unshift(known);save(next)}
  el("clientName").value="";render();
 }
 function exportCSV(){
  const rows=[["Institution","Regulatory notices","Reported customer cases","Unverified headline mentions"],...read().map(name=>{const m=metrics(name);return [name,m.r.length,m.c.length,m.l.length]})];
  const csv=rows.map(row=>row.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(",")).join("\r\n");
  const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});const url=URL.createObjectURL(blob);
  const a=document.createElement("a");a.href=url;a.download="signal-north-client-watchlist.csv";document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
 }
 async function boot(){
  try{
   const files=["events.json","incidents.json","news.json","news_archive.json"];
   const results=await Promise.all(files.map(async file=>{const res=await fetch("./data/"+file+"?t="+Date.now(),{cache:"no-store"});return res.ok?res.json():{}}));
   records=results[0].events||[];cases=results[1].incidents||[];
   const combined=[...(results[2].leads||[]),...(results[3].leads||[])];
   leads=[...new Map(combined.map(e=>[e.id,e])).values()];
  }catch(e){console.warn("Client source load incomplete",e)}
  render();
 }
 document.addEventListener("click",e=>{
  const rm=e.target.closest("[data-remove-client]");
  if(rm){save(read().filter(x=>normalize(x)!==normalize(rm.dataset.removeClient)));render();return}
  const focus=e.target.closest("[data-client-focus]");
  if(focus){document.querySelector('[data-tab="overview"]').click();window.dispatchEvent(new CustomEvent("signalnorth:clientfocus",{detail:{name:focus.dataset.clientFocus}}));}
 });
 el("clientAdd").addEventListener("click",add);
 el("clientName").addEventListener("keydown",e=>{if(e.key==="Enter")add()});
 el("exportWatchlist").addEventListener("click",exportCSV);
 window.addEventListener("signalnorth:refresh",boot);
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
