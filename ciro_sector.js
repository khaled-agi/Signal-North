"use strict";
(()=>{const el=id=>document.getElementById(id),out=el("ciroSectorRows");if(!out)return;
fetch("./data/ciro_enforcement_activity.json?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Data unavailable");return r.json()}).then(d=>{
const rows=d.firm_sanctions||[];if(!rows.length)throw Error("Empty");
el("ciroSectorHealth").textContent=rows.length+" published fiscal years · "+d.last_publication_scope;
out.innerHTML=rows.slice().reverse().map(r=>'<article class="world-reporting-record"><strong>Fiscal '+Number(r.fiscal_year)+' · '+Number(r.firm_decisions)+' firm decisions</strong><div class="world-reporting-details">Firm fines: C$'+Number(r.firm_fines_cad).toLocaleString("en-CA")+' · Costs: C$'+Number(r.firm_costs_cad).toLocaleString("en-CA")+' · Disgorgement: C$'+Number(r.firm_disgorgement_cad).toLocaleString("en-CA")+'</div><a rel="noopener noreferrer" target="_blank" href="'+d.source_url+'">CIRO official activity table ↗</a></article>').join("");
}).catch(()=>{el("ciroSectorHealth").textContent="Unavailable";out.textContent="No validated CIRO annual aggregate data available.";});
})();