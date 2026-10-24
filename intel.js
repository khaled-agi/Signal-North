"use strict";
/* Source-linked Canadian fraud intelligence. News headlines are research leads only. */
(() => {
 const $i = id => document.getElementById(id);
 const esc = value => String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
 const money = n => {
  if(n==null || !Number.isFinite(Number(n)))return "Not disclosed";
  let v=Number(n);
  return v>=1e9?"C$"+(v/1e9).toFixed(2)+"B":v>=1e6?"C$"+(v/1e6).toFixed(2).replace(/0+$/,"").replace(/\.$/,"")+"M":"C$"+v.toLocaleString("en-CA",{maximumFractionDigits:0});
 };
 const link = (url,text) => {
  try{
   const u=new URL(url);
   if(!["https:","http:"].includes(u.protocol))return "";
   return '<a target="_blank" rel="noopener noreferrer" href="'+esc(u.href)+'">'+esc(text)+" ↗</a>";
  }catch{return "";}
 };
 const catalog=[
  {name:"FINTRAC enforcement",value:"Live",source:"FINTRAC",url:"https://fintrac-canafe.canada.ca/pen/4-eng",note:"Public AML penalties and deficiencies; named legal entities"},
  {name:"FCAC decisions",value:"Live",source:"FCAC",url:"https://www.canada.ca/en/financial-consumer-agency/services/industry/commissioner-decisions.html",note:"Consumer protection violations and proceedings"},
  {name:"Canadian fraud reporting",value:"Curated",source:"CAFC / RCMP",url:"https://rcmp.ca/en/corporate-information/transparency-rcmp/enterprise-transparency/canadian-anti-fraud-centre-fraud-reporting",note:"Reported victim losses, fraud type, and eventual geographic trends"},
  {name:"CAFC open fraud dataset",value:"Planned",source:"RCMP Open Government",url:"https://open.canada.ca/data/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f",note:"Anonymized public reports with province, fraud category, number of victims, and reported losses; 2025 data currently partial"},
  {name:"Fraud victim disputes",value:"Research",source:"OBSI",url:"https://www.obsi.ca/en/news/posts/obsi-2025-annual-report-released/",note:"Complaints, fraud-related investigations, and outcomes; not proof of bank misconduct"},
  {name:"Investments / firm discipline",value:"Planned",source:"CIRO",url:"https://www.ciro.ca/rules-and-enforcement/enforcement",note:"Proceedings, orders, dealer discipline and investor protection"},
  {name:"Investment scams / warnings",value:"Planned",source:"CSA",url:"https://www.securities-administrators.ca/",note:"Securities warnings, enforcement and cross-province schemes"},
  {name:"Québec financial crime",value:"Planned",source:"AMF Québec",url:"https://lautorite.qc.ca/en/general-public",note:"Francophone alerts, insurer, broker and securities cases"},
  {name:"Investigations and charges",value:"Planned",source:"RCMP / OPP / local police",url:"https://rcmp.ca/en/news",note:"Victimization, organized crime, charges and seizures; legal-status tracking"},
  {name:"Fraud and banking news",value:"Headlines",source:"Syndicated news discovery",url:"https://news.google.com/",note:"Automated news leads. Requires verification before attributing wrongdoing or amounts"},
  {name:"RCMP local fraud news",value:"Automated",source:"RCMP RSS",url:"https://rcmp.ca/en/news/web-feeds",note:"Independent official police release metadata, filtered for financial crime; allegations and charges retain legal-status caveats"},
  {name:"GDELT Canadian fraud coverage",value:"Automated",source:"GDELT DOC",url:"https://www.gdeltproject.org/",note:"Canadian publisher articles discovered independently of Google News, including French media; observed date may differ from article publication"},
  {name:"Financial institution registry",value:"Planned",source:"OSFI",url:"https://www.osfi-bsif.gc.ca/en/data-forms/open-government-osfi-financial-data/working-open-government-data",note:"Licensing, correct legal entities, affiliates and institution metadata"},
  {name:"Payment-system risk",value:"Planned",source:"Bank of Canada / Payments Canada",url:"https://www.bankofcanada.ca/",note:"Payment-system incidents and operational risk; distinguish from fraud"},
  {name:"Cyber incidents",value:"Planned",source:"Privacy Commissioner / Cyber Centre",url:"https://www.priv.gc.ca/en/opc-actions-and-decisions/investigations/",note:"Incident disclosures and privacy findings; differentiate alleged from confirmed"}
 ];
 let news=[],stats=[],bankDisclosure=[],events=[],incidents=[],newsWired=false,incidentsWired=false,archiveCount=0,newsVisible=100,rawHeadlineCount=0;
 async function getJSON(path){
  const res=await fetch("./data/"+path+"?v="+Date.now(),{cache:"no-store"});
  if(!res.ok)throw Error(path+": HTTP "+res.status);
  return await res.json();
 }
 function national(){
  const all=stats.filter(x=>x.type==="victim_reported_fraud_losses"&&x.category==="All fraud reports");
  const types=stats.filter(x=>x.type==="victim_reported_fraud_losses"&&x.category!=="All fraud reports");
  const main=all.map(m=>'<div class="fraud-amount"><div class="eyebrow">'+esc(m.period)+'</div><div class="fraud-figure">'+money(m.amount_cad)+(m.approximate?'<span class="small"> approx.</span>':"")+'</div><div class="small">Victim-reported Canadian losses · '+link(m.source_url,m.source)+'</div></div>').join("");
  const rows=types.map(m=>'<div class="fraud-stat"><div><strong>'+esc(m.category)+'</strong><div class="small">'+esc(m.period)+'</div></div><strong>'+money(m.amount_cad)+'</strong>'+link(m.source_url,"Source")+'</div>').join("");
  const obsi=stats.find(x=>x.type==="banking_fraud_complaints");
  $i("fraudNational").innerHTML='<div class="fraud-highlights">'+main+'</div><div class="fraud-separator">REPORTED LOSSES BY FRAUD TYPOLOGY — NOT ADDITIVE TO NATIONAL TOTAL</div><div class="fraud-stat-grid">'+rows+'</div>'+(obsi?'<div class="notice" style="margin:14px 20px"><strong>Consumer dispute indicator:</strong> OBSI opened '+Number(obsi.count).toLocaleString()+" fraud-related banking investigations in "+esc(obsi.year)+". This is a complaint count, not a loss amount. "+link(obsi.source_url,"Original source")+"</div>":"");
  const latest=all.find(x=>x.year===2025)||all[0];
  const recent=news.slice(0,4).map(x=>'<div class="mini-lead"><span class="small">'+esc((x.published_at||"").slice(0,10))+'</span><div>'+link(x.url,x.title)+'</div></div>').join("");
  $i("overviewFraud").innerHTML='<div class="fraud-highlightline"><div><span class="small">Canada reported fraud losses · '+esc(latest?.period||"2025")+'</span><div class="fraud-figure">'+money(latest?.amount_cad)+'</div><span class="small">Nationwide victim reports, not institutional loss · '+(latest?link(latest.source_url,"CAFC source"):"")+'</span></div><div class="fraud-split"><div class="eyebrow">LATEST NEWS DISCOVERIES</div>'+ (recent||'<div class="small">No syndicated news leads collected yet. Regulator and CAFC data remain available.</div>')+'</div></div>';
 }
 function renderNews(){
  const q=$i("newsSearch").value.trim().toLowerCase();
  const t=$i("newsCategory").value;
  const year=$i("newsYear").value;
  const month=$i("newsMonth").value;
  const bank=$i("newsBank").value;
  const geo=$i("newsGeo").value;
  const hits=news.filter(x=>(!t||x.category===t)&&(!year||String(x.published_at||"").startsWith(year))&&(!month||String(x.published_at||"").slice(5,7)===month)&&(!bank||(x.banks_mentioned_in_headline||[]).includes(bank))&&(!geo||x.geographic_relevance===geo)&&(!q||[x.title,x.publisher,x.category,...(x.topics||[]),...(x.headline_variations||[]).map(v=>v.title)].join(" ").toLowerCase().includes(q)));
  const visible=hits.slice(0,newsVisible);
  $i("newsCount").textContent=hits.length+" reporting groups matching / "+news.length+" displayed groups";
  $i("newsPageCount").textContent="Showing "+visible.length+" of "+hits.length+" grouped reports from "+rawHeadlineCount.toLocaleString("en-CA")+" indexed headlines";
  $i("newsMore").hidden=visible.length>=hits.length;
  $i("newsAll").hidden=visible.length>=hits.length;
  $i("newsRows").innerHTML=hits.length?visible.map(x=>{
   const banks=x.banks_mentioned_in_headline||[];
   const geography=({canadian_location_or_reference:"Canadian geographic clue",canada_linked_international:"Canada-linked international",international_context_explicit:"International context",geography_unresolved:"Location unverified"})[x.geographic_relevance]||"Location unverified";
   const n=Math.max(1,Number(x.variation_count||1));
   const sources=Math.max(1,Number(x.source_count||x.number_of_article_links||1));
   const mapAction=Number.isFinite(x.map_latitude)&&Number.isFinite(x.map_longitude)?
     '<button class="news-mapaction" type="button" data-mapfocus="'+esc(x.id)+'">Locate mention on map →</button>':"";
   return '<article class="news-item news-group"><div class="news-group-content">'+
     '<div class="news-item-title"><button class="report-open" type="button" data-story="'+esc(x.id)+'">'+esc(x.title)+'</button></div>'+
     '<div class="news-meta">'+esc((x.published_at||"").slice(0,10))+' · '+esc(x.category||"Financial crime research")+' · '+esc(geography)+
       (banks.length?' · Named: '+esc(banks.join(", ")):"")+'</div>'+
     '<div class="news-rowtools"><button class="report-variations" type="button" data-story="'+esc(x.id)+'">'+
      (sources>1?sources+' original source links':"View original source")+
      (n>1?' · '+n+' headline variations':"")+' →</button>'+mapAction+'</div>'+
     '</div><span class="news-label">UNVERIFIED REPORTING</span></article>';
  }).join(""):'<div class="empty">No reporting groups match the filters. Clear the search or try a different year.</div>';
 }
 function openReportingDetail(x){
  if(!x)return;
  const variants=(x.headline_variations?.length?x.headline_variations:
    x.article_links?.length?x.article_links:
    [{title:x.title,url:x.url,publisher:x.publisher,published_at:x.published_at}]);
  const unique=[];
  const seen=new Set();
  for(const v of variants){
   const url=String(v.url||"");
   const key=url+"|"+String(v.title||x.title||"").trim().toLowerCase();
   if(!url.startsWith("https://")||seen.has(key))continue;
   seen.add(key);unique.push(v);
  }
  const meaningful=title=>new Set(String(title||"").toLowerCase()
    .replace(/[^a-z0-9 ]/g," ").split(/\s+/).filter(w=>w.length>3&&!new Set(["this","that","with","from","into","after","reported","reports","says","canada","fraud","scams"]).has(w)));
  const titleTokens=unique.map(v=>meaningful(v.title||x.title));
  const shared=titleTokens.length>1?[...titleTokens[0]].filter(w=>titleTokens.every(t=>t.has(w))):[];
  const heading='<div class="eyebrow">REPORTING GROUP / EDITORIAL COMPARISON</div>'+
    '<h2>'+esc(x.title)+'</h2>'+
    '<p class="report-detail-meta">'+esc((x.published_at||"").slice(0,10))+
    ' · '+esc(x.category||"Financial crime")+' · '+esc(x.geographic_relevance_basis||"Geography not independently verified")+
    ' · '+Math.max(1,x.underlying_headline_count||1)+' indexed headline'+((x.underlying_headline_count||1)===1?"":"s")+
    ' · '+unique.length+' original source link'+(unique.length===1?"":"s")+'</p>';
  const variations=unique.map((v,i)=>{
    const different=[...titleTokens[i]].filter(w=>!titleTokens.some((other,j)=>j!==i&&other.has(w))).slice(0,8);
    return '<article class="report-version"><div class="report-version-index">SOURCE '+(i+1)+' · '+esc(v.publisher||"Publisher")+
    ' · '+esc(String(v.published_at||x.published_at||"").slice(0,10))+'</div>'+
    '<h3>'+esc(v.title||x.title)+'</h3>'+
    (unique.length>1?'<p class="report-wording">Distinct words in this headline: '+esc(different.join(", ")||"No clearly distinct terms")+'</p>':"")+
    '<p>'+link(v.url,"Open original reporting")+'</p></article>';
  }).join("");
  const notice='<div class="warning">These publications have been grouped using closely matching headlines and dates. This is a discovery aid, not an independently verified single victim, incident, fraud loss, or finding against any institution. Compare the sources before using this reporting in research.</div>';
  $i("drawerBody").innerHTML=heading+notice+
     '<h3 class="report-versions-heading">Original reporting and headline variations</h3>'+
     '<p class="report-detail-meta">Compare the publication date and headline wording from each indexed source. This does not analyze the full article text.</p>'+
     (shared.length&&unique.length>1?'<p class="report-shared">Shared headline terms: '+esc(shared.slice(0,12).join(" · "))+'</p>':"")+
     '<div class="report-versions">'+(variations||'<p>No source links retained.</p>')+'</div>';
  $i("overlay").classList.remove("hidden");
  document.body.style.overflow="hidden";
 }
 window.addEventListener("signalnorth:openstory",e=>{
  const report=news.find(x=>String(x.id)===String(e.detail?.id));
  if(report)openReportingDetail(report);
 });
 function initNews(){
  const cats=[...new Set(news.map(x=>x.category).filter(Boolean))].sort();
  $i("newsCategory").innerHTML='<option value="">All fraud types</option>'+cats.map(x=>'<option value="'+esc(x)+'">'+esc(x)+"</option>").join("");
  const years=[...new Set(news.map(x=>String(x.published_at||"").slice(0,4)).filter(y=>/^[0-9]{4}$/.test(y)))].sort().reverse();
  const banks=[...new Set(news.flatMap(x=>x.banks_mentioned_in_headline||[]))].sort();
  const prevYear=$i("newsYear").value,prevBank=$i("newsBank").value,prevMonth=$i("newsMonth").value;
  $i("newsMonth").innerHTML='<option value="">All months</option>'+Array.from({length:12},(_,i)=>{const m=String(i+1).padStart(2,"0");return '<option value="'+m+'">'+new Intl.DateTimeFormat("en-CA",{month:"long",timeZone:"UTC"}).format(new Date(Date.UTC(2026,i,1)))+"</option>"}).join("");
  if(prevMonth)$i("newsMonth").value=prevMonth;
  $i("newsYear").innerHTML='<option value="">All years</option>'+years.map(y=>'<option value="'+esc(y)+'">'+esc(y)+'</option>').join("");
  $i("newsBank").innerHTML='<option value="">All named banks</option>'+banks.map(b=>'<option value="'+esc(b)+'">'+esc(b)+'</option>').join("");
  if(prevYear)$i("newsYear").value=prevYear;
  if(prevBank)$i("newsBank").value=prevBank;
  if(!newsWired){
   $i("newsCategory").addEventListener("change",()=>{newsVisible=100;renderNews()});
   $i("newsYear").addEventListener("change",()=>{newsVisible=100;renderNews()});
   $i("newsMonth").addEventListener("change",()=>{newsVisible=100;renderNews()});
   $i("newsBank").addEventListener("change",()=>{newsVisible=100;renderNews()});
   $i("newsGeo").addEventListener("change",()=>{newsVisible=100;renderNews()});
   $i("newsSearch").addEventListener("input",()=>{newsVisible=100;renderNews()});
   $i("newsMore").addEventListener("click",()=>{newsVisible+=100;renderNews()});
   $i("newsAll").addEventListener("click",()=>{newsVisible=Number.MAX_SAFE_INTEGER;renderNews()});
   newsWired=true;
  }
  renderNews();
 }
 function renderHomeHeadlines(updatedAt){
  const hits=news.slice(0,6);
  const last=updatedAt?new Date(updatedAt):null;
  const stamp=last&&!Number.isNaN(last.getTime())?new Intl.DateTimeFormat("en-CA",{month:"short",day:"numeric",hour:"numeric",minute:"2-digit",timeZone:"America/Toronto",timeZoneName:"short"}).format(last):"Not yet collected";
  const freshness="Google News RSS · "+news.length+" screened leads · Last scan: "+stamp;
  $i("newsFreshness").textContent=freshness;
  $i("newsFreshnessDetail").textContent=freshness+" · Scheduled every 30 minutes (best effort)";
  $i("headlinesTop").innerHTML=hits.length?hits.map(x=>
   '<div class="breaking-story"><div class="breaking-story-head"><span class="breaking-type">'+esc(x.category||"News lead")+'</span><span>'+esc((x.published_at||"").slice(0,10))+'</span></div><div class="breaking-story-title"><button type="button" class="report-open" data-story="'+esc(x.id)+'">'+esc(x.title)+'</button></div><div class="breaking-publisher">'+Math.max(1,Number(x.source_count||1))+' source link(s) · Grouped, unverified reporting</div></div>'
  ).join(""):'<div class="empty">No headlines in the latest snapshot. You can start a new scan from GitHub Actions.</div>';
 }
 function caseAmount(x){
   const a=x.amount_cad==null?"Unreported":money(x.amount_cad);
   const lbl=({"victim_reported_loss":"Victim-reported loss","unauthorized_credit_exposure":"Credit exposure","recovered_amount":"Funds recovered"})[x.amount_type]||"Reported amount";
   return {a,lbl};
 }
 function caseMarkup(x,featured=false){
   const {a,lbl}=caseAmount(x);
   const role=({"customer_financial_institution":"Customer bank","institution_impersonated":"Bank impersonated","bank_not_identified":"Bank unnamed","unnamed_financial_institution_assisted_recovery":"Bank helped recover funds"})[x.institution_role]||"Role unspecified";
   const text=featured?x.title:((x.summary||"")+" "+(x.consulting_theme||""));
   return '<article class="case-item'+(featured?' case-mini':'')+'"><div class="case-head"><span class="case-tag">'+esc(x.fraud_type)+'</span><span class="small">'+esc(x.reported_at||"Date not reported")+'</span></div><h3>'+esc(x.title)+'</h3><div class="case-amount">'+esc(a)+' <span class="small">'+esc(lbl)+'</span></div><div class="case-entity"><strong>'+esc(x.institution||"Bank not named")+'</strong> · '+esc(role)+'</div>'+(featured?'':'<p class="case-summary">'+esc(text)+'</p><div class="small">Reported incident period: '+esc(x.incident_period||"Unknown")+' · '+esc(x.location||"Canada")+'</div><div class="case-disclaimer">'+esc(x.disclaimer||"Media-reported case, not a legal finding.")+'</div>')+'<div class="case-source">'+link(x.source_url,x.source_name)+'</div></article>';
 }
 function renderIncidents(){
   const q=$i("incidentSearch").value.trim().toLowerCase();
   const prov=$i("incidentProvince").value;
   const bank=$i("incidentBank").value;
   const found=incidents.filter(x=>(!q||[x.title,x.institution,x.fraud_type,x.location,x.summary].join(" ").toLowerCase().includes(q))&&(!prov||x.province===prov)&&(!bank||(bank==="__unnamed__"?!x.institution:x.institution===bank)));
   $i("incidentCount").textContent=incidents.length+" source-reviewed cases";
   $i("incidentRows").innerHTML=found.length?found.map(x=>caseMarkup(x)).join(""):'<div class="empty">No incidents match this filter.</div>';
 }
 function initIncidents(){
   $i("featuredIncidents").innerHTML=incidents.length?incidents.slice(0,3).map(x=>caseMarkup(x,true)).join(""):'<div class="empty">Source-reviewed case entries are not yet available.</div>';
   $i("incidentProvince").innerHTML='<option value="">All provinces</option>'+[...new Set(incidents.map(x=>x.province).filter(Boolean))].sort().map(p=>'<option value="'+esc(p)+'">'+esc(p)+'</option>').join("");
   $i("incidentBank").innerHTML='<option value="">All banks / unnamed</option><option value="__unnamed__">Bank unnamed</option>'+[...new Set(incidents.map(x=>x.institution).filter(Boolean))].sort().map(name=>'<option value="'+esc(name)+'">'+esc(name)+'</option>').join("");
   if(!incidentsWired){
    ["incidentProvince","incidentBank"].forEach(id=>$i(id).addEventListener("change",renderIncidents));
    $i("incidentSearch").addEventListener("input",renderIncidents);
    incidentsWired=true;
   }
   renderIncidents();
 }
 function bankRows(){
  const years=[...new Set(events.map(x=>(x.published_at||"").slice(0,4)).filter(Boolean))].sort().reverse();
  const year=$i("lossYear");
  year.innerHTML=years.map(y=>'<option value="'+esc(y)+'">'+esc(y)+" publication year</option>").join("");
  year.addEventListener("change",renderAnnual);
  $i("lossEntityType").addEventListener("change",renderAnnual);
  renderAnnual();
  if(bankDisclosure.length){
   $i("disclosedLossRows").innerHTML=bankDisclosure.map(x=>'<p><strong>'+esc(x.institution)+' · '+esc(x.year)+': '+money(x.amount)+'</strong> '+esc(x.currency||"CAD")+' · '+esc(x.metric_type)+' · '+link(x.source_url,"Verified disclosure")+'</p>').join("");
  }else{
   $i("disclosedLossRows").innerHTML='<p><strong>No verified institution-owned annual fraud losses have been indexed yet.</strong> Individual banks may describe fraud risk without publicly quantifying comparable yearly fraud losses. We will not fill missing numbers with national victim losses, provisions for credit losses, penalties, or values laundered through accounts.</p><p>To add a bank annual loss figure, the source must identify the legal entity, year, currency, loss type, and whether the bank or its customers bore the loss. Where nothing is disclosed, the value remains <strong>not publicly verified</strong>.</p>';
  }
 }
 function renderAnnual(){
  const y=$i("lossYear").value;
  const isFinancial = x => /\b(bank|banque|credit union|credit unions|caisse populaire|caisse financière|financial cooperative)\b/i.test((x.institution||"")+" "+(x.summary||"").slice(0,220));
  const rows=events.filter(x=>(x.published_at||"").slice(0,4)===y && x.penalty_cad!=null && ($i("lossEntityType").value==="all"||isFinancial(x)));
  const groups=new Map();
  for(const x of rows){
    const key=x.institution||"Unknown institution";
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(x);
  }
  const sorted=[...groups].map(([name,ev])=>({name,ev,total:ev.reduce((t,z)=>t+Number(z.penalty_cad||0),0)})).sort((a,b)=>b.total-a.total);
  const value=sorted.reduce((sum,x)=>sum+x.total,0);
  $i("institutionLossRows").innerHTML='<div class="annual-head"><div><div class="small">PUBLISHED ENFORCEMENT PENALTIES · '+esc(y)+'</div><strong>'+money(value)+'</strong></div><div class="small">'+rows.length+' notices · '+sorted.length+' named entities · CAD only</div></div>'+(sorted.length?'<div class="annual-table">'+sorted.slice(0,100).map(x=>'<div class="annual-line"><div><strong>'+esc(x.name)+'</strong><div class="small">'+esc(x.ev.map(z=>z.source).join(", "))+' · '+x.ev.length+' notice(s)</div></div><strong>'+money(x.total)+'</strong>'+link(x.ev[0].source_url,"Primary notice")+'</div>').join("")+'</div>':'<div class="empty">No published penalty amounts for this year in the monitored sources.</div>')+'<div class="small" style="padding:16px 20px">Figures are regulatory penalties issued to named entities, not fraud losses, customer victimization, or alleged criminal proceeds. Publication year can differ from imposition year.</div>';
 }
 function renderCatalog(){
  $i("sourceCatalog").innerHTML=catalog.map(x=>'<div class="source-line"><div><strong>'+esc(x.name)+'</strong><p class="small">'+esc(x.note)+'</p></div><div class="source-end"><span class="source-tag">'+esc(x.value)+'</span>'+link(x.url,x.source)+'</div></div>').join("");
 }
 async function boot(){
  renderCatalog();
  const names=["fraud_stats.json","news.json","bank_disclosures.json","events.json","news_status.json","incidents.json","news_archive.json","article_index.json","external_source_status.json","reporting_groups.json"];
  const fetched=await Promise.allSettled(names.map(getJSON));
  if(fetched[0].status==="fulfilled")stats=fetched[0].value.metrics||[];
  else $i("fraudNational").innerHTML='<div class="error">Fraud statistics unavailable: '+esc(String(fetched[0].reason))+'</div>';
  const recent=fetched[1].status==="fulfilled"?(fetched[1].value.leads||[]):[];
  const history=fetched[6].status==="fulfilled"?(fetched[6].value.leads||[]):[];
  archiveCount=history.length;
  const indexed=fetched[7].status==="fulfilled"?(fetched[7].value.articles||[]):[];
  const grouped=fetched[9].status==="fulfilled"?(fetched[9].value.groups||[]):[];
  rawHeadlineCount=indexed.length||(fetched[9].status==="fulfilled"?Number(fetched[9].value.original_index_headlines||0):0);
  news=grouped.length?grouped:indexed.length?indexed:
    [...new Map([...recent,...history].map(x=>[x.id,x])).values()].sort((a,b)=>String(b.published_at||"").localeCompare(String(a.published_at||"")));
  if(!rawHeadlineCount)rawHeadlineCount=news.length;
  $i("archiveCount").textContent=archiveCount?
    rawHeadlineCount.toLocaleString()+" indexed headlines consolidated into "+news.length.toLocaleString()+" reporting groups · "+archiveCount.toLocaleString()+" historic discoveries":
    rawHeadlineCount.toLocaleString()+" indexed headlines · "+news.length.toLocaleString()+" reporting groups";
  const newsStatus=fetched[4].status==="fulfilled"?fetched[4].value:{};
  const otherHealth=fetched[8].status==="fulfilled"?fetched[8].value:{};
  const collectors=Object.entries(otherHealth.collectors||{});
  $i("externalSourceHealth").innerHTML=collectors.length?
      '<div class="source-line"><strong>Independent news discovery</strong><span class="small">Last scan: '+esc((otherHealth.completed_at||"").slice(0,19))+' UTC</span></div>'+
      collectors.map(([name,info])=>'<div class="source-line"><div><strong>'+esc(name)+'</strong><p class="small">'+esc(info.status||"unknown")+' · '+Number(info.accepted||0)+' candidate records from '+Number(info.scanned||0)+' scanned articles</p></div></div>').join("")
      :'<div class="source-line"><span class="small">RCMP / GDELT source-health data will appear after the next successful collection.</span></div>';
  const lastUpdated=newsStatus.last_completed_at||(fetched[1].status==="fulfilled"?fetched[1].value.updated_at:null);
  renderHomeHeadlines(lastUpdated);
  window.dispatchEvent(new CustomEvent("signalnorth:newsready",{detail:{leads:news,rawHeadlineCount}}));
  if(fetched[2].status==="fulfilled")bankDisclosure=fetched[2].value.records||[];
  if(fetched[3].status==="fulfilled")events=fetched[3].value.events||[];
  if(fetched[5].status==="fulfilled")incidents=fetched[5].value.incidents||[];
  initIncidents();
  window.dispatchEvent(new CustomEvent("signalnorth:incidentsready",{detail:{incidents}}));
  if(stats.length)national();
  else $i("overviewFraud").innerHTML='<div class="empty">National loss metrics are not available.</div>';
  initNews();
  bankRows();
 }
 window.addEventListener("signalnorth:refresh",boot);
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
 else boot();
})();
