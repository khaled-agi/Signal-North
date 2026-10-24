"use strict";
const $ = selector => document.querySelector(selector);
const state = {events:[],status:{},map:null,layer:null,tab:"overview"};
const provinces = {ON:"Ontario",QC:"Québec",BC:"British Columbia",AB:"Alberta",NB:"New Brunswick",NS:"Nova Scotia",MB:"Manitoba",SK:"Saskatchewan",NL:"Newfoundland & Labrador",PE:"Prince Edward Island"};
function escapeHTML(value){return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function currency(value){if(value==null)return "Not reported";const x=Number(value);return x>=1e6?"$"+(x/1e6).toLocaleString("en-CA",{maximumFractionDigits:2})+"M":"$"+x.toLocaleString("en-CA",{maximumFractionDigits:0});}
function date(x){return x?String(x).slice(0,10):"Date not reported";}
function sourceLink(url){try{const u=new URL(url);return u.protocol==="https:"?'<a class="source-link" href="'+escapeHTML(u.href)+'" target="_blank" rel="noopener noreferrer">Read original regulator notice ↗</a>':"";}catch{return "";}}
function eventsByInstitution(){const groups=new Map();for(const e of state.events){if(!e.institution)continue;const key=e.institution.trim();if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e);}return [...groups].map(([name,events])=>({name,events})).sort((a,b)=>b.events.length-a.events.length);}
function switchTab(tab){
 state.tab=tab;
 document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("hidden",x.id!==tab));
 document.querySelectorAll(".nav").forEach(x=>x.classList.toggle("active",x.dataset.tab===tab));
 $("#crumb").textContent=({overview:"INTELLIGENCE OVERVIEW",events:"EVENT EXPLORER",institutions:"INSTITUTION RADAR",sources:"SOURCES & METHODOLOGY"})[tab];
 const t={overview:["Know what changed.","Know where to look.","Monitor public enforcement developments and explore evidence-linked institutions across Canada."],events:["Explore the evidence.","Understand each case.","Search regulator-published actions by entity, location, and legal status."],institutions:["Organizations, not rankings.","Evidence before inference.","Institution profiles connect reported events without implying fraud or demand for consulting services."],sources:["Trust the source.","Understand the gaps.","Track source availability, update times, and limitations of public regulatory data."]}[tab];
 $("#headline").innerHTML=escapeHTML(t[0])+"<br><em>"+escapeHTML(t[1])+"</em>";
 $("#description").textContent=t[2];
 if(tab==="overview"&&state.map)setTimeout(()=>state.map.invalidateSize(),60);
}
function rowHTML(e){
 return '<div class="event" role="button" tabindex="0" data-event="'+escapeHTML(e.id)+'"><div class="event-date">'+escapeHTML(date(e.published_at))+'</div><div><div class="event-title">'+escapeHTML(e.title)+'</div><div class="event-meta"><span>'+escapeHTML(e.source)+'</span><span>'+escapeHTML(e.category)+'</span>'+(e.province?"<span>"+escapeHTML(provinces[e.province]||e.province)+"</span>":"")+'</div></div><div class="event-right">'+(e.penalty_cad==null?"":'<div class="event-amount">'+escapeHTML(currency(e.penalty_cad))+'</div>')+'<span class="pill">'+escapeHTML(e.status||"Published notice")+'</span></div></div>';
}
function renderMetrics(){
 const e=state.events;const fines=e.filter(x=>x.penalty_cad!=null);const total=fines.reduce((a,b)=>a+Number(b.penalty_cad),0);const mapped=e.filter(x=>Number.isFinite(x.latitude)&&Number.isFinite(x.longitude));
 const values=[
 ["Tracked notices",String(e.length),"Observed in monitored public sources"],
 ["Named institutions",String(eventsByInstitution().length),"Name-matched, not corporate-family merged"],
 ["Published penalties",currency(total),"Sum of tracked notices; not fraud losses"],
 ["Mapped events",String(mapped.length),"Only source-supported locations"]
 ];
 $("#metrics").innerHTML=values.map(v=>'<div class="metric"><span class="label">'+escapeHTML(v[0])+'</span><span class="value">'+escapeHTML(v[1])+'</span><span class="foot">'+escapeHTML(v[2])+'</span></div>').join("");
 const counts={};for(const x of mapped){counts[x.province||"Other"]=(counts[x.province||"Other"]||0)+1;}
 const sorted=Object.entries(counts).sort((a,b)=>b[1]-a[1]);const max=Math.max(1,...sorted.map(x=>x[1]));
 $("#regions").innerHTML=sorted.length?sorted.map(x=>'<div class="region"><div class="region-head"><span>'+escapeHTML(provinces[x[0]]||x[0])+'</span><strong>'+x[1]+'</strong></div><div class="track"><div style="width:'+Math.round(x[1]/max*100)+'%"></div></div></div>').join(""):'<div class="empty">No mapped institutions in the current source snapshot.</div>';
 $("#recent").innerHTML=e.length?e.slice(0,8).map(rowHTML).join(""):'<div class="empty">No enforcement records are published in this snapshot yet. Check Source monitoring for the collector status.</div>';
 $("#updated").textContent=state.status.last_completed_at?"Collected "+date(state.status.last_completed_at):"Public-source snapshot";
}
function initMap(){
 if(!window.L){$("#map").innerHTML='<div class="empty">Map tiles unavailable. Events remain accessible in the explorer.</div>';return;}
 if(!state.map){
  $("#map").replaceChildren();
  state.map=L.map("map",{zoomControl:false,minZoom:3}).setView([55,-95],4);
  L.control.zoom({position:"bottomright"}).addTo(state.map);
  const base = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{
   maxZoom:19, attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
  }).addTo(state.map);
  let fallback=false;
  base.on("tileerror",()=>{if(fallback)return;fallback=true;state.map.removeLayer(base);
    L.tileLayer("https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",{maxZoom:19,
     attribution:'&copy; OpenStreetMap contributors, HOT'}).addTo(state.map);});
  state.layer=L.layerGroup().addTo(state.map);
 }
 state.layer.clearLayers();
 let count=0;
 for(const e of state.events){
  if(!Number.isFinite(e.latitude)||!Number.isFinite(e.longitude))continue;
  count++;
  const dot=L.circleMarker([e.latitude,e.longitude],{radius:8,color:"#0d2831",weight:2,fillColor:"#58dccc",fillOpacity:.9}).addTo(state.layer);
  const html='<div style="min-width:180px"><strong>'+escapeHTML(e.institution||e.title)+'</strong><div style="font-size:12px;margin:4px 0">'+escapeHTML(e.category)+'</div><div style="font-size:11px">'+escapeHTML(e.location||"Reported institution location")+'</div><a href="#" data-popup="'+escapeHTML(e.id)+'">View case ↗</a></div>';
  dot.bindPopup(html);
 }
 $("#mapCaption").textContent=count+" of "+state.events.length+" notices have explicitly supported institution locations";
}
function renderEvents(){
 const e=state.events;
 const select=(id,vals,placeholder)=>{const el=$(id);const old=el.value;el.innerHTML='<option value="">'+placeholder+"</option>"+vals.map(x=>'<option value="'+escapeHTML(x)+'">'+escapeHTML(id==="#provinceFilter"?(provinces[x]||x):x)+"</option>").join("");el.value=old;};
 select("#sourceFilter",[...new Set(e.map(x=>x.source).filter(Boolean))].sort(),"All regulators");
 select("#provinceFilter",[...new Set(e.map(x=>x.province).filter(Boolean))].sort(),"All provinces");
 select("#statusFilter",[...new Set(e.map(x=>x.status).filter(Boolean))].sort(),"All legal statuses");
 filterEvents();
}
function filterEvents(){
 const q=$("#search").value.toLowerCase().trim();
 const matches=state.events.filter(e=>(!q||[e.title,e.institution,e.summary,e.category].some(s=>(s||"").toLowerCase().includes(q)))&&(!$("#sourceFilter").value||e.source===$("#sourceFilter").value)&&(!$("#provinceFilter").value||e.province===$("#provinceFilter").value)&&(!$("#statusFilter").value||e.status===$("#statusFilter").value));
 $("#resultCount").textContent=matches.length+" matching records";
 $("#eventRows").innerHTML=matches.length?matches.map(rowHTML).join(""):'<div class="empty">No records match these filters.</div>';
}
function renderInstitutions(){
 const groups=eventsByInstitution();
 $("#institutionRows").innerHTML=groups.length?groups.map(g=>{
 const last=g.events[0];const topics=[...new Set(g.events.map(e=>e.category))];
 return '<div class="institution" data-institution="'+escapeHTML(g.name)+'" tabindex="0" role="button"><div><h3>'+escapeHTML(g.name)+'</h3><p>'+g.events.length+' public notice(s) · '+escapeHTML(topics.join(" · "))+' · Last published '+escapeHTML(date(last.published_at))+'</p></div><div class="score">'+g.events.length+'<small>SOURCED EVENTS</small></div></div>';
 }).join(""):'<div class="empty">Institution profiles will appear when named regulatory records are collected.</div>';
}
function renderSources(){
 const rows=["FINTRAC","FCAC"].map(name=>{
 const s=state.status.sources?.[name];const url=name==="FINTRAC"?"https://fintrac-canafe.canada.ca/pen/4-eng":"https://www.canada.ca/en/financial-consumer-agency/services/industry/commissioner-decisions.html";
 return '<div class="source-row"><div><strong>'+name+'</strong><small>'+escapeHTML(s?.status||"Awaiting first run")+(s?.scanned!=null?" · "+s.scanned+" notices scanned":"")+'</small>'+(s?.error?'<small>'+escapeHTML(s.error)+'</small>':"")+'</div><a href="'+url+'" rel="noopener" target="_blank">Official source ↗</a></div>';
 });
 $("#sourceRows").innerHTML=rows.join("")+'<div class="source-row"><div><strong>Snapshot status</strong><small>Last collection: '+escapeHTML(state.status.last_completed_at||"Not yet available")+' · '+state.events.length+' stored events</small></div><a href="https://github.com/khaled-agi/Signal-North/actions">Workflow logs ↗</a></div>';
}
function openDrawer(html){$("#drawerBody").innerHTML=html;$("#overlay").classList.remove("hidden");document.body.style.overflow="hidden";}
function closeDrawer(){$("#overlay").classList.add("hidden");document.body.style.overflow="";}
function details(e){
 const rows=[["Institution",e.institution],["Institution role","Subject of published enforcement notice"],["Regulator",e.source],["Category",e.category],["Legal status",e.status],["Published",date(e.published_at)],["Action date",date(e.event_at)],["Penalty amount (CAD)",currency(e.penalty_cad)],["Location",e.location||"Not independently located"],["Source tier",e.evidence_level]];
 openDrawer('<div class="eyebrow">SOURCE-LINKED CASE</div><h2>'+escapeHTML(e.title)+'</h2><span class="pill">'+escapeHTML(e.status||"Published notice")+'</span><h3>Regulator summary</h3><p>'+escapeHTML(e.summary||"No additional summary available")+'</p><h3>Evidence details</h3><dl>'+rows.map(row=>'<dt>'+escapeHTML(row[0])+'</dt><dd>'+escapeHTML(row[1]??"Not reported")+'</dd>').join("")+'</dl><div class="warning">A published enforcement notice is not proof of additional unrelated misconduct or current consulting need. Check the original for updates, appeals, or corrections.</div>'+sourceLink(e.source_url));
}
function institutionDetail(name){
 const events=state.events.filter(e=>e.institution===name);
 openDrawer('<div class="eyebrow">INSTITUTION RESEARCH</div><h2>'+escapeHTML(name)+'</h2><p>Public enforcement information only. The presence of multiple notices is not a measure of institutional fraud prevalence.</p><h3>Topics to investigate</h3><p>'+escapeHTML([...new Set(events.map(e=>e.category))].join(" · "))+'</p><h3>Linked regulatory notices</h3>'+events.map(e=>'<p><strong>'+escapeHTML(date(e.published_at))+'</strong> — '+escapeHTML(e.title)+'<br><a href="'+escapeHTML(e.source_url)+'" rel="noopener" target="_blank">Source ↗</a></p>').join(""));
}
async function load(){
 try{
  const [a,b]=await Promise.all([
   fetch("./data/events.json?ts="+Date.now(),{cache:"no-store"}),
   fetch("./data/status.json?ts="+Date.now(),{cache:"no-store"})
  ]);
  if(!a.ok||!b.ok)throw new Error("Source snapshot not yet available ("+a.status+", "+b.status+")");
  const events=await a.json();state.events=Array.isArray(events)?events:(events.events||[]);
  state.events.sort((x,y)=>String(y.published_at||"").localeCompare(String(x.published_at||"")));
  state.status=await b.json();
  $("#error").classList.add("hidden");renderMetrics();renderEvents();renderInstitutions();renderSources();initMap();
 }catch(err){$("#error").classList.remove("hidden");$("#error").textContent="Unable to load published data: "+err.message;}
}
document.addEventListener("click",e=>{
 const tab=e.target.closest("[data-tab],[data-to]");if(tab){switchTab(tab.dataset.tab||tab.dataset.to);return;}
 const event=e.target.closest("[data-event],[data-popup]");if(event){e.preventDefault();const record=state.events.find(x=>x.id===(event.dataset.event||event.dataset.popup));if(record)details(record);return;}
 const inst=e.target.closest("[data-institution]");if(inst)institutionDetail(inst.dataset.institution);
});
document.addEventListener("keydown",e=>{
 if(e.key==="Escape")closeDrawer();
 if((e.key==="Enter"||e.key===" ")&&e.target.matches("[data-event], [data-institution]")){e.preventDefault();e.target.click();}
});
for(const id of ["search","sourceFilter","provinceFilter","statusFilter"]){$("#"+id).addEventListener(id==="search"?"input":"change",filterEvents);}
$("#close").addEventListener("click",closeDrawer);
$("#overlay").addEventListener("click",e=>{if(e.target.id==="overlay")closeDrawer();});
$("#reload").addEventListener("click",load);
window.addEventListener("signalnorth:mapready", () => { if(state.events.length) initMap(); });
load();
