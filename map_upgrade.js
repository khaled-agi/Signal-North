"use strict";
/* Optional modern vector basemap layer.
   Leaflet remains the interaction and evidence-marker engine; vector tiles
   render only as the background. Browser/renderer outages fall back to OSM. */
(() => {
 let attempted = false;
 async function ready(){
  if(attempted || !window.L)return;
  attempted = true;
  try{
   const vector = await import("https://cdn.jsdelivr.net/npm/maplibre-gl@6.9.0/dist/maplibre-gl.mjs");
   window.maplibregl=vector;
   await import("https://cdn.jsdelivr.net/npm/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js");
   if(typeof window.L?.maplibreGL!=="function")throw new Error("Vector map adapter unavailable");
   window.dispatchEvent(new Event("signalnorth:basemapready"));
  }catch(err){
   window.dispatchEvent(new CustomEvent("signalnorth:basemaperror",{detail:{reason:"Vector tiles unavailable; classic OpenStreetMap is in use."}}));
  }
 }
 window.addEventListener("signalnorth:mapready",ready);
 if(document.readyState==="complete"&&window.L)ready();
})();
