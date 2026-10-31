"use strict";
(() => {
 const el=id=>document.getElementById(id),root=el("obsiFirmRows");if(!root)return;
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 fetch("./data/obsi_firm_complaints.json?v="+Date.now(),{cache:"no-store"})
  .then(r=>{if(!r.ok)throw Error("no published institution data");return r.json()})
  .then(d=>{
   const rows=d.records||[];
   if(rows.length<45)throw Error("OBSI named-firm data below documented minimum");
   const year=el("obsiFirmYear"),query=el("obsiFirmName");
   const years=[...new Set(rows.map(x=>x.fiscal_year))].sort((a,b)=>b-a);
   year.innerHTML='<option value="">All published years</option>'+years.map(y=>'<option value="'+y+'">'+y+'</option>').join("");
   el("obsiFirmStatus").textContent=rows.length+" original-source firm-year rows · "+years.join(", ");
   function render(){
    const term=query.value.trim().toLowerCase(),yr=year.value;
    const found=rows.filter(x=>(!yr||String(x.fiscal_year)===yr)&&(!term||x.institution.toLowerCase().includes(term)));
    root.innerHTML=found.slice(0,120).map(x=>
     '<article class="world-reporting-record"><div class="world-reporting-date">OBSI FY'+esc(x.fiscal_year)+' · '+esc(x.sector.replaceAll("_"," "))+'</div><strong>'+esc(x.institution)+'</strong>'+
     '<div class="world-reporting-details">'+Number(x.complaints_received).toLocaleString("en-CA")+' complaints received · '+Number(x.opened_cases).toLocaleString("en-CA")+' opened · '+Number(x.closed_cases).toLocaleString("en-CA")+' closed · '+Number(x.resolved_satisfaction).toLocaleString("en-CA")+' resolved to complainant satisfaction</div>'+
     '<a href="'+esc(x.source_url)+'" rel="noopener noreferrer" target="_blank">OBSI original annual report (p. '+esc(x.source_pages)+') ↗</a></article>').join("")+
     '<p class="supporting-disclaimer">'+found.length+' matching OBSI institution-year records; showing up to 120. No missing year is interpreted as zero.</p>';
   }
   query.addEventListener("input",render);year.addEventListener("change",render);render();
  })
  .catch(()=>{el("obsiFirmStatus").textContent="Data unavailable";root.textContent="A validated OBSI firm-level dataset has not been published; no zero-complaints inference.";});
})();
