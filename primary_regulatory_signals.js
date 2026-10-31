"use strict";
(() => {
 const el=id=>document.getElementById(id),out=el("primarySignalRows");
 if(!out)return;
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const FILES={
   occ:"us_occ_enforcement_actions.json",
   ofac:"us_ofac_sdn_entities.json",
   uk:"uk_sanctions_entities.json",
   sec:"us_sec_litigation_releases.json",
 };
 const data={},status={};
 const selector=el("primarySignalType"),query=el("primarySignalSearch");
 const text=(r,kind)=>kind==="occ"?
    [r.institution,r.individual_party,r.docket,r.action_description,...(r.subject_matters||[])].join(" "):
    kind==="ofac"?[r.name,...(r.sanctions_programs||[])].join(" "):
    kind==="uk"?[r.name,r.regime,r.uk_unique_id,r.sanctions_imposed].join(" "):
    [r.title,r.release_number].join(" ");
 function render(){
   const kind=selector.value,d=data[kind],term=query.value.trim().toLowerCase();
   if(!d){
     el("primarySignalsStatus").textContent="No validated "+kind.toUpperCase()+" snapshot";
     out.innerHTML='<div class="empty">No successfully published original-source dataset for this regulator yet. This is not evidence of zero cases.</div>';return;
   }
   const all=d.records||[],found=all.filter(r=>!term||text(r,kind).toLowerCase().includes(term));
   el("primarySignalsStatus").textContent=all.length.toLocaleString("en-US")+" original "+kind.toUpperCase()+" records · collected "+String(d.retrieved_at||"").slice(0,10);
   out.innerHTML=found.slice(0,100).map(r=>{
     if(kind==="occ"){
       return '<article class="world-reporting-record"><div class="world-reporting-date">'+esc(r.start_date||"Date unavailable")+
        ' · OCC '+esc(r.case_type)+' · '+esc(r.subject_is_individual?"Individual action at named bank":"Institution-related proceeding")+'</div>'+
        '<strong>'+esc(r.institution)+'</strong><div class="world-reporting-details">'+esc(r.action_description)+
        (r.subject_is_individual?' · Individual: '+esc(r.individual_party):'')+
        (r.amount_usd!=null?' · Listed amount US$'+Number(r.amount_usd).toLocaleString("en-US"):'')+
        (r.subject_matters?.length?' · Topics: '+esc(r.subject_matters.join(", ")):'')+
        ' · '+esc(r.termination_date?'Termination recorded: '+r.termination_date:'Current legal status must be checked')+
        '</div><a target="_blank" rel="noopener noreferrer" href="'+esc(r.source_url)+'">Official OCC action search ↗</a></article>';
     }
     if(kind==="ofac"){
       return '<article class="world-reporting-record"><div class="world-reporting-date">OFAC SDN organization/group · listing '+esc(r.ofac_ent_num)+'</div>'+
        '<strong>'+esc(r.name)+'</strong><div class="world-reporting-details">Programs: '+esc((r.sanctions_programs||[]).join(", ")||"Unspecified")+
        ' · Sanctions listing, not proof of bank fraud or a matching institution.</div>'+
        '<a target="_blank" rel="noopener noreferrer" href="'+esc(r.source_url)+'">Official OFAC Sanctions List Service ↗</a></article>';
     }
     if(kind==="uk"){
       return '<article class="world-reporting-record"><div class="world-reporting-date">UK FCDO sanctioned entity · '+esc(r.uk_unique_id)+'</div>'+
        '<strong>'+esc(r.name)+'</strong><div class="world-reporting-details">Regime: '+esc(r.regime||"Not specified")+
        ' · Sanctions: '+esc(r.sanctions_imposed||"See official list")+
        ' · Entity listed by government, not an automatic bank identity match.</div>'+
        '<a target="_blank" rel="noopener noreferrer" href="'+esc(r.source_url)+'">UK FCDO original sanctions list ↗</a></article>';
     }
     return '<article class="world-reporting-record"><div class="world-reporting-date">SEC litigation release · '+esc(r.publication_date||"Publication date unavailable")+
      '</div><strong>'+esc(r.title)+'</strong><div class="world-reporting-details">Official SEC court publication · may report allegations rather than a final judgment.</div>'+
      '<a target="_blank" rel="noopener noreferrer" href="'+esc(r.url)+'">Original SEC release ↗</a></article>';
   }).join("")+
    '<p class="supporting-disclaimer">'+found.length.toLocaleString("en-US")+' matching source records · up to 100 displayed. Sources are not comparable or additive as wrongdoing counts.</p>';
 }
 selector.addEventListener("change",render);
 query.addEventListener("input",render);
 for(const [kind,path] of Object.entries(FILES)){
   fetch("./data/"+path+"?v="+Date.now(),{cache:"no-store"})
     .then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json()})
     .then(d=>{if(!Array.isArray(d.records)||!d.records.length)throw Error("Missing parsed records");data[kind]=d;if(selector.value===kind)render()})
     .catch(()=>{status[kind]="unavailable";if(selector.value===kind)render()});
 }
 const healthPaths=[
  ["OCC","us_occ_enforcement_health.json"],["OFAC","us_ofac_source_health.json"],["UK FCDO","uk_sanctions_source_health.json"],["SEC","us_sec_source_health.json"],
 ];
 Promise.all(healthPaths.map(([name,path])=>fetch("./data/"+path+"?v="+Date.now(),{cache:"no-store"})
   .then(r=>{if(!r.ok)throw Error("not published");return r.json()})
   .then(d=>name+": "+(d.status||"pending")+" · "+(d.last_success||d.updated_at||d.checked_at||"unknown"))
   .catch(()=>name+": no health report")))
  .then(items=>{el("primarySignalHealth").textContent=items.join(" | ")});
})();
