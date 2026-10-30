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
 const model={events:[],countries:[],health:{},canadianEvents:[],worldNews:[],worldNewsStatus:{}};
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
    '<span><b>'+news.length+'</b> recent unverified country-search headlines</span>'+
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
  const paths=["world_jurisdictions.json","global_enforcement.json","global_source_status.json","events.json","world_reporting.json","world_reporting_status.json"];
  const results=await Promise.allSettled(paths.map(async x=>{
    const r=await fetch("./data/"+x+"?ts="+Date.now(),{cache:"no-store"});
    if(!r.ok)throw Error(x+": "+r.status);
    return r.json();
  }));
  if(results[0].status==="fulfilled")model.countries=results[0].value.jurisdictions||[];
  if(results[1].status==="fulfilled")model.events=results[1].value.events||[];
  if(results[2].status==="fulfilled")model.health=results[2].value||{};
  if(results[3].status==="fulfilled")model.canadianEvents=results[3].value.events||[];
  if(results[4].status==="fulfilled")model.worldNews=results[4].value.leads||[];
  if(results[5].status==="fulfilled")model.worldNewsStatus=results[5].value||{};
  const country=get("mapCountry"),current=country.value;
  country.innerHTML='<option value="">All countries (worldwide)</option>'+model.countries.map(c=>
    '<option value="'+html(c.code)+'">'+html(c.name)+(c.coverage==="active"?" · official actions":(c.world_reporting_count?" · recent news":(c.world_reporting_state&&c.world_reporting_state!=="not_attempted"?" · scanned":" · pending scan")))+'</option>').join("");
  if(model.countries.some(c=>c.code===current))country.value=current;
  const regulator=get("mapAgency"),prev=regulator.value;
  const agencies=[...new Set(["FINTRAC","FCAC",...model.events.map(x=>x.regulator).filter(Boolean)])].sort();
  regulator.innerHTML='<option value="">All agencies</option>'+agencies.map(x=>'<option value="'+html(x)+'">'+html(x)+'</option>').join("");
  if(agencies.includes(prev))regulator.value=prev;
  renderCoverage();renderPatterns();renderCountryBrief();renderThreads();
  window.dispatchEvent(new CustomEvent("signalnorth:globalready",{detail:{events:model.events,countries:model.countries,health:model.health,worldNews:model.worldNews,worldNewsStatus:model.worldNewsStatus}}));
 }
 get("mapCountry").addEventListener("change",renderCountryBrief);
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
