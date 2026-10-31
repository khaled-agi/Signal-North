"use strict";
(() => {
  const el=id=>document.getElementById(id),out=el("fintracOfficialRows");
  if(!out)return;
  const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  fetch("./data/fintrac_penalties_official.json?v="+Date.now(),{cache:"no-store"})
   .then(r=>{if(!r.ok)throw Error("No published official penalty index");return r.json()})
   .then(d=>{
     if(!Array.isArray(d.records)||d.records.length<15)throw Error("Unvalidated snapshot");
     const records=d.records;
     el("fintracOfficialStatus").textContent=records.length+" notices · downloaded "+String(d.retrieved_at||"").slice(0,10);
     function draw(){
       const term=(el("fintracOfficialSearch").value||"").toLocaleLowerCase();
       const found=records.filter(x=>[x.entity_name,x.source_text].some(v=>String(v||"").toLocaleLowerCase().includes(term)));
       out.innerHTML=found.slice(0,100).map(x=>{
         return '<article class="world-reporting-record"><div class="world-reporting-date">'+esc(x.published)+' · FINTRAC public notice</div>'+
          '<strong>'+esc(x.entity_name||"Entity name requires review")+'</strong>'+
          '<div class="world-reporting-details">Penalty imposed: C$'+Number(x.penalty_cad).toLocaleString("en-CA")+
          (x.violation_count==null?"":" · "+Number(x.violation_count).toLocaleString("en-CA")+" reported violations")+
          ' · '+esc(x.status_summary||"not_confirmed")+'</div>'+
          '<div class="world-reporting-details">'+esc(x.source_text)+'</div>'+
          '<a href="'+esc(x.source_url)+'" rel="noopener noreferrer" target="_blank">Official FINTRAC notice source ↗</a></article>';
       }).join("")+'<p class="supporting-disclaimer">'+found.length+' matching public notices · displaying up to 100 · no allegations treated as criminal convictions</p>';
     }
     el("fintracOfficialSearch").addEventListener("input",draw);draw();
   }).catch(()=>{el("fintracOfficialStatus").textContent="Collection pending / unavailable";out.textContent="No validated published FINTRAC index data yet. This is not a zero-penalty claim.";});
})();
