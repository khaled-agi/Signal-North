"use strict";
/* Auditable review presentation. No API actions, no automatic evidence promotion. */
(() => {
 const el=id=>document.getElementById(id);
 const escape=x=>String(x??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
 const money=x=>Number(x).toLocaleString("en-CA",{maximumFractionDigits:2,style:"currency",currency:"CAD"});
 const date=x=>x?String(x).slice(0,10):"Date not confirmed";
 const labelRole={
  customer_financial_institution:"Customer's account provider",
  institution_impersonated:"Institution allegedly impersonated",
  bank_not_identified:"Institution not identified",
  unnamed_financial_institution_assisted_recovery:"Unnamed recovery-assisting institution",
  affected_payment_provider:"Affected payment provider",
  subject_of_investigation:"Subject of reported investigation",
  regulator:"Regulator named in reporting",
  named_in_reporting_no_role_established:"Named but role unestablished",
 };
 const impactText={
  victim_reported_loss:"Victim-reported loss, NOT necessarily bank-borne",
  unauthorized_credit_exposure:"Unauthorized credit exposure, NOT established as final loss",
  recovered_amount:"Funds reportedly recovered, NOT a new victim loss",
  bank_borne_loss:"Bank-borne loss (requires explicit documentation)",
  regulatory_penalty:"Regulatory penalty, NOT customer loss",
 };
 let events=[],links=[],visible=20,wired=false;
 function urlLink(url,title){
  try{
   const u=new URL(url);
   if(u.protocol!=="https:")return "";
   return '<a href="'+escape(u.href)+'" target="_blank" rel="noopener noreferrer">'+escape(title)+' ↗</a>';
  }catch{return ""}
 }
 function sectionTitle(label){return '<h3 class="reviewed-section-title">'+escape(label)+'</h3>'}
 function refList(refs,sourceMap){
  const names=(refs||[]).map(x=>sourceMap.get(x)?.publisher||x);
  return '<span class="reviewed-citation">Source: '+escape(names.join(", ")||"Attribution missing")+'</span>';
 }
 function detail(event){
  if(!event)return;
  const sourceMap=new Map(event.sources.map(x=>[x.id,x]));
  const entities=event.entities||[];
  const amounts=event.reported_impact||[];
  const sourceList=(event.sources||[]).map(x=>'<article class="reviewed-source-card">'+
    '<strong>'+escape(x.publisher)+' · '+escape(x.document_type||"Public reporting")+' · '+escape(date(x.publication_date))+'</strong>'+
    '<p>'+urlLink(x.url,"Open cited publication")+'</p>'+
    '<p>Source ID: '+escape(x.id)+' · '+escape(x.provenance||"Curated public evidence")+'</p></article>').join("");
  const claims=(event.claims||[]).map(c=>'<article class="reviewed-claim">'+
    '<strong>'+escape(c.kind.replace(/_/g," "))+' · '+escape(c.certainty||"Source attributed")+'</strong>'+
    '<p>'+escape(c.statement)+'</p>'+refList(c.source_ids,sourceMap)+
    (c.qualification?'<p class="reviewed-evidence-warning">'+escape(c.qualification)+'</p>':"")+'</article>').join("");
  const timeline=(event.timeline||[]).map(x=>'<article class="reviewed-timeline-step">'+
    '<strong>'+escape(x.step)+'. '+escape(x.label||"Reported stage")+'</strong>'+
    '<p>'+escape(x.narrative||"")+'</p><div class="reviewed-citation">'+escape(x.event_date||"Date not established")+'</div>'+
    refList(x.source_ids,sourceMap)+'</article>').join("");
  const moneyRows=amounts.map(x=>'<article class="reviewed-claim">'+
    '<strong>'+escape(money(x.value))+' · '+escape(impactText[x.type]||x.type)+'</strong>'+
    '<p>'+escape(x.approximate?"Approximate amount. ":"")+
    'Original reporting classification: '+escape(x.type.replace(/_/g," "))+
    ' · attributed to '+escape(x.attributed_to)+'.</p>'+
    refList(x.source_ids,sourceMap)+'</article>').join("");
  const entityRows=entities.map(x=>'<li><strong>'+escape(x.name||"Unknown organization")+'</strong> — '+
   escape(labelRole[x.role]||x.role)+' · '+refList(x.source_ids,sourceMap)+
   '. <em>Liability not established.</em></li>').join("");
  const geography=event.geography||{};
  const details=
    '<div class="eyebrow">SOURCE-ATTRIBUTED EVENT / EVIDENCE RECORD</div>'+
    '<h2 class="reviewed-detail-title">'+escape(event.title)+'</h2>'+
    '<div class="reviewed-statusnote"><strong>Review status: '+escape(event.review_state||"Not established")+'</strong>'+
    ' · Independently verified: <strong>No</strong>. This entry preserves claims reported by public sources. It does not independently establish criminal conduct, institutional fault, or a final bank loss.'+
    '</div>'+
    '<div class="reviewed-keyfacts">'+
     '<div><span>Incident period</span><strong>'+escape(event.incident_period||"Not established")+'</strong></div>'+
     '<div><span>Report publication</span><strong>'+escape(date(event.publication_date))+'</strong></div>'+
     '<div><span>Reported location reference</span><strong>'+escape(geography.label||"Not established")+'</strong><span>'+escape(geography.role||"Location role unknown")+'</span></div>'+
     '<div><span>Reviewer audit</span><strong>'+escape(event.reviewer_id||"Legacy review attribution not recorded")+'</strong><span>'+escape(date(event.last_reviewed_at))+'</span></div>'+
    '</div>'+
    sectionTitle("Source-supported claims")+
    (claims||'<p>Individual sourced claims are not yet available.</p>')+
    sectionTitle("Reported financial impact, with amount type")+
    (moneyRows||'<p class="reviewed-intro">The original reporting does not establish a numeric impact.</p>')+
    sectionTitle("Organizations and their reported roles")+
    (entities.length?'<ul class="reviewed-list">'+entityRows+'</ul>':'<p class="reviewed-intro">No institution named in the source. Do not guess.</p>')+
    sectionTitle("Attributed reported sequence")+
    (timeline||'<p class="reviewed-intro">No source-grounded sequence established.</p>')+
    sectionTitle("What remains unanswered")+
    ((event.unanswered_questions||[]).length?'<ul class="reviewed-list">'+event.unanswered_questions.map(q=>'<li>'+escape(q)+'</li>').join("")+'</ul>':'<p class="reviewed-intro">No questions documented; this does not mean the record is complete.</p>')+
    '<p class="reviewed-evidence-warning">Counterevidence: '+escape(event.counterevidence_status||"Not assessed")+'. The absence of contradictory material is not proof that the account is complete.</p>'+
    sectionTitle("Cited publications and provenance")+
    (sourceList||'<p>No sources linked.</p>')+
    ((event.reporting_group_links||[]).length?sectionTitle("Editorially approved linked article groups")+
      event.reporting_group_links.map(link=>'<button type="button" class="report-variations" data-story="'+escape(link.group_id)+'">View reviewed reporting group →</button><p class="reviewed-intro">'+escape(link.review_rationale)+'</p>').join(""):
      '<p class="reviewed-intro"><strong>No article-group identity matches approved.</strong> Similar-sounding headline suggestions remain in the separate unverified review queue.</p>')+
    '<p class="reviewed-statusnote">'+escape(event.disclaimer||"Attributed public-source report; not an independent finding.")+'</p>';
  if(typeof openDrawer==="function")openDrawer(details);
  else{
   el("drawerBody").innerHTML=details;
   el("overlay").classList.remove("hidden");
   document.body.style.overflow="hidden";
  }
 }
 function card(x){
  const amounts=x.reported_impact||[],amount=amounts[0];
  const impact=amount?(money(amount.value)+" · "+(impactText[amount.type]||amount.type)):"No published financial impact";
  return '<article class="reviewed-card"><div class="reviewed-top"><span class="reviewed-status">SOURCE-REVIEWED · ATTRIBUTED</span><span>'+escape(date(x.publication_date))+'</span></div>'+
   '<h3>'+escape(x.title)+'</h3><p>'+escape(x.fraud_type||"Financial crime report")+'</p>'+
   '<div class="reviewed-tags"><span>'+escape(x.province||"Province undetermined")+'</span><span>'+escape(x.institution_role.replace(/_/g," "))+'</span></div>'+
   '<p><strong>'+escape(impact)+'</strong></p>'+
   '<div class="reviewed-actions"><button data-reviewed-open="'+escape(x.id)+'" type="button">Examine evidence trail →</button><span class="reviewed-source-label">'+(x.sources||[]).length+' attributed source(s)</span></div></article>';
 }
 function render(){
  const q=el("reviewedSearch").value.toLowerCase().trim(),prov=el("reviewedProvince").value,type=el("reviewedImpact").value;
  const list=events.filter(e=>(!prov||e.province===prov)&&
   (!type||(e.reported_impact||[]).some(x=>x.type===type))&&
   (!q||[e.title,e.fraud_type,e.incident_period,...(e.entities||[]).map(x=>x.name),...(e.sources||[]).map(x=>x.publisher)].join(" ").toLowerCase().includes(q)));
  el("reviewedCount").textContent=list.length+" matching / "+events.length+" source-reviewed records";
  el("reviewedSummary").innerHTML='<div><strong>'+events.length+'</strong><span>Source-attributed reviewed records</span></div>'+
   '<div><strong>'+events.filter(x=>x.independently_verified).length+'</strong><span>Independently verified by Signal North</span></div>'+
   '<div><strong>'+events.reduce((sum,x)=>sum+(x.sources||[]).length,0)+'</strong><span>Traceable original-source references</span></div>';
  el("reviewedEventRows").innerHTML=list.length?list.map(card).join(""):'<div class="empty">No reviewed events match. Try broader filters or examine the unverified reporting archive.</div>';
 }
 function renderCandidates(){
  const q=el("eventCandidateSearch").value.toLowerCase().trim(),threshold=Number(el("eventCandidateFilter").value||0);
  const matches=links.filter(x=>x.priority>=threshold&&(!q||[...(x.headlines||[]).map(z=>z.title),...(x.reasons||[])].join(" ").toLowerCase().includes(q)));
  el("eventCandidateCount").textContent=matches.length+" suggested pairs · Not verified";
  el("eventCandidateRows").innerHTML=matches.slice(0,visible).map(x=>'<article class="candidate-card">'+
   '<div class="candidate-head"><strong>Unverified link suggestion</strong><span>Review priority '+x.priority+' · NOT one confirmed event</span></div>'+
   '<h3>Compare original reporting</h3><div class="candidate-links">'+(x.headlines||[]).map(r=>
     '<div><div class="reviewed-citation">'+escape(date(r.publication_date))+'</div>'+
     '<button class="candidate-title" data-story="'+escape(r.group_id)+'" type="button">'+escape(r.title)+'</button></div>').join("")+'</div>'+
   '<p class="candidate-reasons">Why suggested: '+escape((x.reasons||[]).join("; "))+'</p></article>').join("")+
   (!matches.length?'<div class="empty">No unverified report pairs match this research search.</div>':"");
  el("eventCandidateMore").hidden=matches.length<=visible;
 }
 async function boot(){
  const promises=await Promise.allSettled(
    ["reviewed_events.json","event_review_candidates.json"].map(async file=>{
      const r=await fetch("./data/"+file+"?v="+Date.now(),{cache:"no-store"});
      if(!r.ok)throw Error(file+": HTTP "+r.status);
      return r.json();
    }));
  if(promises[0].status==="fulfilled"){
    const d=promises[0].value;
    events=d.events||[];
    el("reviewedProvince").innerHTML='<option value="">All provinces</option>'+
      [...new Set(events.map(x=>x.province).filter(Boolean))].sort().map(x=>'<option value="'+escape(x)+'">'+escape(x)+'</option>').join("");
    render();
  }else{
    el("reviewedCount").textContent="Event database temporarily unavailable";
    el("reviewedEventRows").innerHTML='<div class="empty">The sourced event database could not be loaded. The original case summaries below remain accessible.</div>';
  }
  if(promises[1].status==="fulfilled"){
    links=promises[1].value.items||[];
    renderCandidates();
  }else{
    el("eventCandidateCount").textContent="Suggestions unavailable";
    el("eventCandidateRows").innerHTML='<div class="empty">Unverified relationship suggestions are temporarily unavailable. No events were automatically linked.</div>';
  }
  if(!wired){
    for(const id of ["reviewedSearch","reviewedProvince","reviewedImpact"])
      el(id).addEventListener(id==="reviewedSearch"?"input":"change",render);
    el("eventCandidateSearch").addEventListener("input",()=>{visible=20;renderCandidates()});
    el("eventCandidateFilter").addEventListener("change",()=>{visible=20;renderCandidates()});
    el("eventCandidateMore").addEventListener("click",()=>{visible+=20;renderCandidates()});
    document.addEventListener("click",e=>{
      const button=e.target.closest("[data-reviewed-open]");
      if(!button)return;
      detail(events.find(x=>x.id===button.dataset.reviewedOpen));
    });
    wired=true;
  }
 }
 window.addEventListener("signalnorth:refresh",boot);
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
