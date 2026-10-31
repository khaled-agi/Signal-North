"""Country-attributed ORIGINAL publication sources, independently of Google News.

The entries in this curated registry are verified public publisher/authority
domains and index/feed URLs, but configuration is NOT proof of successful
ingestion. Each run verifies live availability; errors are reported explicitly.

A source's institutional country ≠ location of the event in its publications.
Websites with usage restrictions may require permission before commercial use.
Never automatically promote publications into final court/regulatory actions.
"""
from __future__ import annotations

# Unique source id, publisher country, name, class, source URL, feed/index type,
# original host, conservative article-URL fragment. "index" runs on source HTML
# lists only, not crawling page bodies or guessing publication dates.
SOURCES=[
 # Direct, explicitly advertised RSS feeds
 dict(id="in-sebi",country="IN",name="Securities and Exchange Board of India",kind="securities_regulator",
      url="https://www.sebi.gov.in/sebirss.xml",format="rss",domain="sebi.gov.in"),
 dict(id="fr-amf-sanctions",country="FR",name="Autorité des marchés financiers",kind="securities_regulator",
      url="https://www.amf-france.org/fr/flux-rss/display/24",format="rss",domain="amf-france.org"),
 dict(id="fr-amf-warnings",country="FR",name="Autorité des marchés financiers (warnings)",kind="securities_regulator",
      url="https://www.amf-france.org/fr/flux-rss/display/28",format="rss",domain="amf-france.org"),
 dict(id="ng-premiumtimes",country="NG",name="Premium Times Nigeria",kind="local_newspaper",
      url="https://www.premiumtimesng.com/feed",format="rss",domain="premiumtimesng.com"),
 dict(id="pg-police",country="PG",name="Royal Papua New Guinea Constabulary",kind="police",
      url="https://rpngc.gov.pg/feed/",format="rss",domain="rpngc.gov.pg"),
 # Official first-party announcement and enforcement indexes
 dict(id="sg-mas",country="SG",name="Monetary Authority of Singapore",kind="central_bank",
      url="https://www.mas.gov.sg/regulation/enforcement/enforcement-actions",format="index",domain="mas.gov.sg",path_hint="/regulation/enforcement/"),
 dict(id="my-bnm",country="MY",name="Bank Negara Malaysia",kind="central_bank",
      url="https://www.bnm.gov.my/press-release-2026",format="index",domain="bnm.gov.my",path_hint="/"),
 dict(id="my-sc",country="MY",name="Securities Commission Malaysia",kind="securities_regulator",
      url="https://www.sc.com.my/resources/media/media-release",format="index",domain="sc.com.my",path_hint="/resources/media/"),
 dict(id="id-ppatk",country="ID",name="PPATK Financial Intelligence Unit",kind="financial_intelligence_unit",
      url="https://www.ppatk.go.id/",format="index",domain="ppatk.go.id",path_hint="/"),
 dict(id="ph-amlc",country="PH",name="Anti-Money Laundering Council",kind="financial_intelligence_unit",
      url="https://www.amlc.gov.ph/",format="index",domain="amlc.gov.ph",path_hint="/"),
 dict(id="in-fiu",country="IN",name="Financial Intelligence Unit India",kind="financial_intelligence_unit",
      url="https://fiuindia.gov.in/",format="index",domain="fiuindia.gov.in",path_hint="/"),
 dict(id="ng-cbn",country="NG",name="Central Bank of Nigeria",kind="central_bank",
      url="https://www.cbn.gov.ng/",format="index",domain="cbn.gov.ng",path_hint="/"),
 dict(id="ng-efcc",country="NG",name="Economic and Financial Crimes Commission",kind="law_enforcement",
      url="https://www.efcc.gov.ng/News",format="index",domain="efcc.gov.ng",path_hint="/"),
 dict(id="ng-police",country="NG",name="Nigeria Police Force",kind="police",
      url="https://incb.police.gov.ng/news",format="index",domain="incb.police.gov.ng",path_hint="/news"),
 dict(id="mu-bom",country="MU",name="Bank of Mauritius Scam Alerts",kind="central_bank",
      url="https://www.bom.mu/financial-stability/supervision/scam-alerts",format="index",domain="bom.mu",path_hint="/financial-stability/supervision/scam-alerts/"),
 dict(id="nz-fma",country="NZ",name="New Zealand Financial Markets Authority",kind="securities_regulator",
      url="https://www.fma.govt.nz/about-us/enforcement/cases/",format="index",domain="fma.govt.nz",path_hint="/about-us/enforcement/cases/"),
 dict(id="ke-dci",country="KE",name="Kenya Directorate of Criminal Investigations",kind="police",
      url="https://www.dci.go.ke/",format="index",domain="dci.go.ke",path_hint="/"),
 dict(id="gh-bog",country="GH",name="Bank of Ghana",kind="central_bank",
      url="https://www.bog.gov.gh/news/",format="index",domain="bog.gov.gh",path_hint="/"),
 dict(id="cn-csrc",country="CN",name="China Securities Regulatory Commission",kind="securities_regulator",
      url="https://www.csrc.gov.cn/csrc/c100028/common_list.shtml",format="index",domain="csrc.gov.cn",path_hint="/csrc/c"),
 dict(id="th-bot",country="TH",name="Bank of Thailand",kind="central_bank",
      url="https://www.bot.or.th/en/home.html",format="index",domain="bot.or.th",path_hint="/en/news-and-media/news/"),
 dict(id="bo-elpais",country="BO",name="El País Bolivia - Seguridad",kind="local_newspaper",
      url="https://elpais.bo/seguridad/",format="index",domain="elpais.bo",path_hint="/seguridad/"),
 dict(id="bw-dailynews",country="BW",name="Botswana Daily News",kind="local_newspaper",
      url="https://dailynews.gov.bw/",format="index",domain="dailynews.gov.bw",path_hint="/news-detail/"),
 dict(id="fr-amf-index",country="FR",name="AMF France - Official releases",kind="securities_regulator",
      url="https://www.amf-france.org/en/news-publications/news-releases/amf-news-releases",format="index",domain="amf-france.org",path_hint="/en/news-publications/"),
 dict(id="us-fincen",country="US",name="FinCEN",kind="financial_intelligence_unit",
      url="https://www.fincen.gov/news/news-releases",format="index",domain="fincen.gov",path_hint="/news/"),
 dict(id="br-bcb",country="BR",name="Banco Central do Brasil",kind="central_bank",
      url="https://www.bcb.gov.br/",format="index",domain="bcb.gov.br",path_hint="/"),
]
SOURCE_IDS={x["id"] for x in SOURCES}
assert len(SOURCE_IDS)==len(SOURCES)
