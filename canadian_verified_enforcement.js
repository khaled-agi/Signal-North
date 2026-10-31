"use strict";
(()=>{const el=id=>document.getElementById(id),node=el("verifiedCanadaRows");if(!node)return;
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
fetch("./data/canadian_enforcement_verified.json?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("not available");return r.json()}).then(d=>{
const rows=d.records||[],p=el("verifiedCanadaAgency");p.innerHTML='<option value="">All agencies</option>'+[...new Set(rows.map(x=>x.agency))].sort().map(x=>'<option>'+esc(x)+'</option>').join("");
el("verifiedCanadaCount").textContent=rows.length+" index-referenced manually transcribed records (non-exhaustive)";
function render(){let q=el("verifiedCanadaSearch").value.trim().toLowerCase(),items=rows.filter(x=>(!p.value||x.agency===p.value)&&(!q||[x.name,x.topic,x.title].join(" ").toLowerCase().includes(q)));
node.innerHTML=items.map(x=>'<article class="world-reporting-record"><div class="world-reporting-date">'+esc(x.agency)+' · Published '+esc(x.published)+'</div><strong>'+esc(x.name)+'</strong><div class="world-reporting-details">'+esc(x.title)+' · '+esc(x.topic)+'</div><div class="world-reporting-details">Penalty C$'+Number(x.penalty_cad).toLocaleString("en-CA")+' · '+esc(x.status||"")+(x.action_date?' · Action '+esc(x.action_date):'')+'</div><a href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer">Open regulator index ↗</a></article>').join("")||'<div class="empty">No matching cases.</div>';}
el("verifiedCanadaSearch").addEventListener("input",render);p.addEventListener("change",render);render();
}).catch(()=>{el("verifiedCanadaCount").textContent="Published record import unavailable";node.textContent="No cases displayed until published data are available.";});
})();
