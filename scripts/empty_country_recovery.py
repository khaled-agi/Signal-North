"""Alternative country names and fraud terms for a bounded empty-market retry.

These are *search hints* only, not country-to-incident geolocation evidence.
A failed Google News query never confirms the absence of financial crime news.
"""
from __future__ import annotations

# Known alternative country names, local demonyms, official names or abbreviations
# in markets that previously had no accepted country-referenced news.
RECOVERY_ALIASES={
 "BO":("Bolivia","boliviana","estafas"),
 "BW":("Botswana","Botswana","bank fraud"),
 "MU":("Mauritius","Maurice","arnaque"),
 "PG":("Papua New Guinea","PNG","fraud"),
 "NI":("Nicaragua","nicaragüense","estafas"),
 "CV":("Cabo Verde","Cabo Verde","burla"),
 "DJ":("Djibouti","جيبوتي","احتيال"),
 "MR":("Mauritania","موريتانيا","احتيال"),
 "ML":("Mali","Mali","escroquerie"),
 "NE":("Niger","Niger","escroquerie"),
 "SI":("Slovenia","Slovenija","goljufija"),
 "ST":("São Tomé and Príncipe","São Tomé","burla"),
 "FM":("Micronesia","FSM","scam"),
 "KM":("Comoros","Comores","escroquerie"),
 "GF":("French Guiana","Guyane","escroquerie"),
 "GP":("Guadeloupe","Guadeloupe","arnaque"),
 "MQ":("Martinique","Martinique","arnaque"),
 "RE":("Réunion","Réunion","arnaque"),
 "NC":("New Caledonia","Nouvelle-Calédonie","escroquerie"),
 "PF":("French Polynesia","Polynésie française","arnaque"),
 "AI":("Anguilla","Anguilla","bank scam"),
 "CK":("Cook Islands","Cook Islands","fraud"),
 "TT":("Trinidad and Tobago","Trinidad","bank fraud"),
 "SR":("Suriname","Suriname","oplichting"),
 "SL":("Sierra Leone","Sierra Leone","financial fraud"),
 "VG":("British Virgin Islands","BVI","fraud"),
 "VI":("U.S. Virgin Islands","Virgin Islands","fraud"),
}
# Evidence that the collector was previously too restrictive, not seeded map
# incidents. Source review must remain separate from the news index.
RETRY_DAYS=90
EXTRA_RETRY_PER_RUN=8

def recovery_queries(profile):
    """One longer-lookback English query and one local/alternate query.

    Per-market recovery runs are bounded and must retain the same headline
    country-evidence rules as the ordinary collector.
    """
    code=profile["code"]
    name=profile["name"].replace('"',"")
    alias=RECOVERY_ALIASES.get(code)
    queries=[f'"{name}" (fraud OR scam OR estafa OR arnaque OR financial crime) when:{RETRY_DAYS}d']
    if alias:
        local_name=alias[1].replace('"',"")
        term=alias[2]
        queries.append(f'{term} "{local_name}" when:{RETRY_DAYS}d')
    elif profile.get("local_term") and profile.get("local_country_term"):
        queries.append(f'{profile["local_term"]} "{profile["local_country_term"]}" when:{RETRY_DAYS}d')
    return list(dict.fromkeys(queries))[:2]

def choose_gap_batch(profiles,existing_status,already_selected,cursor,count=EXTRA_RETRY_PER_RUN):
    """Attempt not-yet-scanned markets, then empty/error markets, fairly.

    These are extra scans and cannot displace the 32-country world rotation.
    Never label a country news-free because a particular query found nothing.
    """
    selected={p["code"] for p in already_selected}
    pending=[]
    empty=[]
    for p in profiles:
        if p["code"] in selected:continue
        status=existing_status.get(p["code"],{})
        if not status.get("attempted_at"):
            pending.append(p)
        elif status.get("state") in ("attempted_empty","partial_error","error"):
            empty.append(p)
    # Keep the not-attempted first, but rotate across failed/empty markets.
    pending.sort(key=lambda p:p["code"])
    empty.sort(key=lambda p:p["code"])
    if not (pending or empty):return [],int(cursor)
    size=max(0,int(count))
    out=pending[:size]
    if len(out)<size and empty:
        start=int(cursor)%len(empty)
        choose=min(len(empty),size-len(out))
        out.extend(empty[(start+i)%len(empty)] for i in range(choose))
        cursor=(start+choose)%len(empty)
    return out,int(cursor)
