"use strict";
const $ = selector => document.querySelector(selector);
const state = {events:[],news:[],status:{},map:null,layer:null,tab:"overview",mapMode:"all",mapCountMode:"groups",mapTopic:"",mapYearFrom:"",mapYearTo:"",mapProvince:"",mapMonth:"",clientFocus:"",mapMarkers:new Map(),incidents:[],entityAliases:[],rawHeadlineCount:0,globalEvents:[],worldCountries:[],globalHealth:{},mapCountry:"",mapAgency:"",globalPattern:""};
const provinces = {ON:"Ontario",QC:"Québec",BC:"British Columbia",AB:"Alberta",NB:"New Brunswick",NS:"Nova Scotia",MB:"Manitoba",SK:"Saskatchewan",NL:"Newfoundland & Labrador",PE:"Prince Edward Island"};
function escapeHTML(value){return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function currency(value){if(value==null)return "Not reported";const x=Number(value);return x>=1e6?"$"+(x/1e6).toLocaleString("en-CA",{maximumFractionDigits:2})+"M":"$"+x.toLocaleString("en-CA",{maximumFractionDigits:0});}
function date(x){return x?String(x).slice(0,10):"Date not reported";}
function sourceLink(url){try{const u=new URL(url);return u.protocol==="https:"?'<a class="source-link" href="'+escapeHTML(u.href)+'" target="_blank" rel="noopener noreferrer">Read original regulator notice ↗</a>':"";}catch{return "";}}
function eventsByInstitution(){const groups=new Map();for(const e of state.events){if(!e.institution)continue;const key=e.institution.trim();if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e);}return [...groups].map(([name,events])=>({name,events})).sort((a,b)=>b.events.length-a.events.length);}
function switchTab(tab){
 const changing=state.tab!==tab;
 state.tab=tab;
 document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("hidden",x.id!==tab));
 document.querySelectorAll(".nav").forEach(x=>x.classList.toggle("active",x.dataset.tab===tab));
 $("#crumb").textContent=({overview:"INTELLIGENCE OVERVIEW",events:"EVENT EXPLORER",incidents:"REPORTED FRAUD CASES",clients:"CLIENT WORKSPACE",connections:"INSTITUTION INTELLIGENCE",themes:"SCAM THEMES",sectors:"SECTOR INTELLIGENCE",community:"COMMUNITY NETWORK",reports:"RESEARCH LIBRARY",institutions:"INSTITUTION RADAR",fraud:"FRAUD INTELLIGENCE",losses:"LOSSES & PENALTIES",sources:"SOURCES & METHODOLOGY"})[tab];
 const t={overview:["Know what changed.","Know where to look.","Monitor public enforcement developments and explore evidence-linked institutions across Canada."],events:["Explore the evidence.","Understand each case.","Search regulator-published actions by entity, location, and legal status."],incidents:["Follow individual cases.","Know what was reported.","Source-linked customer incidents, financial impact and bank relationships."],clients:["Track client priorities.","Act on evidence.","Manage research notes, institution timelines and sourced briefs."],reports:["Understand the bigger picture.","Stay grounded in research.","Official studies, national fraud statistics and evidence limitations."],connections:["Connect the dots.","Keep evidence distinct.","Follow an institution across enforcement decisions, reported customer incidents, and preliminary news leads."],themes:["Follow the patterns.","Across the years.","Explore article coverage by scam typology, year and original source; trends are not incidence estimates."],sectors:["Beyond traditional banks.","Track every sector.","Crypto platforms, fintech, casinos and securities—classified by their actual regulatory evidence."],community:["Help connect the evidence.","Build a safer network.","Contribute public reports and corrections for independent review, without sharing private information."],institutions:["Organizations, not rankings.","Evidence before inference.","Institution profiles connect reported events without implying fraud or demand for consulting services."],fraud:["Follow the patterns.","Separate leads from findings.","Reported fraud losses, emerging incidents, and Canadian threat intelligence."],losses:["Follow the money.","Separate losses from penalties.","Compare reported enforcement penalties by publication year and see which institution fraud-loss figures remain undisclosed."],sources:["Trust the source.","Understand the gaps.","Track source availability, update times, and limitations of public regulatory data."]}[tab];
 $("#headline").innerHTML=escapeHTML(t[0])+"<br><em>"+escapeHTML(t[1])+"</em>";
 $("#description").textContent=t[2];
 if(tab==="overview"&&state.map)setTimeout(()=>state.map.invalidateSize(),60);
 if(changing)window.scrollTo(0,0);
}
function rowHTML(e){
 return '<div class="event" role="button" tabindex="0" data-event="'+escapeHTML(e.id)+'"><div class="event-date">'+escapeHTML(date(e.published_at))+'</div><div><div class="event-title">'+escapeHTML(e.title)+'</div><div class="event-meta"><span>'+escapeHTML(e.source)+'</span><span>'+escapeHTML(e.category)+'</span>'+(e.province?"<span>"+escapeHTML(provinces[e.province]||e.province)+"</span>":"")+'</div></div><div class="event-right">'+(e.penalty_cad==null?"":'<div class="event-amount">'+escapeHTML(currency(e.penalty_cad))+'</div>')+'<span class="pill">'+escapeHTML(e.status||"Published notice")+'</span></div></div>';
}
function renderMetrics(){
 const e=state.events;const fines=e.filter(x=>x.penalty_cad!=null);const total=fines.reduce((a,b)=>a+Number(b.penalty_cad),0);const mapped=e.filter(x=>Number.isFinite(x.latitude)&&Number.isFinite(x.longitude));
 const values=[
 ["Reporting groups",state.news.length?state.news.length.toLocaleString("en-CA"):"Loading", (state.rawHeadlineCount||0).toLocaleString("en-CA")+" indexed headlines · grouped, unverified reporting"],
 ["Official notices",String(e.length),"Regulator-published enforcement actions"],
 ["Reported cases",String(state.incidents.length),"Individually source-reviewed reports"],
 ["Global enforcement",String(state.globalEvents.length),"Non-Canadian official actions; not added to CAD penalty totals"]
 ];
 $("#metrics").innerHTML=values.map(v=>'<div class="metric"><span class="label">'+escapeHTML(v[0])+'</span><span class="value">'+escapeHTML(v[1])+'</span><span class="foot">'+escapeHTML(v[2])+'</span></div>').join("");
 const counts={};for(const x of mapped){counts[x.province||"Other"]=(counts[x.province||"Other"]||0)+1;}
 const sorted=Object.entries(counts).sort((a,b)=>b[1]-a[1]);const max=Math.max(1,...sorted.map(x=>x[1]));
 $("#regions").innerHTML=sorted.length?sorted.map(x=>'<div class="region"><div class="region-head"><span>'+escapeHTML(provinces[x[0]]||x[0])+'</span><strong>'+x[1]+'</strong></div><div class="track"><div style="width:'+Math.round(x[1]/max*100)+'%"></div></div></div>').join(""):'<div class="empty">No mapped institutions in the current source snapshot.</div>';

 const major=e.filter(x=>Number(x.penalty_cad)>=1000000).sort((x,y)=>Number(y.penalty_cad)-Number(x.penalty_cad));
 $("#majorOrders").innerHTML=major.length?major.slice(0,6).map(rowHTML).join(""):'<div class="empty">No major penalties have been identified in the current source snapshot.</div>';
 $("#recent").innerHTML=e.length?e.slice(0,8).map(rowHTML).join(""):'<div class="empty">No enforcement records are published in this snapshot yet. Check Source monitoring for the collector status.</div>';
 $("#updated").textContent=state.status.last_completed_at?"Collected "+date(state.status.last_completed_at):"Public-source snapshot";
}
// One source record contributes exactly one count. A news article is not an
// independently verified incident; unlocated articles remain in the list.
function mapRecord(kind,e){
 const news=kind==="news",world=kind==="global",reg=kind==="reg"||world,dateValue=reg?e.published_at:news?e.published_at:e.reported_at;
 const country=world?state.worldCountries.find(c=>c.code===e.country_code):null;
 const lat=world?country?.map_latitude:(news?e.map_latitude:e.latitude),
       lon=world?country?.map_longitude:(news?e.map_longitude:e.longitude);
 const hasGeo=Number.isFinite(lat)&&Number.isFinite(lon)&&Math.abs(lat)<=90&&Math.abs(lon)<=180;
 return {kind,id:String(e.id||""),date:dateValue||"",raw:e,
  title:String(e.title||e.institution||"Untitled evidence"),
  searchText:[e.title,...(e.headline_variations||[]).map(v=>v.title)].join(" ").toLowerCase(),
  reportCount:e.underlying_headline_count||1,
  sourceCount:e.source_count||e.number_of_article_links||1,
  publisher:String(e.regulator||e.publisher||e.source||e.institution||"Original source"),
  lat:hasGeo?lat:null,lon:hasGeo?lon:null,province:news?e.map_province:e.province,
  countryCode:world?e.country_code:"CA",agency:world?e.regulator:(kind==="reg"?e.source:""),
  locationRole:world?"regulator_jurisdiction_country_center":news?"headline_city_mention":"source_supported_location",
  location:world?e.country+" · regulator jurisdiction":news?(e.map_location||"City mentioned in headline"):e.location||"Source-reported location",
  sourceUrl:news?e.url:e.source_url};
}
function refreshMapList(){
 const host=$("#mappedStories");if(!host)return;
 let rows=state.mapRows||[];
 const q=($("#mapStorySearch")?.value||"").trim().toLocaleLowerCase();
 if(q)rows=rows.filter(x=>[x.searchText,x.publisher,x.province,x.location].some(t=>String(t||"").toLocaleLowerCase().includes(q)));
 const scope=state.mapSideScope||"all";
 if(scope==="mapped")rows=rows.filter(x=>x.lat!==null);
 else if(scope==="unmapped")rows=rows.filter(x=>x.lat===null);
 else if(scope==="selected")rows=rows.filter(x=>state.mapSelectedIds?.has(x.id));
 const located=rows.filter(x=>x.lat!==null).length;
 const international=rows.filter(x=>x.kind==="global").length;
 const total=rows.length;
 $("#mapStorySummary").textContent=
  total.toLocaleString("en-CA")+" records · "+international+" global jurisdiction actions · "+located.toLocaleString("en-CA")+" placed by source clue or jurisdiction · "+
  Math.min(state.mapSideVisible||100,total).toLocaleString("en-CA")+" shown";
 $("#mapStoryScope").value=scope;
 $("#mapStoryClear").hidden=scope!=="selected";
 $("#mapStoryMore").hidden=total<=(state.mapSideVisible||100);
 $("#mapStoryAll").hidden=total<=(state.mapSideVisible||100);
 host.innerHTML=rows.length?rows.slice(0,state.mapSideVisible||100).map(x=>{
  const located=x.lat!==null;
  const label=x.kind==="global"?"International agency action":x.kind==="reg"?"Canadian regulatory notice":x.kind==="case"?"Reviewed case":"News headline";
  return '<article class="map-story"><div class="map-story-meta">'+escapeHTML(date(x.date))+" · "+escapeHTML(label)+" · "+escapeHTML(x.publisher)+'</div>'+
   '<div class="map-story-title">'+(x.kind==="news"?
    '<button data-story="'+escapeHTML(x.id)+'" type="button">'+escapeHTML(x.title)+'</button>':
    '<a href="'+escapeHTML(/^https:\/\//.test(x.sourceUrl||"")?x.sourceUrl:"#")+'" target="_blank" rel="noopener noreferrer">'+escapeHTML(x.title)+' ↗</a>')+'</div>'+
   '<div class="map-story-sub">'+
    (x.kind==="global"?'<span class="map-reg-note">Regulator country, not incident location · '+escapeHTML(x.raw.status||"Published official action")+'</span> · ':"")+
    (x.kind==="news"&&x.sourceCount>1?x.sourceCount+' source links · ':"")+
    (located?'<span class="map-geo-yes">◉ '+escapeHTML(x.location)+'</span>':'<span class="map-geo-no">Location not verified</span>')+
    (located? ' · <button data-mapfocus="'+escapeHTML(x.id)+'" type="button" class="map-locate">Locate →</button>':"")+
    (x.kind!=="news"&&/^https:\/\//.test(x.sourceUrl||"")?' · <a href="'+escapeHTML(x.sourceUrl)+'" target="_blank" rel="noopener noreferrer">Source ↗</a>':"")+
   '</div></article>';
 }).join(""):'<div class="empty">No articles match this search, map layer or geographic coverage filter. Clear the filters or explore the full archive.</div>';
}
function renderMapClusters(){
 if(!state.map||!state.layer)return;
 state.layer.clearLayers();state.mapMarkers.clear();
 const zoom=state.map.getZoom();
 // Cluster nearby symbols in projected pixels at the current zoom. Each source
 // is only counted once; marker AREA broadly tracks grouped record count.
 const gridSize=84;
 const clusters=new Map();
 for(const x of state.mapRows||[]){
  if(x.lat===null)continue;
  const point=state.map.project(L.latLng(x.lat,x.lon),zoom);
  const key=Math.floor(point.x/gridSize)+"/"+Math.floor(point.y/gridSize);
  if(!clusters.has(key))clusters.set(key,{items:[],x:0,y:0,weights:{news:0,reg:0,case:0,global:0}});
  const g=clusters.get(key);g.items.push(x);g.x+=point.x;g.y+=point.y;g.weights[x.kind]++;
 }
 for(const g of clusters.values()){
  const recordCount=g.items.length;
  const n=state.mapCountMode==="headlines"?
      g.items.reduce((sum,x)=>sum+(x.kind==="news"?Math.max(1,Number(x.reportCount||1)):1),0):recordCount;
  const centre=state.map.unproject(L.point(g.x/recordCount,g.y/recordCount),zoom);
  const areaDiameter=Math.min(83,Math.max(28,22+Math.sqrt(n)*7));
  const kind=Object.entries(g.weights).sort((a,b)=>b[1]-a[1])[0][0];
  const accessibleLabel=n+" "+(state.mapCountMode==="headlines"?"headline and notice units":"grouped records")+" near "+(g.items[0]?.location||"this location");
  const marker=L.marker(centre,{
   icon:L.divIcon({html:'<span class="count-pin-inner">'+escapeHTML(String(n))+'</span>',className:"count-map-pin count-"+kind,
    iconSize:[areaDiameter,areaDiameter],iconAnchor:[areaDiameter/2,areaDiameter/2]}),
   keyboard:true,title:accessibleLabel,alt:accessibleLabel,
  }).addTo(state.layer);
  const geoNames=[...new Set(g.items.map(x=>x.location).filter(Boolean))].slice(0,3).join(" · ");
  const popup='<div class="map-pop"><div class="map-pop-heading">'+escapeHTML(n.toLocaleString("en-CA"))+
    (state.mapCountMode==="headlines"?' headline / evidence units':' grouped records')+'</div>'+
    '<span class="map-pop-source">'+escapeHTML(geoNames||"Source-supported geography")+'</span>'+
    '<p class="map-pop-notice">'+g.weights.news+' Canadian headlines · '+g.weights.reg+' Canadian notices · '+g.weights.global+' international jurisdiction actions · '+g.weights.case+' reviewed cases. International dots locate regulatory jurisdiction, not alleged offences.</p>'+
    '<div class="map-popup-record">'+g.items.slice(0,4).map(x=>'<div><span class="map-popup-date">'+escapeHTML(date(x.date))+'</span> '+(x.kind==="news"?'<button type="button" class="report-popup-open" data-story="'+escapeHTML(x.id)+'">'+escapeHTML(x.title)+'</button>':escapeHTML(x.title))+'</div>').join("")+
    (recordCount>4?'<div class="small">+'+(recordCount-4)+' additional groups; select this circle to explore them.</div>':"")+'</div></div>';
  marker.bindPopup(popup,{maxWidth:330,minWidth:230,maxHeight:350});
  marker.on("click",()=>{
   state.mapSelectedIds=new Set(g.items.map(x=>x.id));
   state.mapSideScope="selected";state.mapSideVisible=100;
   refreshMapList();
   $("#mapStorySummary").scrollIntoView({behavior:"smooth",block:"nearest"});
  });
  for(const x of g.items)state.mapMarkers.set(x.id,marker);
 }
 $("#mapClusterCount").textContent=clusters.size.toLocaleString("en-CA")+" proportional circles at this zoom";
}
function initMap(){
 if(!window.L){
  // A CDN outage must not disable the research list. The list never depends
  // on Leaflet: preserve all headline titles and source links independently.
  let rows=[...state.news.map(e=>mapRecord("news",e)),
            ...state.events.map(e=>mapRecord("reg",e)),
            ...state.incidents.map(e=>mapRecord("case",e)),
            ...state.globalEvents.map(e=>mapRecord("global",e))];
  if(state.mapMode==="news")rows=rows.filter(e=>e.kind==="news"||e.kind==="case");
  else if(state.mapMode==="enforcement")rows=rows.filter(e=>e.kind==="reg"||e.kind==="global");
  else if(state.mapMode==="major")rows=rows.filter(e=>e.kind==="reg"&&Number(e.raw.penalty_cad)>=1000000);
  if(state.mapCountry)rows=rows.filter(e=>e.countryCode===state.mapCountry);
  if(state.mapAgency)rows=rows.filter(e=>e.agency===state.mapAgency);
  if(state.mapProvince)rows=rows.filter(e=>e.countryCode!=="CA"||e.province===state.mapProvince);
  if(state.mapMonth)rows=rows.filter(e=>String(e.date).startsWith(state.mapMonth));
  if(state.mapTopic)rows=rows.filter(e=>e.raw.category===state.mapTopic||e.raw.fraud_type===state.mapTopic||(e.raw.fraud_themes||[]).includes(state.mapTopic));
  if(state.globalPattern){const re=new RegExp(state.globalPattern,"i");rows=rows.filter(e=>re.test([e.title,e.raw.category,e.raw.institution].join(" ")));}
  if(state.mapYearFrom)rows=rows.filter(e=>String(e.date).slice(0,4)>=state.mapYearFrom);
  if(state.mapYearTo)rows=rows.filter(e=>String(e.date).slice(0,4)<=state.mapYearTo);
  state.mapRows=rows.sort((a,b)=>String(b.date).localeCompare(String(a.date)));
  const newsCount=state.news.length,originalCount=state.rawHeadlineCount||newsCount,
        located=state.news.filter(e=>Number.isFinite(e.map_latitude)&&Number.isFinite(e.map_longitude)).length;
  $("#mapCoverage").innerHTML='<div class="coverage-number"><strong>'+originalCount.toLocaleString()+'</strong><span>indexed headlines</span></div>'+
   '<div class="coverage-number"><strong>'+newsCount.toLocaleString()+'</strong><span>reporting groups</span></div>'+
   '<div class="coverage-number"><strong>'+located.toLocaleString()+'</strong><span>groups with city mentions</span></div>'+
   '<p>The archive remains available even when the basemap cannot load.</p>';
  $("#mapCaption").textContent="Map library unavailable. Research titles and original links remain available.";
  $("#mapClusterCount").textContent="Map unavailable; use the article browser.";
  $("#map").textContent="Map tiles unavailable. Browse and filter every article on the right.";
  refreshMapList();
  return;
 }
 const newsTopics=[...new Set(state.news.flatMap(x=>[x.category,...(x.fraud_themes||[])]).filter(Boolean))].sort();
 if(newsTopics.length){
  const current=state.mapTopic||$("#mapTopic").value;
  $("#mapTopic").innerHTML='<option value="">All topics</option>'+newsTopics.map(x=>'<option value="'+escapeHTML(x)+'">'+escapeHTML(x)+'</option>').join("");
  if(newsTopics.includes(current))$("#mapTopic").value=current;
 }
 const availableYears=[...new Set([...state.news,...state.events,...state.incidents,...state.globalEvents]
    .map(x=>String(x.published_at||x.reported_at||"").slice(0,4))
    .filter(y=>/^20\d{2}$/.test(y)))].sort();
 if(availableYears.length){
  const yearOptions=availableYears.map(y=>'<option value="'+y+'">'+y+'</option>').join("");
  $("#mapYearFrom").innerHTML='<option value="">From any year</option>'+yearOptions;
  $("#mapYearTo").innerHTML='<option value="">Through latest</option>'+yearOptions;
  $("#mapYearFrom").value=state.mapYearFrom;
  $("#mapYearTo").value=state.mapYearTo;
 }
 if(!state.map){
  $("#map").replaceChildren();
  state.map=L.map("map",{zoomControl:false,minZoom:2,maxZoom:13,scrollWheelZoom:false,preferCanvas:true}).setView([24,0],2);
  L.control.zoom({position:"bottomright"}).addTo(state.map);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{
   maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
  }).addTo(state.map);
  state.layer=L.layerGroup().addTo(state.map);
  state.map.on("zoomend",renderMapClusters);
  const provinceSelect=$("#mapProvince");
  provinceSelect.innerHTML='<option value="">All provinces</option>'+Object.entries(provinces).sort((a,b)=>a[1].localeCompare(b[1])).map(([code,name])=>'<option value="'+escapeHTML(code)+'">'+escapeHTML(name)+'</option>').join("");
 }
 const layers=state.mapMode;
 const showReg=["all","enforcement","major"].includes(layers);
 const showNews=["all","news"].includes(layers);
 const showCases=["all","news"].includes(layers);
 const norm=v=>String(v||"").trim().toLowerCase();
 const focus=new Set([norm(state.clientFocus)]);
 const found=state.entityAliases.find(x=>norm(x.name)===norm(state.clientFocus)||(x.aliases||[]).some(a=>norm(a)===norm(state.clientFocus)));
 if(found)for(const name of [found.name,...(found.aliases||[])])focus.add(norm(name));
 const matchesClient=e=>!state.clientFocus||focus.has(norm(e.institution))||
  (e.banks_mentioned_in_headline||[]).some(n=>focus.has(norm(n)))||
  (e.organizations_mentioned_in_headline||[]).some(n=>focus.has(norm(n)));
 const inDate=e=>{
  const dt=String(e.published_at||e.reported_at||"");
  const yr=dt.slice(0,4);
  return (!state.mapMonth||dt.startsWith(state.mapMonth))&&
    (!state.mapYearFrom||yr>=state.mapYearFrom)&&
    (!state.mapYearTo||yr<=state.mapYearTo);
 };
 const matchTopic=e=>!state.mapTopic||e.category===state.mapTopic||e.fraud_type===state.mapTopic||(e.fraud_themes||[]).includes(state.mapTopic);
 let records=[];
 if(showNews)records.push(...state.news.filter(e=>inDate(e)&&matchTopic(e)&&matchesClient(e)).map(e=>mapRecord("news",e)));
 if(showCases)records.push(...state.incidents.filter(e=>inDate(e)&&matchTopic(e)&&matchesClient(e)).map(e=>mapRecord("case",e)));
 if(showReg)records.push(...state.events.filter(e=>inDate(e)&&matchTopic(e)&&matchesClient(e)&&
  (layers!=="major"||Number(e.penalty_cad)>=1000000)).map(e=>mapRecord("reg",e)));
 if(showReg&&layers!=="major")records.push(...state.globalEvents.filter(e=>inDate(e)&&
  (!state.mapTopic||e.category===state.mapTopic)&&matchesClient(e)).map(e=>mapRecord("global",e)));
 if(state.mapCountry)records=records.filter(x=>x.countryCode===state.mapCountry);
 if(state.mapAgency)records=records.filter(x=>x.agency===state.mapAgency);
 if(state.mapProvince)records=records.filter(x=>x.countryCode!=="CA"||x.province===state.mapProvince);
 if(state.globalPattern){
  const regex=new RegExp(state.globalPattern,"i");
  records=records.filter(x=>regex.test([x.title,x.raw.category,x.raw.institution].join(" ")));
 }
 const query=($("#mapStorySearch")?.value||"").trim().toLowerCase();
 if(query)records=records.filter(x=>[x.searchText,x.publisher,x.location].some(y=>String(y||"").toLowerCase().includes(query)));
 records.sort((x,y)=>String(y.date).localeCompare(String(x.date)));
 state.mapRows=records;
 const byYear={};
 for(const rec of records){
  const y=String(rec.date||"").slice(0,4);
  if(rec.kind==="news"&&/^20\d{2}$/.test(y))byYear[y]=(byYear[y]||0)+1;
 }
 const allYears=[...new Set([...Object.keys(byYear),...state.news.map(x=>String(x.published_at||"").slice(0,4))])]
   .filter(y=>/^20\d{2}$/.test(y)).sort();
 const trendMax=Math.max(1,...Object.values(byYear));
 $("#mapFilteredTrend").innerHTML='<strong>Publication-year coverage in this view</strong><div class="map-year-bars">'+
  allYears.map(y=>'<div class="map-year-unit"><span>'+y+'</span><div title="'+(byYear[y]||0)+' grouped reporting titles"><i style="height:'+Math.max(2,100*(byYear[y]||0)/trendMax).toFixed(1)+'%"></i></div><b>'+(byYear[y]||0)+'</b></div>').join("")+'</div>'+
  '<small>Grouped reporting headlines, not fraud occurrence dates or incidence rates.</small>';
 const mapped=records.filter(x=>x.lat!==null).length,unmapped=records.length-mapped;
 const headlineAll=state.news.length,rawHeadlineTotal=state.rawHeadlineCount||headlineAll,
       geoNews=state.news.filter(x=>Number.isFinite(x.map_latitude)&&Number.isFinite(x.map_longitude)).length;
 $("#mapCoverage").innerHTML=
  '<div class="coverage-number"><strong>'+rawHeadlineTotal.toLocaleString("en-CA")+'</strong><span>indexed article headlines</span></div>'+
  '<div class="coverage-number"><strong>'+headlineAll.toLocaleString("en-CA")+'</strong><span>collapsed reporting groups</span></div>'+
  '<div class="coverage-number"><strong>'+geoNews.toLocaleString("en-CA")+'</strong><span>groups with city mentions</span></div>'+
  '<p>'+Math.max(0,headlineAll-geoNews).toLocaleString("en-CA")+' groups lack supported locations. Grouping is provisional, not a verified incident match.</p>';
 $("#mapCaption").textContent=mapped.toLocaleString()+" mapped / "+records.length.toLocaleString()+" records in this view · "+
  (state.mapProvince?provinces[state.mapProvince]+" · ":"")+
  (state.mapMonth?state.mapMonth+" · ":"")+  (state.mapTopic?state.mapTopic+" · ":"")+
  (state.mapYearFrom||state.mapYearTo?(state.mapYearFrom||"earliest")+"–"+(state.mapYearTo||"latest")+" · ":"")+
  (state.clientFocus?"Organization: "+state.clientFocus+" · ":"")+
  (state.mapCountry?"Jurisdiction: "+(state.worldCountries.find(x=>x.code===state.mapCountry)?.name||state.mapCountry)+" · ":"Worldwide · ")+
  (state.mapAgency?"Agency: "+state.mapAgency+" · ":"")+
  "International pins show regulator jurisdiction, not crime location.";
 if(state.mapSideScope==="selected")state.mapSideScope="all";
 state.mapSelectedIds=null;
 refreshMapList();
 renderMapClusters();
 if((state.mapProvince||state.mapCountry||state.clientFocus)&&mapped){
  const pts=records.filter(x=>x.lat!==null).map(x=>[x.lat,x.lon]);
  state.map.fitBounds(L.latLngBounds(pts).pad(.25),{maxZoom:7,padding:[28,28]});
 }
 // Otherwise preserve the analyst's zoom and location. Only Reset moves
 // back to a national view; reloading/filtering must not unexpectedly jump.
 setTimeout(()=>state.map.invalidateSize(),60);
}

function renderEvents(){
 const e=state.events;
 const select=(id,vals,placeholder)=>{const el=$(id);const old=el.value;el.innerHTML='<option value="">'+placeholder+"</option>"+vals.map(x=>'<option value="'+escapeHTML(x)+'">'+escapeHTML(id==="#provinceFilter"?(provinces[x]||x):x)+"</option>").join("");el.value=old;};
 select("#sourceFilter",[...new Set(e.map(x=>x.source).filter(Boolean))].sort(),"All regulators");
 select("#provinceFilter",[...new Set(e.map(x=>x.province).filter(Boolean))].sort(),"All provinces");
 select("#statusFilter",[...new Set(e.map(x=>x.status).filter(Boolean))].sort(),"All legal statuses");
 filterEvents();
}
function filterEvents(){
 const q=$("#search").value.toLowerCase().trim();
 const matches=state.events.filter(e=>(!q||[e.title,e.institution,e.summary,e.category].some(s=>(s||"").toLowerCase().includes(q)))&&(!$("#sourceFilter").value||e.source===$("#sourceFilter").value)&&(!$("#provinceFilter").value||e.province===$("#provinceFilter").value)&&(!$("#statusFilter").value||e.status===$("#statusFilter").value));
 $("#resultCount").textContent=matches.length+" matching records";
 $("#eventRows").innerHTML=matches.length?matches.map(rowHTML).join(""):'<div class="empty">No records match these filters.</div>';
}
function renderInstitutions(){
 const groups=eventsByInstitution();
 $("#institutionRows").innerHTML=groups.length?groups.map(g=>{
 const last=g.events[0];const topics=[...new Set(g.events.map(e=>e.category))];
 return '<div class="institution" data-institution="'+escapeHTML(g.name)+'" tabindex="0" role="button"><div><h3>'+escapeHTML(g.name)+'</h3><p>'+g.events.length+' public notice(s) · '+escapeHTML(topics.join(" · "))+' · Last published '+escapeHTML(date(last.published_at))+'</p></div><div class="score">'+g.events.length+'<small>SOURCED EVENTS</small></div></div>';
 }).join(""):'<div class="empty">Institution profiles will appear when named regulatory records are collected.</div>';
}
function renderSources(){
 const rows=["FINTRAC","FCAC"].map(name=>{
 const s=state.status.sources?.[name];const url=name==="FINTRAC"?"https://fintrac-canafe.canada.ca/pen/4-eng":"https://www.canada.ca/en/financial-consumer-agency/services/industry/commissioner-decisions.html";
 return '<div class="source-row"><div><strong>'+name+'</strong><small>'+escapeHTML(s?.status||"Awaiting first run")+(s?.scanned!=null?" · "+s.scanned+" notices scanned":"")+'</small>'+(s?.error?'<small>'+escapeHTML(s.error)+'</small>':"")+'</div><a href="'+url+'" rel="noopener" target="_blank">Official source ↗</a></div>';
 });
 $("#sourceRows").innerHTML=rows.join("")+'<div class="source-row"><div><strong>Snapshot status</strong><small>Last collection: '+escapeHTML(state.status.last_completed_at||"Not yet available")+' · '+state.events.length+' stored events</small></div><a href="https://github.com/khaled-agi/Signal-North/actions">Workflow logs ↗</a></div>';
}
function openDrawer(html){$("#drawerBody").innerHTML=html;$("#overlay").classList.remove("hidden");document.body.style.overflow="hidden";}
function closeDrawer(){$("#overlay").classList.add("hidden");document.body.style.overflow="";}
function details(e){
 const rows=[["Institution",e.institution],["Institution role","Subject of published enforcement notice"],["Regulator",e.source],["Category",e.category],["Legal status",e.status],["Published",date(e.published_at)],["Action date",date(e.event_at)],["Penalty amount (CAD)",currency(e.penalty_cad)],["Location",e.location||"Not independently located"],["Source tier",e.evidence_level]];
 openDrawer('<div class="eyebrow">SOURCE-LINKED CASE</div><h2>'+escapeHTML(e.title)+'</h2><span class="pill">'+escapeHTML(e.status||"Published notice")+'</span><h3>Regulator summary</h3><p>'+escapeHTML(e.summary||"No additional summary available")+'</p><h3>Evidence details</h3><dl>'+rows.map(row=>'<dt>'+escapeHTML(row[0])+'</dt><dd>'+escapeHTML(row[1]??"Not reported")+'</dd>').join("")+'</dl><div class="warning">A published enforcement notice is not proof of additional unrelated misconduct or current consulting need. Check the original for updates, appeals, or corrections.</div>'+sourceLink(e.source_url));
}
function institutionDetail(name){
 const events=state.events.filter(e=>e.institution===name);
 openDrawer('<div class="eyebrow">INSTITUTION RESEARCH</div><h2>'+escapeHTML(name)+'</h2><p>Public enforcement information only. The presence of multiple notices is not a measure of institutional fraud prevalence.</p><h3>Topics to investigate</h3><p>'+escapeHTML([...new Set(events.map(e=>e.category))].join(" · "))+'</p><h3>Linked regulatory notices</h3>'+events.map(e=>'<p><strong>'+escapeHTML(date(e.published_at))+'</strong> — '+escapeHTML(e.title)+'<br><a href="'+escapeHTML(e.source_url)+'" rel="noopener" target="_blank">Source ↗</a></p>').join(""));
}
async function load(){
 try{
  const [a,b]=await Promise.all([
   fetch("./data/events.json?ts="+Date.now(),{cache:"no-store"}),
   fetch("./data/status.json?ts="+Date.now(),{cache:"no-store"})
  ]);
  if(!a.ok||!b.ok)throw new Error("Source snapshot not yet available ("+a.status+", "+b.status+")");
  const events=await a.json();state.events=Array.isArray(events)?events:(events.events||[]);
  state.events.sort((x,y)=>String(y.published_at||"").localeCompare(String(x.published_at||"")));
  state.status=await b.json();
  $("#error").classList.add("hidden");renderMetrics();renderEvents();renderInstitutions();renderSources();initMap();
 }catch(err){$("#error").classList.remove("hidden");$("#error").textContent="Unable to load published data: "+err.message;}
}
document.addEventListener("click",e=>{
 const story=e.target.closest("[data-story]");
 if(story){
  e.preventDefault();
  window.dispatchEvent(new CustomEvent("signalnorth:openstory",{detail:{id:story.dataset.story}}));
  return;
 }
 const focus=e.target.closest("[data-mapfocus]");
 if(focus){
   // From the News Explorer: clear conflicting filters and show the matching
   // marker rather than jumping to an invisible map.
   if(state.mapProvince||state.mapMonth||state.mapTopic||state.mapYearFrom||state.mapYearTo||state.clientFocus||state.mapMode!=="all"){
    state.mapProvince="";$("#mapProvince").value="";
    state.mapMonth="";$("#mapMonth").value="";
    state.mapTopic="";$("#mapTopic").value="";
    state.mapYearFrom="";$("#mapYearFrom").value="";
    state.mapYearTo="";$("#mapYearTo").value="";
    state.clientFocus="";state.mapCountry="CA";$("#mapCountry").value="CA";state.mapAgency="";$("#mapAgency").value="";state.globalPattern="";state.mapMode="all";
    document.querySelectorAll("[data-mapmode]").forEach(b=>b.classList.toggle("active",b.dataset.mapmode==="all"));
    initMap();
   }
   $("#mapStorySearch").value="";
   state.mapSideScope="all";
   initMap();
   switchTab("overview");
   const selected=state.mapRows?.find(x=>x.id===focus.dataset.mapfocus);
   if(selected?.lat!==null&&selected){
    state.map.setView([selected.lat,selected.lon],Math.max(state.map.getZoom(),8),{animate:false});
    const pin=state.mapMarkers.get(selected.id);
    if(pin){pin.openPopup();state.mapSideScope="selected";state.mapSelectedIds=new Set([selected.id]);refreshMapList();}
    $("#map").scrollIntoView({behavior:"smooth",block:"center"});
   }
   return;
 }
 const layer=e.target.closest("[data-mapmode]");
 if(layer){
  state.mapMode=layer.dataset.mapmode;
  document.querySelectorAll("[data-mapmode]").forEach(b=>b.classList.toggle("active",b.dataset.mapmode===state.mapMode));
  initMap();
  return;
 }
 const tab=e.target.closest("[data-tab],[data-to]");if(tab){switchTab(tab.dataset.tab||tab.dataset.to);return;}
 const event=e.target.closest("[data-event],[data-popup]");if(event){e.preventDefault();const record=state.events.find(x=>x.id===(event.dataset.event||event.dataset.popup));if(record)details(record);return;}
 if(e.target.closest("[data-open-connection]"))return;
 const inst=e.target.closest("[data-institution]");if(inst)institutionDetail(inst.dataset.institution);
});
document.addEventListener("keydown",e=>{
 if(e.key==="Escape")closeDrawer();
 if((e.key==="Enter"||e.key===" ")&&e.target.matches("[data-event], [data-institution]")){e.preventDefault();e.target.click();}
});
for(const id of ["search","sourceFilter","provinceFilter","statusFilter"]){$("#"+id).addEventListener(id==="search"?"input":"change",filterEvents);}
$("#close").addEventListener("click",closeDrawer);
$("#overlay").addEventListener("click",e=>{if(e.target.id==="overlay")closeDrawer();});
$("#reload").addEventListener("click",()=>{load(); window.dispatchEvent(new Event("signalnorth:refresh"));});
$("#mapReset").addEventListener("click",()=>{state.mapProvince="";$("#mapProvince").value="";state.mapMonth="";$("#mapMonth").value="";state.mapTopic="";$("#mapTopic").value="";state.mapYearFrom="";$("#mapYearFrom").value="";state.mapYearTo="";$("#mapYearTo").value="";state.clientFocus="";state.mapCountry="CA";$("#mapCountry").value="CA";state.mapAgency="";$("#mapAgency").value="";state.globalPattern="";state.mapMode="all";document.querySelectorAll("[data-mapmode]").forEach(b=>b.classList.toggle("active",b.dataset.mapmode==="all"));$("#mapStorySearch").value="";state.mapSideVisible=100;initMap();if(state.map)state.map.setView([55,-96],4);});
$("#mapCountry").addEventListener("change",e=>{
 state.mapCountry=e.target.value;state.mapProvince="";$("#mapProvince").value="";state.globalPattern="";
 state.mapSideVisible=100;initMap();
});
$("#mapAgency").addEventListener("change",e=>{state.mapAgency=e.target.value;state.mapSideVisible=100;initMap();});
$("#worldView").addEventListener("click",()=>{
 state.mapCountry="";$("#mapCountry").value="";state.mapAgency="";$("#mapAgency").value="";
 state.mapProvince="";$("#mapProvince").value="";state.mapMonth="";$("#mapMonth").value="";
 state.mapTopic="";$("#mapTopic").value="";state.mapYearFrom="";$("#mapYearFrom").value="";
 state.mapYearTo="";$("#mapYearTo").value="";state.globalPattern="";state.clientFocus="";
 state.mapMode="all";document.querySelectorAll("[data-mapmode]").forEach(b=>b.classList.toggle("active",b.dataset.mapmode==="all"));
 initMap();if(state.map)state.map.setView([24,0],2);
});
$("#mapProvince").addEventListener("change",e=>{
 state.mapProvince=e.target.value;
 if(state.mapProvince){state.mapCountry="CA";$("#mapCountry").value="CA";}
 initMap();
});
$("#mapMonth").addEventListener("change",e=>{state.mapMonth=e.target.value;initMap();});
$("#mapTopic").addEventListener("change",e=>{state.mapTopic=e.target.value;state.mapSideVisible=100;initMap();});
$("#mapYearFrom").addEventListener("change",e=>{state.mapYearFrom=e.target.value;state.mapSideVisible=100;initMap();});
$("#mapYearTo").addEventListener("change",e=>{state.mapYearTo=e.target.value;state.mapSideVisible=100;initMap();});
$("#mapClearMonth").addEventListener("click",()=>{state.mapMonth="";$("#mapMonth").value="";initMap();});
$("#mapCountMode").addEventListener("change",e=>{state.mapCountMode=e.target.value;renderMapClusters();});
$("#mapStorySearch").addEventListener("input",()=>{state.mapSideVisible=100;initMap();});
$("#mapStoryScope").addEventListener("change",e=>{state.mapSideScope=e.target.value;state.mapSideVisible=100;refreshMapList();});
$("#mapStoryMore").addEventListener("click",()=>{state.mapSideVisible=(state.mapSideVisible||100)+100;refreshMapList();});
$("#mapStoryAll").addEventListener("click",()=>{state.mapSideVisible=Number.MAX_SAFE_INTEGER;refreshMapList();});
$("#mapStoryClear").addEventListener("click",()=>{state.mapSelectedIds=null;state.mapSideScope="all";refreshMapList();});

window.addEventListener("signalnorth:applytheme",event=>{
 const theme=String(event.detail?.theme||""),year=String(event.detail?.year||"");
 state.mapTopic=theme;
 state.mapYearFrom=year;
 state.mapYearTo=year;
 state.mapMonth="";
 state.clientFocus="";
 state.mapCountry="CA";
 state.mapProvince="";
 state.mapAgency="";
 state.globalPattern="";
 state.mapSideScope="all";
 state.mapSideVisible=100;
 state.mapMode="news";
 document.querySelectorAll("[data-mapmode]").forEach(b=>b.classList.toggle("active",b.dataset.mapmode==="news"));
 $("#mapTopic").value=theme;
 $("#mapYearFrom").value=year;
 $("#mapYearTo").value=year;
 $("#mapCountry").value="CA";
 $("#mapProvince").value="";
 $("#mapAgency").value="";
 $("#mapMonth").value="";
 $("#mapStorySearch").value="";
 initMap();
});
window.addEventListener("signalnorth:clientfocus",e=>{state.clientFocus=e.detail?.name||"";state.mapMode="all";document.querySelectorAll("[data-mapmode]").forEach(b=>b.classList.toggle("active",b.dataset.mapmode==="all"));initMap();});
window.addEventListener("signalnorth:aliasesready",event=>{state.entityAliases=event.detail?.institutions||[];renderMetrics();initMap();});
window.addEventListener("signalnorth:globalready",event=>{
 state.globalEvents=event.detail?.events||[];
 state.worldCountries=event.detail?.countries||[];
 state.globalHealth=event.detail?.health||{};
 renderMetrics();initMap();
});
window.addEventListener("signalnorth:globalentity",event=>{
 window.dispatchEvent(new CustomEvent("signalnorth:globalpattern",{detail:event.detail}));
});
window.addEventListener("signalnorth:globalpattern",event=>{
 state.globalPattern=event.detail?.pattern||"";
 state.mapCountry="";$("#mapCountry").value="";
 state.mapAgency="";$("#mapAgency").value="";state.clientFocus="";
 state.mapTopic="";$("#mapTopic").value="";
 state.mapMode="enforcement";document.querySelectorAll("[data-mapmode]").forEach(b=>b.classList.toggle("active",b.dataset.mapmode==="enforcement"));
 state.mapSideVisible=100;initMap();
});
window.addEventListener("signalnorth:newsready",event=>{state.news=event.detail?.leads||[];state.rawHeadlineCount=Number(event.detail?.rawHeadlineCount||state.news.length);renderMetrics();initMap();});
window.addEventListener("signalnorth:incidentsready",event=>{state.incidents=event.detail?.incidents||[];renderMetrics();initMap();});
window.addEventListener("signalnorth:mapready", () => { if(state.events.length) initMap(); });
load();
