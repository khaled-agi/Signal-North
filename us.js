"use strict";
/* United States workspace: federal source records are never allocated to a state;
   state map circles mean title-mentioned geography only, NOT reported fraud rates. */
(() => {
 const $=id=>document.getElementById(id);
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const url=v=>{try{const u=new URL(v);return u.protocol==="https:"?u.href:""}catch{return ""}};
 const link=(raw,label)=>{const u=url(raw);return u?'<a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' ↗</a>':""};
 const n=x=>Number(x||0).toLocaleString("en-US");
 const day=v=>String(v||"").slice(0,10)||"Date not established";
 const st={states:{},enforcement:[],leads:[],status:{},country:"US",
  view:"overview",state:"",layer:"all",year:"",agency:"",topic:"",q:"",limit:30,map:null,pins:null};
 const directory=[
  {name:"Financial Crimes Enforcement Network (FinCEN)",source:"FinCEN",url:"https://www.fincen.gov/news/enforcement-actions",desc:"Bank Secrecy Act / AML administrative enforcement; indexed official actions",monitored:true},
  {name:"Consumer Financial Protection Bureau (CFPB)",source:"CFPB",url:"https://www.consumerfinance.gov/enforcement/actions/",desc:"Consumer financial enforcement; complaints, orders, terminations and dismissals must be distinguished",monitored:true},
  {name:"Google News (United States)",source:"Google News RSS",url:"https://news.google.com/search?q=fraud%20United%20States&hl=en-US&gl=US&ceid=US%3Aen",desc:"Rotating syndicated headline discovery, not independently confirmed incident reporting",monitored:true},
  {name:"FBI Internet Crime Complaint Center (IC3)",source:"FBI IC3",url:"https://www.ic3.gov/annualreport/reports",desc:"Annual internet-crime reporting and separate geographic complaint statistics",monitored:false},
  {name:"Federal Trade Commission (FTC)",source:"FTC",url:"https://www.ftc.gov/news-events/explore-data",desc:"Consumer Sentinel reports and state/metro fraud reporting statistics",monitored:false},
  {name:"Department of Justice (DOJ)",source:"DOJ",url:"https://www.justice.gov/news",desc:"Federal prosecutions and press releases; allegations and dispositions require case review",monitored:false},
  {name:"Securities and Exchange Commission (SEC)",source:"SEC",url:"https://www.sec.gov/enforcement-litigation",desc:"Civil securities enforcement, litigation releases and administrative proceedings",monitored:false},
  {name:"Office of the Comptroller of the Currency (OCC)",source:"OCC",url:"https://www.occ.gov/topics/laws-and-regulations/enforcement-actions/index-enforcement-actions.html",desc:"Federal banking supervision and formal enforcement orders",monitored:false},
  {name:"Federal Deposit Insurance Corporation (FDIC)",source:"FDIC",url:"https://www.fdic.gov/",desc:"Bank regulatory enforcement and financial institution source records",monitored:false},
  {name:"State attorneys general (all states + D.C.)",source:"State AGs",url:"https://www.usa.gov/state-attorney-general",desc:"Official directory of state attorney general offices; links are not ingested cases",monitored:false},
  {name:"Financial Industry Regulatory Authority (FINRA)",source:"FINRA",url:"https://www.finra.org/",desc:"Broker-dealer disciplinary matters and investor alerts",monitored:false}
 ];
 const sources=()=>st.enforcement.map(e=>({...e,kind:"official",agency:e.source||"Federal regulator"})).concat(
  st.leads.map(e=>({...e,kind:"lead",agency:"Syndicated news"})));
 const isLead=e=>e.kind==="lead";
 const recordUrl=e=>isLead(e)?e.url:e.source_url;
 const recordDate=e=>e.published_at||"";
 function displayed(){
  let rows=sources();
  if(st.state)rows=rows.filter(e=>isLead(e)&&e.state===st.state); // Federal cases have NO incident state.
  if(st.layer!=="all")rows=rows.filter(e=>e.kind===(st.layer==="official"?"official":"lead"));
  if(st.year)rows=rows.filter(e=>String(recordDate(e)).startsWith(st.year));
  if(st.agency)rows=rows.filter(e=>e.agency===st.agency);
  if(st.topic)rows=rows.filter(e=>e.category===st.topic);
  if(st.q)rows=rows.filter(e=>[e.title,e.institution,e.publisher,e.summary,e.category,e.source,e.state_reference,e.sector].some(v=>String(v||"").toLowerCase().includes(st.q)));
  return rows.sort((a,b)=>String(recordDate(b)).localeCompare(String(recordDate(a))));
 }
 function metric(label,value,foot){
  return '<div class="metric"><span class="label">'+esc(label)+'</span><span class="value">'+esc(value)+'</span><span class="foot">'+esc(foot)+'</span></div>';
 }
 function renderMetrics(){
  const located=st.leads.filter(e=>e.state&&st.states[e.state]).length;
  const states=new Set(st.leads.map(e=>e.state).filter(Boolean));
  const official=st.enforcement.length;
  $("usMetrics").innerHTML=[
   metric("Official federal cases",n(official),"FinCEN / CFPB indexed source records"),
   metric("Unverified news leads",n(st.leads.length),"Google News discovery · not reviewed incidents"),
   metric("States named in headlines",n(states.size)+" / 51", "All 50 states + D.C. searchable"),
   metric("Federal agencies indexed",n(new Set(st.enforcement.map(e=>e.source)).size),"Other regulators in source directory")
  ].join("");
  const scanned=Number(st.status.states_ever_scanned||0);
  $("usCoverageMessage").textContent=st.state?
   "State "+st.states[st.state]?.name+": "+located+" located titles nationwide. Nationwide federal cases are not attributed to this state.":
   scanned+" of 51 jurisdictions have been queried by the rotating news scan. A missing title or state marker says nothing about actual fraud incidence.";
 }
 function narrative(){
  const rows=displayed();
  const official=rows.filter(e=>!isLead(e));
  const leads=rows.filter(isLead);
  const last=official[0]||null;
  const topics=new Map(); for(const r of leads)topics.set(r.category,(topics.get(r.category)||0)+1);
  const leadTopic=[...topics].sort((a,b)=>b[1]-a[1])[0];
  const scope=st.state?st.states[st.state]?.name||"Selected state":"U.S. public-source";
  $("usPulseDate").textContent=scope+" · source publications";
  const stateNotice=st.state?"State filters use literal title mentions. Federal cases remain available in Nationwide view.":
    "Only original federal listings are counted as official actions; news is unverified.";
  $("usPulse").innerHTML='<div class="us-pulse-grid">'+
   '<div class="us-pulse-item"><div class="us-pulse-label">Official source record</div><strong>'+esc(n(official.length))+'</strong><small>'+esc(last?"Latest selected: "+last.institution+" ("+day(last.published_at)+").":stateNotice)+'</small></div>'+
   '<div class="us-pulse-item"><div class="us-pulse-label">Reporting leads</div><strong>'+esc(n(leads.length))+'</strong><small>News title matches in this view. Not unique crimes, victims or proven losses.</small></div>'+
   '<div class="us-pulse-item"><div class="us-pulse-label">Most frequent headline topic</div><strong>'+esc(leadTopic?leadTopic[0]:"Not established")+'</strong><small>'+esc(leadTopic?leadTopic[1]+" collected title(s) in this view.": "No classified headlines in this view yet.")+'</small></div>'+
   '</div>';
 }
 function latest(){
  const rows=displayed().slice(0,9);
  $("usLatest").innerHTML=rows.length?rows.map(e=>
    '<article class="us-latest-record"><div class="us-latest-meta"><span class="us-evidence-pill '+(isLead(e)?"lead":"")+'">'+
    (isLead(e)?"UNVERIFIED NEWS":"OFFICIAL SOURCE")+'</span> · '+esc(day(e.published_at))+' · '+
    esc(e.source||e.publisher||"Source")+'</div>'+
    '<button type="button" class="us-record-title" data-usrecord="'+esc(e.id)+'">'+esc(e.title)+'</button>'+
    '<div class="us-latest-meta">'+esc(isLead(e)?(e.state?st.states[e.state]?.name+" named in headline":"Location unverified"):(e.status||"Published action"))+'</div></article>').join(""):
    '<div class="us-map-empty">No records in these filters. Try Nationwide or a different evidence layer. No state is assumed to be free of fraud.</div>';
 }
 function renderMap(){
  const host=$("usMap");
  if(!window.L){
   host.innerHTML='<p class="us-map-empty">The external map library has not loaded. All 50 states and D.C. remain accessible in the geography menu, and original evidence records stay searchable.</p>';
   $("usMapCaption").textContent="Map unavailable; all reporting and enforcement records remain accessible.";
   return;
  }
  if(!st.map){
   host.replaceChildren();
   st.map=L.map(host,{minZoom:3,maxZoom:11,scrollWheelZoom:false}).setView([39,-98],4);
   L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{
    maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
   }).addTo(st.map);
   L.control.zoom({position:"bottomright"}).addTo(st.map);
   st.pins=L.layerGroup().addTo(st.map);
  }
  st.pins.clearLayers();
  // Only title-based state references count as map observations.
  const permitted = displayed().filter(isLead).filter(e=>e.state&&st.states[e.state]);
  const counts=new Map();
  permitted.forEach(e=>counts.set(e.state,(counts.get(e.state)||0)+1));
  counts.forEach((count,code)=>{
    const loc=st.states[code],diameter=Math.max(29,Math.min(65,24+Math.sqrt(count)*7));
    const pin=L.marker([loc.latitude,loc.longitude],{
      icon:L.divIcon({className:"us-pin",html:'<span class="us-pin-inner">'+esc(n(count))+'</span>',
                     iconSize:[diameter,diameter],iconAnchor:[diameter/2,diameter/2]}),
      title:n(count)+" title reference(s) to "+loc.name+" (state-capital reference, not incidents)"
    }).addTo(st.pins);
    pin.bindPopup('<div class="us-state-popup"><strong>'+esc(loc.name)+'</strong><div>'+n(count)+' headline reference(s)</div><div>Marker at approximate state capital, not a crime scene. Click to filter by state.</div></div>');
    pin.on("click",()=>{st.state=code;$("usState").value=code;st.limit=30;refresh();});
  });
  $("usMapCaption").textContent=n(permitted.length)+" headlines explicitly name "+
    counts.size+" state(s) in this selection. Markers represent state-capital references, not incident sites or fraud rates.";
  if(st.state&&st.states[st.state]){
    const loc=st.states[st.state];st.map.setView([loc.latitude,loc.longitude],st.state==="AK"||st.state==="HI"?5:6,{animate:false});
  }
  setTimeout(()=>st.map&&st.map.invalidateSize(),50);
 }
 function reportRow(e){
  const desc=isLead(e)?
    (e.state?st.states[e.state]?.name+" in title · UNVERIFIED reporting":"Location unresolved · UNVERIFIED reporting"):
    (e.status||"Federal enforcement listing")+" · No state inferred";
  return '<article class="us-record"><div><div class="us-latest-meta"><span class="us-evidence-pill '+(isLead(e)?"lead":"")+'">'+
   (isLead(e)?"UNVERIFIED HEADLINE":"OFFICIAL REGULATOR INDEX")+'</span> · '+esc(day(e.published_at))+' · '+
   esc(e.source||e.publisher||"Original record")+'</div><button type="button" class="us-record-title" data-usrecord="'+esc(e.id)+'">'+
   esc(e.title)+'</button><div class="us-record-meta">'+esc(e.category||"Financial crime")+' · '+esc(desc)+'</div>'+
   (!isLead(e)&&e.summary?'<p class="us-record-summary">'+esc(e.summary)+'</p>':"")+'</div>'+
   '<button class="us-record-open" type="button" data-usrecord="'+esc(e.id)+'">View evidence →</button></article>';
 }
 function renderReporting(){
  const rows=displayed();
  const max=Math.min(st.limit,rows.length);
  $("usResultCount").textContent=n(rows.length)+" matching source records";
  $("usReportExplain").textContent=st.state?"Only headlines explicitly naming "+st.states[st.state]?.name+
   " appear here. Federal regulator filings have no inferred state location.":"Syndicated reporting is unverified. Official enforcement records represent published matters; consult the original for later dispositions.";
  $("usRows").innerHTML=rows.length?rows.slice(0,max).map(reportRow).join(""):'<div class="us-map-empty">No matching records. Clear the filters; an empty result means insufficient source coverage, not absence of financial crime.</div>';
  $("usMore").hidden=max===rows.length;
  $("usPageCount").textContent="Showing "+n(max)+" of "+n(rows.length)+" records";
 }
 function bars(entries,foot,barTitle){
  if(!entries.length)return '<div class="us-map-empty">No entries collected for this selection. This is a coverage gap, not a finding of zero incidents.</div>';
  const max=Math.max(1,...entries.map(x=>x[1]));
  return '<div class="us-chart-rows">'+entries.map(([label,count])=>
   '<div class="us-chart-row"><span class="label">'+esc(label)+'</span><div class="us-bar-track" title="'+esc(barTitle)+
   '"><div class="us-bar-fill" style="width:'+Math.max(0,(100*count/max)).toFixed(1)+'%"></div></div><strong>'+n(count)+'</strong></div>').join("")+
   '</div><p class="us-chart-foot">'+esc(foot)+'</p>';
 }
 function renderTrends(){
  const filtered=displayed(),official=filtered.filter(e=>!isLead(e)),leads=filtered.filter(isLead);
  const officialByYear=new Map();
  for(const e of official){const y=day(e.published_at).slice(0,4);if(/^20\d\d$/.test(y))officialByYear.set(y,(officialByYear.get(y)||0)+1);}
  $("usOfficialTrend").innerHTML=bars([...officialByYear].sort((a,b)=>a[0].localeCompare(b[0])),
   "Number of tracked FinCEN/CFPB source records by filing/publication year. Not comparable to fraud cases, prosecution rates, penalties, or losses.",
   "Official federal source publications");
  const monthly=new Map();
  for(const e of leads){const month=day(e.published_at).slice(0,7);if(/^20\d\d-\d\d$/.test(month))monthly.set(month,(monthly.get(month)||0)+1);}
  $("usNewsTrend").innerHTML=bars([...monthly].sort((a,b)=>a[0].localeCompare(b[0])).slice(-12),
   "Headline discoveries, subject to rotating state scans and changes in Google News indexing. Not a measure of fraud prevalence or growth.",
   "Discovered syndicated titles");
  const topics=new Map();
  for(const x of leads)topics.set(x.category,(topics.get(x.category)||0)+1);
  $("usMethodList").innerHTML=topics.size?'<div class="us-method-list">'+[...topics].sort((a,b)=>b[1]-a[1])
   .map(([c,count])=>'<span class="us-method-chip">'+esc(c)+' <strong>'+n(count)+'</strong></span>').join("")+'</div>'+
   '<p class="us-chart-foot">Multi-source headlines can cover related events. The categories reflect literal title clues only.</p>':
   '<div class="us-map-empty">No headline categories available in the selected period. The publication coverage will populate as state scans complete.</div>';
 }
 function renderOrganizations(){
  const q=$("usOrgSearch").value.toLowerCase().trim();
  const groups=new Map();
  for(const e of st.enforcement){
    const name=e.institution||e.title;
    if(!groups.has(name))groups.set(name,[]);
    groups.get(name).push(e);
  }
  const list=[...groups].filter(([name])=>name.toLowerCase().includes(q))
   .sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0]));
  $("usOrgCount").textContent=n(list.length)+" separately named subjects";
  $("usOrgRows").innerHTML=list.length?list.slice(0,150).map(([name,items])=>
   '<div class="us-org-entry"><div><button type="button" data-usorg="'+esc(name)+'">'+esc(name)+'</button><small>'+
   esc([...new Set(items.map(e=>e.source))].join(" · "))+' · Most recent index date '+esc(day(items[0].published_at))+
   '</small></div><span class="us-org-count">'+n(items.length)+' source record(s)</span></div>').join(""):
   '<div class="us-map-empty">No entities match the search.</div>';
 }
 function renderSources(){
  const scanned=Number(st.status.states_ever_scanned||0);
  $("usSourceAsOf").textContent="Snapshot "+day(st.status.updated_at);
  $("usSourceHealth").innerHTML='<div class="us-pulse-grid">'+
   '<div class="us-pulse-item"><span class="us-pulse-label">United States geography</span><strong>50 states + D.C.</strong><small>Complete jurisdiction directory, not complete evidence coverage</small></div>'+
   '<div class="us-pulse-item"><span class="us-pulse-label">States queried</span><strong>'+n(scanned)+' / 51</strong><small>Rotating state keyword scans since collection was enabled</small></div>'+
   '<div class="us-pulse-item"><span class="us-pulse-label">Original federal feeds</span><strong>FinCEN + CFPB</strong><small>Federal listing records, not a nationwide census of wrongdoing</small></div></div>'+
   '<div class="us-chart-foot">Federal source fetch status: '+esc(Object.entries(st.status.source_health||{}).filter(([k])=>k==="FinCEN"||k==="CFPB").map(([k,v])=>k+": "+(v.status||"unknown")).join(" · ")||"Not scanned yet")+'</div>';
  $("usSourceDirectory").innerHTML=directory.map(d=>
   '<div class="us-source-entry"><div><strong>'+esc(d.name)+'</strong><span class="us-source-state '+(d.monitored?"monitored":"")+'">'+
   (d.monitored?"COLLECTION ENABLED":"REFERENCE ONLY")+'</span><p>'+esc(d.desc)+'</p></div>'+
   link(d.url,"Original source")+'</div>').join("");
 }
 function openRecord(id){
  const e=sources().find(x=>String(x.id)===String(id));if(!e)return;
  const pairs=isLead(e)?[
   ["Evidence level","Unverified syndicated headline"],
   ["Publisher named in feed",e.publisher||"Unspecified"],
   ["Publication date",day(e.published_at)],
   ["Method from title",e.category||"Not classified"],
   ["State evidence",e.state?st.states[e.state]?.name+" expressly mentioned in the title":"No supported state mention"],
   ["Original review","Required before using as an investigated case"]
  ]:[
   ["Evidence level","Official federal regulatory listing"],
   ["Agency",e.source],
   ["Entity named",e.institution||"Not established"],
   ["Filing/index date",day(e.published_at)],
   ["Category",e.category],
   ["Current annotated status",e.status||"Review original source"],
   ["Matter number",e.case_number||"Not listed"],
   ["Outcome update",e.outcome_at||"Review latest original case materials"],
   ["Geography","Federal; no incident state assigned"],
   ["Financial measures","Not extracted; fines, restitution, consumer losses and exposure are distinct"]
  ];
  $("usDrawerBody").innerHTML='<div class="eyebrow">'+(isLead(e)?"UNVERIFIED RESEARCH LEAD":"ORIGINAL FEDERAL ENFORCEMENT SOURCE")+
   '</div><h2>'+esc(e.title)+'</h2><p>'+esc(isLead(e)?
    "This headline is a discovery aid only. A publisher's location and a state mention are not evidence that a crime occurred there, or that a named financial firm committed misconduct.":
    e.summary||"Consult the original federal enforcement record for the full findings, procedural status and source documents.")+
    '</p><h3>Evidence details</h3><dl>'+pairs.map(([k,v])=>'<dt>'+esc(k)+'</dt><dd>'+esc(v||"Not specified")+'</dd>').join("")+'</dl>'+
    '<div class="warning">'+(isLead(e)?
    "Not verified: do not treat this as a distinct incident, proven victim loss, charge or finding against a named institution.":
    "An enforcement filing may be modified, dismissed or appealed. Confirm the latest outcome at the issuing agency. Published records are not consumer fraud-loss statistics.")+
    '</div><div class="case-primary-source">'+link(recordUrl(e),isLead(e)?"Open reported publication":"Open original regulatory case document")+'</div>';
  $("usOverlay").classList.remove("hidden");document.body.style.overflow="hidden";
 }
 function openOrg(name){
  const records=st.enforcement.filter(e=>e.institution===name);
  $("usDrawerBody").innerHTML='<div class="eyebrow">ORGANIZATION RESEARCH / FEDERAL RECORDS</div><h2>'+esc(name)+'</h2>'+
   '<p>'+n(records.length)+' original regulator index record(s). This is not a measure of the institution’s fraud activity or customer loss. Proceedings may change status over time.</p>'+
   '<h3>Original notices</h3>'+records.map(e=>'<div class="us-source-entry"><div><strong>'+esc(day(e.published_at))+
   '</strong><p>'+esc(e.source+" · "+e.status)+'</p></div>'+link(e.source_url,"Source")+'</div>').join("");
  $("usOverlay").classList.remove("hidden");document.body.style.overflow="hidden";
 }
 function close(){$("usOverlay").classList.add("hidden");document.body.style.overflow="";}
 function switchView(view){
  if(!["overview","reporting","trends","organizations","sources"].includes(view))return;
  st.view=view;
  document.querySelectorAll(".us-view").forEach(el=>el.classList.toggle("hidden",el.id!=="us-"+view));
  document.querySelectorAll("button.nav[data-usview]").forEach(el=>el.classList.toggle("active",el.dataset.usview===view));
  const crumb={overview:"RESEARCH OVERVIEW",reporting:"EVIDENCE EXPLORER",trends:"COVERAGE TRENDS",organizations:"ORGANIZATION RESEARCH",sources:"SOURCES & METHODS"};
  $("usCrumb").textContent=crumb[view];
  if(view==="overview")setTimeout(()=>{if(st.map)st.map.invalidateSize();else renderMap();},60);
  window.scrollTo(0,0);
 }
 function refresh(){
  renderMetrics();narrative();latest();renderReporting();renderTrends();renderOrganizations();renderSources();renderMap();
 }
 function prepareFilters(){
  const sel=$("usState");
  const current=st.state;
  sel.innerHTML='<option value="">Nationwide / all 50 states + D.C.</option>'+
    Object.entries(st.states).sort((a,b)=>a[1].name.localeCompare(b[1].name))
    .map(([code,x])=>'<option value="'+esc(code)+'">'+esc(x.name)+'</option>').join("");
  sel.value=current;
  const rows=sources();
  const ag=$("usAgency");ag.innerHTML='<option value="">All source agencies</option>'+
    [...new Set(rows.map(x=>x.agency).filter(Boolean))].sort().map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join("");
  if([...ag.options].some(x=>x.value===st.agency))ag.value=st.agency;else st.agency="";
  const topic=$("usTopic");topic.innerHTML='<option value="">All subjects</option>'+
    [...new Set(rows.map(x=>x.category).filter(Boolean))].sort().map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join("");
  if([...topic.options].some(x=>x.value===st.topic))topic.value=st.topic;else st.topic="";
 }
 async function getJSON(path){const r=await fetch("./data/"+path+"?v="+Date.now(),{cache:"no-store"});if(!r.ok)throw Error(path+": "+r.status);return r.json();}
 async function load(){
  const paths=["us_states.json","us_enforcement.json","us_news.json","us_status.json"];
  const results=await Promise.allSettled(paths.map(getJSON));
  if(results[0].status!=="fulfilled"||results[1].status!=="fulfilled"){
    $("usError").textContent="U.S. geographic or primary-source data is temporarily unavailable. The source directory remains accessible.";
    $("usError").classList.remove("hidden");
  }else{$("usError").classList.add("hidden");}
  st.states=results[0].status==="fulfilled"?(results[0].value.states||{}):{};
  st.enforcement=results[1].status==="fulfilled"?(results[1].value.events||[]):[];
  st.leads=results[2].status==="fulfilled"?(results[2].value.leads||[]):[];
  st.status=results[3].status==="fulfilled"?results[3].value:{};
  $("usUpdated").textContent="Sources "+day(st.status.updated_at||results[1].value?.updated_at);
  prepareFilters();refresh();
 }
 function wire(){
  $("usReload").addEventListener("click",load);
  $("usState").addEventListener("change",e=>{st.state=e.target.value;st.limit=30;refresh();});
  $("usType").addEventListener("change",e=>{st.layer=e.target.value;st.limit=30;refresh();});
  $("usPeriod").addEventListener("change",e=>{st.year=e.target.value;st.limit=30;refresh();});
  $("usClear").addEventListener("click",()=>{
   st.state="";st.layer="all";st.year="";st.agency="";st.topic="";st.q="";st.limit=30;
   $("usState").value="";$("usType").value="all";$("usPeriod").value="";
   $("usAgency").value="";$("usTopic").value="";$("usSearch").value="";
   refresh();if(st.map)st.map.setView([39,-98],4);
  });
  $("usMapReset").addEventListener("click",()=>{st.state="";$("usState").value="";refresh();if(st.map)st.map.setView([39,-98],4);});
  $("usAgency").addEventListener("change",e=>{st.agency=e.target.value;st.limit=30;refresh();});
  $("usTopic").addEventListener("change",e=>{st.topic=e.target.value;st.limit=30;refresh();});
  $("usSearch").addEventListener("input",e=>{st.q=e.target.value.trim().toLowerCase();st.limit=30;refresh();});
  $("usMore").addEventListener("click",()=>{st.limit+=30;renderReporting();});
  $("usOrgSearch").addEventListener("input",renderOrganizations);
  document.addEventListener("click",e=>{
   const rec=e.target.closest("[data-usrecord]");
   if(rec){openRecord(rec.dataset.usrecord);return;}
   const org=e.target.closest("[data-usorg]");
   if(org){openOrg(org.dataset.usorg);return;}
   const nav=e.target.closest("[data-usview]");
   if(nav){switchView(nav.dataset.usview);return;}
  });
  $("usClose").addEventListener("click",close);
  $("usOverlay").addEventListener("click",e=>{if(e.target.id==="usOverlay")close();});
  document.addEventListener("keydown",e=>{if(e.key==="Escape")close();});
  window.addEventListener("signalnorth:usmapready",renderMap);
 }
 function start(){wire();load();switchView("overview");}
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start);
 else start();
})();
