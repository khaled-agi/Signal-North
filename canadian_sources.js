"use strict";
(()=>{const byId=id=>document.getElementById(id),target=byId("canadianHubRows");if(!target)return;
const safe=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
fetch("./data/canadian_source_registry.json?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{
const items=d.sources||[];byId("canadianHubCount").textContent=items.length+" registered official source entry points";
const render=()=>{const type=byId("canadianHubType").value,q=byId("canadianHubQuery").value.toLowerCase().trim();
const found=items.filter(x=>(!type||x.type===type)&&(!q||[x.agency,x.dataset,x.jurisdiction,x.notes].join(" ").toLowerCase().includes(q)));
target.innerHTML=found.map(x=>'<article class="world-reporting-record"><div class="world-reporting-date">'+safe(x.jurisdiction)+' · '+safe(x.type)+' · '+safe(x.status.replaceAll("_"," "))+'</div><strong>'+safe(x.agency)+' — '+safe(x.dataset)+'</strong><div class="world-reporting-details">'+safe(x.notes)+'</div><a href="'+safe(x.url)+'" target="_blank" rel="noopener noreferrer">Official source ↗</a></article>').join("")||'<div class="empty">No matching source.</div>';};
byId("canadianHubType").addEventListener("change",render);byId("canadianHubQuery").addEventListener("input",render);render();
}).catch(()=>{target.textContent="Source registry not available; no missing sources are counted as zero.";});
})();
