"use strict";
(()=>{const el=id=>document.getElementById(id),out=el("ciroNamedRows");if(!out)return;
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
fetch("./data/ciro_named_enforcement.json?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("not published");return r.json()}).then(d=>{
const records=d.records||[];if(records.length<5)throw Error("No validated case collection");
el("ciroNamedStatus").textContent=records.length+" official concluded case records";
function draw(){const q=el("ciroNamedSearch").value.trim().toLowerCase();const rows=records.filter(x=>x.institution.toLowerCase().includes(q));
out.innerHTML=rows.map(x=>'<article class="world-reporting-record"><div class="world-reporting-date">'+esc(x.regulator)+' · '+esc(x.concluded_date||"legacy concluded")+'</div><strong>'+esc(x.institution)+'</strong><div class="world-reporting-details">'+esc(x.topic)+' · Fine C$'+Number(x.fine_cad).toLocaleString("en-CA")+' · Costs C$'+Number(x.costs_cad).toLocaleString("en-CA")+' · Disgorgement C$'+Number(x.disgorgement_cad).toLocaleString("en-CA")+'</div><a rel="noopener noreferrer" href="'+esc(x.case_url)+'" target="_blank">CIRO original proceeding ↗</a></article>').join("")+
'<p class="supporting-disclaimer">'+rows.length+' matched concluded proceedings, not a complete historical CIRO database.</p>';}
el("ciroNamedSearch").addEventListener("input",draw);draw();
}).catch(()=>{el("ciroNamedStatus").textContent="Collection unavailable";out.textContent="No verified concluded cases published; this is not evidence of zero sanctions.";});
})();