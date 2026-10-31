"use strict";
(()=>{const el=id=>document.getElementById(id),target=el("osfiInstitutionRows");if(!target)return;
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
fetch("./data/osfi_institutions.json?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("No collected register");return r.json()}).then(d=>{
if(!Array.isArray(d.records)||d.records.length<20)throw Error("No validated register");
const cols=d.source_columns||[];
const nameCol=cols.find(k=>/institution.*name|name.*institution|legal.*name|^name$|entity.*name/i.test(k))||cols.find(k=>/name/i.test(k));
const names=d.records.map(r=>({row:r,display:nameCol?r.fields[nameCol]:Object.values(r.fields).find(Boolean)||""}));
el("osfiRegisterStatus").textContent=d.record_count+" official rows · retrieved "+(d.retrieved_at||"").slice(0,10);
function render(){const q=(el("osfiInstitutionSearch").value||"").toLowerCase(),arr=names.filter(x=>Object.values(x.row.fields).some(v=>String(v).toLowerCase().includes(q)));
target.innerHTML=arr.slice(0,100).map(x=>'<article class="world-reporting-record"><strong>'+esc(x.display)+'</strong><div class="world-reporting-details">'+esc(Object.entries(x.row.fields).filter(([k,v])=>v&&k!==nameCol).slice(0,4).map(([k,v])=>k+": "+v).join(" · "))+'</div></article>').join("")+'<p class="supporting-disclaimer">'+arr.length+' matching official directory rows · showing first 100 · not allegations or penalties</p>';}
el("osfiInstitutionSearch").addEventListener("input",render);render();
}).catch(()=>{el("osfiRegisterStatus").textContent="Collection pending / unavailable";target.textContent="Monthly OSFI data collection has not yet produced a validated file. The official source remains available in the registry.";});
})();
