"""Country-specific discovery lenses for worldwide fraud reporting.

All ISO 3166-1 markets have an English country-named query (discovery ONLY).
Country/local-language editions are curated; arbitrary locales are never
claimed to be available. An editorial source watchlist is NOT an ingested feed.
"""
from __future__ import annotations

# Each tuple: Google News language edition, locally spoken geographic term,
# one representative local fraud term. This does NOT guarantee local coverage.
# A canonical English country-named search also runs for every market.
LOCAL = {
 "AE":("ar","الإمارات","احتيال"),"SA":("ar","السعودية","احتيال"),
 "QA":("ar","قطر","احتيال"),"JO":("ar","الأردن","احتيال"),
 "EG":("ar","مصر","احتيال"),"MA":("ar","المغرب","نصب"),
 "TN":("ar","تونس","تحيل"),"LB":("ar","لبنان","احتيال"),
 "KW":("ar","الكويت","احتيال"),"BH":("ar","البحرين","احتيال"),
 "OM":("ar","عمان","احتيال"),"PS":("ar","فلسطين","احتيال"),
 "BR":("pt","Brasil","golpe"),"PT":("pt","Portugal","burla"),
 "MX":("es","México","fraude"),"AR":("es","Argentina","estafa"),
 "CL":("es","Chile","estafa"),"CO":("es","Colombia","estafa"),
 "PE":("es","Perú","estafa"),"ES":("es","España","estafa"),
 "EC":("es","Ecuador","estafa"),"UY":("es","Uruguay","estafa"),
 "CR":("es","Costa Rica","estafa"),"PA":("es","Panamá","estafa"),
 "FR":("fr","France","escroquerie"),"BE":("fr","Belgique","fraude"),
 "CH":("de","Schweiz","Betrug"),"DE":("de","Deutschland","Betrug"),
 "AT":("de","Österreich","Betrug"),"IT":("it","Italia","truffa"),
 "NL":("nl","Nederland","oplichting"),"PL":("pl","Polska","oszustwo"),
 "CZ":("cs","Česko","podvod"),"SK":("sk","Slovensko","podvod"),
 "HU":("hu","Magyarország","csalás"),"RO":("ro","România","fraudă"),
 "GR":("el","Ελλάδα","απάτη"),"TR":("tr","Türkiye","dolandırıcılık"),
 "RU":("ru","Россия","мошенничество"),"UA":("uk","Україна","шахрайство"),
 "IL":("he","ישראל","הונאה"),"IR":("fa","ایران","کلاهبرداری"),
 "IN":("hi","भारत","धोखाधड़ी"),"PK":("ur","پاکستان","فراڈ"),
 "BD":("bn","বাংলাদেশ","প্রতারণা"),"NP":("ne","नेपाल","ठगी"),
 "LK":("si","ශ්‍රී ලංකාව","වංචා"),"TH":("th","ประเทศไทย","หลอกลวง"),
 "VN":("vi","Việt Nam","lừa đảo"),"ID":("id","Indonesia","penipuan"),
 "MY":("ms","Malaysia","penipuan"),"PH":("en","Philippines","scam"),
 "JP":("ja","日本","詐欺"),"CN":("zh","中国","诈骗"),
 "TW":("zh","台灣","詐騙"),"HK":("zh","香港","詐騙"),
 "KR":("ko","한국","사기"),"KE":("sw","Kenya","utapeli"),
 "TZ":("sw","Tanzania","utapeli"),"ZA":("en","South Africa","scam"),
 "NG":("en","Nigeria","fraud"),"GH":("en","Ghana","fraud"),
}
COUNTRY_NAMES={
 "US":"United States","GB":"United Kingdom","KR":"South Korea","KP":"North Korea",
 "RU":"Russia","IR":"Iran","SY":"Syria","LA":"Laos","VN":"Vietnam",
 "BO":"Bolivia","VE":"Venezuela","TZ":"Tanzania","TW":"Taiwan",
 "PS":"Palestine","HK":"Hong Kong","MO":"Macau","TR":"Türkiye",
 "AE":"United Arab Emirates","CD":"DR Congo","CG":"Republic of the Congo",
 "CI":"Côte d'Ivoire","CZ":"Czechia","BN":"Brunei","MD":"Moldova",
}
# Only explicitly configured editions; unsupported markets use en-US search
# with the country's name in the query (not falsely presented as local media).
NEWS_EDITIONS={
 "US":("en-US","US","en"),"CA":("en-CA","CA","en"),
 "GB":("en-GB","GB","en"),"AU":("en-AU","AU","en"),"IE":("en-IE","IE","en"),
 "IN":("en-IN","IN","en"),"NZ":("en-NZ","NZ","en"),"SG":("en-SG","SG","en"),
 "MY":("en-MY","MY","en"),"PH":("en-PH","PH","en"),
 "ZA":("en-ZA","ZA","en"),"NG":("en-NG","NG","en"),
 "AE":("en-AE","AE","en"),"SA":("ar","SA","ar"),"EG":("ar","EG","ar"),
 "FR":("fr","FR","fr"),"BE":("fr","BE","fr"),"CH":("de","CH","de"),
 "DE":("de","DE","de"),"AT":("de","AT","de"),"IT":("it","IT","it"),
 "ES":("es","ES","es"),"MX":("es-419","MX","es-419"),
 "AR":("es-419","AR","es-419"),"CO":("es-419","CO","es-419"),
 "BR":("pt-BR","BR","pt-419"),"PT":("pt-PT","PT","pt"),
 "NL":("nl","NL","nl"),"PL":("pl","PL","pl"),"TR":("tr","TR","tr"),
 "RU":("ru","RU","ru"),"UA":("uk","UA","uk"),
 "JP":("ja","JP","ja"),"KR":("ko","KR","ko"),"CN":("zh-CN","CN","zh-Hans"),
 "TW":("zh-TW","TW","zh-Hant"),"HK":("zh-HK","HK","zh-Hant"),
 "TH":("th","TH","th"),"ID":("id","ID","id"),"VN":("vi","VN","vi"),
}
# Human-reviewed authority discovery links. NOT automatic ingestion or verified
# enforcement feeds. Add jurisdictions only with trusted actual agency URLs.
AUTHORITIES={
 "US":[("FinCEN","https://www.fincen.gov/news/enforcement-actions")],
 "CA":[("FINTRAC","https://fintrac-canafe.canada.ca/pen/4-eng")],
 "GB":[("FCA","https://www.fca.org.uk/news")],
 "AU":[("AUSTRAC","https://www.austrac.gov.au/about-us/record-our-actions/enforcement-actions-taken")],
 "SG":[("MAS","https://www.mas.gov.sg/regulation/enforcement")],
 "IN":[("RBI","https://www.rbi.org.in/"),("SEBI","https://www.sebi.gov.in/")],
 "FR":[("AMF","https://www.amf-france.org/")],
 "DE":[("BaFin","https://www.bafin.de/")],
 "BR":[("Banco Central do Brasil","https://www.bcb.gov.br/")],
 "MX":[("CNBV","https://www.gob.mx/cnbv")],
 "JP":[("FSA","https://www.fsa.go.jp/en/")],
 "ZA":[("FIC","https://www.fic.gov.za/")],
 "NG":[("EFCC","https://www.efcc.gov.ng/")],
 "KE":[("Central Bank of Kenya","https://www.centralbank.go.ke/")],
 "AE":[("Central Bank of the UAE","https://www.centralbank.ae/")],
 "IE":[("Central Bank of Ireland","https://www.centralbank.ie/")],
 "HK":[("HKMA","https://www.hkma.gov.hk/eng/")],
}

