"use strict";
/* CFPB public categorical complaint explorer. No consumer narratives or ZIPs. */
(() => {
 const $=id=>document.getElementById(id);
 const html=value=>String(value??"").replace(/[&<>"']/g,c=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
 }[c]));
 const model={records:[],status:{},visible:30,history:[],historyStatus:{status:"not_attempted"}};
 function setOptions(id,values,label){
  const el=$(id);if(!el)return;
  const prior=el.value;
  el.innerHTML='<option value="">'+html(label)+'</option>'+
   values.map(x=>'<option value="'+html(x)+'">'+html(x)+'</option>').join("");
  if(values.includes(prior))el.value=prior;
 }
 function render(){
  if(!$("cfpbRows"))return;
  const source=model.status;
  const state=$("cfpbState").value;
  const company=$("cfpbCompany").value;
  const product=$("cfpbProduct").value;
  const issue=$("cfpbIssue").value;
  const q=$("cfpbQuery").value.toLocaleLowerCase().trim();
  const filtered=model.records.filter(x=>
   (!state||x.state===state)&&(!company||x.company===company)&&(!product||x.product===product)&&(!issue||x.issue===issue)&&
   (!q||[x.company,x.issue,x.sub_issue,x.sub_product].some(t=>
     String(t||"").toLocaleLowerCase().includes(q))))
   .slice().sort((a,b)=>String(b.date_received||"").localeCompare(String(a.date_received||"")) ||
     Number(b.id)-Number(a.id));
  const visible=filtered.slice(0,model.visible);
  $("cfpbHealth").textContent="Collection: "+(source.status||"not_attempted")+
   " · Last attempt "+String(source.last_attempt_at||"never").slice(0,16);
  $("cfpbSummary").textContent=model.records.length+
   " stored recent public complaints · "+(source.status||"not attempted")+
   " · Bounded sample, not national totals";
  const counts=new Map();
  for(const x of model.records){
   const name=x.product||"Unspecified product";
   counts.set(name,(counts.get(name)||0)+1);
  }
  const groups=[...counts].sort((a,b)=>b[1]-a[1]).slice(0,4);
  const companies=new Set(model.records.map(x=>x.company).filter(Boolean));
  const bankingProducts=new Set(["Checking or savings account","Credit card",
    "Money transfer, virtual currency, or money service","Mortgage","Vehicle loan or lease"]);
  const bankingRecords=model.records.filter(x=>bankingProducts.has(x.product));
  $("cfpbStats").innerHTML='<div class="cfpb-sample-count"><strong>'+
   model.records.length.toLocaleString()+'</strong><span>Stored complaint records (sample)</span></div>'+
   '<div class="cfpb-mini-stat"><strong>'+companies.size+'</strong><span>Named companies in sample (not all banks)</span></div>'+
   '<div class="cfpb-mini-stat"><strong>'+bankingRecords.length+'</strong><span>Banking-product complaints in sample</span></div>'+
   groups.map(([product,n])=>'<div class="cfpb-mini-stat"><strong>'+n+
    '</strong><span>'+html(product)+'</span></div>').join("");
  $("cfpbRows").innerHTML=visible.length?visible.map(x=>{
   const link=String(x.source_url||"");
   const safe=/^https:\/\/www\.consumerfinance\.gov\/data-research\/consumer-complaints\/search\/api\/v1\/[0-9]{1,10}$/.test(link);
   return '<article class="world-reporting-record cfpb-record">'+
    '<div class="world-reporting-date">CFPB #'+html(x.id)+' · Received '+html(x.date_received)+
     (x.state?' · Consumer state '+html(x.state):"")+'</div>'+
    '<strong>'+html(x.company||"Company not specified")+'</strong>'+
    '<p>'+html(x.product||"Product not specified")+
     (x.sub_product?' · '+html(x.sub_product):"")+'</p>'+
    '<div class="world-reporting-details">Consumer-reported issue: '+html(x.issue||"Unspecified")+
     (x.sub_issue?' · '+html(x.sub_issue):"")+'</div>'+
    '<div class="world-reporting-details">Company response: '+html(x.company_response||"Not listed")+
     (x.company_public_response?' · Public response: '+html(x.company_public_response):"")+
     (x.date_sent_to_company?' · Sent to company: '+html(x.date_sent_to_company):"")+
     (x.submitted_via?' · Submitted via: '+html(x.submitted_via):"")+
     ' · Timely response: '+html(x.timely||"Not listed")+'</div>'+
    '<div class="world-reporting-details">Public complaint allegation · Not an enforcement finding'+
     (safe?' · <a target="_blank" rel="noopener noreferrer" href="'+html(link)+'">CFPB original record ↗</a>':"")+
    '</div></article>';
  }).join(""):'<div class="empty">'+(model.records.length?
   "No records match your filters.":"No complaint records have been successfully collected yet. Check the source status; zero records do not mean zero complaints.")+'</div>';
  $("cfpbShown").textContent=visible.length+" of "+filtered.length+" matching records shown (stored sample, not population)";
  $("cfpbMore").hidden=visible.length>=filtered.length;
 }

 function renderHistorical(){
  if(!$("cfpbHistoryRows"))return;
  const status=model.historyStatus;
  const year=$("cfpbHistoryYear").value;
  const issue=$("cfpbHistoryIssue").value;
  const matches=model.history.filter(x=>(!year||x.month.startsWith(year))&&
   (!issue||(x.sample_issue_breakdown||[]).some(r=>r.issue===issue)))
   .slice().sort((a,b)=>b.month.localeCompare(a.month));
  const exact=model.history.filter(x=>x.monthly_total_status==="exact_api_total").length;
  $("cfpbHistorySummary").textContent=exact+"/"+(status.months_available||"~179")+
   " months with exact totals · last scan "+String(status.last_attempt_at||"not yet").slice(0,16);
  $("cfpbHistoryRows").innerHTML=matches.length?matches.map(m=>{
   const exactTotal=m.monthly_total_status==="exact_api_total" &&
    Number.isInteger(m.exact_published_complaint_total)?
    m.exact_published_complaint_total.toLocaleString()+" exact published complaints":
    "Exact monthly total unavailable";
   const reasons=(m.sample_issue_breakdown||[]).slice(0,6);
   return '<article class="world-reporting-record cfpb-history-row">'+
    '<div class="world-reporting-date">'+html(m.month)+' · '+html(exactTotal)+'</div>'+
    '<strong>'+html(m.sample_size||0)+' sampled public records (max 100)</strong>'+
    '<div class="world-reporting-details">Sampled complaint reasons (not population totals):</div>'+
    '<div class="cfpb-history-reasons">'+reasons.map(r=>'<span>'+
      html(r.issue)+(r.sub_issue?' / '+html(r.sub_issue):"")+
      ' · '+html(r.sample_count)+' sampled</span>').join("")+'</div>'+
    '</article>';
  }).join(""):'<div class="empty">No historical months match yet. Unfetched months are not zero-complaint months.</div>';
 }

 async function load(){
  if(!$("cfpbComplaints"))return;
  const paths=["cfpb_complaints.json","cfpb_complaints_status.json","cfpb_monthly_history.json","cfpb_monthly_history_status.json"];
  const results=await Promise.allSettled(paths.map(async file=>{
   const resp=await fetch("./data/"+file+"?v="+Date.now(),{cache:"no-store"});
   if(!resp.ok)throw new Error(file+" HTTP "+resp.status);
   return resp.json();
  }));
  if(results[0].status==="fulfilled")
   model.records=(results[0].value.complaints||[]).filter(x=>
    x.evidence_status==="published_consumer_complaint_not_verified" && /^\d+$/.test(x.id));
  if(results[2].status==="fulfilled")model.history=results[2].value.months||[];
  if(results[3].status==="fulfilled")model.historyStatus=results[3].value||{};
  else model.historyStatus={status:"unavailable",months_available:0};
  if(results[1].status==="fulfilled")model.status=results[1].value||{};
  else model.status={status:"status_unavailable"};
  setOptions("cfpbCompany",[...new Set(model.records.map(x=>x.company).filter(Boolean))].sort(),"All companies");
  setOptions("cfpbProduct",[...new Set(model.records.map(x=>x.product).filter(Boolean))].sort(),"All products");
  setOptions("cfpbState",[...new Set(model.records.map(x=>x.state).filter(Boolean))].sort(),"All states");
  setOptions("cfpbIssue",[...new Set(model.records.map(x=>x.issue).filter(Boolean))].sort(),"All issues");
  setOptions("cfpbHistoryYear",[...new Set(model.history.map(x=>x.month.slice(0,4)))].sort().reverse(),"All fetched years");
  setOptions("cfpbHistoryIssue",[...new Set(model.history.flatMap(x=>(x.sample_issue_breakdown||[]).map(y=>y.issue)).filter(Boolean))].sort(),"All sampled reasons");
  render();
  renderHistorical();
  for(const id of ["cfpbHistoryYear","cfpbHistoryIssue"]){
   $(id)?.addEventListener("change",renderHistorical);
  }
  for(const id of ["cfpbCompany","cfpbProduct","cfpbIssue","cfpbState","cfpbQuery"]){
   $(id)?.addEventListener(id==="cfpbQuery"?"input":"change",()=>{
    model.visible=30;render();
   });
  }
  $("cfpbMore")?.addEventListener("click",()=>{model.visible+=30;render();});
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",load);
 else load();
})();
