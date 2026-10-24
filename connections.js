"use strict";
/* Evidence-aware cross-source institution intelligence: never scores culpability. */
(() => {
 const el=id=>document.getElementById(id);
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const date=v=>v?String(v).slice(0,10):"Date not established";
 const money=v=>v==null?"Not reported":"C$"+Number(v).toLocaleString("en-CA",{maximumFractionDigits:2});
 const safeLink=(url,label)=>{
   try{const u=new URL(url);if(u.protocol!=="https:")return "";return '<a href="'+esc(u.href)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' ↗</a>'}catch{return ""}
 };
 const state={institutions:[],queue:[],selected:null,visible:35,reviewVisible:35};
 const kindName={enforcement:"Regulator decision",incident:"Source-reviewed reported case",headline:"Unverified headline"};
 const labels={subject_of_enforcement:"Subject of published regulatory action",
 customer_financial_institution:"Customer's reported bank",institution_impersonated:"Institution reportedly impersonated",
 bank_not_identified:"Bank not identified",mentioned_in_headline_only:"Named in news headline only"};
 const normalize=v=>String(v||"").toLowerCase().trim();
 function updatePicker(keep=true){
   const q=normalize(el("connectSearch").value);
   const matches=state.institutions.filter(x=>!q||normalize(x.name).includes(q)||(x.aliases||[]).some(a=>normalize(a).includes(q)));
   const current=keep?state.selected:null;
   el("connectInstitution").innerHTML='<option value="">Choose an institution ('+matches.length+' matches)</option>'+
    matches.slice(0,250).map(x=>'<option value="'+esc(x.id)+'">'+esc(x.name)+'</option>').join("");
   if(current&&matches.some(x=>x.id===current))el("connectInstitution").value=current;
 }
 function evidenceRow(r){
  const kind=kindName[r.kind]||"Source";
  const amount=r.kind==="enforcement"&&r.penalty_cad!=null?"Regulatory penalty: "+money(r.penalty_cad):
   r.kind==="incident"&&r.amount_cad!=null?
    (({victim_reported_loss:"Reported customer loss",unauthorized_credit_exposure:"Unauthorized credit exposure",recovered_amount:"Funds recovered"})[r.amount_type]||"Reported amount")+": "+money(r.amount_cad):
    r.amount_text?.length?"Quoted headline amount: "+r.amount_text.join(", "):"";
  return '<article class="evidence-entry evidence-'+esc(r.kind)+'"><div class="evidence-top"><span class="evidence-type">'+esc(kind)+'</span><span>'+esc(date(r.date))+'</span></div>'+
   '<div class="evidence-name">'+esc(r.title||"Public notice")+'</div><div class="evidence-meta">'+esc(labels[r.role]||r.role||"Published source")+' · '+esc(r.source||"Publisher")+'</div>'+
   (amount?'<div class="evidence-amount">'+esc(amount)+'</div>':"")+
   (r.kind==="incident"&&r.recovery_status?'<div class="evidence-meta">Reported recovery: '+esc(r.recovery_status)+'</div>':"")+
   '<div class="evidence-bottom">'+safeLink(r.source_url,"Original publication")+(r.kind==="headline"?"<span class='evidence-caveat'>No institutional responsibility established</span>":"")+'</div></article>';
 }
 function activityChart(records){
  const grouped={};
  for(const r of records){
   const year=String(r.date||"").slice(0,4);
   if(!/^\d{4}$/.test(year))continue;
   grouped[year]??={enforcement:0,incident:0,headline:0};
   grouped[year][r.kind]=(grouped[year][r.kind]||0)+1;
  }
  const years=Object.keys(grouped).sort().slice(-6);
  const max=Math.max(1,...years.map(y=>Object.values(grouped[y]).reduce((a,b)=>a+b,0)));
  return '<div class="evidence-trend">'+years.map(y=>{
   const g=grouped[y],total=g.enforcement+g.incident+g.headline;
   return '<div class="trend-row"><span>'+y+'</span><div class="trend-track">'+
    ["enforcement","incident","headline"].map(k=>'<div class="trend-segment trend-'+k+'" style="width:'+(100*g[k]/max).toFixed(2)+'%"></div>').join("")+
    '</div><strong>'+total+'</strong></div>';
  }).join("")+'</div>';
 }
 function renderInstitution(){
  const x=state.institutions.find(a=>a.id===state.selected);
  el("connectTrack").disabled=el("connectMap").disabled=!x;
  if(!x){el("connectContent").innerHTML='<div class="empty">Choose a bank or credit union to explore its connected public evidence.</div>';return}
  const items=x.evidence||[];
  const shown=items.slice(0,state.visible);
  const penalties=Object.entries(x.annual_penalties_cad||{}).sort((a,b)=>b[0].localeCompare(a[0]));
  const themes=(x.themes||[]).slice(0,6);
  el("connectContent").innerHTML=
   '<div class="connection-title"><div><div class="eyebrow">CANONICAL INSTITUTION · PUBLIC-SOURCE RESEARCH</div><h3>'+esc(x.name)+'</h3><div class="small">Alias names linked for research: '+esc((x.aliases||[]).join(", "))+'</div></div><div class="small">Last observed evidence: '+esc(date(x.recent_activity))+'</div></div>'+
   '<div class="connection-metrics"><div><strong>'+x.counts.enforcement+'</strong><span>Published regulator actions</span></div><div><strong>'+x.counts.incidents+'</strong><span>Source-reviewed reported incidents</span></div><div><strong>'+x.counts.headlines+'</strong><span>Unverified name mentions</span></div></div>'+
   '<div class="connection-insight-grid"><div><h4>Evidence by publication year</h4>'+activityChart(items)+
   '<div class="evidence-legend"><span class="legend-reg">Regulator</span><span class="legend-case">Reported case</span><span class="legend-headline">Headline only</span></div></div>'+
   '<div><h4>Topics to investigate, not proven failures</h4>'+
    (themes.length?themes.map(t=>'<div class="theme-row"><span>'+esc(t.name)+'</span><strong>'+t.matching_records+' matched records</strong></div>').join(""):'<div class="small">Insufficient source text to identify recurring topics.</div>')+
   '<p class="evidence-footnote">Themes are keyword co-occurrences. A story about an impersonated institution does not establish its controls were deficient.</p></div></div>'+
   (penalties.length?'<div class="evidence-penalties"><strong>Published regulatory penalties by notice year</strong><span>'+penalties.slice(0,7).map(([y,a])=>esc(y)+": "+esc(money(a))).join(" · ")+'</span><small>Not customer fraud losses and not necessarily the year of the underlying violation</small></div>':"")+
   '<div class="connection-timeline-title"><h4>Linked evidence timeline</h4><span class="small">Showing '+shown.length+' of '+(x.counts.enforcement+x.counts.incidents+x.counts.headlines)+' source links</span></div>'+
   '<div class="connection-timeline">'+shown.map(evidenceRow).join("")+'</div>'+
   (items.length>state.visible?'<button id="connectionsMore" type="button" class="connection-more">Show more source-linked records ↓</button>':"")+
   '<p class="evidence-footnote">News links here are headline-level mentions and may not describe a fraud case or wrongdoing by this institution. Original articles require review before case-level conclusions.</p>';
 }
 function renderQueue(){
   const f=el("reviewType").value,q=normalize(el("reviewSearch").value);
   const items=state.queue.filter(x=>(f==="all"||(f==="bank"&&x.banks.length)||(f==="amount"&&x.amount_text.length)||(f==="victim"&&x.priority_basis.includes("possible victim story")))&&
    (!q||normalize([x.headline,x.publisher,...x.banks].join(" ")).includes(q)));
   el("reviewCount").textContent=items.length+" unverified leads to review";
   el("reviewRows").innerHTML=items.slice(0,state.reviewVisible).map(x=>
    '<article class="review-item"><div class="review-p"><span>REVIEW PRIORITY '+x.priority+'/9 · '+esc(date(x.date))+'</span><span>'+esc((x.banks||[]).join(", ")||"No bank named")+'</span></div>'+
    '<div class="review-title">'+safeLink(x.source_url,x.headline)+'</div><div class="small">'+esc(x.publisher||"Publisher")+" · "+esc((x.priority_basis||[]).join("; "))+'</div>'+
    '<p class="review-next">Next step: '+esc(x.next_step)+'</p></article>').join("")+
    (items.length>state.reviewVisible?'<button id="reviewMore" type="button" class="connection-more">Show additional review leads ↓</button>':"")+
    (!items.length?'<div class="empty">No matching unverified leads in this research queue.</div>':"");
 }
 function selectByName(name){
  const n=normalize(name);
  const x=state.institutions.find(x=>x.id===name||normalize(x.name)===n||(x.aliases||[]).some(a=>normalize(a)===n));
  if(!x){el("connectSearch").value=name;updatePicker(false);return}
  state.selected=x.id;state.visible=35;el("connectSearch").value="";updatePicker();renderInstitution();
 }
 function render(){
  const current=state.selected;
  updatePicker();
  if(!current&&state.institutions.length)state.selected=state.institutions[0].id;
  updatePicker();renderInstitution();renderQueue();
 }
 async function boot(){
  try{
   const urls=["institution_intelligence.json","review_queue.json"];
   const results=await Promise.all(urls.map(async x=>{const r=await fetch("./data/"+x+"?t="+Date.now(),{cache:"no-store"});if(!r.ok)throw Error(x+": HTTP "+r.status);return r.json()}));
   state.institutions=results[0].institutions||[];state.queue=results[1].items||[];
   el("connectionUpdated").textContent="Updated "+date(results[0].generated_at)+" · "+state.institutions.length+" linked entities";
   render();
   window.dispatchEvent(new CustomEvent("signalnorth:aliasesready",{detail:{institutions:state.institutions}}));
  }catch(error){
   el("connectionUpdated").textContent="Evidence graph unavailable";
   el("connectContent").innerHTML='<div class="empty">Graph unavailable: '+esc(error.message)+'. The enforcement and news lists remain accessible.</div>';
   el("reviewRows").innerHTML='<div class="empty">Review queue will appear when its published data file is ready.</div>';
  }
 }
 el("connectSearch").addEventListener("input",()=>updatePicker(false));
 el("connectInstitution").addEventListener("change",e=>{state.selected=e.target.value;state.visible=35;renderInstitution()});
 el("connectTrack").addEventListener("click",()=>{
  const x=state.institutions.find(a=>a.id===state.selected);
  if(x)window.dispatchEvent(new CustomEvent("signalnorth:trackinstitution",{detail:{name:x.name}}));
  document.querySelector('[data-tab="clients"]').click();
 });
 el("connectMap").addEventListener("click",()=>{
  const x=state.institutions.find(a=>a.id===state.selected);
  if(!x)return;
  document.querySelector('[data-tab="overview"]').click();
  window.dispatchEvent(new CustomEvent("signalnorth:clientfocus",{detail:{name:x.name}}));
 });
 el("reviewType").addEventListener("change",()=>{state.reviewVisible=35;renderQueue()});
 el("reviewSearch").addEventListener("input",()=>{state.reviewVisible=35;renderQueue()});
 document.addEventListener("click",event=>{
  if(event.target.closest("#connectionsMore")){state.visible+=35;renderInstitution()}
  if(event.target.closest("#reviewMore")){state.reviewVisible+=35;renderQueue()}
  const open=event.target.closest("[data-open-connection]");
  if(open){document.querySelector('[data-tab="connections"]').click();selectByName(open.dataset.openConnection)}
 });
 window.addEventListener("signalnorth:selectinstitution",e=>{document.querySelector('[data-tab="connections"]').click();selectByName(e.detail?.name||"")});
 window.addEventListener("signalnorth:refresh",boot);
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