def country_name(code, country):
    return COUNTRY_NAMES.get(code, getattr(country,"common_name",country.name))

def country_profile(country):
    code=country.alpha_2
    name=country_name(code,country)
    local=LOCAL.get(code)
    hl,gl,ceid=NEWS_EDITIONS.get(code,("en-US","US","en"))
    return {
        "code":code,"name":name,"edition_language":hl,"edition_country":gl,
        "edition_id":ceid,"local_term":local[2] if local else None,
        "local_country_term":local[1] if local else None,
        "local_language":local[0] if local else None,
        "language_strategy":"country_configured" if local else "english_country_named_fallback",
        "agency_directory":[{"name":n,"url":u} for n,u in AUTHORITIES.get(code,[])],
    }

CRIME_TERMS=(
 "fraud","scam","phish","launder","identity theft","ponzi","embezzle",
 "forgery","financial crime","ransomware","money mule","fraude",
 "escroquer","arnaque","estafa","estafas","fraudul","golpe",
 "burla","truffa","betrug","oplichting","oszust","podvod","csalás",
 "απάτη","dolandır","мошенн","шахрай","احتيال","نصب","تحيل",
 "הונאה","کلاهبردار","धोखाधड़","فراڈ","প্রতারণা","ठगी","වංචා",
 "หลอกลวง","lừa đảo","penipuan","詐欺","诈骗","詐騙","사기","utapeli",
)
