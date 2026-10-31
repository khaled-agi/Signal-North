"use strict";
/* International data is intentionally separate from Canadian verified events. */
(() => {
 const get=id=>document.getElementById(id);
 const html=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const THEMES={
  "AML / transaction monitoring":/(aml|bsa|anti.money laundering|transaction monitoring|money laundering|kyc|due diligence)/i,
  "Sanctions controls":/(sanctions|ofac|export control)/i,
  "Crypto / money services":/(crypto|virtual currency|binance|exchange|money services)/i,
  "Casino / gambling":/(casino|gambling|gaming|betting|lottery)/i,
  "Investor / consumer protection":/(investor|consumer|client.asset|securities|conduct|financial crime controls)/i,
 };
 const model={events:[],countries:[],health:{},canadianEvents:[],worldNews:[],worldNewsStatus:{},regLeads:[],regStatus:{},coverageExamples:[],directLeads:[],directStatus:{},directCatalog:[],directVisible:30,localCandidates:[],localVisible:50,newsVisible:50,regVisible:50};
 function renderPatterns(){
  const host=get("globalPatterns");
  const themes=Object.entries(THEMES).map(([name,rx])=>{
   const matches=model.events.filter(x=>rx.test((x.category||"")+" "+(x.title||"")+" "+(x.institution||"")));
   const countries=[...new Set(matches.map(x=>x.country_code))].length;
   return {name,matches:matches.length,countries};
  });
  host.innerHTML=themes.map(t=>'<button type="button" data-global-pattern="'+html(t.name)+'"><strong>'+html(t.name)+'</strong>'+
    '<span>'+t.matches.toLocaleString("en-CA")+' source records · '+t.countries+' jurisdictions</span></button>').join("");
  get("globalPatternStatus").textContent=model.events.length+" international actions · "+themes.length+" research themes";
 }
 function renderCountryBrief(){
  const code=get("mapCountry")?.value||"";
  const host=get("worldCountryBrief");
  if(!host)return;
  if(!code){
   host.innerHTML='<strong>Worldwide intelligence:</strong> official agency actions and unverified country-market news searches are separate layers. The map never asserts the location of an alleged offence based on search-market metadata. <a href="https://www.fatf-gafi.org/en/countries.html" target="_blank" rel="noopener noreferrer">FATF jurisdictions ↗</a>';
   return;
  }
  const country=model.countries.find(c=>c.code===code);
  if(!country){host.textContent="Country source status unavailable.";return;}
  const found=model.events.filter(e=>e.country_code===code);
  const news=model.worldNews.filter(e=>e.country_code===code);
  const officialLeads=model.regLeads.filter(e=>e.country_code===code);
  const cs=model.worldNewsStatus.countries?.[code]||{};
  const officialCount=found.length+(code==="CA"?model.canadianEvents.length:0);
  const state=cs.state||"not_attempted";
  const status={
   not_attempted:"Not yet scanned for local reporting",
   attempted_empty:"Scanned; no qualifying recent headlines accepted",
   reporting_found:"Recent headlines discovered (unverified)",
   partial_error:"Partial coverage; some searches failed",
   error:"Latest search attempt failed"
  }[state]||"Country discovery status unavailable";
  const checked=cs.attempted_at?String(cs.attempted_at).slice(0,16).replace("T"," ")+" UTC":"No completed scan yet";
  const authorities=(country.agency_directory||[]).slice(0,4).map(x=>
   '<a href="'+html(x.url)+'" target="_blank" rel="noopener noreferrer">'+html(x.name)+' ↗</a>').join(' · ');
  host.innerHTML='<div class="country-intelligence"><div><strong>'+html(country.name)+'</strong>'+
    '<span class="country-intelligence-status">'+html(status)+' · Last attempted: '+html(checked)+'</span></div>'+
    '<div class="country-intelligence-grid"><span><b>'+officialCount+'</b> official actions collected</span>'+
    '<span><b>'+news.length+'</b> unverified country-search headlines · '+officialLeads.length+' agency-site publication leads</span>'+
    '<span><b>'+html(country.local_language||"English fallback")+'</b> discovery language hint</span></div>'+
    (authorities?'<div class="country-intelligence-authorities"><b>Agency directory (not automatically monitored):</b> '+authorities+'</div>':
      '<div class="country-intelligence-authorities">No country-specific agency directory verified yet. <a href="https://www.fatf-gafi.org/en/countries.html" target="_blank" rel="noopener noreferrer">Browse FATF country information ↗</a></div>')+
    '<p>News is indexed by search market only, not where an incident occurred. No collection result means no coverage conclusion; only official-source actions are verified as regulator publications.</p></div>';

 }
 const KNOWN_THREADS=[
  {key:"td",name:"TD banking group · Canada / United States",
   ca:/\btoronto.dominion bank\b/i,
   global:/\btd bank\b|\btoronto.dominion\b/i,
   description:"The US enforcement notice concerns TD's US subsidiaries; the Canadian parent and US operating banks are separate legal entities. These are not one enforcement proceeding.",
   search:"td bank|toronto.dominion"},
  {key:"binance",name:"Binance Holdings Limited · Canada / United States",
   ca:/\bbinance holdings limited\b/i,
   global:/\bbinance\b/i,
   description:"The same named organization appears in distinct FINTRAC and FinCEN regulatory matters. Record overlap does not establish common factual allegations.",
   search:"binance"},
 ];
 function renderThreads(){
  const host=get("globalOrgThreads");if(!host)return;
  const cards=[];
  for(const thread of KNOWN_THREADS){
   const ca=model.canadianEvents.filter(x=>thread.ca.test(x.institution||""));
   const abroad=model.events.filter(x=>thread.global.test(x.institution||""));
   if(!ca.length||!abroad.length)continue;
   const sample=[...ca.map(x=>({agency:x.source,uri:x.source_url,date:x.published_at,country:"Canada"})),
     ...abroad.map(x=>({agency:x.regulator,uri:x.source_url,date:x.published_at,country:x.country}))];
   const links=sample.filter(x=>/^https:\/\//.test(x.uri||"")).slice(0,7).map(x=>
     '<a href="'+html(x.uri)+'" target="_blank" rel="noopener noreferrer">'+html(x.agency+" · "+x.country+" · "+String(x.date||"").slice(0,10))+' ↗</a>').join("");
   cards.push('<article class="crossborder-thread"><h3>'+html(thread.name)+'</h3>'+
    '<div class="thread-counts"><span>'+ca.length+' Canadian regulatory notices</span><span>'+abroad.length+' international agency actions</span></div>'+
    '<p>'+html(thread.description)+'</p><div class="thread-sources">'+links+'</div>'+
    '<button type="button" data-global-entity="'+html(thread.key)+'">View the linked agency records on the map →</button></article>');
  }
  host.innerHTML=cards.join("")||'<div class="empty">No corroborated cross-jurisdiction institution links in the currently collected records.</div>';
 }


 function goodUrl(url){
  try{const x=new URL(url);return x.protocol==="https:"&&!x.username&&!x.password?x.href:"";}catch{return "";}
 }
 function bindSelect(id,values,allLabel){
  const el=get(id),prior=el.value;
  el.innerHTML='<option value="">'+html(allLabel)+'</option>'+values.map(x=>
   '<option value="'+html(x)+'">'+html(x)+'</option>').join("");
  if(values.includes(prior))el.value=prior;
 }

 // Geographic regions select *which country-mentioned records* to display;
 // these lists are not proof of event location or publisher nationality.
 const REGION_MARKETS={
  "africa":"DZ AO BJ BW BF BI CM CV CF TD KM CG CD CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY MG MW ML MR MU YT MA MZ NA NE NG RE RW ST SN SC SL SO ZA SS SH SD TZ TG TN UG EH ZM ZW",
  "southeast-asia":"BN KH ID LA MY MM PH SG TH TL VN",
  "south-asia":"AF BD BT IN MV NP PK LK",
  "east-asia":"CN HK JP KP KR MO MN TW"
 };
 const IN_REGIONS=Object.fromEntries(Object.entries(REGION_MARKETS).map(([k,v])=>[k,new Set(v.split(" "))]));
 function matchesRegion(code){
  const region=get("worldNewsRegion")?.value||"";
  return !region||Boolean(IN_REGIONS[region]?.has(code));
 }

 function renderWorldReporting(){
  const code=get("worldNewsCountry")?.value||"";
  const topic=get("worldNewsCategory")?.value||"";
  const q=(get("worldNewsQuery")?.value||"").trim().toLocaleLowerCase();
  const matches=model.worldNews.filter(x=>(!code||x.country_code===code) && matchesRegion(x.country_code) &&
    (!topic||x.category===topic) &&
    (!q||[x.title,x.country,x.publisher,x.category].some(v=>String(v||"").toLocaleLowerCase().includes(q))))
    .slice().sort((a,b)=>String(b.published_at||"").localeCompare(String(a.published_at||"")));
  const scan=model.worldNewsStatus.countries?.[code];
  const last=model.worldNewsStatus.last_completed_at;
  get("worldReportingSummary").textContent=
    model.worldNews.length+" country-referenced articles · "+(model.worldNewsStatus.markets_attempted||0)+
    " markets scanned · Last refresh "+String(last||"not yet").slice(0,10);
  get("worldReportingHealth").textContent=code?
    (model.countries.find(x=>x.code===code)?.name||code)+" · "+(scan?.state||"not attempted")+
      " · Last scan "+String(scan?.attempted_at||"never").slice(0,16):
    (model.worldNewsStatus.markets_attempted||0)+" / "+model.countries.length+
      " markets attempted · "+model.worldNews.length+" country-referenced unverified articles · "+(get("worldNewsRegion")?.selectedOptions?.[0]?.textContent||"All regions");
  const visible=matches.slice(0,model.newsVisible);
  get("worldReportingRows").innerHTML=visible.length?visible.map(x=>{
   const url=goodUrl(x.url);
   return '<article class="world-reporting-record"><div class="world-reporting-date">'+
    html(x.country)+" · "+html(String(x.published_at||"").slice(0,10))+" · "+
    html(x.publisher||"Unknown publisher")+'</div><strong>'+html(x.title)+'</strong>'+
    '<div class="world-reporting-details">'+html(x.category||"News lead")+
    ' · Country explicitly referenced in headline · Unverified; NOT confirmed incident location'+
    (url?' · <a href="'+html(url)+'" target="_blank" rel="noopener noreferrer">Open linked article ↗</a>':"")+
    '</div></article>';
  }).join(""):'<div class="empty">No matching reported headlines stored. This does not mean there were no fraud incidents; see the country scan status.</div>';
  get("worldNewsShown").textContent=visible.length+" of "+matches.length+" matching reports shown";
  get("worldNewsMore").hidden=visible.length>=matches.length;
  get("worldNewsAll").hidden=visible.length>=matches.length;
 }



 function renderDirectFeeds(){
  const health=get("directFeedsHealth");if(!health)return;
  const states=model.directStatus.sources||{};
  const all=model.directCatalog;
  get("directFeedsSummary").textContent=(model.directStatus.sources_attempted||0)+
    "/"+all.length+" feeds attempted · "+model.directLeads.length+" topic-matched publications";
  health.innerHTML=all.map(x=>{
   const h=states[x.id]||{};
   const checked=h.checked_at?String(h.checked_at).slice(0,16):"Not scanned";
   return '<div class="world-coverage-audit-row"><strong>'+html(x.name)+
    '</strong><span>'+html(x.country_code)+' · '+html(x.kind)+
    ' · '+html(h.status||"unattempted")+'</span><small>Last checked: '+
    html(checked)+' · '+(h.accepted||0)+' qualifying headlines</small></div>';
  }).join("")||'<p class="supporting-disclaimer">No original-domain sources configured yet.</p>';
  const market=get("worldNewsCountry")?.value||"";
  const q=(get("worldNewsQuery")?.value||"").toLowerCase().trim();
  const matches=model.directLeads.filter(x=>(!market||x.country_code===market)&&
    matchesRegion(x.country_code)&&(!q||[x.title,x.source_name].some(y=>String(y||"").toLowerCase().includes(q))))
    .slice().sort((a,b)=>String(b.published_at||"").localeCompare(String(a.published_at||"")));
  const list=matches.slice(0,model.directVisible);
  get("directFeedRows").innerHTML=list.length?list.map(x=>{
   const url=goodUrl(x.url);
   return '<article class="world-reporting-record"><div class="world-reporting-date">'+
    html(x.source_name)+' · '+html(x.source_kind)+' · '+html(String(x.published_at).slice(0,10))+
    '</div><strong>'+html(x.title)+'</strong><div class="world-reporting-details">'+
    'Original publisher domain · Unreviewed publication · NOT incident geography or confirmed enforcement'+
    (url?' · <a href="'+html(url)+'" target="_blank" rel="noopener noreferrer">Original publication ↗</a>':"")+
    '</div></article>';
  }).join(""):'<div class="empty">No direct-source topic-matched articles have been collected in this selection. This does not establish an absence of news or enforcement.</div>';
  get("directFeedsShown").textContent=list.length+" of "+matches.length+" direct-source records shown";
  get("directFeedsMore").hidden=list.length>=matches.length;
 }

 function renderCoverageAudit(){
  const root=get("worldCoverageAuditRows");if(!root)return;
  const statuses=model.worldNewsStatus.countries||{};
  const countries=model.countries.filter(c=>matchesRegion(c.code));
  const empty=countries.filter(c=>statuses[c.code]?.state==="attempted_empty");
  const unscanned=countries.filter(c=>!statuses[c.code]?.attempted_at);
  const errors=countries.filter(c=>["partial_error","error"].includes(statuses[c.code]?.state));
  const unresolved=[
   ...unscanned.map(c=>({c,sort:0,state:"Not yet scanned"})),
   ...errors.map(c=>({c,sort:1,state:"Collection failed / partial"})),
   ...empty.map(c=>({c,sort:2,state:"Scanned; no accepted headlines"}))
  ].sort((a,b)=>a.sort-b.sort||a.c.name.localeCompare(b.c.name));
  get("worldCoverageAuditSummary").textContent=
    unscanned.length+" not scanned · "+empty.length+" empty last scan · "+errors.length+" errors";
  root.innerHTML=unresolved.length?unresolved.map(({c,state})=>{
   const health=statuses[c.code]||{};
   return '<div class="world-coverage-audit-row"><strong>'+html(c.name)+
    ' <small>'+html(c.code)+'</small></strong><span>'+html(state)+'</span>'+
    '<small>Last checked: '+html(String(health.attempted_at||"Never").slice(0,16))+
    ' · '+(health.queries_attempted||0)+' queries'+
    (health.recovery_queries_attempted?' · '+health.recovery_queries_attempted+' recovery queries':'')+
    '</small></div>';
  }).join(""):'<p class="supporting-disclaimer">Every market shown has a scan with accepted news. That is not proof of full news coverage.</p>';
  const examples=model.coverageExamples.filter(x=>matchesRegion(x.country_code));
  get("worldCoverageExamples").innerHTML=examples.map(x=>{
   const source=goodUrl(x.url);
   return '<article class="world-coverage-example"><span>'+html(x.country)+
    ' · '+html(x.published_at)+' · '+html(x.source)+'</span>'+
    '<strong>'+html(x.title)+'</strong><small>'+html(x.notes||"")+'</small>'+
    (source?'<a href="'+html(source)+'" target="_blank" rel="noopener noreferrer">Inspect published source ↗</a>':"")+
    '</article>';
  }).join("")||'<p class="supporting-disclaimer">No independently checked examples in this region yet; that is not proof of no fraud reporting.</p>';
 }

 function renderLocalLanguageCandidates(){
  const target=get("localLanguageRows");if(!target)return;
  const market=get("worldNewsCountry")?.value||"";
  const q=(get("worldNewsQuery")?.value||"").toLocaleLowerCase().trim();
  const topic=get("worldNewsCategory")?.value||"";
  const matches=model.localCandidates.filter(x=>
    (!market||x.search_market_code===market)&&matchesRegion(x.search_market_code)&&(!topic||x.category===topic)&&
    (!q||[x.title,x.publisher,x.search_market_name].some(v=>String(v||"").toLocaleLowerCase().includes(q)))
  ).slice().sort((a,b)=>String(b.published_at||"").localeCompare(String(a.published_at||"")));
  const visible=matches.slice(0,model.localVisible);
  target.innerHTML=visible.length?visible.map(x=>{
   const source=goodUrl(x.url);
   return '<article class="world-reporting-record">'+
    '<div class="world-reporting-date">'+html(String(x.published_at||"").slice(0,10))+
    ' · '+html(x.publisher||"Publisher unknown")+
    ' · Query language: '+html(x.query_language||"not established")+'</div>'+
    '<strong>'+html(x.title)+'</strong>'+
    '<div class="world-reporting-details">Local-language search targeted '+
    html(x.search_market_name||"an unconfirmed market")+
    ' · Country and article origin NOT established · No map pin'+
    (source?' · <a href="'+html(source)+'" target="_blank" rel="noopener noreferrer">Open linked article ↗</a>':"")+
    '</div></article>';
  }).join(""):'<div class="empty">No additional original-language candidates stored in this selection. Only matches explicitly supported by their headlines appear in the country-referenced feed above.</div>';
  get("localLanguageSummary").textContent=model.localCandidates.length+" unlocated source leads";
  get("localLanguageShown").textContent=visible.length+" of "+matches.length+" candidate reports shown";
  get("localLanguageMore").hidden=visible.length>=matches.length;
 }

 function renderRegulatorPublications(){
  const country=get("worldRegCountry")?.value||"";
  const agency=get("worldRegAgency")?.value||"";
  const q=(get("worldRegQuery")?.value||"").trim().toLocaleLowerCase();
  const filtered=model.regLeads.filter(x=>(!country||x.country_code===country)&&
    (!agency||x.regulator===agency)&&
    (!q||[x.title,x.regulator,x.country].some(y=>String(y||"").toLocaleLowerCase().includes(q))))
    .slice().sort((a,b)=>String(b.first_observed_at||"").localeCompare(String(a.first_observed_at||"")));
  const shown=filtered.slice(0,model.regVisible);
  const stats=model.regStatus;
  get("worldRegulatorHealth").textContent=(stats.regulators_attempted||0)+" of "+(stats.regulators_configured||0)+
    " targeted agencies scanned · "+model.regLeads.length+" official-site leads";
  get("worldRegRows").innerHTML=shown.length?shown.map(x=>{
   const url=goodUrl(x.source_url);
   return '<article class="world-reporting-record">'+
    '<div class="world-reporting-date">'+html(x.country)+' · '+html(x.regulator)+
    ' · Indexed '+html(String(x.first_observed_at||"").slice(0,10))+'</div>'+
    '<strong>'+html(x.title)+'</strong>'+
    '<div class="world-reporting-details">Regulator website · Publication lead, decision status not reviewed'+
     (url?' · <a href="'+html(url)+'" target="_blank" rel="noopener noreferrer">Official original URL ↗</a>':"")+
    '</div></article>';
  }).join(""):'<div class="empty">No matching original-domain regulator publications collected yet. This is not evidence of no enforcement. Official index records remain visible separately.</div>';
  get("worldRegShown").textContent=shown.length+" of "+filtered.length+" matching original-domain publications shown";
  get("worldRegMore").hidden=shown.length>=filtered.length;
  get("worldRegAll").hidden=shown.length>=filtered.length;
 }

 function renderCoverage(){
  const active=model.countries.filter(x=>x.coverage==="active");
  const countries=model.countries.length;
  const count=model.events.length;
  const attempts=Object.values(model.worldNewsStatus.countries||{}).filter(x=>x.attempted_at).length;
  const activeNews=new Set(model.worldNews.map(x=>x.country_code)).size;
  get("worldCoverage").innerHTML='<strong>'+countries.toLocaleString("en-CA")+' country and territory lenses</strong>'+
   '<span>'+attempts+' scanned for country-specific reporting · '+activeNews+' with recent unverified news · '+
   active.length+' jurisdictions with official enforcement records including Canada · '+count+' non-Canadian official actions</span>';
 }
 async function load(){
  const paths=["world_jurisdictions.json","global_enforcement.json","global_source_status.json","events.json","world_reporting.json","world_reporting_status.json","global_regulator_publications.json","global_regulator_publications_status.json","world_local_unattributed.json","world_coverage_counterexamples.json","direct_country_sources.json","direct_country_source_status.json","direct_country_source_catalog.json"];
  const results=await Promise.allSettled(paths.map(async x=>{
    const r=await fetch("./data/"+x+"?ts="+Date.now(),{cache:"no-store"});
    if(!r.ok)throw Error(x+": "+r.status);
    return r.json();
  }));
  if(results[0].status==="fulfilled")model.countries=results[0].value.jurisdictions||[];
  if(results[1].status==="fulfilled")model.events=results[1].value.events||[];
  if(results[2].status==="fulfilled")model.health=results[2].value||{};
  if(results[3].status==="fulfilled")model.canadianEvents=results[3].value.events||[];
  if(results[4].status==="fulfilled"){
    const raw=results[4].value.leads||[];
    // Historical RSS market labels weren't evidence of geography.
    // Unlinked Orlando/Alberta/Israel headlines cannot be shown as Jordan news.
    model.worldNews=raw.filter(e=>{
      const country=model.countries.find(c=>c.code===e.country_code);
      return Boolean(window.SignalNorthGeo?.evaluate?.(e,country)?.referenced);
    });
  }
  if(results[5].status==="fulfilled")model.worldNewsStatus=results[5].value||{};
  if(results[6].status==="fulfilled")model.regLeads=results[6].value.leads||[];
  if(results[7].status==="fulfilled")model.regStatus=results[7].value||{};
  if(results[8].status==="fulfilled")model.localCandidates=(results[8].value.leads||[])
    .filter(x=>x.country_code===null && x.evidence_status==="unattributed_local_language_search_candidate");
  if(results[9].status==="fulfilled")model.coverageExamples=results[9].value.examples||[];
  if(results[10].status==="fulfilled")model.directLeads=results[10].value.leads||[];
  if(results[11].status==="fulfilled")model.directStatus=results[11].value||{};
  if(results[12].status==="fulfilled")model.directCatalog=results[12].value.sources||[];
  const country=get("mapCountry"),current=country.value;
  const referencedMarkets=new Set(model.worldNews.map(x=>x.country_code));
  country.innerHTML='<option value="">All countries (worldwide)</option>'+model.countries.map(c=>
    '<option value="'+html(c.code)+'">'+html(c.name)+(c.coverage==="active"?" · official actions":(c.world_reporting_count?" · recent news":(c.world_reporting_state&&c.world_reporting_state!=="not_attempted"?" · scanned":" · pending scan")))+'</option>').join("");
  if(model.countries.some(c=>c.code===current))country.value=current;
  const regulator=get("mapAgency"),prev=regulator.value;
  const agencies=[...new Set(["FINTRAC","FCAC",...model.events.map(x=>x.regulator).filter(Boolean)])].sort();
  regulator.innerHTML='<option value="">All agencies</option>'+agencies.map(x=>'<option value="'+html(x)+'">'+html(x)+'</option>').join("");
  if(agencies.includes(prev))regulator.value=prev;
  bindSelect("worldNewsCountry",model.countries.map(c=>c.code),"All countries");
  // Country labels in the dropdown remain available through the primary map picker.
  for(const opt of get("worldNewsCountry").options){
   const c=model.countries.find(x=>x.code===opt.value);
   if(c)opt.textContent=c.name;
  }
  bindSelect("worldNewsCategory",[...new Set(model.worldNews.map(x=>x.category).filter(Boolean))].sort(),"All topics");
  bindSelect("worldRegCountry",[...new Set(model.regLeads.map(x=>x.country_code))].sort(),"All countries");
  for(const opt of get("worldRegCountry").options){
   const c=model.countries.find(x=>x.code===opt.value);
   if(c)opt.textContent=c.name;
  }
  bindSelect("worldRegAgency",[...new Set(model.regLeads.map(x=>x.regulator).filter(Boolean))].sort(),"All agencies");
  renderWorldReporting();
  renderCoverageAudit();
  renderDirectFeeds();
  renderLocalLanguageCandidates();
  renderRegulatorPublications();
  renderCoverage();renderPatterns();renderCountryBrief();renderThreads();
  window.dispatchEvent(new CustomEvent("signalnorth:globalready",{detail:{events:model.events,countries:model.countries,health:model.health,worldNews:model.worldNews,worldNewsStatus:model.worldNewsStatus,regLeads:model.regLeads,regStatus:model.regStatus}}));
 }
 get("mapCountry").addEventListener("change",renderCountryBrief);
 get("worldNewsRegion")?.addEventListener("change",()=>{
  if(get("worldNewsCountry"))get("worldNewsCountry").value="";
  model.newsVisible=50;model.localVisible=50;
  renderWorldReporting();renderCoverageAudit();renderDirectFeeds();renderLocalLanguageCandidates();
 });
 get("worldNewsCountry")?.addEventListener("change",()=>{
  if(get("worldNewsRegion"))get("worldNewsRegion").value="";
  model.newsVisible=50;model.localVisible=50;
  renderWorldReporting();renderCoverageAudit();renderDirectFeeds();renderLocalLanguageCandidates();
 });
 get("worldNewsCategory")?.addEventListener("change",()=>{model.newsVisible=50;model.localVisible=50;renderWorldReporting();renderLocalLanguageCandidates();});
 get("worldNewsQuery")?.addEventListener("input",()=>{model.newsVisible=50;model.localVisible=50;renderWorldReporting();renderLocalLanguageCandidates();});
 get("worldNewsMore")?.addEventListener("click",()=>{model.newsVisible+=50;renderWorldReporting();});
 get("worldNewsAll")?.addEventListener("click",()=>{model.newsVisible=Number.MAX_SAFE_INTEGER;renderWorldReporting();});
 get("localLanguageMore")?.addEventListener("click",()=>{model.localVisible+=50;renderLocalLanguageCandidates();});
 get("directFeedsMore")?.addEventListener("click",()=>{model.directVisible+=30;renderDirectFeeds();});
 for(const id of ["worldRegCountry","worldRegAgency","worldRegQuery"]){
  get(id)?.addEventListener(id==="worldRegQuery"?"input":"change",()=>{model.regVisible=50;renderRegulatorPublications();});
 }
 get("worldRegMore")?.addEventListener("click",()=>{model.regVisible+=50;renderRegulatorPublications();});
 get("worldRegAll")?.addEventListener("click",()=>{model.regVisible=Number.MAX_SAFE_INTEGER;renderRegulatorPublications();});
 get("mapReset").addEventListener("click",renderCountryBrief);
 get("worldView").addEventListener("click",renderCountryBrief);
 document.addEventListener("click",e=>{
  const entity=e.target.closest("[data-global-entity]");
  if(entity){
   const spec=KNOWN_THREADS.find(x=>x.key===entity.dataset.globalEntity);
   if(!spec)return;
   window.dispatchEvent(new CustomEvent("signalnorth:globalentity",{detail:{name:spec.name,pattern:spec.search}}));
   return;
  }
  const button=e.target.closest("[data-global-pattern]");
  if(!button)return;
  const name=button.dataset.globalPattern;
  const rx=THEMES[name];
  if(!rx)return;
  window.dispatchEvent(new CustomEvent("signalnorth:globalpattern",{detail:{name,pattern:rx.source}}));
  renderCountryBrief();
  document.querySelectorAll("[data-global-pattern]").forEach(b=>b.classList.toggle("active",b===button));
 });
 window.addEventListener("signalnorth:refresh",load);
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",load);
 else load();
})();
