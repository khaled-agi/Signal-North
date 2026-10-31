#!/usr/bin/env python3
"""Smoke-test Signal North in a real headless browser, with the committed data snapshot."""
import contextlib
import functools
import http.server
import json
import os
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = len(json.loads((ROOT / "data" / "events.json").read_text())["events"])
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT))
)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f"http://127.0.0.1:{server.server_port}/"

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        errors = []
        resources = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda resp: resources.append(
            (resp.status, resp.url)) if "/data/events.json" in resp.url or resp.url.endswith("/app.js") else None)
        # Browser-only CFPB fixture; no synthetic complaint is committed to site data.
        page.route("**/data/cfpb_complaints.json*",lambda route:route.fulfill(
            status=200,content_type="application/json",body=json.dumps({
              "source":"CFPB","country_code":"US","complaints":[{
                "id":"12345678","date_received":"2026-10-25",
                "company":"Example Financial Services","product":"Checking or savings account",
                "sub_product":"Checking account","issue":"Managing an account",
                "sub_issue":"Problem with a transaction","state":"NY",
                "company_response":"Closed with explanation","timely":"Yes",
                "source_url":"https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/12345678",
                "evidence_status":"published_consumer_complaint_not_verified",
                "geography_basis":"consumer_reported_state_not_incident_location"
              }]
            })))
        page.route("**/data/cfpb_complaints_status.json*",lambda route:route.fulfill(
            status=200,content_type="application/json",body=json.dumps({
              "status":"ok","stored_records":1,
              "last_attempt_at":"2026-10-30T12:00:00+00:00"
            })))
        page.route("**/data/cfpb_monthly_history.json*",lambda route:route.fulfill(
            status=200,content_type="application/json",body=json.dumps({
              "earliest_possible_month":"2011-12","months":[{
                "month":"2011-12","monthly_total_status":"exact_api_total",
                "exact_published_complaint_total":1234,
                "sample_size":2,
                "sample_issue_breakdown":[{"issue":"Managing an account","sub_issue":"Problem with a transaction","sample_count":2}],
                "sample_product_breakdown":[{"product":"Checking or savings account","sample_count":2}]
              }]
            })))
        page.route("**/data/cfpb_monthly_history_status.json*",lambda route:route.fulfill(
            status=200,content_type="application/json",body=json.dumps({
              "status":"ok","months_available":178,"months_with_results":1,
              "last_attempt_at":"2026-10-30T12:00:00+00:00"
            })))
        page.route("**/data/cafc_aggregates.json*",lambda route:route.fulfill(
            status=200,content_type="application/json",body=json.dumps({
              "dataset_coverage":"2021-01-01 through 2025-09-30","minimum_public_cell_size":5,
              "rows":[{"dimension":"category","year":"2025","label":"Investment Fraud",
                "province":None,"report_rows":12,"reported_victims_sum":12,
                "reported_dollar_loss_sum":75000,"rows_without_loss":0},
               {"dimension":"province","year":"2025","label":"Ontario",
                "province":None,"report_rows":17,"reported_victims_sum":17,
                "reported_dollar_loss_sum":75000,"rows_without_loss":0}]
            })))
        page.route("**/data/cafc_source_status.json*",lambda route:route.fulfill(
            status=200,content_type="application/json",body=json.dumps({
              "status":"ok","canada_rows":100,"dataset_end_date":"2025-09-30"
            })))
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        try:
            page.wait_for_function("document.querySelectorAll('.metric').length === 4", timeout=20000)
        except Exception:
            print("BROWSER LOGS:", errors)
            print("RESOURCE RESPONSES:", resources)
            print("VISIBLE ERROR:", page.locator("#error").inner_text())
            print("BODY:", page.locator("body").inner_text()[:1800])
            raise
        actual = page.locator(".metric .value").nth(1).inner_text()
        print("Expected official notice count:", EXPECTED, "Dashboard official notice count:", actual)
        print("Network responses:", resources)
        print("Runtime errors:", errors)
        assert actual == str(EXPECTED), f"Expected {EXPECTED}, got {actual}"
        assert not errors, str(errors)
        page.locator("details.nav-datasets summary").first.click()
        page.locator('[data-tab="events"]').click()
        assert page.locator("#eventRows .event").count() == EXPECTED
        page.locator("#search").fill("RBC Unlikelyterm")
        assert page.locator("#eventRows .event").count() == 0
        page.locator('[data-tab="fraud"]').click()
        page.locator("#cfpbComplaints > summary").click()
        page.wait_for_function("document.querySelectorAll('#cfpbRows .cfpb-record').length === 1")
        assert "Example Financial Services" in page.locator("#cfpbRows").inner_text()
        assert "allegation" in page.locator("#cfpbRows").inner_text().lower()
        assert "not verified misconduct" in page.locator("#cfpbComplaints").inner_text().lower()
        assert page.locator('#cfpbRows a[href="https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/12345678"]').count() == 1
        assert page.locator("#cfpbRows").locator("text=private narrative").count() == 0
        page.locator("#cfpbQuery").fill("unmatched company")
        assert page.locator("#cfpbRows .cfpb-record").count() == 0
        page.locator("#cfpbQuery").fill("Example")
        assert page.locator("#cfpbRows .cfpb-record").count() == 1
        assert page.locator('#cfpbCompany option[value="Example Financial Services"]').count() == 1
        page.locator("#cfpbCompany").select_option("Example Financial Services")
        assert page.locator("#cfpbRows .cfpb-record").count() == 1
        assert "Named companies in sample" in page.locator("#cfpbStats").inner_text()
        page.locator("#cfpbState").select_option("NY")
        assert page.locator("#cfpbRows .cfpb-record").count() == 1
        page.locator('#cfpbIssue').select_option("Managing an account")
        assert page.locator("#cfpbRows .cfpb-record").count() == 1
        page.locator("#cfpbHistoricalPanel > summary").click()
        assert "1/178 months" in page.locator("#cfpbHistorySummary").inner_text()
        assert "1,234 exact published complaints" in page.locator("#cfpbHistoryRows").inner_text()
        assert "2 sampled" in page.locator("#cfpbHistoryRows").inner_text()
        page.locator("#cfpbHistoryYear").select_option("2011")
        assert page.locator("#cfpbHistoryRows .cfpb-history-row").count() == 1
        page.locator("#cfpbHistoryIssue").select_option("Managing an account")
        assert page.locator("#cfpbHistoryRows .cfpb-history-row").count() == 1
        page.locator("#cfpbHistoricalPanel > summary").click()
        page.locator("#cfpbComplaints > summary").click()
        print("CFPB public structured complaint record and safe search/filter display: PASS")
        page.locator("#cafcOpenData > summary").click()
        page.wait_for_function("document.querySelectorAll('#cafcRows .cafc-row').length === 1")
        assert "Investment Fraud" in page.locator("#cafcRows").inner_text()
        assert "2025-09-30" in page.locator("#cafcOpenData").inner_text()
        assert "not confirmed crimes" in page.locator("#cafcOpenData").inner_text().lower()
        assert page.locator("#cafcRows").locator("text=Number ID").count() == 0
        page.locator("#cafcDimension").select_option("province")
        assert "Ontario" in page.locator("#cafcRows").inner_text()
        page.locator("#cafcSearch").fill("Not a category")
        assert page.locator("#cafcRows .cafc-row").count() == 0
        page.locator("#cafcSearch").fill("")
        page.locator("#cafcOpenData > summary").click()
        print("CAFC Canadian official reporting aggregate and evidence labels: PASS")

        page.wait_for_function("document.querySelectorAll('#fraudNational .fraud-amount').length >= 2", timeout=10000)
        print("National fraud statistics:", page.locator("#fraudNational .fraud-amount").count())
        page.locator('[data-tab="losses"]').click()
        page.wait_for_function("document.querySelector('#lossYear').options.length > 0", timeout=10000)
        assert page.locator("#institutionLossRows").inner_text().strip()
        assert page.locator("#disclosedLossRows").inner_text().strip()
        print("Yearly penalties and disclosure explanation: PASS")
        page.locator('[data-tab="overview"]').click()
        page.wait_for_function("document.querySelectorAll('#featuredIncidents .case-item').length > 0", timeout=15000)
        assert page.locator("#majorOrders .event").count() > 0
        page.wait_for_function(
            "document.querySelector('#supportCasesStatus').textContent.includes('Scan:')", timeout=15000)
        assert page.locator("#supportCases .supporting-news-item").count() > 0
        assert "Unverified news lead" in page.locator("#supportCases").text_content()
        assert "Latest reporting" in page.locator("#overviewSupportingSummary").text_content()
        assert "newest publication" in page.locator("#reviewedCasesLatest").text_content()
        page.locator('[data-tab="reports"]').click()
        page.locator("#overviewDeepDive > summary").click()
        assert page.locator("#supportCases .supporting-news-item").first.is_visible()
        assert not page.locator("#featuredIncidents .case-item").first.is_visible()
        first_reported = page.locator("#supportCases .supporting-news-meta").first.text_content()[:10]
        latest_curated = page.locator("#reviewedCasesLatest").text_content()[-10:]
        assert first_reported > latest_curated, (
            f"Fresh reporting {first_reported} must lead older reviewed cases {latest_curated}")
        page.locator("#overviewDeepDive .supporting-reviewed-details").first.locator("summary").click()
        assert page.locator("#featuredIncidents .case-item").first.is_visible()
        page.locator("#overviewDeepDive .supporting-reviewed-details").first.locator("summary").click()
        assert not page.locator("#featuredIncidents .case-item").first.is_visible()
        print("Latest reported articles are prioritized; curated Oct-23 files are secondary: PASS")
        assert "Scan:" in page.locator("#supportEnforcementStatus").text_content()
        assert "Scan:" in page.locator("#supportRegulatoryStatus").text_content()
        assert "partial year" in page.locator("#overviewFraud").text_content()
        assert "UNVERIFIED" in page.locator("#overviewFraud").text_content()
        assert page.locator("#supportCases .supporting-news-item a").first.get_attribute("href").startswith("https://")
        print("Supporting intelligence routing, evidence labels and 2026 partial-year figures: PASS")
        assert page.locator("#headlinesTop .breaking-story").count() > 0
        page.wait_for_function(
            "document.querySelector('#communitySignalHealth').textContent.includes('Reddit:')", timeout=15000)
        assert "Telegram:" in page.locator("#communitySignalHealth").text_content()
        assert "No matching social signals collected yet" in page.locator("#communitySignalRows").text_content() or page.locator("#communitySignalRows .community-signal-card").count() > 0
        assert "unverified signal" in page.locator("#communitySignalCount").text_content()
        print("Authorized social signal health and no-fabrication empty state: PASS")
        print("Featured reviewed incidents:", page.locator("#featuredIncidents .case-item").count())
        page.locator('[data-tab="incidents"]').click()
        page.wait_for_function("document.querySelectorAll('#reviewedEventRows .reviewed-card').length >= 5", timeout=15000)
        assert page.locator("#reviewedEventRows .reviewed-card").count() == 6
        assert "6" in page.locator("#reviewedSummary").inner_text()
        assert "0" in page.locator("#reviewedSummary").inner_text()
        page.locator("#reviewedSearch").fill("Scotiabank")
        assert page.locator("#reviewedEventRows .reviewed-card").count() == 1
        page.locator("#reviewedEventRows [data-reviewed-open]").first.click()
        assert "Source-supported claims" in page.locator("#drawerBody").inner_text()
        assert "What remains unanswered" in page.locator("#drawerBody").inner_text()
        assert "Cited publications and provenance" in page.locator("#drawerBody").inner_text()
        assert "Counterevidence: not_assessed" in page.locator("#drawerBody").inner_text()
        assert page.locator("#drawerBody .reviewed-source-card a").count() >= 1
        assert page.locator("#drawerBody .reviewed-timeline-step").count() >= 2
        assert "Unauthorized credit exposure" in page.locator("#drawerBody").inner_text()
        page.locator("#close").click()
        page.locator("#reviewedSearch").fill("")
        page.wait_for_function("document.querySelectorAll('#eventCandidateRows .candidate-card').length > 0", timeout=10000)
        assert "unverified" in page.locator("#eventCandidateRows").inner_text().lower()
        assert page.locator("#eventCandidateRows [data-story]").count() >= 2
        print("Source-grounded review database + explicit unverified suggestions: PASS")
        page.locator("#incidents .overview-deepdive summary").click()
        page.wait_for_function("document.querySelectorAll('#incidentRows .case-item').length > 0", timeout=10000)
        assert page.locator("#incidentRows .case-item").count() >= 5
        page.locator("#incidentSearch").fill("Scotiabank")
        assert page.locator("#incidentRows .case-item").count() == 1
        page.locator("#incidentRows [data-case-investigate]").first.click()
        assert "Reported sequence" in page.locator("#drawerBody").inner_text()
        assert "Credit exposure" in page.locator("#drawerBody").inner_text()
        assert "Investigator research prompts" in page.locator("#drawerBody").inner_text()
        assert page.locator("#drawerBody .case-step").count() >= 2
        assert page.locator("#drawerBody .case-primary-source a").count() == 1
        page.locator("#close").click()
        print("Reviewed source-backed case investigation drawer: PASS")
        page.locator('[data-tab="overview"]').click()
        page.wait_for_function("document.querySelector('#mapCountry').options.length >= 240",timeout=20000)
        assert "country and territory lenses" in page.locator("#worldCoverage").inner_text().lower()
        page.locator("#worldView").click()
        assert page.locator("#mapCountry").input_value() == ""
        page.locator("#mapCountry").select_option("US")
        assert "Jurisdiction: United States" in page.locator("#mapCaption").inner_text()
        page.locator('[data-mapmode="enforcement"]').click()
        assert page.locator("#mappedStories .map-story").count() >= 2
        assert "international agency" in page.locator("#mappedStories").inner_text().lower()
        page.locator("#mapAgency").select_option("FinCEN")
        assert "Agency: FinCEN" in page.locator("#mapCaption").inner_text()
        assert "FinCEN" in page.locator("#mappedStories").inner_text()
        page.locator("#mapAgency").select_option("")
        page.locator('[data-mapmode="all"]').click()
        page.locator("#mapCountry").select_option("GB")
        assert "Jurisdiction: United Kingdom" in page.locator("#mapCaption").inner_text()
        for code,agency in [("HK","HKMA"),("SG","MAS"),("IE","Central Bank of Ireland")]:
            page.locator("#mapCountry").select_option(code)
            # News can be more recent than enforcement and crowd it out of the
            # first 12 items. Explicitly select the regulator evidence layer.
            page.locator('[data-mapmode="enforcement"]').click()
            assert agency in page.locator("#mappedStories").inner_text()
            assert "Jurisdiction:" in page.locator("#mapCaption").inner_text()
            page.locator('[data-mapmode="all"]').click()
        # Kosovo is a separately labeled non-ISO research jurisdiction,
        # not an alleged incident location or an invented official action.
        assert page.locator("#mapCountry option[value='XK']").count() == 1
        page.locator("#mapCountry").select_option("XK")
        assert "Kosovo" in page.locator("#worldCountryBrief").inner_text()
        assert "Central Bank of Kosovo" in page.locator("#worldCountryBrief").inner_text()
        assert "0 official actions collected" in page.locator("#worldCountryBrief").inner_text()
        page.locator("#mapCountry").select_option("AF")
        assert "0 official actions collected" in page.locator("#worldCountryBrief").inner_text()
        # A country can have unverified search-market news without any official
        # enforcement. Verify the official layer separately from news discovery.
        page.locator('[data-mapmode="enforcement"]').click()
        assert page.locator("#mappedStories .map-story").count() == 0
        page.locator('[data-mapmode="all"]').click()
        page.locator('[data-tab="fraud"]').click()
        assert page.locator("#worldNewsCountry option").count() >= 240
        # The gap audit distinguishes unscanned and empty feeds from genuine
        # proof of absent fraud reporting, and links real counterexamples.
        page.locator("#worldCoverageAudit > summary").click()
        assert "empty last scan" in page.locator("#worldCoverageAuditSummary").inner_text()
        assert "not scanned" in page.locator("#worldCoverageAuditSummary").inner_text()
        assert page.locator("#worldCoverageExamples .world-coverage-example").count() == 4
        assert page.locator('#worldCoverageExamples a[href*="elpais.bo/seguridad/"]').count() == 1
        assert page.locator('#worldCoverageExamples a[href*="bom.mu/"]').count() == 1
        assert page.locator('#worldCoverageExamples a[href*="rpngc.gov.pg/"]').count() == 1
        assert page.locator('#worldCoverageExamples a[href*="dailynews.gov.bw/"]').count() == 1
        page.locator("#worldCoverageAudit > summary").click()

        assert page.locator("#worldNewsRegion option").count() == 5
        page.locator("#worldNewsRegion").select_option("africa")
        assert "matching reports shown" in page.locator("#worldNewsShown").inner_text()
        page.locator("#worldNewsRegion").select_option("southeast-asia")
        assert page.locator("#worldNewsRegion").input_value() == "southeast-asia"
        page.locator("#worldNewsRegion").select_option("")
        # The prior ASCII-boundary checker dropped concatenated Chinese
        # and Southeast Asian script headlines even when names were explicit.
        assert page.evaluate("""() => {
          const examples=[
            [{country_code:"CN",title:"中国网络诈骗案件"},{name:"China",local_country_term:"中国"}],
            [{country_code:"MY",title:"马来西亚银行诈骗"},{name:"Malaysia",local_country_term:"Malaysia",country_headline_aliases:["马来西亚"]}],
            [{country_code:"IN",title:"இந்தியா வங்கி மோசடி"},{name:"India",local_country_term:"भारत",country_headline_aliases:["இந்தியா"]}]
          ];
          return examples.every(([record,place])=>SignalNorthGeo.evaluate(record,place).referenced);
        }""")

        assert page.locator("#worldNewsQuery").count() == 1
        assert page.locator("#worldNewsCategory").count() == 1
        assert page.locator("#worldNewsShown").text_content()
        assert page.locator("#worldNewsMore").count() == 1
        assert page.locator("#localLanguageDiscovery").count() == 1
        page.locator("#localLanguageDiscovery > summary").click()
        assert "Search market is a discovery clue only" in page.locator("#localLanguageDiscovery").inner_text()
        assert page.locator("#localLanguageRows").count() == 1
        assert page.locator("#localLanguageMore").count() == 1
        page.locator("#localLanguageDiscovery > summary").click()

        page.locator('[data-tab="events"]').click()
        page.wait_for_function("document.querySelector('#worldRegulatorHealth').textContent.includes('agencies scanned')")
        assert page.locator("#worldRegRows").count() == 1
        assert page.locator("#worldRegQuery").count() == 1
        assert page.locator("#worldRegCountry").count() == 1
        assert "original-domain" in page.locator(".regulator-publications-panel").text_content().lower()
        page.locator('[data-tab="fraud"]').click()
        page.locator("#worldReportingPanel > summary").click()
        assert "country-referenced articles" in page.locator("#worldReportingSummary").text_content()
        page.locator('[data-tab="overview"]').click()
        # Synthetic browser-only record tests country search-market map attribution.
        page.evaluate("""() => {
          window.__originalWorldNewsForTest=state.worldNews;
          state.worldNews=[{id:"world-news-fixture",country_code:"FR",country:"France",
            title:"French bank fraud research example",publisher:"Test fixture only",
            published_at:"2026-10-30T12:00:00+00:00",
            url:"https://example.org/fixture",category:"Fraud and scam reporting",
            evidence_status:"unverified_news_lead"}];
          state.mapCountry="FR";document.querySelector("#mapCountry").value="FR";
          state.mapMode="news";initMap();
        }""")
        assert "Headline names France" in page.locator("#mappedStories").inner_text()
        assert "not a verified incident location" in page.locator("#mappedStories").inner_text()
        assert page.locator("#mappedStories a[href='https://example.org/fixture']").count() >= 1
        page.locator(".count-map-pin").first.click()
        assert not page.locator(".leaflet-popup").is_visible()
        assert "selected records" in page.locator("#mapSelectedContext").inner_text()
        page.locator('#mappedStories [data-mapdetail="world-news-fixture"]').click()
        assert "explicitly mentions this country" in page.locator("#mapRecordDetail").inner_text()
        assert page.locator('#mapRecordDetail a[href="https://example.org/fixture"]').count() == 1
        page.locator("#mapDetailClose").click()
        assert page.locator("#mapRecordDetail").is_hidden()
        page.locator("#mapSelectionClear").click()
        assert page.locator("#mapSelectedContext").is_hidden()
        # A Jordan RSS search must not place unrelated world stories in Jordan.
        assert page.evaluate("""() => {
          const jordan=state.worldCountries.find(c=>c.code==="JO");
          return ["Orlando man arrested in fraud","Israeli police report election fraud",
             "RCMP in Alberta investigating fraud","Former RMW worker charged with bribery scam"]
             .every(title=>!SignalNorthGeo.evaluate({country_code:"JO",country:"Jordan",title},jordan).referenced);
        }""")

        page.evaluate("""() => {
          state.worldNews=window.__originalWorldNewsForTest;
          state.mapCountry="";document.querySelector("#mapCountry").value="";
          state.mapMode="all";initMap();
        }""")
        page.locator("#worldView").click()
        page.locator('[data-tab="connections"]').click()
        page.locator(".connections-crossborder > summary").click()
        assert page.locator("#globalPatterns button").count() >= 4
        assert page.locator("#globalOrgThreads .crossborder-thread").count() >= 2
        page.locator('[data-global-entity="td"]').click()
        assert "FINTRAC" in page.locator("#mappedStories").inner_text() or "FinCEN" in page.locator("#mappedStories").inner_text()
        assert "Agency:" not in page.locator("#mapCaption").inner_text()
        print("Cross-jurisdiction TD family source links on same world map: PASS")
        page.locator("#worldView").click()
        page.locator('[data-tab="connections"]').click()
        page.locator("[data-global-pattern]").first.click()
        assert page.locator('[data-mapmode="enforcement"]').get_attribute("class") == "active"
        page.locator("#mapReset").click()
        assert page.locator("#mapCountry").input_value() == "CA"
        assert "Jurisdiction: Canada" in page.locator("#mapCaption").inner_text()
        page.locator("#worldView").click()
        print("World+Canada single map, global jurisdiction/agency/pattern filters: PASS")
        page.locator('[data-mapmode="news"]').click()
        assert "mapped" in page.locator("#mapCaption").inner_text()
        assert page.locator("#mapProvince").count() == 1
        assert page.locator("#mapStyle").count() == 1
        assert page.locator("#mapAdvancedFilters").count() == 1
        print("News, major orders, source-reviewed incidents, and cleaner map controls: PASS")
        page.wait_for_function("document.querySelectorAll('#mappedStories .map-story').length > 0", timeout=10000)
        assert page.locator("#mapMonth").count() == 1
        assert "indexed" in page.locator("#mapCoverage").inner_text().lower()
        assert page.locator(".count-map-pin").count() > 0
        print("Geographic data coverage:", page.locator("#mapCoverage").inner_text())
        assert page.locator(".count-map-pin .count-pin-inner").first.inner_text().strip().isdigit()
        page.locator("#mapAdvancedFilters > summary").click()
        assert page.locator("#mapStyle").input_value() in ("positron", "liberty", "osm")
        page.locator("#mapStyle").select_option("osm")
        assert "Classic OpenStreetMap" in page.locator("#mapBasemapStatus").text_content()
        page.locator("#mapStyle").select_option("positron")
        assert page.locator("#mapBasemapStatus").text_content()
        assert page.locator(".explore-pathways button").count() == 3
        page.locator("#mapFocus").click()
        assert page.locator("#mapFocus").get_attribute("aria-pressed") == "true"
        assert not page.locator("#mappedStories").is_visible()
        page.locator("#mapFocus").click()
        assert page.locator("#mappedStories").is_visible()
        assert page.locator(".sidebar > .nav").count() == 5
        page.locator("#mapCountMode").select_option("headlines")
        assert page.locator("#mapCountMode").input_value() == "headlines"
        assert page.locator(".count-map-pin").count() > 0
        page.locator("#mapCountMode").select_option("groups")
        print("Map count modes for reporting groups vs underlying headlines: PASS")
        if page.locator("#mapStoryAll").is_visible():
            page.locator("#mapStoryAll").click()
            assert page.locator("#mappedStories .map-story").count() > 500
            page.locator("#mappedStories .map-story button[data-story]").first.click()
            assert "Original reporting and headline variations" in page.locator("#drawerBody").inner_text()
            page.locator("#close").click()
            print("All map-adjacent article titles are accessible: PASS")

        page.locator("#mapStoryScope").select_option("mapped")
        assert page.locator('#mappedStories button[data-mapfocus]').count() > 0
        page.locator("#mapStoryScope").select_option("all")
        known_location = page.locator("#mappedStories [data-mapfocus]").first.get_attribute("data-mapfocus")
        assert known_location
        assert page.locator("#mapTopic option").count() >= 2
        page.locator("#mapYearFrom").select_option("2023")
        page.locator("#mapYearTo").select_option("2026")
        assert "2023–2026" in page.locator("#mapCaption").inner_text()
        assert page.locator("#mapFilteredTrend .map-year-unit").count() >= 5
        page.locator("#mapYearFrom").select_option("")
        page.locator("#mapYearTo").select_option("")
        page.locator("#mapMonth").fill("2026-03")
        assert "2026-03" in page.locator("#mapCaption").inner_text()
        page.locator("#mapClearMonth").click()
        page.locator("#mapTopic").select_option(index=1)
        page.locator("#mapYearFrom").select_option("2020")
        page.locator("#mapYearTo").select_option("2020")
        page.evaluate("""id => {
            const control = document.createElement('button');
            control.dataset.mapfocus = id;
            document.body.appendChild(control);
            control.click();
            control.remove();
        }""", known_location)
        assert page.locator("#mapTopic").input_value() == ""
        assert page.locator("#mapYearFrom").input_value() == ""
        assert page.locator("#mapYearTo").input_value() == ""
        assert page.locator("#mappedStories [data-mapfocus]").count() > 0
        print("Article-to-map navigation clears conflicting filters: PASS")
        page.locator('[data-tab="fraud"]').click()
        page.wait_for_function("document.querySelector('#newsYear').options.length > 1", timeout=15000)
        print("News archive count:", page.locator("#archiveCount").inner_text())
        if (ROOT / "data" / "news_archive.json").exists():
            archive = json.loads((ROOT / "data" / "news_archive.json").read_text())
            assert len(archive["leads"]) >= 300
            assert "reporting groups" in page.locator("#archiveCount").inner_text()
            first_page = page.locator("#newsRows .news-item").count()
            assert first_page == 100, f"Expected paginated 100 stories, got {first_page}"
            page.locator("#newsMore").click()
            assert page.locator("#newsRows .news-item").count() == 200
            print("Historic archive pagination: PASS")
        if (ROOT / "data" / "article_index.json").exists():
            index = json.loads((ROOT / "data" / "article_index.json").read_text())
            assert index["unique_headlines"] == len(index["articles"])
            assert index["unique_headlines"] >= 500
            assert "indexed headlines" in page.locator("#archiveCount").inner_text()
            print("Unified multi-source article index:", index["unique_headlines"])
            grouped_path = ROOT / "data" / "reporting_groups.json"
            if grouped_path.exists():
                groups = json.loads(grouped_path.read_text())
                assert groups["original_index_headlines"] == index["unique_headlines"]
                assert sum(x["underlying_headline_count"] for x in groups["groups"]) == index["unique_headlines"]
                assert groups["reporting_groups"] <= groups["original_index_headlines"]
                assert groups["multi_report_groups"] >= 1
                assert page.locator("#newsRows .news-item").count() == 200
                page.locator("#newsRows button[data-story]").first.click()
                page.wait_for_function("!document.querySelector('#overlay').classList.contains('hidden')")
                assert "Original reporting and headline variations" in page.locator("#drawerBody").inner_text()
                assert page.locator("#drawerBody .report-version").count() >= 1
                assert page.locator("#drawerBody .report-version a").first.get_attribute("href").startswith("https://")
                page.locator("#close").click()
                assert page.locator("#overlay").get_attribute("class").find("hidden")>=0
                print("Reporting group click-to-compare and immutable original records: PASS")



        if page.locator("#newsAll").is_visible():
            page.locator("#newsAll").click()
            assert page.locator("#newsRows .news-item").count() >= 200
            print("Full headline list: PASS")
        page.locator("#newsYear").select_option("2026")
        assert page.locator("#newsRows .news-item").count() > 0
        page.locator(".nav-datasets").nth(1).locator("summary").click()
        page.locator('[data-tab="clients"]').click()
        page.locator("#clientName").fill("Royal Bank of Canada")
        page.locator("#clientAdd").click()
        assert page.locator("#clientWatchlist .client-item").count() >= 1
        assert "Royal Bank of Canada" in page.locator("#clientWatchlist").inner_text()
        bg=page.evaluate("getComputedStyle(document.body).backgroundColor")
        assert bg in ("rgb(243, 246, 250)","rgb(255, 255, 255)","rgb(251, 252, 253)","rgb(245, 247, 248)","rgb(245, 248, 249)"),f"Expected light theme, got {bg}"
        if (ROOT / "data" / "institution_intelligence.json").exists():
            page.locator('[data-tab="connections"]').click()
            page.wait_for_function("document.querySelectorAll('#connectInstitution option').length > 5", timeout=20000)
            page.locator("#connectSearch").fill("Royal Bank")
            page.locator("#connectInstitution").select_option("rbc")
            assert "Royal Bank of Canada" in page.locator("#connectContent").inner_text()
            assert page.locator("#connectContent .evidence-enforcement").count() > 0
            assert page.locator("#connectContent .evidence-incident").count() > 0
            assert page.locator("#reviewRows [data-review-status]").count() > 0
            page.locator("#reviewRows [data-review-status]").first.select_option("In review")
            assert page.locator("#reviewRows [data-review-status]").first.input_value() == "In review"
            with page.expect_download() as download_info:
                page.locator("#connectExport").click()
            download = download_info.value
            assert "rbc" in download.suggested_filename
            print("Source-linked research brief export: PASS")
            page.locator("#connectTrack").click()
            assert "Royal Bank of Canada" in page.locator("#clientWatchlist").inner_text()
            assert page.locator('#clientWatchlist button[data-open-connection]').count() > 0
            page.locator('[data-tab="connections"]').click()
            page.locator("#connectInstitution").select_option("rbc")
            page.locator("#connectMap").click()
            assert "Organization: Royal Bank of Canada" in page.locator("#mapCaption").inner_text()
            print("Institution graph, evidence provenance, triage, watchlist, alias-aware map: PASS")
        page.locator('[data-tab="reports"]').click()
        page.wait_for_function("document.querySelectorAll('#libraryRows .library-record').length >= 10", timeout=12000)
        assert page.locator("#lossTrend .loss-trend-row").count() >= 6
        page.locator("#librarySearch").fill("ombudsman")
        assert page.locator("#libraryRows .library-record").count() >= 1
        page.locator("#librarySearch").fill("")
        assert page.locator("#libraryCount").inner_text()
        page.locator('[data-tab="overview"]').click()
        assert page.locator(".sidebar > .nav").count() == 5  # Main navigation is focused; specialist tools remain accessible
        assert page.locator("#metrics .metric").count() == 4
        page.locator('[data-tab="themes"]').click()
        page.wait_for_function("document.querySelectorAll('#themeGrid .theme-matrix-row').length >= 8", timeout=12000)
        assert page.locator("#themeYearCoverage > div").count() == 7
        assert page.locator("#themeCompareChart .compare-year").count() == 7
        page.locator("#themeCompareMode").select_option("count")
        assert "indexed headlines" in page.locator("#themeCompareChart").inner_text()
        page.locator("#themeCompareMode").select_option("share")
        assert "%" in page.locator("#themeCompareChart").inner_text()
        print("Theme comparisons use coverage share or raw counts, and flag 2026 YTD: PASS")
        page.locator("#themeChoose").select_option("Investment & crypto scams")
        assert "Investment & crypto" in page.locator("#themeExamplesTitle").inner_text()
        page.locator("#themeYear").select_option("2025")
        page.locator("#themeToMap").click()
        assert page.locator("#mapTopic").input_value() == "Investment & crypto scams"
        assert page.locator("#mapYearFrom").input_value() == "2025"
        assert page.locator("#mapYearTo").input_value() == "2025"
        assert "2025" in page.locator("#mapCaption").inner_text()
        assert page.locator("#mapStorySummary").inner_text()
        page.locator('[data-tab="themes"]').click()
        page.locator("#themeToStories").click()
        assert page.locator("#newsTheme").input_value() == "Investment & crypto scams"
        assert page.locator("#newsYear").input_value() == "2025"
        assert page.locator("#newsRows .news-item").count() > 0
        page.locator('[data-tab="themes"]').click()
        page.locator("#themeYear").select_option("")
        print("Cross-page scam theme and year filter synchronization: PASS")
        page.locator('[data-tab="sectors"]').click()
        page.wait_for_function("document.querySelectorAll('#sectorEntries .sector-item').length >= 10", timeout=12000)
        page.locator("#sectorSearch").fill("Wealthsimple")
        assert page.locator("#sectorEntries .sector-item").count() >= 2
        page.locator("#sectorSearch").fill("")
        page.locator("#sectorFilter").select_option("Casinos & gaming")
        assert page.locator("#sectorEntries .sector-item").count() >= 4
        page.locator('[data-tab="community"]').click()
        assert page.locator(".contribution-card").count() == 3
        assert "not anonymous" in page.locator("#community").inner_text().lower()
        assert page.locator('a[href*="template=public-source.yml"]').count() == 1
        page.locator('[data-tab="overview"]').click()
        assert page.locator('[data-tab="community"]').count() >= 1
        print("Themes, Wealthsimple, gaming, community safety and navigation: PASS")
        print("Research reports, CAFC historical trend, and simplified consultant workflow: PASS")
        print("Client watchlists, historical filters, linked map, light theme: PASS")
        # CDN failure may remove the basemap, but must not erase the archive.
        offline = browser.new_page()
        offline.route("**/leaflet@1.9.4/dist/leaflet.js", lambda route: route.abort())
        offline.goto(url, wait_until="domcontentloaded", timeout=20000)
        offline.wait_for_function("document.querySelector('#mapCoverage').textContent.includes('indexed')", timeout=15000)
        assert offline.locator("#mappedStories .map-story").count() > 0
        assert "Map library unavailable" in offline.locator("#mapCaption").inner_text()
        offline.close()
        print("Map-CDN outage preserves the article archive: PASS")
        assert not errors, str(errors)
        print("Browser smoke test: PASS")
        browser.close()
finally:
    server.shutdown()
