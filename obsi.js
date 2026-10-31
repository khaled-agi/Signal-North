"use strict";
/* Official OBSI source navigation. No institution counts are invented or inferred. */
(() => {
 const root=document.getElementById("obsiSourceLinks");
 if(!root)return;
 const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
 const links=[
  {label:"Cases by banking services firms",desc:"Named firms: complaints received, scope decisions, recommendations, resolutions and fiscal-year filters.",url:"https://www.obsi.ca/en/case-data-insights/data-cube/cases-by-banking-services-firms/"},
  {label:"Banking products and issues",desc:"Explore products, complaint issues and trends (aggregate; not necessarily cross-tabulated by individual firm).",url:"https://www.obsi.ca/en/case-data-insights/data-cube/banking-products-and-issues/"},
  {label:"Banking case summaries",desc:"Closed federally regulated bank cases with bank names and anonymized case details from June 30, 2022.",url:"https://www.obsi.ca/en/case-data-insights/banking-case-summaries/"},
  {label:"OBSI Data Cube",desc:"Interactive statistics, outcomes, industry breakdowns and historical quarterly data.",url:"https://www.obsi.ca/en/case-data-insights/data-cube/"}
 ];
 function render(){
  const term=(document.getElementById("obsiFirmSearch")?.value||"").trim();
  root.innerHTML=links.map(x=>'<article class="world-reporting-record"><strong>'+escapeHTML(x.label)+'</strong><div class="world-reporting-details">'+escapeHTML(x.desc)+'</div><a target="_blank" rel="noopener noreferrer" href="'+escapeHTML(x.url)+'">Open official OBSI source ↗</a></article>').join("")+
   (term?'<p class="supporting-disclaimer">Institution filter requested: <strong>'+escapeHTML(term)+'</strong>. Open the named-firm Data Cube or case summaries and select that bank inside OBSI’s controls. Signal North does not yet contain extracted firm-level rows.</p>':"");
 }
 document.getElementById("obsiFirmSearch")?.addEventListener("input",render);render();
})();
