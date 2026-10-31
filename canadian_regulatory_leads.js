"use strict";
(()=>{const get=id=>document.getElementById(id),out=get("canRegRows");if(!out)return;
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
fetch("./data/canadian_regulatory_leads.json?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("No published snapshot");return r.json()}).then(d=>{
const a=Array.isArray(d.leads)?d.leads:[],health=d.sources||{},picker=get("canRegAgency");
picker.innerHTML='<option value="">All collected agencies</option>'+[...new Set(a.map(x=>x.agency))].sort().map(x=>'<option>'+esc(x)+'</option>').join("");
const ok=Object.values(health).filter(x=>x.status==="success").length;
get("canRegLeadStatus").textContent=a.length+" index links · "+ok+"/"+Object.keys(health).length+" sources refreshed";
function render(){const agency=picker.value,q=get("canRegSearch").value.toLowerCase().trim();const match=a.filter(x=>(!agency||agency===x.agency)&&(!q||(x.title+" "+x.agency).toLowerCase().includes(q)));
out.innerHTML=match.slice(0,150).map(x=>'<article class="world-reporting-record"><div class="world-reporting-date">'+esc(x.agency)+' · unreviewed official link</div><strong>'+esc(x.title)+'</strong><div><a href="'+esc(x.url)+'" rel="noopener noreferrer" target="_blank">Original regulator source ↗</a></div></article>').join("")+'<p class="supporting-disclaimer">'+match.length+' matching official links; first 150 shown. No case counts inferred from links.</p>';}
picker.addEventListener("change",render);get("canRegSearch").addEventListener("input",render);render();
}).catch(()=>{get("canRegLeadStatus").textContent="First collection not yet confirmed";out.textContent="No verified collected source index yet. Use the official source registry above.";});
})();
