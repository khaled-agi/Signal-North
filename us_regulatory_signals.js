"use strict";
(() => {
 const el=id=>document.getElementById(id),out=el("usSignalRows");
 if(!out)return;
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 fetch("./data/us_regulatory_signal_publications.json?v="+Date.now(),{cache:"no-store"})
 .then(r=>{if(!r.ok)throw Error("No source snapshot");return r.json()})
 .then(d=>{
  const data=d.records||[];
  const checks=Object.entries(d.source_health||{}).map(([id,v])=>id+": "+v.status).join(" | ");
  el("usAgencySignalHealth").textContent=checks||"No successful source yet";
  el("usAgencySignalStatus").textContent=data.length+" official publication leads (not adjudicated cases)";
  function render(){
   const agency=el("usSignalAgency").value,q=el("usSignalSearch").value.trim().toLowerCase();
   const rows=data.filter(x=>(!agency||x.agency===agency)&&(!q||[x.title,x.agency].some(v=>String(v||"").toLowerCase().includes(q))));
   out.innerHTML=rows.slice(0,120).map(x=>'<article class="world-reporting-record"><div class="world-reporting-date">'+esc(x.agency)+' · '+esc(x.publication_date||"Publication date unavailable")+' · '+esc(x.signal_type.replaceAll("_"," "))+'</div><strong>'+esc(x.title)+'</strong><div class="world-reporting-details">Official publication lead · requires review of underlying notice before treating as enforcement</div><a target="_blank" rel="noopener noreferrer" href="'+esc(x.url)+'">Original regulator publication ↗</a></article>').join("")+
    '<p class="supporting-disclaimer">Showing '+Math.min(rows.length,120)+' of '+rows.length+' matching source links. Source failures and unavailable sources are tracked separately.</p>';
  }
  el("usSignalAgency").addEventListener("change",render);
  el("usSignalSearch").addEventListener("input",render);render();
 })
 .catch(()=>{el("usAgencySignalStatus").textContent="Feed not available";out.textContent="The official U.S. regulator feed has not produced a published snapshot; this is not a zero-enforcement claim.";});
})();
