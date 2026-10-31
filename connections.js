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
 const reviewStorageKey="signalnorth.article_review.v1";
 function reviewMeta(){
   try{const d=JSON.parse(localStorage.getItem(reviewStorageKey)||"{}");return d&&typeof d==="object"?d:{}}catch{return {}}
 }
 function persistReview(id,change){
   const d=reviewMeta();d[id]={...(d[id]||{}),...change};
   try{localStorage.setItem(reviewStorageKey,JSON.stringify(d))}catch(e){console.warn("Local review storage unavailable",e)}
 }

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
   '<div class="evidence-bottom">'+safeLink(r.source_url,"Original publication")+
   (r.kind==="incident"?'<button type="button" class="report-variations" data-reviewed-open="'+esc(r.id)+'">Examine structured evidence →</button>':"")+
   (r.kind==="headline"?"<span class='evidence-caveat'>No institutional responsibility established</span>":"")+'</div></article>';
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
 function officialSections(x){
  const o=x.official_data||{}, reports=o.bank_disclosures||[], fintrac=o.fintrac_notices||[], fcac=o.fcac_notices||[];
  const osfi=o.osfi,amf=o.amf_registrations||[],obsi=o.obsi_firm_complaints||[],ciro=o.ciro_concluded_cases||[];
  if(!osfi&&!amf.length&&!obsi.length&&!ciro.length&&!reports.length&&!fintrac.length&&!fcac.length)return '';
  const head='<div class="connection-timeline-title"><h4>Official institution data</h4><span class="small">Different sources and denominators · never sum the figures</span></div>';
  const identity=osfi?'<div class="evidence-entry"><strong>OSFI regulated institution</strong><div class="small">'+esc(osfi.name)+' · '+esc(osfi.group||osfi.industry||"Federal institution registry")+'</div>'+safeLink(osfi.source_url,"Official OSFI directory")+'</div>':'';
  const complaintRows=reports.map(r=>'<article class="evidence-entry"><div class="evidence-top"><strong>'+esc(r.year)+' · '+esc(r.office||"Complaints office")+'</strong><span>'+Number(r.metric_value).toLocaleString("en-CA")+' records</span></div><div class="small">'+esc(r.scope||r.metric_name)+'</div>'+
  (r.fraud_nature_pct!=null?'<div class="small">Published fraud category: '+esc(r.fraud_nature_pct)+'%</div>':'')+
  (r.fraud_nature_count!=null?'<div class="small">Fraud-category cases: '+esc(r.fraud_nature_count)+'</div>':'')+
  '<div>'+safeLink(r.source_url,"Bank annual disclosure")+'</div></article>').join('');
  const penaltyRows=fintrac.slice(0,35).map(r=>'<article class="evidence-entry"><div class="evidence-top"><strong>FINTRAC · '+esc(r.date)+'</strong><span>'+esc(money(r.penalty_cad))+'</span></div><div class="small">Official-index notice · '+esc(r.violation_count==null?"Violation count unavailable":r.violation_count+" violations")+' · '+esc(r.status_summary||"Status not confirmed")+'</div>'+safeLink(r.source_url,"Original FINTRAC index")+'</article>').join('');
  const fcacRows=fcac.map(r=>'<article class="evidence-entry"><div class="evidence-top"><strong>FCAC · '+esc(r.date)+'</strong><span>'+esc(money(r.penalty_cad))+'</span></div><div class="small">'+esc(r.topic||"Published action")+' · Source is agency index</div>'+safeLink(r.source_url,"Original FCAC index")+'</article>').join('');
  const quebec=amf.length?'<div class="evidence-entry"><strong>Québec AMF registered entity</strong><div class="small">'+esc(amf.length)+' official registry matches · not enforcement findings</div>'+safeLink(amf[0].source_url,"Québec AMF open data")+'</div>':'';
  const obsiRows=obsi.slice().sort((a,b)=>b.fiscal_year-a.fiscal_year).map(r=>'<article class="evidence-entry"><div class="evidence-top"><strong>OBSI external complaints · FY'+esc(r.fiscal_year)+'</strong><span>'+Number(r.opened_cases).toLocaleString("en-CA")+' opened</span></div>'+
   '<div class="small">Received '+Number(r.complaints_received).toLocaleString("en-CA")+' · Closed '+Number(r.closed_cases).toLocaleString("en-CA")+' · Resolved to complainant satisfaction '+Number(r.resolved_satisfaction).toLocaleString("en-CA")+'</div>'+
   '<div class="small">Official OBSI annual report, '+esc(r.sector||"regulated banking")+' · distinct from internal bank complaints</div>'+
   safeLink(r.source_url,"OBSI annual source table")+'</article>').join("");
  const ciroRows=ciro.map(r=>'<article class="evidence-entry"><div class="evidence-top"><strong>CIRO concluded proceeding · '+esc(r.date||r.publication_date||"date not in index")+'</strong><span>Fine '+esc(money(r.fine_cad))+'</span></div>'+
    '<div class="small">'+esc(r.topic||"Official proceeding")+' · costs '+esc(money(r.costs_cad))+' · disgorgement '+esc(money(r.disgorgement_cad))+'</div>'+
    '<div class="small">Exact investment-dealer entity, not automatically the parent bank</div>'+safeLink(r.source_url,"CIRO case page")+'</article>').join("");
  return head+identity+quebec+
   (ciro.length?'<details class="supporting-reviewed-details"><summary>Concluded CIRO investment-dealer proceedings · '+ciro.length+'</summary>'+ciroRows+'</details>':'')+
   (obsi.length?'<details class="supporting-reviewed-details"><summary>OBSI external escalated complaints · '+obsi.length+' firm-year records</summary>'+obsiRows+'</details>':'')+
   (reports.length?'<details class="supporting-reviewed-details"><summary>Internal bank complaints · '+reports.length+' fiscal years</summary>'+complaintRows+'</details>':'')+
   (fintrac.length?'<details class="supporting-reviewed-details"><summary>FINTRAC monetary penalty notices · '+fintrac.length+' (may overlap other enforcement feeds)</summary>'+penaltyRows+'</details>':'')+
   (fcac.length?'<details class="supporting-reviewed-details"><summary>FCAC index-sourced actions · '+fcac.length+' (not deduplicated against existing event tracker)</summary>'+fcacRows+'</details>':'');
 }
 function renderInstitution(){
  const x=state.institutions.find(a=>a.id===state.selected);
  el("connectTrack").disabled=el("connectMap").disabled=el("connectExport").disabled=!x;
  if(!x){el("connectContent").innerHTML='<div class="empty">Choose a bank or credit union to explore its connected public evidence.</div>';return}
  const items=x.evidence||[];
  const shown=items.slice(0,state.visible);
  const penalties=Object.entries(x.annual_penalties_cad||{}).sort((a,b)=>b[0].localeCompare(a[0]));
  const themes=(x.themes||[]).slice(0,6);
  el("connectContent").innerHTML=
   '<div class="connection-title"><div><div class="eyebrow">CANONICAL INSTITUTION · PUBLIC-SOURCE RESEARCH</div><h3>'+esc(x.name)+'</h3><div class="small">Alias names linked for research: '+esc((x.aliases||[]).join(", "))+'</div></div><div class="small">Last observed evidence: '+esc(date(x.recent_activity))+'</div></div>'+
   '<div class="connection-metrics"><div><strong>'+x.counts.enforcement+'</strong><span>Published regulator actions</span></div><div><strong>'+x.counts.incidents+'</strong><span>Source-reviewed reported incidents</span></div><div><strong>'+x.counts.headlines+'</strong><span>Unverified name mentions</span></div></div>'+
   officialSections(x)+
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
   const f=el("reviewType").value,q=normalize(el("reviewSearch").value),wanted=el("reviewState").value;
   const saved=reviewMeta();
   const items=state.queue.filter(x=>
    (f==="all"||(f==="bank"&&x.banks.length)||(f==="amount"&&x.amount_text.length)||(f==="victim"&&x.priority_basis.includes("possible victim story")))&&
    (wanted==="all"||(saved[x.article_id]?.status||"New")===wanted)&&
    (!q||normalize([x.headline,x.publisher,...x.banks].join(" ")).includes(q)));
   el("reviewCount").textContent=items.length+" research leads matching filters";
   el("reviewRows").innerHTML=items.slice(0,state.reviewVisible).map(x=>{
    const info=saved[x.article_id]||{status:"New",note:""};
    const options=["New","In review","Documented","Dismissed"];
    const reviewControls='<div class="review-edit"><label>Analyst status<select data-review-status="'+esc(x.article_id)+'">'+options.map(x=>'<option value="'+esc(x)+'"'+(info.status===x?" selected":"")+'>'+esc(x)+'</option>').join("")+'</select></label><label>Research note<textarea rows="2" data-review-note="'+esc(x.article_id)+'" placeholder="What does the original source actually establish?">'+esc(info.note||"")+'</textarea></label></div>';
    return '<article class="review-item"><div class="review-p"><span>REVIEW PRIORITY '+x.priority+'/9 · '+esc(date(x.date))+'</span><span>'+esc((x.banks||[]).join(", ")||"No bank named")+'</span></div>'+
    '<div class="review-title">'+safeLink(x.source_url,x.headline)+'</div><div class="small">'+esc(x.publisher||"Publisher")+" · "+esc((x.priority_basis||[]).join("; "))+'</div>'+
    '<p class="review-next">Next step: '+esc(x.next_step)+'</p>'+reviewControls+'</article>';
   }).join("")+
    (items.length>state.reviewVisible?'<button id="reviewMore" type="button" class="connection-more">Show additional review leads ↓</button>':"")+
    (!items.length?'<div class="empty">No matching articles at this review status.</div>':"");
 }
 function exportReview(){
   const saved=reviewMeta();
   const rows=[["Article ID","Published","Title","Bank names (unverified)","Analyst status","Research notes","Source URL"]];
   for(const x of state.queue){
    const info=saved[x.article_id]||{status:"New",note:""};
    if(info.status==="New"&&!info.note)continue;
    rows.push([x.article_id,x.date,x.headline,(x.banks||[]).join(";"),info.status,info.note,x.source_url]);
   }
   const csv=rows.map(r=>r.map(v=>'"'+String(v??"").replace(/"/g,'""')+'"').join(",")).join("\r\n");
   const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
   const a=document.createElement("a");a.href=url;a.download="signal-north-reviewed-article-notes.csv";
   document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
 }
 function exportInstitutionBrief(){
   const x=state.institutions.find(y=>y.id===state.selected);
   if(!x)return;
   const lines=[
    "# Signal North — Source-linked research brief",
    "",
    "**Institution:** "+x.name,
    "**Generated:** "+new Date().toISOString().slice(0,10),
    "**Status:** Research draft, NOT a legal conclusion or finding of bank wrongdoing",
    "",
    "## Evidence summary",
    "Regulatory actions: "+x.counts.enforcement,
    "Source-reviewed reported customer incidents: "+x.counts.incidents,
    "Unverified media headline mentions: "+x.counts.headlines,
    "",
    "These three evidence categories must not be combined into one count of financial crime or misconduct.",
    "A customer fraud loss is not necessarily a loss borne by the institution. A regulatory fine is not a customer fraud loss.",
    "",
    "## Potential research themes (keyword matches only)",
    ...(x.themes||[]).slice(0,8).map(t=>"- "+t.name+" ("+t.matching_records+" matching records; no causation implied)"),
    "",
    "## Published regulatory penalties by notice publication year",
    ...Object.entries(x.annual_penalties_cad||{}).sort((a,b)=>b[0].localeCompare(a[0])).map(([year,value])=>"- "+year+": C$"+Number(value).toLocaleString("en-CA",{maximumFractionDigits:2})+" in published penalties (not fraud losses)"),
    "",
    "## Official regulatory source notices",
    ...(x.evidence||[]).filter(z=>z.kind==="enforcement").map(z=>"- "+(z.date||"Date not reported")+" | "+z.title+" | "+(z.source_url||"Source unavailable")),
    "",
    "## Individually source-reviewed reported cases",
    ...(x.evidence||[]).filter(z=>z.kind==="incident").map(z=>"- "+(z.date||"Unknown")+" | "+z.title+" | institution role: "+(z.role||"not established")+" | impact type: "+(z.amount_type||"not reported")+" | "+(z.source_url||"Source unavailable")),
    "",
    "## Unverified headlines — open and verify before using in client materials",
    ...(x.evidence||[]).filter(z=>z.kind==="headline").slice(0,35).map(z=>"- "+(z.date||"Unknown")+" | "+z.title+" | "+(z.source_url||"Source unavailable")),
    "",
    "## Consultant follow-up checklist",
    "- Read each original article or regulator decision and confirm its latest legal status.",
    "- Identify what happened, when, to whom, and the exact role of the named institution.",
    "- Determine whether any quoted amount is a victim loss, bank-borne loss, credit exposure, recovery or regulatory penalty.",
    "- Validate whether multiple reports concern the same underlying incident before adding them together.",
    "- Look for substantiated themes; identify competing explanations and gaps in available evidence.",
    "- Develop only evidence-backed hypotheses for potential KYC, fraud operations, AML or customer-protection engagements.",
    "",
    "Generated from public-source metadata. Reviewed customer reports are not findings against the institution.",
   ];
   const content=lines.join("\n")+"\n";
   const blob=new Blob([content],{type:"text/markdown;charset=utf-8"});
   const url=URL.createObjectURL(blob),a=document.createElement("a");
   a.href=url;a.download="signal-north-"+String(x.id).replace(/[^a-z0-9-]/gi,"-")+"-research-brief.md";
   document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
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
 el("connectExport").addEventListener("click",exportInstitutionBrief);
 el("connectMap").addEventListener("click",()=>{
  const x=state.institutions.find(a=>a.id===state.selected);
  if(!x)return;
  document.querySelector('[data-tab="overview"]').click();
  window.dispatchEvent(new CustomEvent("signalnorth:clientfocus",{detail:{name:x.name}}));
 });
 el("reviewType").addEventListener("change",()=>{state.reviewVisible=35;renderQueue()});
 el("reviewState").addEventListener("change",()=>{state.reviewVisible=35;renderQueue()});
 el("reviewExport").addEventListener("click",exportReview);
 el("reviewSearch").addEventListener("input",()=>{state.reviewVisible=35;renderQueue()});
 document.addEventListener("change",e=>{
  const control=e.target.closest("[data-review-status]");
  if(control){persistReview(control.dataset.reviewStatus,{status:control.value});if(el("reviewState").value!=="all")renderQueue();}
 });
 document.addEventListener("input",e=>{
  const note=e.target.closest("[data-review-note]");
  if(note)persistReview(note.dataset.reviewNote,{note:note.value});
 });
 document.addEventListener("click",event=>{
  if(event.target.closest("#connectionsMore")){state.visible+=35;renderInstitution()}
  if(event.target.closest("#reviewMore")){state.reviewVisible+=35;renderQueue()}
  const open=event.target.closest("[data-open-connection]");
  if(open){if(typeof closeDrawer==="function")closeDrawer();document.querySelector('[data-tab="connections"]').click();selectByName(open.dataset.openConnection)}
 });
 window.addEventListener("signalnorth:selectinstitution",e=>{document.querySelector('[data-tab="connections"]').click();selectByName(e.detail?.name||"")});
 window.addEventListener("signalnorth:refresh",boot);
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
