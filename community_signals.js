"use strict";
/* Public, opt-in social signals are NEVER reviewed fraud cases. */
(() => {
  const byId=id=>document.getElementById(id);
  const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  let records=[],status={};
  function safeLink(url,platform){
    try{
      const u=new URL(url);
      if(u.protocol!=="https:")return "";
      if(platform==="reddit"&&u.hostname!=="www.reddit.com")return "";
      if(platform==="telegram"&&u.hostname!=="t.me")return "";
      return u.href;
    }catch{return "";}
  }
  const monthDate=s=>String(s||"").slice(0,10)||"Date unavailable";
  function render(){
    const selected=byId("communitySignalPlatform").value;
    const theme=byId("communitySignalTheme").value;
    const subset=records.filter(x=>(!selected||x.platform===selected)&&(!theme||x.topic===theme));
    byId("communitySignalCount").textContent=records.length+
      " unverified signal"+(records.length===1?"":"s")+" · past 7 days";
    const rs=status.sources?.reddit||{},ts=status.sources?.telegram||{};
    const labels={ok:"collecting",partial:"partial coverage",pending_approval:"awaiting approval",
      not_configured:"not connected",no_channels:"no approved channels",api_error:"collector error",
      webhook_conflict:"bot webhook in use",invalid_token_format:"configuration error"};
    byId("communitySignalHealth").textContent="Reddit: "+(labels[rs.status]||rs.status||"not connected")+
      " · Telegram: "+(labels[ts.status]||ts.status||"not connected")+
      " · Last collector: "+monthDate(status.last_completed_at);
    byId("communitySignalRows").innerHTML=subset.length?subset.slice(0,12).map(x=>{
      const url=safeLink(x.source_url,x.platform);
      const names=(x.institutions_mentioned||[]).slice(0,5);
      return '<article class="community-signal-card"><div class="community-signal-meta">'+
        esc(x.platform==="reddit"?"Reddit":"Telegram")+" · "+esc(x.community)+" · "+esc(monthDate(x.published_at))+
        '</div><strong>'+esc(x.label||"Public scam-related signal")+'</strong>'+
        '<div class="community-signal-tags"><span>'+esc(x.topic||"Unclassified")+'</span>'+
        (names.length?'<span>Mentioned: '+esc(names.join(", "))+'</span>':"")+
        (x.country_hint?'<span>Geographic clue: '+esc(x.country_hint)+'</span>':"")+
        '</div><div class="community-signal-foot">Unverified public post · No author or raw text stored'+
        (url?' · <a target="_blank" rel="noopener noreferrer" href="'+esc(url)+'">Open original post ↗</a>':"")+'</div></article>';
    }).join(""):'<div class="community-signal-empty"><strong>No matching social signals collected yet.</strong><p>'+
      (records.length?"Try clearing the filters.":"Reddit requires approved API access. Telegram requires a dedicated bot connected to whitelisted public channels. No posts are fabricated or scraped without permission.")+
      '</p></div>';
  }
  async function load(){
    const names=["community_signals.json","community_status.json"];
    const data=await Promise.allSettled(names.map(async name=>{
      const r=await fetch("./data/"+name+"?v="+Date.now(),{cache:"no-store"});
      if(!r.ok)throw new Error(name+" returned "+r.status);
      return r.json();
    }));
    records=data[0].status==="fulfilled"&&Array.isArray(data[0].value.signals)?
      data[0].value.signals.filter(x=>x.evidence_status==="unverified_social_signal"):[];
    status=data[1].status==="fulfilled"?data[1].value:{};
    const platform=byId("communitySignalPlatform").value;
    const topic=byId("communitySignalTheme").value;
    const themes=[...new Set(records.map(x=>x.topic).filter(Boolean))].sort();
    byId("communitySignalTheme").innerHTML='<option value="">All scam methods</option>'+themes.map(x=>
      '<option value="'+esc(x)+'">'+esc(x)+'</option>').join("");
    byId("communitySignalTheme").value=themes.includes(topic)?topic:"";
    byId("communitySignalPlatform").value=platform;
    render();
  }
  document.addEventListener("DOMContentLoaded",()=>{
    if(!byId("communitySignalRows"))return;
    byId("communitySignalPlatform").addEventListener("change",render);
    byId("communitySignalTheme").addEventListener("change",render);
    window.addEventListener("signalnorth:refresh",load);
    load();
  });
})();
