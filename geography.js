"use strict";
/* Country search markets are NOT event locations. A title mention only makes
 * the country a research reference; it does not establish where a crime occurred.
 */
(() => {
 const aliases={
  US:["United States","U.S.A.","USA","American","U.S."],
  CA:["Canada","Canadian"], GB:["United Kingdom","Britain","British","U.K."],
  IL:["Israel","Israeli","ישראל"], JO:["Jordan","Jordanian","الأردن","الأردني"],
  PS:["Palestine","Palestinian","فلسطين","فلسطيني"],
  AE:["United Arab Emirates","UAE","Emirati","الإمارات"],
  SA:["Saudi Arabia","Saudi","السعودية"],
  FR:["France","French"],DE:["Germany","German","Deutschland"],
  IN:["India","Indian","भारत"],AU:["Australia","Australian"],
  BR:["Brazil","Brazilian","Brasil"],JP:["Japan","Japanese","日本"],
  CN:["China","Chinese","中国"],KR:["South Korea","Korean","한국"],
  HK:["Hong Kong","香港"],TW:["Taiwan","Taiwanese","台灣"],
  NZ:["New Zealand"],MX:["Mexico","Mexican","México"],
  XK:["Kosovo","Kosovë","Kosovar"]
 };
 const special=".*+?^"+"$"+"{}()|[]\\";
 const esc=s=>String(s).split("").map(ch=>special.includes(ch)?"\\"+ch:ch).join("");
 function termPresent(title,term){
  if(!term)return false;
  // Chinese/Japanese/Thai/Khmer and other non-spaced writing systems have
  // no whitespace word boundaries; explicit native country names still count
  // as mentions (never incident coordinates).
  const nonspace=/[\u3400-\u9fff\u3040-\u30ff\u0e00-\u0e7f\u1780-\u17ff\u0e80-\u0eff\u1000-\u109f\u0900-\u0d7f]/u.test(term);
  if(nonspace)return term.length>=2&&String(title||"").normalize("NFC").toLocaleLowerCase().includes(term.normalize("NFC").toLocaleLowerCase());
  if(term.length<3)return false;
  const pattern="(?:^|[^\\p{L}\\p{N}])"+esc(term)+"(?=$|[^\\p{L}\\p{N}])";
  try{return new RegExp(pattern,"iu").test(String(title||""));}
  catch{return false;}
 }
 function evaluate(item,country){
  const code=String(item?.country_code||"");
  const name=country?.name||item?.country||"";
  const terms=[name,country?.local_country_term,...(country?.country_headline_aliases||[]),...(aliases[code]||[])].filter(Boolean);
  const matched=[...new Set(terms)].filter(t=>termPresent(item?.title||"",t));
  return {
   referenced:matched.length>0,
   basis:matched.length?"country_name_in_headline_not_incident_location":"no_country_reference_in_headline",
   matched_term:matched[0]||null
  };
 }
 window.SignalNorthGeo={evaluate,termPresent};
})();
