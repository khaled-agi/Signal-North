"use strict";
/* Signal North data loader.
 *
 * Every module fetches ./data/*.json on its own. This shim sits in front of
 * window.fetch for those requests only and:
 *  1. versions URLs by deploy build instead of Date.now(), so browsers can
 *     cache data between visits (each deploy gets a fresh build id);
 *  2. shares one request when several modules ask for the same file;
 *  3. holds back data that only a non-opening tab needs until that tab opens
 *     (roughly 40 MB of the 52 MB the page used to download up front).
 * Non-data requests pass straight through. "Refresh snapshot" bypasses caches.
 */
(() => {
  const nativeFetch = window.fetch.bind(window);
  const meta = document.querySelector('meta[name="sn-build"]');
  const raw = meta && meta.content;
  const BUILD = raw && !raw.startsWith("__") ? raw : "dev-" + Date.now();

  // file -> tabs that render it. Files not listed load immediately.
  const DEFER = {};
  const assign = (tabs, files) => files.forEach(f => { DEFER[f] = tabs; });
  assign(["connections", "clients"], ["institution_intelligence.json", "review_queue.json"]);
  assign(["clients"], ["article_index.json", "news_archive.json"]);
  assign(["fraud"], [
    "cfpb_complaints.json", "cfpb_complaints_status.json", "cfpb_monthly_history.json",
    "cfpb_monthly_history_status.json", "cafc_aggregates.json", "cafc_source_status.json",
    "amf_quebec_entities.json", "bcsc_official_rss.json", "osfi_institutions.json",
    "fintrac_penalties_official.json", "obsi_annual_banking.json", "obsi_public_report_catalog.json",
    "obsi_firm_complaints.json", "ciro_enforcement_activity.json", "ciro_named_enforcement.json",
    "canadian_regulatory_leads.json", "canadian_enforcement_verified.json",
    "canadian_source_registry.json", "bank_complaint_disclosures.json"]);
  assign(["sources"], [
    "us_occ_enforcement_actions.json", "us_occ_enforcement_health.json", "us_ofac_sdn_entities.json",
    "us_ofac_source_health.json", "us_sec_litigation_releases.json", "us_sec_source_health.json",
    "uk_sanctions_entities.json", "uk_sanctions_source_health.json",
    "us_regulatory_signal_publications.json"]);
  assign(["institutions"], [
    "us_fdic_institutions.json", "us_fdic_failures.json", "us_fdic_source_health.json",
    "us_ncua_credit_unions.json", "us_ncua_source_health.json"]);
  assign(["incidents", "sources"], ["event_review_candidates.json", "reviewed_events.json"]);
  assign(["reports"], ["research_library.json"]);
  // Tiny status files (community, health) stay eager: deferring them saves
  // nothing and other panels read them before their tab is opened.

  const opened = new Set(["overview"]);
  const waiting = new Map();        // tab -> [resolve]
  const shared = new Map();         // path -> Promise<Response>
  let bust = "";
  const stats = { requested: 0, network: 0, deferred: new Set(), released: new Set() };

  function release(tab) {
    if (!tab || opened.has(tab)) return;
    opened.add(tab);
    (waiting.get(tab) || []).forEach(go => go());
    waiting.delete(tab);
  }
  function whenOpen(tabs) {
    if (tabs.some(t => opened.has(t))) return Promise.resolve();
    return new Promise(go => tabs.forEach(t => {
      if (!waiting.has(t)) waiting.set(t, []);
      waiting.get(t).push(go);
    }));
  }
  function dataPath(input) {
    const href = typeof input === "string" ? input : input instanceof URL ? input.href : input && input.url;
    if (!href) return null;
    let url;
    try { url = new URL(href, location.href); } catch { return null; }
    if (url.origin !== location.origin) return null;
    const m = url.pathname.match(/\/data\/(.+\.json)$/);
    return m ? m[1] : null;
  }
  function load(path) {
    stats.requested++;
    if (shared.has(path)) return shared.get(path);
    const file = path.split("/").pop();
    const tabs = DEFER[file];
    if (tabs && !tabs.some(t => opened.has(t))) stats.deferred.add(file);
    const gate = tabs ? whenOpen(tabs) : Promise.resolve();
    const base = new URL("./data/" + path, document.baseURI);
    base.searchParams.set("v", BUILD + bust);
    const p = gate.then(() => {
      if (stats.deferred.has(file)) stats.released.add(file);
      stats.network++;
      return nativeFetch(base.href, bust ? { cache: "reload" } : {});
    }).then(res => {
      if (!res.ok) shared.delete(path);   // let a later call retry failures
      return res;
    }, err => { shared.delete(path); throw err; });
    shared.set(path, p);
    return p;
  }

  window.fetch = function (input, init) {
    const path = dataPath(input);
    if (!path || (init && init.method && init.method.toUpperCase() !== "GET")) return nativeFetch(input, init);
    return load(path).then(res => res.clone());
  };

  // Release a tab's data as soon as the user heads there.
  document.addEventListener("click", e => {
    if (e.target.closest && e.target.closest("#reload")) { shared.clear(); bust = "-r" + Date.now(); }
    const t = e.target.closest && e.target.closest("[data-tab],[data-to]");
    if (t) release(t.dataset.tab || t.dataset.to);
  }, true);
  const watch = () => {
    document.querySelectorAll(".tab").forEach(el => {
      if (!el.classList.contains("hidden")) release(el.id);
      new MutationObserver(() => { if (!el.classList.contains("hidden")) release(el.id); })
        .observe(el, { attributes: true, attributeFilter: ["class"] });
    });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", watch);
  else watch();

  // "Refresh snapshot" must fetch the newest deploy, not the cached copy.
  window.addEventListener("signalnorth:refresh", () => { shared.clear(); bust = "-r" + Date.now(); }, true);

  window.SignalNorthData = {
    build: BUILD,
    json: path => window.fetch("./data/" + path).then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }),
    release,
    stats: () => ({ requested: stats.requested, network: stats.network,
      deferred: [...stats.deferred].filter(f => !stats.released.has(f)), opened: [...opened] }),
  };
})();
