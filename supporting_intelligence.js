"use strict";
/* Routes unverified, grouped reporting to relevant homepage panels.
   A classification is NEVER an assertion of wrongdoing or independent review. */
(function (root) {
  const CRIME = /\b(fraud|fraude|scam|scams|phishing|ransomware|money laundering|blanchiment|identity theft|account takeover|stolen|defrauded|embezzl|cyberattack|crypto|investment scheme)\b/i;
  const PERSON = /\b(victim|victims|customer|customers|client|clients|resident|residents|family|woman|man|senior|seniors|scammed|defrauded|lost|loses|stolen|unauthori[sz]ed|drained|charged|arrested|convicted|sentenced|found guilty|pleads guilty|pleaded guilty|police investigate|police investigating)\b/i;
  const ACTION = /\b(fined|fine|fines|penalty|penalties|settlement|settles|settled|sanction|sanctions|consent order|cease.and.desist|enforcement action|ordered to pay|disciplin(?:e|ary)|sues|lawsuit|charges filed|administrative monetary penalty)\b/i;
  const REGULATOR = /\b(FINTRAC|FCAC|FINCEN|CFPB|OSC|CIRO|AMF|OSFI|SEC|CFTC|OCC|FDIC|FINRA|regulator|regulatory|securities commission|consumer protection agency)\b/i;
  const POLICY = /\b(regulation|regulations|regulatory|legislation|compliance rules|guidance|consultation|rulemaking|policy change|new rules|proposed rules|warning issued|investor alert|advisory issued|regulatory alert)\b/i;

  function evidenceText(item) {
    return [item.title || "", item.category || "", ...(Array.isArray(item.fraud_themes) ? item.fraud_themes : []),
      ...(Array.isArray(item.headline_variations) ? item.headline_variations.map(x => x.title || "") : [])].join(" ");
  }

  function sections(item) {
    const text = evidenceText(item || {});
    const enforcement = ACTION.test(text) && (REGULATOR.test(text) || /\b(fined|penalty|penalties|consent order|enforcement action|settlement)\b/i.test(text));
    const regulatory = enforcement || REGULATOR.test(text) || POLICY.test(text);
    const incident = !enforcement && (PERSON.test(text) || Boolean(item && item.headline_case_candidate)) &&
      (CRIME.test(text) || /\b(charged|arrested|convicted|sentenced|found guilty|stolen|unauthori[sz]ed)\b/i.test(text));
    const threat = !enforcement && CRIME.test(text);
    const out = [];
    if (incident) out.push("incidents");
    if (enforcement) out.push("enforcement");
    if (threat) out.push("fraud");
    if (regulatory) out.push("regulatory");
    return out;
  }

  function sourceUrl(item) {
    const possible = [item.url, ...(Array.isArray(item.article_links) ? item.article_links.map(x => x.url) : []),
      ...(Array.isArray(item.headline_variations) ? item.headline_variations.map(x => x.url) : [])];
    return possible.find(url => typeof url === "string" && /^https:\/\//i.test(url)) || "";
  }

  function select(items, section, limit = 4, now = Date.now(), windowDays = 90) {
    if (!Array.isArray(items) || !["incidents", "enforcement", "fraud", "regulatory"].includes(section)) return [];
    const seen = new Set();
    return items.filter(item => {
      if (!item || !sourceUrl(item) || !sections(item).includes(section)) return false;
      const date = Date.parse(item.published_at || "");
      if (!Number.isFinite(date) || date > now + 86400000 || date < now - windowDays * 86400000) return false;
      const id = String(item.id || item.title || "").trim().toLowerCase();
      if (!id || seen.has(id)) return false;
      seen.add(id);
      return true;
    }).sort((a,b) => Date.parse(b.published_at) - Date.parse(a.published_at) ||
      Number(b.source_count || 1) - Number(a.source_count || 1))
      .slice(0, Math.max(0, Math.min(12, Math.floor(Number(limit) || 0))));
  }

  const api = Object.freeze({ sections, select, sourceUrl });
  root.SignalNorthSupportingIntelligence = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
