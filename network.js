"use strict";
/* Sector facts are sourced and typed. Theme trends are headline coverage only. */
(() => {
 const el=id=>document.getElementById(id);
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const safeLink=(raw,txt)=>{
  try{const u=new URL(raw);return u.protocol==="https:"?'<a href="'+esc(u.href)+'" target="_blank" rel="noopener noreferrer">'+esc(txt)+' ↗</a>':""}catch{return ""}
 };
 const number=n=>Number(n||0).toLocaleString("en-CA");
 const state={themes:[],years:[],byYear:{},selected:"",sectors:[]};let wired=false;
 function themeCurrent(){return state.themes.find(x=>x.name===state.selected)||state.themes[0]}
 function renderThemes(){
  const selected=themeCurrent();if(!selected)return;
  state.selected=selected.name;
  el("themeChoose").value=state.selected;
  const years=state.years;
  const max=Math.max(1,...state.themes.flatMap(x=>Object.values(x.year_counts||{})));
  const year=el("themeYear").value;
  el("themeCount").textContent=number(state.byYear[year]||Object.values(state.byYear).reduce((a,b)=>a+b,0))+
   " unique articles"+(year?" published in "+year:" across the indexed archive");
  el("themeYearCoverage").innerHTML=years.map(y=>'<div><strong>'+esc(y)+'</strong><span>'+number(state.byYear[y])+' indexed titles</span></div>').join("");
  el("themeGrid").innerHTML='<div class="theme-matrix-header"><span>Scam / financial-crime theme</span>'+years.map(y=>'<span>'+esc(y)+'</span>').join("")+'<span>Total</span></div>'+
   state.themes.map(x=>{
    const chosen=x.name===state.selected;
    return '<div class="theme-matrix-row'+(chosen?" active":"")+'"><button type="button" data-select-theme="'+esc(x.name)+'">'+esc(x.name)+'</button>'+
     years.map(y=>{const n=x.year_counts?.[y]||0,alpha=Math.min(.85,.12+(n/max)*.75);
      return '<button type="button" data-select-theme="'+esc(x.name)+'" data-theme-year="'+esc(y)+'" class="theme-cell" title="'+n+' classified article headlines in '+y+'" style="--theme-strength:'+alpha+'">'+number(n)+'</button>';}).join("")+
     '<strong>'+number(x.total_headlines)+'</strong></div>';
   }).join("");
  const examples=(selected.examples||[]).filter(x=>!year||String(x.date||"").startsWith(year)).slice(0,24);
  el("themeExamplesTitle").textContent=selected.name+(year?" — "+year:"");
  el("themeExamples").innerHTML=examples.length?examples.map(x=>'<article class="theme-story"><div class="theme-story-meta">'+esc((x.date||"").slice(0,10))+' · '+esc(x.publisher||"Publisher")+
    (x.geography?" · City mentioned: "+esc(x.geography):"")+'</div><strong>'+safeLink(x.url,x.title)+'</strong></article>').join(""):
   '<div class="empty">No featured headlines for this theme and year. Use the full article archive to inspect all titles.</div>';
 }
 function renderCompare(){
  const a=state.themes.find(x=>x.name===el("themeCompareA").value);
  const b=state.themes.find(x=>x.name===el("themeCompareB").value);
  if(!a||!b)return;
  const share=el("themeCompareMode").value==="share";
  const rows=state.years.map(y=>{
   const total=Number(state.byYear[y]||0);
   return {year:y,total,
    a:share?(total?100*Number(a.year_counts?.[y]||0)/total:0):Number(a.year_counts?.[y]||0),
    b:share?(total?100*Number(b.year_counts?.[y]||0)/total:0):Number(b.year_counts?.[y]||0)
   };
  });
  const max=Math.max(1,...rows.flatMap(r=>[r.a,r.b]));
  const fmt=x=>share?x.toFixed(1)+"%":number(x);
  el("themeCompareChart").innerHTML='<div class="compare-labels"><span><i class="compare-a"></i>'+esc(a.name)+'</span><span><i class="compare-b"></i>'+esc(b.name)+'</span></div>'+
   rows.map(r=>'<div class="compare-year"><div class="compare-year-meta"><strong>'+esc(r.year)+(r.year==="2026"?" YTD":"")+'</strong><span>'+
      number(r.total)+' indexed headlines</span></div>'+
    '<div class="compare-bars"><div><span class="compare-a" style="width:'+(100*r.a/max).toFixed(1)+'%"></span><b>'+fmt(r.a)+'</b></div>'+
    '<div><span class="compare-b" style="width:'+(100*r.b/max).toFixed(1)+'%"></span><b>'+fmt(r.b)+'</b></div></div></div>').join("");
 }
 function renderSectors(){
  const q=el("sectorSearch").value.toLowerCase().trim(),sector=el("sectorFilter").value,type=el("sectorType").value;
  const found=state.sectors.filter(x=>(!sector||x.sector===sector)&&(!type||x.kind===type)&&
   (!q||[x.name,x.title,x.summary,x.publisher,x.sector,x.status].join(" ").toLowerCase().includes(q)));
  el("sectorCount").textContent=found.length+" / "+state.sectors.length+" reviewed source entries";
  const kinds={administrative_penalty:"Published administrative penalty",authorized_platform_decision:"Authorized platform / regulatory decision",fraud_warning:"Fraud warning / prevention",regulator_directory:"Regulatory source directory"};
  el("sectorEntries").innerHTML=found.length?found.map(x=>
   '<article class="sector-item"><div class="sector-meta"><span class="sector-tag sector-'+esc(x.kind)+'">'+esc(kinds[x.kind]||x.kind)+'</span><span>'+esc(x.event_date||"")+' · '+esc(x.publisher||"")+'</span></div>'+
   '<h3>'+esc(x.name)+'</h3><p class="sector-title">'+esc(x.title)+'</p>'+
   '<div class="sector-status">'+esc(x.sector)+' · '+esc(x.status||"Status not established")+'</div>'+
   (x.amount_cad!=null?'<strong class="sector-amount">C$'+Number(x.amount_cad).toLocaleString("en-CA")+' administrative penalty</strong>':"")+
   '<p>'+esc(x.summary||"")+'</p><div class="sector-source">'+safeLink(x.source_url,"Examine original regulator or institution source")+'</div></article>'
  ).join(""):'<div class="empty">No source entries match these sectors and terms.</div>';
 }
 async function boot(){
  const names=["theme_trends.json","sector_watch.json"];
  const results=await Promise.allSettled(names.map(async name=>{
   const res=await fetch("./data/"+name+"?t="+Date.now(),{cache:"no-store"});
   if(!res.ok)throw Error("HTTP "+res.status);
   return res.json();
  }));
  if(results[0].status==="fulfilled"){
   const d=results[0].value;state.themes=d.themes||[];state.years=d.years||[];state.byYear=d.articles_by_year||{};
   const prev=state.selected;state.selected=(state.themes.find(x=>x.name===prev)||state.themes[0]||{}).name||"";
   el("themeChoose").innerHTML=state.themes.map(x=>'<option value="'+esc(x.name)+'">'+esc(x.name)+'</option>').join("");
   el("themeYear").innerHTML='<option value="">All publication years</option>'+state.years.map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join("");
   const opts=state.themes.map(x=>'<option value="'+esc(x.name)+'">'+esc(x.name)+'</option>').join("");
   for(const id of ["themeCompareA","themeCompareB"]){
     const previous=el(id).value;
     el(id).innerHTML=opts;
     if(previous&&state.themes.some(x=>x.name===previous))el(id).value=previous;
   }
   if(state.themes.length>1&&el("themeCompareA").value===el("themeCompareB").value)el("themeCompareB").selectedIndex=1;
   renderThemes();renderCompare();
  }else{
   el("themeCount").textContent="Theme analysis unavailable";
   el("themeGrid").innerHTML='<div class="empty">Theme data will appear after the next successful source scan.</div>';
  }
  if(results[1].status==="fulfilled"){
   state.sectors=results[1].value.entries||[];
   el("sectorFilter").innerHTML='<option value="">All sectors</option>'+[...new Set(state.sectors.map(x=>x.sector))].sort().map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join("");
   const kinds={administrative_penalty:"Administrative penalties",authorized_platform_decision:"Authorized platforms",fraud_warning:"Fraud & scam advisories",regulator_directory:"Enforcement directories"};
   el("sectorType").innerHTML='<option value="">All evidence types</option>'+Object.entries(kinds).map(([k,v])=>'<option value="'+esc(k)+'">'+esc(v)+'</option>').join("");
   renderSectors();
  }else{
   el("sectorCount").textContent="Sector directory unavailable";
   el("sectorEntries").innerHTML='<div class="empty">The regulator directory could not be loaded.</div>';
  }
  if(!wired){
   el("themeChoose").addEventListener("change",e=>{state.selected=e.target.value;renderThemes()});
   el("themeYear").addEventListener("change",renderThemes);
   for(const id of ["themeCompareA","themeCompareB","themeCompareMode"])el(id).addEventListener("change",renderCompare);
   const openThemeIn=(tab)=>{
     const theme=state.selected||el("themeChoose").value;
     const year=el("themeYear").value;
     window.dispatchEvent(new CustomEvent("signalnorth:applytheme",{detail:{theme,year}}));
     const button=document.querySelector('[data-tab="'+tab+'"]');
     if(button)button.click();
   };
   el("themeToMap").addEventListener("click",()=>openThemeIn("overview"));
   el("themeToStories").addEventListener("click",()=>openThemeIn("fraud"));
   el("themeSourceLink").addEventListener("click",()=>document.querySelector('[data-tab="reports"]').click());
   el("sectorSearch").addEventListener("input",renderSectors);
   el("sectorFilter").addEventListener("change",renderSectors);
   el("sectorType").addEventListener("change",renderSectors);
   document.addEventListener("click",e=>{
    const sel=e.target.closest("[data-select-theme]");
    if(sel){
     state.selected=sel.dataset.selectTheme;
     if(sel.dataset.themeYear)el("themeYear").value=sel.dataset.themeYear;
     renderThemes();
     el("themeExamplesTitle").scrollIntoView({behavior:"smooth",block:"center"});
    }
   });
   wired=true;
  }
 }
 window.addEventListener("signalnorth:refresh",boot);
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
