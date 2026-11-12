"use strict";
/* Map layers added on top of app.js's evidence map:
 *  - countries shaded by OFFICIAL records (regulator actions + regulator-site
 *    publications) for the selected years; news mentions never colour a country;
 *  - click a country to open its profile, hover for counts;
 *  - a two-handle year slider bound to the existing From/Through year filters.
 * The shading is a count of published records, not a measure of crime.
 */
(() => {
  const $ = s => document.querySelector(s);
  const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const COLORS = ["#d8eeec", "#a9dbd6", "#6fc0b9", "#2f9d98", "#0b7d81", "#06555a"];
  let geo = null, geoLoading = null, layer = null, legend = null, enabled = true, lastCounts = new Map();

  function app() { try { return state; } catch { return null; } }   // app.js global
  function yearOf(v) { return String(v || "").slice(0, 4); }
  function inYears(v) {
    const s = app(); const y = yearOf(v);
    return (!s.mapYearFrom || y >= s.mapYearFrom) && (!s.mapYearTo || y <= s.mapYearTo);
  }
  function counts() {
    const s = app(), out = new Map();
    const bump = (cc, key) => { if (!cc) return; const c = out.get(cc) || { official: 0, leads: 0, news: 0 }; c[key]++; out.set(cc, c); };
    const agencyOk = a => !s.mapAgency || a === s.mapAgency;
    for (const e of s.events || []) if (inYears(e.published_at) && agencyOk(e.source)) bump("CA", "official");
    for (const e of s.globalEvents || []) if (inYears(e.published_at) && agencyOk(e.regulator)) bump(e.country_code, "official");
    for (const e of s.worldRegLeads || []) if (inYears(e.first_observed_at) && agencyOk(e.regulator)) bump(e.country_code, "leads");
    for (const e of s.worldNews || []) if (inYears(e.published_at)) bump(e.country_code, "news");
    for (const e of s.news || []) if (inYears(e.published_at)) bump("CA", "news");
    return out;
  }
  function scale(max) {
    // Log buckets keep the UK/US from washing every other country out.
    return n => {
      if (!n) return null;
      const i = Math.min(COLORS.length - 1, Math.floor(Math.log(n) / Math.log(Math.max(2, max)) * (COLORS.length - 1) + 1e-9));
      return COLORS[Math.max(0, i)];
    };
  }
  function ensureGeo() {
    if (geo || geoLoading) return geoLoading;
    geoLoading = fetch("./assets/world-countries.geo.json?v=" + (window.SignalNorthData?.build || "1"))
      .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(d => { geo = d; update(); })
      .catch(() => { geoLoading = null; });
    return geoLoading;
  }
  function addLegend(map, max) {
    if (!legend) {
      legend = L.control({ position: "bottomleft" });
      legend.onAdd = () => {
        const div = L.DomUtil.create("div", "sn-map-legend");
        L.DomEvent.disableClickPropagation(div);
        return div;
      };
      legend.addTo(map);
    }
    const el = legend.getContainer();
    const s = app();
    const range = s.mapYearFrom || s.mapYearTo ? (s.mapYearFrom || "earliest") + "–" + (s.mapYearTo || "latest") : "all years";
    el.innerHTML = '<label class="sn-legend-toggle"><input type="checkbox" id="snShadeToggle"' + (enabled ? " checked" : "") + "> Shade by official records</label>" +
      (enabled ? '<div class="sn-legend-scale">' + COLORS.map(c => '<i style="background:' + c + '"></i>').join("") + "</div>" +
        '<div class="sn-legend-ends"><span>1</span><span>' + max + "</span></div>" +
        '<small>Regulator actions and regulator-site publications, ' + esc(range) + ". Not a crime rate. Click a country for its profile.</small>" : "");
    el.querySelector("#snShadeToggle").addEventListener("change", e => { enabled = e.target.checked; update(); });
  }
  function update() {
    const s = app();
    if (!s || !s.map || !window.L) return;
    syncSlider();
    if (!geo) { ensureGeo(); return; }
    lastCounts = counts();
    const max = Math.max(1, ...[...lastCounts.values()].map(c => c.official + c.leads));
    const color = scale(max);
    if (!s.map.getPane("snShade")) { const pane = s.map.createPane("snShade"); pane.style.zIndex = 350; }
    if (layer) { s.map.removeLayer(layer); layer = null; }
    if (enabled) {
      layer = L.geoJSON(geo, {
        pane: "snShade", renderer: L.svg({ pane: "snShade" }),
        style: f => {
          const c = lastCounts.get(f.properties.iso2), n = c ? c.official + c.leads : 0, fill = color(n);
          // Zoomed into one country, keep its provinces and clusters readable:
          // outline it and fade the shading everywhere.
          const focus = Boolean(s.mapCountry), selected = focus && s.mapCountry === f.properties.iso2;
          return { fillColor: fill || "#ffffff", fillOpacity: !fill ? 0 : selected ? .06 : focus ? .3 : .62,
            color: selected ? "#10283c" : fill ? "#ffffff" : "#c9d6dc", weight: selected ? 2.2 : .7, opacity: fill || selected ? .9 : .6 };
        },
        onEachFeature: (f, lyr) => {
          const code = f.properties.iso2, c = lastCounts.get(code) || { official: 0, leads: 0, news: 0 };
          lyr.bindTooltip('<strong>' + esc(f.properties.name) + "</strong><br>" + c.official + " regulator action" + (c.official === 1 ? "" : "s") +
            (c.leads ? " · " + c.leads + " regulator publications" : "") + "<br>" + c.news + " news mention" + (c.news === 1 ? "" : "s") + " (unverified)" +
            '<br><em>Click for country profile</em>', { sticky: true, className: "sn-map-tip", direction: "top", offset: [0, -6] });
          lyr.on("mouseover", () => lyr.setStyle({ weight: 2, color: "#10283c" }));
          lyr.on("mouseout", () => layer && layer.resetStyle(lyr));
          lyr.on("click", () => window.SignalNorthProfile?.open("c", code));
        },
      }).addTo(s.map);
    }
    addLegend(s.map, max);
  }

  // ------------------------------------------------------------ year slider
  let slider = null;
  function buildSlider() {
    const from = $("#mapYearFrom"), to = $("#mapYearTo"), toolbar = $(".map-primary-toolbar");
    if (!from || !to || !toolbar) return null;
    const wrap = document.createElement("div");
    wrap.className = "sn-years";
    wrap.innerHTML = '<span class="sn-years-label" id="snYearsLabel">All years</span>' +
      '<div class="sn-years-track"><div class="sn-years-fill"></div>' +
      '<input type="range" id="snYearMin" aria-label="Earliest publication year"><input type="range" id="snYearMax" aria-label="Latest publication year"></div>';
    toolbar.after(wrap);
    const cs = getComputedStyle(toolbar);
    wrap.style.marginLeft = (parseFloat(cs.marginLeft) + parseFloat(cs.paddingLeft)) + "px";
    wrap.style.marginRight = (parseFloat(cs.marginRight) + parseFloat(cs.paddingRight)) + "px";
    const min = wrap.querySelector("#snYearMin"), maxEl = wrap.querySelector("#snYearMax");
    const apply = () => {
      const years = optionYears(); if (!years.length) return;
      let a = +min.value, b = +maxEl.value;
      if (a > b) { if (document.activeElement === min) a = b; else b = a; min.value = a; maxEl.value = b; }
      const lo = years[0], hi = years[years.length - 1];
      setSelect(from, a === lo ? "" : String(a));
      setSelect(to, b === hi ? "" : String(b));
    };
    let t = 0;
    for (const el of [min, maxEl]) {
      el.addEventListener("input", () => { paint(); clearTimeout(t); t = setTimeout(apply, 120); });
      el.addEventListener("change", apply);
    }
    return { wrap, min, max: maxEl };
  }
  function optionYears() {
    return [...($("#mapYearFrom")?.options || [])].map(o => +o.value).filter(Boolean).sort((a, b) => a - b);
  }
  function setSelect(sel, value) {
    if (sel.value === value) return;
    sel.value = value;
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  }
  function paint() {
    if (!slider) return;
    const years = optionYears(); if (!years.length) return;
    const lo = years[0], hi = years[years.length - 1], span = Math.max(1, hi - lo);
    const a = +slider.min.value, b = +slider.max.value;
    const fill = slider.wrap.querySelector(".sn-years-fill");
    fill.style.left = (100 * (a - lo) / span) + "%";
    fill.style.right = (100 * (hi - b) / span) + "%";
    slider.wrap.querySelector("#snYearsLabel").textContent = a === lo && b === hi ? "All years" : a === b ? String(a) : a + "–" + b;
  }
  function syncSlider() {
    const years = optionYears();
    if (!years.length) return;
    if (!slider) slider = buildSlider();
    if (!slider) return;
    const lo = years[0], hi = years[years.length - 1], s = app();
    for (const el of [slider.min, slider.max]) { el.min = lo; el.max = hi; el.step = 1; }
    slider.min.value = s.mapYearFrom || lo;
    slider.max.value = s.mapYearTo || hi;
    slider.wrap.hidden = lo === hi;
    paint();
  }

  window.SignalNorthMapLayers = { update, counts: () => lastCounts };
  window.addEventListener("signalnorth:globalready", () => setTimeout(update, 0));
})();
