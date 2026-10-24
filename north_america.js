"use strict";
/* Additional U.S. intelligence within the SAME Signal North SPA, map and navigation.
   Country selection remains a shared app filter, not a website redirect. */
(() => {
 const $=id=>document.getElementById(id);
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;":"&#39;"}[c]));
 const money=v=>Number(v)>=1e9?"US$"+(v/1e9).toFixed(2)+"B":"US$"+(v/1e6).toFixed(1)+"M";
 const num=v=>Number(v||0).toLocaleString("en-US");
 const link=(raw,text)=>{try{const u=new URL(raw);return u.protocol==="https:"?'<a href="'+esc(u.href)+'" target="_blank" rel="noopener noreferrer">'+esc(text)+' ↗</a>':"";}catch{return ""}};
 const data={states:{},ic3:null,news:[],events:[],status:{},visible:30,q:""};
 const sources=[
 ["FinCEN","https://www.fincen.gov/news/enforcement-actions","Federal BSA/AML enforcement index","Monitored"],
 ["CFPB","https://www.consumerfinance.gov/enforcement/actions/","Consumer financial enforcement listings and procedural outcomes","Monitored"],
 ["FBI IC3","https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf","State complaint counts, reported USD losses, complaints per 100K (2025)","Official annual study"],
 ["FTC","https://www.ftc.gov/news-events/explore-data","Consumer Sentinel and identity theft statistics","Reference only"],
 ["DOJ","https://www.justice.gov/news","U.S. Attorney prosecutions and charging releases","Reference only"],
 ["SEC","https://www.sec.gov/enforcement-litigation","Securities enforcement and litigation","Reference only"],
 ["OCC","https://www.occ.gov/topics/laws-and-regulations/enforcement-actions/index-enforcement-actions.html","National bank supervisory actions","Reference only"],
 ["FDIC","https://www.fdic.gov/","Bank regulatory and supervisory actions","Reference only"],
 ["FBI","https://www.ic3.gov/","Internet crime reporting, alerts and national statistics","Reference only"],
 ["State attorneys general","https://www.usa.gov/state-attorney-general","Directory covering state AG offices throughout the U.S.","Reference only"],
 ["FINRA","https://www.finra.org/","Broker dealer disciplinary matters and investor warnings","Reference only"]
 ];
 function list(){
  return [...data.events.map(e=>({...e,kind:"official"})),...data.news.map(e=>({...e,kind:"lead"}))]
   .sort((a,b)=>String(b.published_at||"").localeCompare(String(a.published_at||"")));
 }
 function nation(){
  const c=$("countryScope")?.value||"all";
  document.body.dataset.country=c;
  const usActive=c!=="ca";
  const caActive=c!=="us";
  ["northInsight","northIC3Context"].forEach(id=>{const el=$(id);if(el)el.hidden=!usActive;});
  document.querySelectorAll(".north-us-scope").forEach(el=>el.hidden=!usActive);
  document.querySelectorAll(".north-ca-scope").forEach(el=>el.hidden=!caActive);
  const select=$("mapMeasure"); if(select){
   [...select.options].filter(x=>x.value!=="records").forEach(o=>o.disabled=c==="ca");
   if(c==="ca"&&select.value!=="records")select.value="records";
  }
  render();
 }
 function filtered(){
  const q=data.q.toLowerCase().trim();
  return list().filter(r=>!q||[r.title,r.institution,r.publisher,r.summary,r.category,r.source,r.state_reference]
   .some(x=>String(x||"").toLowerCase().includes(q)));
 }
 function cards(rows){
  return rows.map(x=>{
   const source=x.kind==="official"?x.source:x.publisher||"Publisher unavailable";
   return '<article class="north-source-record"><div class="north-source-meta"><b class="'+(x.kind==="lead"?"north-unverified":"")+'">'+
    (x.kind==="lead"?"UNVERIFIED HEADLINE":"U.S. FEDERAL SOURCE")+'</b> · '+esc(String(x.published_at||"").slice(0,10))+' · '+
    esc(source)+'</div><button type="button" class="north-source-title" data-northrecord="'+esc(x.id)+'">'+esc(x.title)+'</button>'+
    '<p>'+esc(x.kind==="lead"?(x.state?data.states[x.state]?.name+" named in headline, not a verified incident location":"U.S. discovery query; geography not independently verified"):
    (x.status||"Federal case listing")+" · Federal filing, no assigned state")+'</p></article>';
  }).join("");
 }
 function renderReports(){
  const rows=filtered();
  $("northReporting").innerHTML='<div class="north-section-heading"><div class="eyebrow">UNITED STATES / SOURCE EVIDENCE</div><h2>U.S. reporting and federal enforcement</h2>'+
   '<p>Explore original FinCEN/CFPB records and syndicated news titles. Complaints, filings and headlines are distinct evidence levels; U.S. entries are not confirmed fraud incidents.</p></div>'+
   '<section class="panel"><div class="panel-heading"><div><h2>Original U.S. sources</h2></div><span class="small">'+num(rows.length)+' available records</span></div>'+
   '<div class="north-report-controls"><input id="northReportSearch" type="search" aria-label="Search U.S. reporting" value="'+esc(data.q)+'" placeholder="Search U.S. scam method, agency, institution..."></div>'+
   '<div id="northReportList">'+(rows.length?cards(rows.slice(0,data.visible)):'<p class="north-empty">No matching U.S. records in the current source snapshot.</p>')+'</div>'+
   '<div class="north-report-footer">'+(rows.length>data.visible?'<button id="northLoadMore" type="button">Load 30 more reports ↓</button>':"")+
   '<small>'+num(Math.min(rows.length,data.visible))+' of '+num(rows.length)+' sources shown</small></div></section>';
 }
 function renderEnforcement(){
  $("northEnforcement").innerHTML='<div class="north-section-heading"><div class="eyebrow">UNITED STATES / ENFORCEMENT</div><h2>Federal enforcement source records</h2><p>'+
   'FinCEN and CFPB listings retain source links and the latest known procedural outcome where reviewed. This is not a complete U.S. enforcement registry; no agency location is treated as a crime scene.</p></div>'+
   '<section class="panel"><div class="panel-heading"><div><h2>U.S. federal actions</h2></div><span class="small">'+num(data.events.length)+' indexed actions</span></div>'+
   (data.events.length?cards(data.events.map(x=>({...x,kind:"official"}))):'<p class="north-empty">No federal records are currently indexed.</p>')+'</section>';
 }
 function renderOrg(){
  const groups=new Map();
  for(const e of data.events){const key=e.institution||e.title;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e);}
  $("northInstitutions").innerHTML='<div class="north-section-heading"><div class="eyebrow">UNITED STATES / ORGANIZATIONS</div><h2>U.S. institutions named in source listings</h2>'+
   '<p>A mention or filing is not a risk score or finding of misconduct. Each organization is displayed as the exact source-named entity.</p></div>'+
   '<section class="panel"><div class="panel-heading"><div><h2>Named federal subjects</h2></div><span class="small">'+num(groups.size)+' names</span></div>'+
   [...groups].map(([name,items])=>'<div class="north-org-row"><strong>'+esc(name)+'</strong><span>'+num(items.length)+' record(s) · '+
     esc([...new Set(items.map(x=>x.source))].join(", "))+'</span></div>').join("")+'</section>';
 }
 function renderTrend(){
  const states=Object.entries(data.ic3?.states||{}).sort((a,b)=>b[1].complaints_per_100k-a[1].complaints_per_100k);
  const high=states.slice(0,12);
  const peak=high.length?high[0][1].complaints_per_100k:1;
  $("northTrends").innerHTML='<div class="north-section-heading"><div class="eyebrow">UNITED STATES / ORIGINAL FBI DATA</div><h2>2025 state-level IC3 complaint reporting</h2>'+
   '<p>Population-normalized 2025 FBI IC3 complaint counts, across all 50 states and D.C. This is not a measure of actual crime incidence.</p></div>'+
   '<section class="panel"><div class="panel-heading"><div><h2>Highest recorded complaints per 100,000</h2></div><span class="small">Source: FBI IC3 report, pp. 28–30</span></div>'+
   '<div class="north-bars">'+high.map(([code,r])=>'<div class="north-bar"><span>'+esc(r.name)+'</span><div class="north-bar-track"><i style="width:'+Math.min(100,100*r.complaints_per_100k/peak).toFixed(1)+'%"></i></div><strong>'+
    r.complaints_per_100k.toFixed(1)+'</strong></div>').join("")+'</div>'+
   '<p class="north-evidence-caution">These are IC3 complaints per 100K population, not victimization or substantiated fraud rates. '+
   link(data.ic3?.source_url,"Original 2025 report")+'</p></section>';
 }
 function renderSources(){
  $("northSources").innerHTML='<div class="north-section-heading"><div class="eyebrow">UNITED STATES / COVERAGE</div><h2>U.S. source monitoring and gaps</h2><p>'+
    'The 50-state directory and 2025 FBI IC3 map are complete. Ongoing enforcement ingestion is currently limited to FinCEN/CFPB and rotating syndicated titles; other agencies are listed as references only.</p></div>'+
    '<section class="panel"><div class="panel-heading"><div><h2>U.S. source registry</h2></div><span class="small">'+num(data.status.states_ever_scanned||0)+' / 51 states scanned for news</span></div>'+
    sources.map(([name,url,desc,status])=>'<div class="north-source-entry"><div><strong>'+esc(name)+'</strong><span>'+esc(status)+'</span><p>'+esc(desc)+'</p></div>'+
      link(url,"Official source")+'</div>').join("")+'</section>';
 }
 function renderOverview(){
  const national=data.ic3?.national||{};
  const selectedRegion=$("mapProvince")?.value||"";
  const state=selectedRegion.startsWith("US-")?data.ic3?.states?.[selectedRegion.slice(3)]:null;
  const c=$("countryScope").value;
  if(c==="ca")return;
  const title=state?state.name+" · 2025 FBI IC3":"United States · 2025 FBI IC3";
  const complaint=state?state.complaints:national.all_complaints;
  const loss=state?state.reported_loss_usd:national.reported_loss_usd;
  const rate=state?state.complaints_per_100k:null;
  $("northInsight").innerHTML='<div><div class="eyebrow">U.S. DATA · ALL 50 STATES + D.C.</div><strong>'+esc(title)+'</strong><span>'+num(complaint)+' reported complaints · '+
    money(loss||0)+' losses reported in USD'+(rate?" · "+rate.toFixed(1)+" complaints per 100K":"")+'</span><p>Source: FBI IC3 2025. Counts represent filed complaints, not independently confirmed crimes. U.S. enforcement and Canadian CAFC measures are kept separate. '+
    link(data.ic3?.source_url,"Original report")+'</p></div>';
  $("northIC3Context").innerHTML='<strong>U.S. geographic evidence:</strong> Choose <b>FBI IC3 complaints / rate / reported USD losses</b> above to compare all 50 states and D.C. The default map combines Canadian reports and U.S. state-mentioned reporting; no U.S. federal action is assigned to an invented state.';
 }
 function render(){renderOverview();renderReports();renderEnforcement();renderOrg();renderTrend();renderSources();}
 function detail(id){
  const x=list().find(x=>String(x.id)===String(id));if(!x)return;
  const official=x.kind==="official";
  const fields=official?[
    ["Agency",x.source],["Named entity",x.institution],["Original filing date",x.published_at],
    ["Procedural status",x.status],["Outcome date",x.outcome_at||"See issuing agency"],
    ["Source type",x.evidence_level],["U.S. state","Not inferred for federal filings"]
   ]:[
    ["Publisher",x.publisher],["Publication date",x.published_at],
    ["Headline type",x.category],["U.S. state",x.state?data.states[x.state]?.name+" mentioned in headline":"Not independently located"],
    ["Evidence status","Unverified syndicated headline"]
   ];
  $("drawerBody").innerHTML='<div class="eyebrow">'+(official?"U.S. FEDERAL SOURCE":"UNVERIFIED U.S. REPORTING")+'</div><h2>'+
    esc(x.title)+'</h2><p>'+esc(official?(x.summary||"See original regulator notice."):
    "This article title is a research lead only, not a verified incident, adjudicated finding, loss or attribution of misconduct.")+'</p><h3>Evidence</h3><dl>'+
    fields.map(([k,v])=>'<dt>'+esc(k)+'</dt><dd>'+esc(v||"Not reported")+'</dd>').join("")+'</dl>'+
    '<div class="warning">'+(official?"An enforcement filing may later be dismissed, amended or appealed. Confirm latest disposition with the regulator.":
    "Do not infer victim losses, geographic incidence or institutional fault from a headline or its publisher.")+'</div>'+
    link(official?x.source_url:x.url,"Open original source");
  $("overlay").classList.remove("hidden");document.body.style.overflow="hidden";
 }
 async function getJSON(file){
  const r=await fetch("./data/"+file+"?v="+Date.now(),{cache:"no-store"});
  if(!r.ok)throw Error(file+" HTTP "+r.status);
  return r.json();
 }
 async function load(){
  const files=["us_states.json","us_ic3_2025.json","us_enforcement.json","us_news.json","us_status.json"];
  const results=await Promise.allSettled(files.map(getJSON));
  data.states=results[0].status==="fulfilled"?(results[0].value.states||{}):{};
  data.ic3=results[1].status==="fulfilled"?results[1].value:null;
  data.events=results[2].status==="fulfilled"?(results[2].value.events||[]).map(x=>({...x,country:"US"})):[];
  data.news=results[3].status==="fulfilled"?(results[3].value.leads||[]).map(x=>({
   ...x,country:"US",map_province:x.state?"US-"+x.state:null,
   map_location:x.state?(data.states[x.state]?.name||x.state)+" — headline state mention (state-capital reference)":null,
   map_latitude:x.state?data.states[x.state]?.latitude:null,map_longitude:x.state?data.states[x.state]?.longitude:null,
   underlying_headline_count:1,source_count:1
  })):[];
  data.status=results[4].status==="fulfilled"?results[4].value:{};
  window.dispatchEvent(new CustomEvent("signalnorth:usready",{detail:{
   states:data.states,ic3:data.ic3,news:data.news,events:data.events
  }}));
  nation();
 }
 function wire(){
  document.addEventListener("click",e=>{
    const rec=e.target.closest("[data-northrecord]");
    if(rec){e.preventDefault();detail(rec.dataset.northrecord);return;}
    if(e.target.id==="northLoadMore"){data.visible+=30;renderReports();}
  });
  document.addEventListener("input",e=>{
    if(e.target.id==="northReportSearch"){data.q=e.target.value;data.visible=30;
      // Rebuild only records to preserve caret and typed value.
      const rows=filtered();
      $("northReportList").innerHTML=rows.length?cards(rows.slice(0,data.visible)):'<p class="north-empty">No matching records.</p>';
      const footer=$("northReportList").nextElementSibling;
      footer.innerHTML=(rows.length>data.visible?'<button id="northLoadMore" type="button">Load 30 more reports ↓</button>':"")+
       '<small>'+num(Math.min(rows.length,data.visible))+' of '+num(rows.length)+' sources shown</small>';
    }
  });
  $("countryScope").addEventListener("change",nation);
  $("mapProvince").addEventListener("change",renderOverview);
  $("mapMeasure").addEventListener("change",renderOverview);
  window.addEventListener("signalnorth:countryscope",nation);
  window.addEventListener("signalnorth:refresh",load);
 }
 function start(){wire();load();}
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start);
 else start();
})();
