"""Additional sector/linguistic fraud searches for major Asian and African markets.

Every entry means ONE deliberately bounded *query* (not an active publisher
feed, validated Google edition, proof of article origin or fraud location).
Tuple: (query language, native country/market phrase, local fraud term).
The standalone baseline English and primary-local searches remain unchanged.
"""
from __future__ import annotations

# Content terms are intentionally short/observable. Editors can adjust terms
# after checking the source-health reports for accepted and rejected results.
MARKET_EXTRA_QUERIES={
    # East / South / Southeast Asia, including multilingual countries.
    "CN":[("zh","中国","网络诈骗"),("zh","中国","洗钱")],
    "IN":[("hi","भारत","बैंक धोखाधड़ी"),("ta","இந்தியா","மோசடி"),
          ("bn","ভারত","প্রতারণা"),("te","భారతదేశం","మోసం"),
          ("mr","भारत","फसवणूक")],
    "MY":[("ms","Malaysia","penipuan dalam talian"),
          ("zh","马来西亚","诈骗"),("ta","மலேசியா","மோசடி")],
    "ID":[("id","Indonesia","penipuan online"),("id","Indonesia","pencucian uang")],
    "TH":[("th","ประเทศไทย","หลอกลวงออนไลน์"),("th","ประเทศไทย","ฟอกเงิน")],
    "VN":[("vi","Việt Nam","lừa đảo ngân hàng"),("vi","Việt Nam","rửa tiền")],
    "PH":[("tl","Pilipinas","panloloko"),("en","Philippines","bank scam")],
    "SG":[("zh","新加坡","诈骗"),("en","Singapore","money laundering")],
    "KH":[("km","កម្ពុជា","បោកប្រាស់តាមអ៊ីនធឺណិត")],
    "LA":[("lo","ລາວ","ຫຼອກລວງອອນລາຍ")],
    "MM":[("my","မြန်မာ","အွန်လိုင်းလိမ်လည်မှု")],
    "BN":[("ms","Brunei","penipuan dalam talian")],
    "TL":[("pt","Timor-Leste","fraude bancária")],
    "PK":[("ur","پاکستان","بینک فراڈ")],
    "BD":[("bn","বাংলাদেশ","ব্যাংক প্রতারণা")],
    "NP":[("ne","नेपाल","अनलाइन ठगी")],
    "LK":[("ta","இலங்கை","மோசடி")],
    "HK":[("zh","香港","網絡詐騙")],
    "TW":[("zh","台灣","洗錢")],
    # Africa: variety of languages, legal systems, and publisher ecosystems.
    "NG":[("ha","Najeriya","zamba"),("en","Nigeria","bank fraud")],
    "KE":[("sw","Kenya","ulaghai"),("en","Kenya","mobile money fraud")],
    "TZ":[("sw","Tanzania","udanganyifu")],
    "UG":[("sw","Uganda","utapeli")],
    "ZA":[("af","Suid-Afrika","bedrog"),("en","South Africa","bank scam")],
    "GH":[("en","Ghana","mobile money fraud")],
    "ET":[("am","ኢትዮጵያ","የባንክ ማጭበርበር")],
    "EG":[("ar","مصر","نصب إلكتروني")],
    "MA":[("fr","Maroc","arnaque"),("ar","المغرب","احتيال")],
    "DZ":[("fr","Algérie","escroquerie")],
    "TN":[("fr","Tunisie","fraude")],
    "SN":[("fr","Sénégal","blanchiment")],
    "CI":[("fr","Côte d'Ivoire","blanchiment")],
    "CM":[("fr","Cameroun","escroquerie bancaire")],
    "CD":[("fr","RDC","blanchiment")],
    "RW":[("en","Rwanda","bank fraud")],
    "AO":[("pt","Angola","burla bancária")],
    "MZ":[("pt","Moçambique","burla bancária")],
    "ZM":[("en","Zambia","mobile money fraud")],
    "ZW":[("en","Zimbabwe","bank fraud")],
}
# Deliberately limited priority scan. English baseline for all 250 continues.
PRIORITY_MARKETS=("CN","IN","MY","ID","TH","VN","PH","SG","KH",
                  "NG","KE","ZA","EG","GH","TZ","ET")
PRIORITY_EXTRA_PER_RUN=4
