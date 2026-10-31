"use strict";
(() => {
 const el=id=>document.getElementById(id),out=el("provincialFeedRows");
 if(!out)return;
 const safe=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const datasets={},health={};
 const files={bcsc:"bcsc_official_rss.json",amf:"amf_quebec_entities.json"};
 const type=el("provincialFeedType");
 function render(){
  const kind=type.value,q=el("provincialFeedSearch").value.toLowerCase(),d=datasets[kind];
  if(!d){out.textContent="No successful validated collection has been published for this source. This is not a zero-record result.";return;}
  const fields=x=>x.fields||{};
  const records=(d.records||[]).filter(x=>[x.title,x.summary,...Object.values(fields(x))].join(" ").toLowerCase().includes(q));
  el("provincialFeedStatus").textContent=records.length+" matching of "+d.records.length+" "+(kind==="bcsc"?"regulatory notices":"regulated-entity rows");
  out.innerHTML=records.slice(0,80).map(r=>kind==="bcsc"?
   '<article class="world-reporting-record"><strong>'+safe(r.title)+'</strong><div class="world-reporting-details">'+safe(r.type==='disciplined_list'?'Official disciplinary publication':'Hearing / order notice — not a final finding')+' · '+safe(r.publication_text)+'</div><a rel="noopener noreferrer" target="_blank" href="'+safe(r.url)+'">Original BCSC RSS source ↗</a></article>':
   '<article class="world-reporting-record"><strong>'+safe(Object.entries(fields(r)).find(([k,v])=>v&&/dénomination|nom.*institution|raison sociale|institution|organization|company|name/i.test(k))?.[1]||"Québec licensed entity")+'</strong><div class="world-reporting-details">'+safe(Object.entries(fields(r)).filter(([k,v])=>v).slice(0,4).map(([k,v])=>k+": "+v).join(" · "))+'</div></article>').join("")+
   '<p class="supporting-disclaimer">Showing up to 80 matching rows. Public data are not proof of wrongdoing.</p>';
 }
 for(const [name,file] of Object.entries(files)){
  fetch("./data/"+file+"?v="+Date.now(),{cache:"no-store"})
   .then(r=>{if(!r.ok)throw Error("No source snapshot");return r.json()})
   .then(d=>{if(!Array.isArray(d.records)||d.records.length===0)throw Error("Empty");datasets[name]=d;if(type.value===name)render();})
   .catch(()=>{health[name]="unavailable";if(type.value===name)render();});
 }
 type.addEventListener("change",render);
 el("provincialFeedSearch").addEventListener("input",render);
})();
