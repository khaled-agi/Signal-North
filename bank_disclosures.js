"use strict";
(() => {
const el=id=>document.getElementById(id), safe=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
if(!el("bankDisclosureRows"))return;
fetch("./data/bank_complaint_disclosures.json?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json()}).then(payload=>{
const rows=payload.records||[],picker=el("bankDisclosureFilter");
picker.innerHTML='<option value="">All available banks</option>'+rows.map(x=>x.institution).filter((x,i,a)=>a.indexOf(x)===i).sort().map(x=>'<option value="'+safe(x)+'">'+safe(x)+'</option>').join("");
function render(){const filter=picker.value,items=rows.filter(x=>!filter||x.institution===filter);
el("bankDisclosureRows").innerHTML=items.map(x=>'<article class="world-reporting-record"><div class="world-reporting-date">'+safe(x.year)+' · '+safe(x.office)+'</div><strong>'+safe(x.institution)+'</strong><div class="world-reporting-details"><strong>'+Number(x.metric_value).toLocaleString('en-CA')+'</strong> '+safe(x.metric_name.replaceAll("_"," "))+' · '+safe(x.scope)+'</div>'+
(x.fraud_nature_pct!=null?'<div class="world-reporting-details">Fraud category: '+safe(x.fraud_nature_pct)+'% (published percentage)</div>':'')+
(x.fraud_nature_count!=null?'<div class="world-reporting-details">Fraud-category cases: '+safe(x.fraud_nature_count)+' (published count)</div>':'')+
'<div class="world-reporting-details">'+safe(x.fraud_percentage_note||"")+'</div><a href="'+safe(x.source_url)+'" rel="noopener noreferrer" target="_blank">Read original annual report ↗</a></article>').join("")||'<div class="empty">No published records match.</div>';}
picker.addEventListener("change",render);render();
}).catch(()=>{el("bankDisclosureRows").textContent="The verified annual disclosure snapshot is not available. No figures have been inferred.";});
})();
