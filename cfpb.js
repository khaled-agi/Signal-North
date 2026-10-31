"use strict";
/* CFPB public categorical complaint explorer. No consumer narratives or ZIPs. */
(() => {
 const $=id=>document.getElementById(id);
 const html=value=>String(value??"").replace(/[&<>"']/g,c=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
 }[c]));
 const model={records:[],status:{},visible:30};
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
  const product=$("cfpbProduct").value;
  const q=$("cfpbQuery").value.toLocaleLowerCase().trim();
  const filtered=model.records.filter(x=>
   (!state||x.state===state)&&(!product||x.product===product)&&
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
  $("cfpbStats").innerHTML='<div class="cfpb-sample-count"><strong>'+
   model.records.length.toLocaleString()+'</strong><span>Stored complaint records (sample)</span></div>'+
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
     ' · Timely response: '+html(x.timely||"Not listed")+'</div>'+
    '<div class="world-reporting-details">Public complaint allegation · Not an enforcement finding'+
     (safe?' · <a target="_blank" rel="noopener noreferrer" href="'+html(link)+'">CFPB original record ↗</a>':"")+
    '</div></article>';
  }).join(""):'<div class="empty">'+(model.records.length?
   "No records match your filters.":"No complaint records have been successfully collected yet. Check the source status; zero records do not mean zero complaints.")+'</div>';
  $("cfpbShown").textContent=visible.length+" of "+filtered.length+" matching records shown (stored sample, not population)";
  $("cfpbMore").hidden=visible.length>=filtered.length;
 }
 async function load(){
  if(!$("cfpbComplaints"))return;
  const paths=["cfpb_complaints.json","cfpb_complaints_status.json"];
  const results=await Promise.allSettled(paths.map(async file=>{
   const resp=await fetch("./data/"+file+"?v="+Date.now(),{cache:"no-store"});
   if(!resp.ok)throw new Error(file+" HTTP "+resp.status);
   return resp.json();
  }));
  if(results[0].status==="fulfilled")
   model.records=(results[0].value.complaints||[]).filter(x=>
    x.evidence_status==="published_consumer_complaint_not_verified" && /^\d+$/.test(x.id));
  if(results[1].status==="fulfilled")model.status=results[1].value||{};
  else model.status={status:"status_unavailable"};
  setOptions("cfpbProduct",[...new Set(model.records.map(x=>x.product).filter(Boolean))].sort(),"All products");
  setOptions("cfpbState",[...new Set(model.records.map(x=>x.state).filter(Boolean))].sort(),"All states");
  render();
  for(const id of ["cfpbProduct","cfpbState","cfpbQuery"]){
   $(id)?.addEventListener(id==="cfpbQuery"?"input":"change",()=>{
    model.visible=30;render();
   });
  }
  $("cfpbMore")?.addEventListener("click",()=>{model.visible+=30;render();});
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",load);
 else load();
})();
