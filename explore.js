"use strict";
/* Global search + profile pages (institution, country, scam pattern).
 * Routes: #/i/<id>  #/c/<CODE>  #/t/<slug>  — shareable and back-button aware.
 * Profiles regroup already-published records; every row keeps its source link
 * and evidence level. A name in a headline is never presented as a finding.
 */
(() => {
  const $ = s => document.querySelector(s);
  const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fold = v => String(v ?? "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const json = path => (window.SignalNorthData ? window.SignalNorthData.json(path)
    : fetch("./data/" + path).then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }));
  const safeUrl = u => { try { const x = new URL(u); return x.protocol === "https:" ? x.href : ""; } catch { return ""; } };
  const fmt = n => Number(n || 0).toLocaleString("en-CA");
  const plural = (n, word) => n ? fmt(n) + " " + word + (n === 1 ? "" : "s") : "";
  const money = (v, cur) => v == null ? "" : (cur || "CAD") + " " + Number(v).toLocaleString("en-CA", { maximumFractionDigits: 0 });

  const KIND = {
    enforcement: { label: "Regulator action", cls: "k-enf" },
    regulator_publication: { label: "Regulator publication", cls: "k-pub" },
    incident: { label: "Reviewed case", cls: "k-case" },
    headline: { label: "News mention", cls: "k-news" },
  };
  const KIND_ORDER = ["enforcement", "regulator_publication", "incident", "headline"];
  const ROLE = {
    official_entity_name_in_headline: "Official name appears in headline",
    mentioned_in_headline_only: "Named in headline",
    official_entity_name_in_regulator_publication: "Named in regulator publication title",
    subject_of_enforcement: "Subject of regulatory action",
    customer_financial_institution: "Customer's bank",
    institution_impersonated: "Institution impersonated",
  };
  const TYPE = { i: "Organizations", c: "Countries", t: "Scam patterns", e: "Regulator actions", h: "Canadian news", w: "Worldwide news" };

  // ---------------------------------------------------------------- shell
  const header = $(".header");
  const box = document.createElement("div");
  box.className = "sn-search";
  box.innerHTML =
    '<label class="sn-search-field"><span class="sn-search-icon" aria-hidden="true">⌕</span>' +
    '<input id="snSearch" type="search" autocomplete="off" spellcheck="false" ' +
    'placeholder="Search organizations, countries, scam patterns, news…" aria-label="Search Signal North" ' +
    'role="combobox" aria-expanded="false" aria-controls="snResults" aria-autocomplete="list">' +
    '<kbd class="sn-kbd" aria-hidden="true">' + (/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘K" : "Ctrl K") + "</kbd></label>" +
    '<div id="snResults" class="sn-results" role="listbox" hidden></div>';
  if (header) header.insertBefore(box, header.querySelector(".header-right"));
  const input = $("#snSearch"), results = $("#snResults");

  const panel = document.createElement("div");
  panel.id = "snProfile";
  panel.className = "sn-profile-backdrop";
  panel.hidden = true;
  panel.innerHTML = '<section class="sn-profile" role="dialog" aria-modal="true" aria-labelledby="snProfileTitle"><div class="sn-profile-inner" id="snProfileBody"></div></section>';
  document.body.appendChild(panel);
  const body = $("#snProfileBody");

  // ------------------------------------------------------- shared lookups
  let countries = new Map();          // code -> name
  let countryByName = new Map();      // folded name -> code
  json("explore/entities.json").then(d => {
    for (const c of d.countries || []) { countries.set(c.code, c.name); countryByName.set(fold(c.name), c.code); }
    // Map client-focus aliases without downloading the full institution graph.
    window.dispatchEvent(new CustomEvent("signalnorth:aliasesready", { detail: { institutions: d.institutions || [] } }));
  }).catch(() => {});

  // --------------------------------------------------------------- search
  let index = null, registry = null, loading = null, active = -1, shown = [];
  function ensureIndex() {
    if (loading) return loading;
    loading = Promise.all([
      json("explore/search.json").then(d => { index = prep(d.rows); }),
      json("explore/search_registry.json").then(d => { registry = prep(d.rows); }).catch(() => { registry = []; }),
    ]).then(() => render());
    loading.catch(() => { results.innerHTML = '<div class="sn-empty">Search is unavailable right now.</div>'; });
    return loading;
  }
  function prep(rows) {
    return rows.map(r => ({ type: r[0], id: r[1], label: r[2] || "", sub: r[3] || "", w: r[4] || 0,
      hay: fold(r[2] + " " + (r[5] || "")), target: r[6] }));
  }
  function search(q) {
    const terms = fold(q).split(/\s+/).filter(Boolean);
    if (!terms.length) return [];
    const scored = [];
    for (const list of [index || [], registry || []]) {
      for (const r of list) {
        if (!terms.every(t => r.hay.includes(t))) continue;
        const label = fold(r.label);
        let s = Math.log2(2 + r.w);
        const whole = terms.join(" ");
        if (label === whole) s += 40; else if (label.startsWith(whole)) s += 20;
        else if (terms.every(t => new RegExp("(^|[^a-z0-9])" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).test(label))) s += 8;
        if (r.type === "c" || r.type === "t") s += 10;
        if (r.type === "h" || r.type === "w") s -= 3;
        scored.push([s, r]);
      }
    }
    scored.sort((a, b) => b[0] - a[0]);
    const per = { i: 6, c: 3, t: 3, e: 4, h: 4, w: 4 }, used = {}, out = [];
    for (const [, r] of scored) {
      if ((used[r.type] = (used[r.type] || 0) + 1) > per[r.type]) continue;
      out.push(r);
      if (out.length >= 22) break;
    }
    const order = ["i", "c", "t", "e", "h", "w"];
    return out.sort((a, b) => order.indexOf(a.type) - order.indexOf(b.type));
  }
  function mark(text, q) {
    const terms = fold(q).split(/\s+/).filter(t => t.length > 1);
    let html = esc(text);
    const folded = fold(text);
    if (!terms.length || folded.length !== text.length) return html;
    const ranges = [];
    for (const t of terms) { let i = folded.indexOf(t); while (i > -1) { ranges.push([i, i + t.length]); i = folded.indexOf(t, i + t.length); } }
    if (!ranges.length) return html;
    ranges.sort((a, b) => a[0] - b[0]);
    let out = "", pos = 0;
    for (const [a, b] of ranges) { if (a < pos) continue; out += esc(text.slice(pos, a)) + "<mark>" + esc(text.slice(a, b)) + "</mark>"; pos = b; }
    return out + esc(text.slice(pos));
  }
  function render() {
    const q = input.value.trim();
    if (!q) { close(); return; }
    if (!index) { open(); results.innerHTML = '<div class="sn-empty">Loading search…</div>'; return; }
    shown = search(q);
    active = shown.length ? 0 : -1;
    let html = "", last = "";
    shown.forEach((r, i) => {
      if (r.type !== last) { html += '<div class="sn-group">' + esc(TYPE[r.type]) + "</div>"; last = r.type; }
      html += '<div class="sn-hit' + (i === active ? " is-active" : "") + '" role="option" id="snHit' + i + '" data-hit="' + i + '" aria-selected="' + (i === active) + '">' +
        '<span class="sn-hit-badge t-' + r.type + '" aria-hidden="true">' + ({ i: "◆", c: "◉", t: "◫", e: "§", h: "≋", w: "≋" }[r.type]) + "</span>" +
        '<span class="sn-hit-text"><span class="sn-hit-label">' + mark(r.label, q) + '</span><span class="sn-hit-sub">' + esc(r.sub) + "</span></span></div>";
    });
    results.innerHTML = html || '<div class="sn-empty">No matches for “' + esc(q) + '”. Try a shorter name or a country.</div>';
    input.setAttribute("aria-activedescendant", active >= 0 ? "snHit" + active : "");
    open();
  }
  function open() { results.hidden = false; input.setAttribute("aria-expanded", "true"); }
  function close() { results.hidden = true; input.setAttribute("aria-expanded", "false"); }
  function choose(r) {
    if (!r) return;
    close(); input.blur();
    if (r.type === "i") go("i", r.id);
    else if (r.type === "c") go("c", r.id);
    else if (r.type === "t") go("t", r.id);
    else if (r.type === "h") window.dispatchEvent(new CustomEvent("signalnorth:openstory", { detail: { id: r.id } }));
    else if (r.type === "w" && r.target) go("c", r.target, r.id);
    else if (r.type === "e" && safeUrl(r.target)) window.open(safeUrl(r.target), "_blank", "noopener");
  }
  function move(step) {
    if (!shown.length) return;
    active = (active + step + shown.length) % shown.length;
    results.querySelectorAll(".sn-hit").forEach((el, i) => { el.classList.toggle("is-active", i === active); el.setAttribute("aria-selected", String(i === active)); });
    const el = $("#snHit" + active); if (el) el.scrollIntoView({ block: "nearest" });
    input.setAttribute("aria-activedescendant", "snHit" + active);
  }
  let timer = 0;
  input.addEventListener("focus", () => { ensureIndex(); if (input.value.trim()) render(); });
  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { ensureIndex(); render(); }, 60); });
  input.addEventListener("keydown", e => {
    if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter") { e.preventDefault(); choose(shown[active]); }
    else if (e.key === "Escape") { input.value = ""; close(); input.blur(); }
  });
  results.addEventListener("mousedown", e => { const h = e.target.closest("[data-hit]"); if (h) { e.preventDefault(); choose(shown[+h.dataset.hit]); } });
  document.addEventListener("click", e => { if (!box.contains(e.target)) close(); });
  document.addEventListener("keydown", e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); input.focus(); input.select(); }
    else if (e.key === "/" && !/input|textarea|select/i.test(document.activeElement?.tagName || "") && !document.activeElement?.isContentEditable) { e.preventDefault(); input.focus(); }
  });

  // -------------------------------------------------------------- routing
  let returnFocus = null, highlight = null;
  function go(type, id, hl) {
    highlight = hl || null;
    const next = "#/" + type + "/" + encodeURIComponent(id);
    if (location.hash === next) route(); else location.hash = next;
  }
  window.SignalNorthProfile = { open: go };
  function hide() {
    panel.hidden = true;
    document.documentElement.classList.remove("sn-profile-open");
    if (returnFocus && document.contains(returnFocus)) returnFocus.focus();
  }
  function closeProfile() {
    if (/^#\/[ict]\//.test(location.hash)) history.pushState("", document.title, location.pathname + location.search);
    hide();
  }
  window.addEventListener("hashchange", route);
  window.addEventListener("popstate", () => { if (!/^#\/[ict]\//.test(location.hash)) hide(); });
  panel.addEventListener("click", e => {
    if (e.target === panel || e.target.closest("[data-sn-close]")) { closeProfile(); return; }
    const link = e.target.closest("[data-sn-open]");
    if (link) { e.preventDefault(); const [t, ...rest] = link.dataset.snOpen.split(":"); go(t, rest.join(":")); return; }
    const story = e.target.closest("[data-sn-story]");
    if (story) { e.preventDefault(); hide(); window.dispatchEvent(new CustomEvent("signalnorth:openstory", { detail: { id: story.dataset.snStory } })); return; }
    const chip = e.target.closest("[data-sn-filter]");
    if (chip) { filterTimeline(chip.dataset.snFilter); return; }
    const more = e.target.closest("[data-sn-more]");
    if (more) { showMore(); return; }
    const map = e.target.closest("[data-sn-map]");
    if (map) { hide(); history.pushState("", document.title, location.pathname + location.search); window.dispatchEvent(new CustomEvent("signalnorth:mapfocus", { detail: JSON.parse(map.dataset.snMap) })); return; }
    const copy = e.target.closest("[data-sn-copy]");
    if (copy) { navigator.clipboard?.writeText(location.href).then(() => { copy.textContent = "Link copied"; setTimeout(() => { copy.textContent = "Copy link"; }, 1600); }); }
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !panel.hidden) closeProfile(); });
  // Anything on the site can open a profile with data-sn-open="i:<id>".
  document.addEventListener("click", e => {
    const link = !panel.contains(e.target) && e.target.closest("[data-sn-open]");
    if (link) { e.preventDefault(); const [t, ...rest] = link.dataset.snOpen.split(":"); go(t, rest.join(":")); }
  });

  function fnv(text) {
    let h = 0x811c9dc5;
    for (const b of new TextEncoder().encode(text)) { h ^= b; h = Math.imul(h, 0x01000193) >>> 0; }
    return (h % 256).toString(16).padStart(2, "0");
  }
  async function route() {
    const m = location.hash.match(/^#\/([ict])\/(.+)$/);
    if (!m) { if (!panel.hidden) hide(); return; }
    const type = m[1], id = decodeURIComponent(m[2]);
    if (panel.hidden) returnFocus = document.activeElement;
    panel.hidden = false;
    document.documentElement.classList.add("sn-profile-open");
    body.innerHTML = '<div class="sn-profile-loading">Loading profile…</div>';
    try {
      if (type === "i") {
        const shard = await json("explore/i/" + fnv(id) + ".json");
        if (!shard[id]) throw new Error("not found");
        renderInstitution(shard[id]);
      } else if (type === "c") renderCountry(await json("explore/c/" + id.toUpperCase() + ".json"));
      else renderTheme(await json("explore/t/" + id + ".json"));
      document.title = ($("#snProfileTitle")?.textContent || "Profile") + " · Signal North";
      body.parentElement.scrollTop = 0;
      $("#snProfileClose")?.focus({ preventScroll: true });
      if (highlight) {
        const el = body.querySelector('[data-row-id="' + CSS.escape(highlight) + '"]');
        if (el) { el.classList.add("is-highlight"); el.scrollIntoView({ block: "center" }); }
        highlight = null;
      }
    } catch (err) {
      body.innerHTML = head("Profile", "Not found", "This record is not in the current snapshot. It may have been renamed or removed in a newer collection run.") ;
    }
  }

  // ------------------------------------------------------------ rendering
  function head(eyebrow, title, sub, actions) {
    return '<header class="sn-ph"><div class="sn-ph-top"><div class="sn-eyebrow">' + esc(eyebrow) + "</div>" +
      '<div class="sn-ph-actions">' + (actions || "") + '<button type="button" class="sn-btn sn-ghost" data-sn-copy>Copy link</button>' +
      '<button type="button" id="snProfileClose" class="sn-close" data-sn-close aria-label="Close profile">×</button></div></div>' +
      '<h2 id="snProfileTitle">' + esc(title) + "</h2>" + (sub ? '<p class="sn-ph-sub">' + sub + "</p>" : "") + "</header>";
  }
  function stats(items) {
    return '<div class="sn-stats">' + items.map(([n, label, cls]) =>
      '<div class="sn-stat ' + (cls || "") + '"><strong>' + fmt(n) + "</strong><span>" + esc(label) + "</span></div>").join("") + "</div>";
  }
  function yearChart(years, title) {
    const ys = Object.keys(years || {}).sort().slice(-10);
    if (!ys.length) return "";
    const totals = ys.map(y => KIND_ORDER.reduce((a, k) => a + (years[y][k] || 0), 0));
    const max = Math.max(1, ...totals);
    const present = KIND_ORDER.filter(k => ys.some(y => years[y][k]));
    return '<div class="sn-card"><div class="sn-card-head"><h3>' + esc(title || "Activity by year") + '</h3><span class="sn-legend">' +
      present.map(k => '<i class="' + KIND[k].cls + '"></i>' + esc(KIND[k].label)).join("") + "</span></div>" +
      '<div class="sn-bars" role="img" aria-label="' + esc(ys.map((y, i) => y + ": " + totals[i]).join(", ")) + '">' +
      ys.map((y, i) => '<div class="sn-bar"><div class="sn-bar-stack" style="height:' + (100 * totals[i] / max).toFixed(1) + '%">' +
        KIND_ORDER.filter(k => years[y][k]).map(k => '<span class="' + KIND[k].cls + '" style="flex:' + years[y][k] + '" title="' + esc(y + " · " + KIND[k].label + ": " + years[y][k]) + '"></span>').join("") +
        '</div><b>' + fmt(totals[i]) + "</b><small>" + y + "</small></div>").join("") + "</div></div>";
  }
  let timeline = [], timelineFilter = "all", timelineShown = 40;
  function timelineCard(rows, note) {
    timeline = rows; timelineFilter = "all"; timelineShown = 40;
    const counts = {}; rows.forEach(r => { counts[r.kind] = (counts[r.kind] || 0) + 1; });
    const chips = ['<button type="button" class="sn-chip is-on" data-sn-filter="all">All · ' + fmt(rows.length) + "</button>"]
      .concat(KIND_ORDER.filter(k => counts[k]).map(k => '<button type="button" class="sn-chip ' + KIND[k].cls + '" data-sn-filter="' + k + '">' + esc(KIND[k].label) + " · " + fmt(counts[k]) + "</button>"));
    return '<div class="sn-card"><div class="sn-card-head"><h3>Combined timeline</h3><span class="sn-note">' + esc(note || "Newest first · each row links to its original source") + "</span></div>" +
      '<div class="sn-chips" role="toolbar" aria-label="Filter timeline">' + chips.join("") + "</div>" +
      '<ol class="sn-timeline" id="snTimeline"></ol><button type="button" class="sn-btn sn-more" data-sn-more hidden>Show more</button></div>';
  }
  function drawTimeline() {
    const list = $("#snTimeline"); if (!list) return;
    const rows = timeline.filter(r => timelineFilter === "all" || r.kind === timelineFilter);
    list.innerHTML = rows.slice(0, timelineShown).map(row).join("") || '<li class="sn-empty">No records of this type.</li>';
    const more = body.querySelector("[data-sn-more]");
    if (more) { more.hidden = rows.length <= timelineShown; more.textContent = "Show more (" + fmt(rows.length - timelineShown) + " remaining)"; }
  }
  function filterTimeline(kind) {
    timelineFilter = kind; timelineShown = 40;
    body.querySelectorAll("[data-sn-filter]").forEach(c => c.classList.toggle("is-on", c.dataset.snFilter === kind));
    drawTimeline();
  }
  function showMore() { timelineShown += 60; drawTimeline(); }
  function row(r) {
    const k = KIND[r.kind] || { label: "Record", cls: "" };
    const url = safeUrl(r.url || r.source_url);
    const title = esc(r.title || "Untitled record");
    const titleHtml = r.kind === "headline" && r.story ? '<button type="button" class="sn-link" data-sn-story="' + esc(r.story) + '">' + title + "</button>"
      : url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + title + " ↗</a>" : title;
    const bits = [esc(r.publisher || r.source || "")];
    if (r.role && ROLE[r.role]) bits.push(esc(ROLE[r.role]));
    if (r.matched_name) bits.push("matched “" + esc(r.matched_name) + "”");
    if (r.penalty != null) bits.push(esc(money(r.penalty, r.currency)));
    else if (r.penalty_cad != null) bits.push(esc(money(r.penalty_cad, "CAD")));
    if (r.status && r.kind === "enforcement") bits.push(esc(r.status));
    if (r.institution && r.kind === "enforcement") bits.push(esc(r.institution));
    return '<li class="sn-row" data-row-id="' + esc(r.id || "") + '"><span class="sn-date">' + esc(String(r.date || "—").slice(0, 10)) + "</span>" +
      '<span class="sn-kind ' + k.cls + '">' + esc(k.label) + "</span>" +
      '<div class="sn-row-main"><div class="sn-row-title">' + titleHtml + '</div><div class="sn-row-meta">' + bits.filter(Boolean).join(" · ") + "</div></div></li>";
  }
  function after(html) {
    body.innerHTML = html;
    drawTimeline();
  }
  const caveat = '<p class="sn-caveat">Records keep their own evidence level: regulator actions are published decisions; news mentions are unverified headlines and do not establish wrongdoing.</p>';

  // ------------------------------------------------------- institution page
  const OFFICIAL = [
    ["sanctions_designations", "Sanctions designations", x => esc(x.list) + " · " + esc(x.regime || "programme n/a") + (x.date_designated ? " · " + esc(x.date_designated) : ""), x => x.source_url],
    ["fintrac_notices", "FINTRAC penalty notices", x => esc(x.date || "") + " · " + esc(money(x.penalty_cad, "CAD")) + (x.violation_count != null ? " · " + esc(x.violation_count) + " violations" : ""), x => x.source_url],
    ["fcac_notices", "FCAC actions", x => esc(x.date || "") + " · " + esc(x.topic || "") + " · " + esc(money(x.penalty_cad, "CAD")), x => x.source_url],
    ["ciro_concluded_cases", "CIRO concluded cases", x => esc(x.date || "") + " · " + esc(x.topic || "") + (x.fine_cad != null ? " · fine " + esc(money(x.fine_cad, "CAD")) : ""), x => x.source_url],
    ["occ_institution_actions", "OCC institution actions", x => esc(x.start_date || "") + " · " + esc(x.type_description || x.case_type || "") + (x.amount_raw ? " · " + esc(x.amount_raw) : ""), x => x.source_url],
    ["occ_individual_matters", "OCC individual-related matters", x => esc(x.start_date || "") + " · " + esc(x.type_description || x.case_type || ""), x => x.source_url],
    ["fdic_failure_events", "FDIC failure / resolution events", x => esc(x.date || "") + " · " + esc(x.resolution_type || "") + " · not a fraud finding", x => x.source_url],
    ["obsi_firm_complaints", "OBSI escalated complaints", x => "FY" + esc(x.fiscal_year) + " · " + fmt(x.opened_cases) + " cases opened", x => x.source_url],
    ["bank_disclosures", "Bank-published complaint data", x => esc(x.year) + " · " + fmt(x.metric_value) + " " + esc(x.metric_name || "records"), x => x.source_url],
  ];
  function officialCard(od) {
    if (!od) return "";
    const ids = [];
    if (od.osfi) ids.push("OSFI-regulated · " + esc(od.osfi.group || od.osfi.industry || od.osfi.type || ""));
    if (od.fdic) ids.push("FDIC CERT " + esc(od.fdic.cert) + " · " + esc([od.fdic.city, od.fdic.state].filter(Boolean).join(", ")));
    if (od.ncua) ids.push("NCUA charter " + esc(od.ncua.charter) + " · " + esc([od.ncua.city, od.ncua.state].filter(Boolean).join(", ")));
    if (od.occ) ids.push("OCC charter " + esc(od.occ.charter));
    if ((od.amf_registrations || []).length) ids.push("Québec AMF register");
    const sections = OFFICIAL.filter(([k]) => (od[k] || []).length).map(([k, label, fmtRow, link]) =>
      "<details" + (k === "sanctions_designations" ? " open" : "") + '><summary><span>' + esc(label) + "</span><b>" + fmt(od[k].length) + "</b></summary><ul>" +
      od[k].slice(0, 25).map(x => { const u = safeUrl(link(x)); return "<li>" + fmtRow(x) + (u ? ' <a href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">source ↗</a>' : "") + "</li>"; }).join("") + "</ul></details>").join("");
    if (!ids.length && !sections) return "";
    return '<div class="sn-card"><div class="sn-card-head"><h3>Official records</h3><span class="sn-note">Separate sources · never added together</span></div>' +
      (ids.length ? '<div class="sn-ids">' + ids.map(x => "<span>" + x + "</span>").join("") + "</div>" : "") + '<div class="sn-official">' + sections + "</div></div>";
  }
  function renderInstitution(p) {
    const c = p.counts || {}, od = p.official_data || {};
    const jur = p.jurisdiction;
    const clink = code => '<a href="#/c/' + esc(code) + '" data-sn-open="c:' + esc(code) + '">' + esc(countries.get(code) || code) + "</a>";
    const acted = (p.acted_in || []).filter(Boolean);
    const sub = [jur ? "On official register: " + clink(jur) : "",
      acted.length ? "Regulator actions in " + acted.map(clink).join(", ") : "",
      p.recent_activity ? "Latest evidence " + esc(String(p.recent_activity).slice(0, 10)) : "",
      (p.aliases || []).filter(a => a !== p.name).slice(0, 4).map(esc).join(", ")].filter(Boolean).join(" · ");
    const rows = (p.evidence || []).map(e => Object.assign({}, e, {
      kind: e.kind, url: e.source_url, publisher: e.source,
      story: e.kind === "headline" && !String(e.id || "").startsWith("world-") ? e.id : null,
    }));
    const locs = new Map();
    for (const e of p.evidence || []) {
      const code = countryByName.get(fold(e.location || "")) || (countries.has(e.location) ? e.location : null);
      if (code && code !== jur && !acted.includes(code)) locs.set(code, (locs.get(code) || 0) + 1);
    }
    const themes = (p.themes || []).slice(0, 6);
    const side =
      (locs.size ? '<div class="sn-card"><h3>Other countries in its records</h3><div class="sn-taglist">' +
        [...locs].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([code, n]) => '<a href="#/c/' + esc(code) + '" data-sn-open="c:' + esc(code) + '">' + esc(countries.get(code) || code) + " <b>" + n + "</b></a>").join("") + "</div></div>" : "") +
      (themes.length ? '<div class="sn-card"><h3>Recurring topics</h3><div class="sn-taglist">' + themes.map(t => "<span>" + esc(t.name) + " <b>" + t.matching_records + "</b></span>").join("") +
        '</div><p class="sn-note">Keyword overlap, not established causation.</p></div>' : "") +
      '<div class="sn-card"><h3>Go deeper</h3><div class="sn-actions-col">' +
      '<button type="button" class="sn-btn" data-sn-map=\'' + esc(JSON.stringify({ client: p.name })) + '\'>Show on map</button>' +
      '<button type="button" class="sn-btn sn-ghost" data-sn-connections="' + esc(p.name) + '">Open in Organizations</button></div></div>';
    after(
      head("ORGANIZATION PROFILE", p.name, sub) +
      stats([[c.enforcement, "Regulator actions", "k-enf"], [c.regulator_publications, "Regulator publications", "k-pub"],
        [c.incidents, "Reviewed cases", "k-case"], [c.headlines, "News mentions", "k-news"]]) +
      '<div class="sn-grid"><div class="sn-col">' + yearChart(p.years) + officialCard(od) + timelineCard(rows) + caveat + "</div>" +
      '<aside class="sn-col sn-side">' + side + "</aside></div>");
  }
  body.addEventListener("click", e => {
    const b = e.target.closest("[data-sn-connections]");
    if (!b) return;
    hide(); history.pushState("", document.title, location.pathname + location.search);
    window.dispatchEvent(new CustomEvent("signalnorth:selectinstitution", { detail: { name: b.dataset.snConnections } }));
  });

  // ----------------------------------------------------------- country page
  function renderCountry(p) {
    const c = p.counts || {};
    const cov = p.coverage || {};
    const coverage = { active: "Official actions collected", ingested: "Official actions collected", seed_verified: "Manually verified official actions", not_ingested: "No official feed collected yet" }[cov.coverage] || (cov.coverage ? String(cov.coverage).replace(/_/g, " ") : "");
    const sub = [coverage, cov.regulator_feed_status && cov.regulator_feed_status !== "not_monitored" ? "Regulator feed: " + String(cov.regulator_feed_status).replace(/_/g, " ") : ""].filter(Boolean).map(esc).join(" · ");
    const rows = (p.timeline || []).map(r => Object.assign({}, r, { story: r.kind === "headline" && p.code === "CA" && !String(r.id || "").startsWith("world-") ? r.id : null }));
    const insts = p.institutions || [];
    const side =
      (insts.length ? '<div class="sn-card"><h3>Organizations with evidence</h3><ul class="sn-entity-list">' +
        insts.slice(0, 25).map(x => '<li><a href="#/i/' + esc(encodeURIComponent(x.id)) + '" data-sn-open="i:' + esc(x.id) + '">' + esc(x.name) + "</a><small>" +
          [plural(x.counts.enforcement, "regulator action"), plural(x.counts.headlines, "news mention"), plural(x.counts.incidents, "reviewed case")].filter(Boolean).join(" · ") + "</small></li>").join("") + "</ul></div>" : "") +
      '<div class="sn-card"><h3>Go deeper</h3><div class="sn-actions-col"><button type="button" class="sn-btn" data-sn-map=\'' + esc(JSON.stringify({ country: p.code })) + '\'>Show on map</button></div>' +
      (p.news_total > 150 ? '<p class="sn-note">Showing the newest 150 of ' + fmt(p.news_total) + " news mentions.</p>" : "") + "</div>";
    after(
      head("COUNTRY PROFILE · " + p.code, p.name, sub) +
      stats([[c.enforcement, "Regulator actions", "k-enf"], [c.regulator_publications, "Regulator publications", "k-pub"],
        [c.incidents || 0, "Reviewed cases", "k-case"], [c.headlines, "News mentions", "k-news"]]) +
      '<div class="sn-grid"><div class="sn-col">' + yearChart(p.years) + timelineCard(rows, "Newest first · news mentions name the country in the headline, which is not proof of where an incident happened") + caveat + "</div>" +
      '<aside class="sn-col sn-side">' + side + "</aside></div>");
  }

  // ------------------------------------------------------------- theme page
  function renderTheme(p) {
    const years = {};
    for (const [y, n] of Object.entries(p.year_counts || {})) years[y] = { headline: n };
    const insts = p.institutions || [];
    const side =
      (insts.length ? '<div class="sn-card"><h3>Organizations named alongside it</h3><ul class="sn-entity-list">' +
        insts.map(x => '<li><a href="#/i/' + esc(encodeURIComponent(x.id)) + '" data-sn-open="i:' + esc(x.id) + '">' + esc(x.name) + "</a><small>" + plural(x.mentions, "headline") + "</small></li>").join("") +
        '</ul><p class="sn-note">Named in the same headline, often as an impersonated brand or the victim\'s bank, not as a wrongdoer.</p></div>' : "") +
      '<div class="sn-card"><h3>Go deeper</h3><div class="sn-actions-col"><button type="button" class="sn-btn" data-sn-map=\'' + esc(JSON.stringify({ topic: p.name })) + '\'>Show on map</button>' +
      '<button type="button" class="sn-btn sn-ghost" data-tab="themes" data-sn-close>Compare all patterns</button></div></div>';
    const rows = (p.timeline || []).map(r => Object.assign({}, r, { story: r.id }));
    after(
      head("SCAM PATTERN", p.name, esc(p.note || "")) +
      stats([[p.total_headlines, "Headlines", "k-news"], [p.publisher_count || 0, "Publishers", ""], [insts.length, "Organizations named", ""]]) +
      '<div class="sn-grid"><div class="sn-col">' + yearChart(years, "Coverage by year") + timelineCard(rows) + "</div>" +
      '<aside class="sn-col sn-side">' + side + "</aside></div>");
  }

  if (/^#\/[ict]\//.test(location.hash)) route();
})();
