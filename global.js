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
 const model={events:[],countries:[],health:{}};
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
  if(!code){host.innerHTML='<strong>Global source coverage:</strong> Populated enforcement jurisdictions are marked with counted circles; other countries remain selectable but do not have invented cases. <a href="https://www.fatf-gafi.org/en/countries.html" target="_blank" rel="noopener noreferrer">FATF country assessments ↗</a>';return;}
  const country=model.countries.find(c=>c.code===code);
  if(!country){host.textContent="Country source status unavailable.";return;}
  const found=model.events.filter(e=>e.country_code===code);
  host.innerHTML='<strong>'+html(country.name)+': '+(country.coverage==="active"?
    found.length+' collected international agency action(s)'+(code==="CA"?" plus Canadian domestic sources":""):
    'no official enforcement actions ingested yet')+'</strong> · '+
    'Country markers indicate regulator jurisdiction, not where fraud occurred. '+
    '<a href="https://www.fatf-gafi.org/en/countries.html" target="_blank" rel="noopener noreferrer">Search FATF jurisdiction reviews ↗</a> · '+
    '<a href="https://egmontgroup.org/members-by-region/" target="_blank" rel="noopener noreferrer">Find financial intelligence units ↗</a>';
 }
 function renderCoverage(){
  const active=model.countries.filter(x=>x.coverage==="active");
  const countries=model.countries.length;
  const count=model.events.length;
  get("worldCoverage").innerHTML='<strong>'+countries.toLocaleString("en-CA")+' countries & territories indexed for discovery</strong>'+
   '<span>Official enforcement currently populated for '+active.length+' jurisdictions including Canada · '+
     count+' non-Canadian actions · other countries explicitly marked not yet ingested</span>';
 }
 async function load(){
  const paths=["world_jurisdictions.json","global_enforcement.json","global_source_status.json"];
  const results=await Promise.allSettled(paths.map(async x=>{
    const r=await fetch("./data/"+x+"?ts="+Date.now(),{cache:"no-store"});
    if(!r.ok)throw Error(x+": "+r.status);
    return r.json();
  }));
  if(results[0].status==="fulfilled")model.countries=results[0].value.jurisdictions||[];
  if(results[1].status==="fulfilled")model.events=results[1].value.events||[];
  if(results[2].status==="fulfilled")model.health=results[2].value||{};
  const country=get("mapCountry"),current=country.value;
  country.innerHTML='<option value="">All countries (worldwide)</option>'+model.countries.map(c=>
    '<option value="'+html(c.code)+'">'+html(c.name)+(c.coverage==="active"?" · source records":" · not yet ingested")+'</option>').join("");
  if(model.countries.some(c=>c.code===current))country.value=current;
  const regulator=get("mapAgency"),prev=regulator.value;
  const agencies=[...new Set(["FINTRAC","FCAC",...model.events.map(x=>x.regulator).filter(Boolean)])].sort();
  regulator.innerHTML='<option value="">All agencies</option>'+agencies.map(x=>'<option value="'+html(x)+'">'+html(x)+'</option>').join("");
  if(agencies.includes(prev))regulator.value=prev;
  renderCoverage();renderPatterns();renderCountryBrief();
  window.dispatchEvent(new CustomEvent("signalnorth:globalready",{detail:{events:model.events,countries:model.countries,health:model.health}}));
 }
 get("mapCountry").addEventListener("change",renderCountryBrief);
 get("mapReset").addEventListener("click",renderCountryBrief);
 get("worldView").addEventListener("click",renderCountryBrief);
 document.addEventListener("click",e=>{
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
