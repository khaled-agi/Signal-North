#!/usr/bin/env python3
"""Bounded 2011–present CFPB monthly source history with explicit completeness.

Each monthly CFPB API request returns at most 100 PUBLIC complaints; an exact
hits.total (relation=eq) is a MONTH TOTAL, whereas the issue breakdown derived
from those 100 is explicitly a NONREPRESENTATIVE SAMPLE. Never conflate them.
No consumer narratives, ZIPs, direct identifiers except CFPB complaint IDs.
"""
from __future__ import annotations
import calendar
import json,os
from collections import Counter
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import requests
try:
 from . import collect_cfpb_complaints as c
except ImportError:
 import collect_cfpb_complaints as c

BASE=c.BASE
DATA=c.DATA
OUT=DATA/"cfpb_monthly_history.json"
STATUS=DATA/"cfpb_monthly_history_status.json"
STATE=DATA/"cfpb_monthly_history_state.json"
FIRST=(2011,12)
BATCH=6
MIN_PUBLICATION_LAG_DAYS=17
SOURCE="CFPB Consumer Complaint Database API"

def month_sequence(now):
 """Return complete calendar months in descending order from 2011-12.

 Recent months are not considered complete until at least 17 days after their
 final calendar day. CFPB eligibility and publication can still change later.
 """
 limit=(now.date()-timedelta(days=MIN_PUBLICATION_LAG_DAYS)).replace(day=1)
 # If on Oct 30, a Sep 30 month meets 17-day lag; Oct is open.
 y,m=limit.year,limit.month
 # Exclude the month containing the lagged date.
 if m==1:y,m=y-1,12
 else:m-=1
 rows=[]
 while (y,m)>=FIRST:
  rows.append(f"{y:04d}-{m:02d}")
  if m==1:y,m=y-1,12
  else:m-=1
 return rows

def boundaries(month):
 year,number=(int(x) for x in month.split("-"))
 if not (2011<=year<=2100 and 1<=number<=12):raise ValueError("bad month")
 start=f"{year:04d}-{number:02d}-01"
 if number==12:end=f"{year+1:04d}-01-01"
 else:end=f"{year:04d}-{number+1:02d}-01"
 return start,end

def monthly_query(month,session=None):
 session=session or requests.Session()
 start,end=boundaries(month)
 response=session.get(BASE,params={
  "size":c.API_PAGE_SIZE,
  "sort":"created_date_desc",
  "date_received_min":start,
  "date_received_max":end, # API max is EXCLUSIVE
  "no_aggs":"true",
  "no_highlight":"true"
 },headers={
  "User-Agent":"SignalNorthResearch/1.0 (+https://github.com/khaled-agi/Signal-North)",
  "Accept":"application/json",
 },timeout=35)
 response.raise_for_status()
 if len(response.content)>3_000_000:raise ValueError("unusually large CFPB response")
 rows,total=c.unpack(response.json())
 # API filters may be subject to implementation changes: verify the date range.
 returned_rows=len(rows)
 raw_dates=[r["date_received"] for r in rows]
 outside_window=sum(not (start<=r["date_received"]<end) for r in rows)
 rows=[r for r in rows if start<=r["date_received"]<end]
 # The official API says date_received_max is exclusive, but do NOT assume
 # the returned hit total is date-correct if its example rows contradict it
 # or if it reports records yet the reconstructed public examples are empty.
 verified_scope=outside_window==0 and (bool(rows) or total==0)
 count_status=("exact_api_total" if verified_scope and total is not None else
   "unverified_date_scope" if not verified_scope else "unknown_api_total")
 reported_total=total if count_status=="exact_api_total" else None
 by_issue=Counter((r.get("issue") or "Not specified",r.get("sub_issue") or "") for r in rows)
 by_product=Counter(r.get("product") or "Not specified" for r in rows)
 return {
  "month":month,"date_received_min":start,"date_received_max_exclusive":end,
  "exact_published_complaint_total":reported_total,
  "monthly_total_status":count_status,
  "api_returned_count":returned_rows,
  "api_returned_date_min":min(raw_dates) if raw_dates else None,
  "api_returned_date_max":max(raw_dates) if raw_dates else None,
  "api_hits_outside_requested_month":outside_window,
  "scope_warning":"CFPB page date scope not verified; count withheld" if not verified_scope else None,
  "sample_size":len(rows),"page_limit":c.API_PAGE_SIZE,
  "sample_issue_breakdown":[{"issue":issue,"sub_issue":sub,"sample_count":n}
    for (issue,sub),n in by_issue.most_common(12)],
  "sample_product_breakdown":[{"product":product,"sample_count":n}
    for product,n in by_product.most_common(12)],
  "sample_basis":"Most recently indexed <=100 public complaints for month; NOT full issue/product counts",
  "source":SOURCE,"source_url":BASE,
  "last_checked_at":c.stamp(),
 }

def run():
 clock=c.utcnow()
 months=month_sequence(clock)
 prev=c.read(OUT,{"months":[]})
 valid=set(months)
 # Refresh any previous entries when queried again; retain exact historical
 # results rather than rolling them off after 90 days.
 stored={}
 for entry in prev.get("months",[]):
  if not isinstance(entry,dict) or entry.get("month") not in valid:continue
  entry=dict(entry)
  # Prior backfill accepted a monthly hits.total even when no dated complaint
  # from its first page matched that month. Such counts are not defensible.
  if (entry.get("monthly_total_status")=="exact_api_total"
      and (entry.get("sample_size") or 0)==0
      and (entry.get("exact_published_complaint_total") or 0)>0):
   entry["monthly_total_status"]="unverified_date_scope"
   entry["exact_published_complaint_total"]=None
   entry["scope_warning"]="Prior API month count withheld: page had no matching dated examples"
  stored[entry["month"]]=entry
 progress=c.read(STATE,{"next_cursor":0})
 cursor=int(progress.get("next_cursor",0))%len(months) if months else 0
 batch=min(max(int(os.environ.get("CFPB_HISTORY_BATCH",str(BATCH))),0),12)
 selected=[months[(cursor+i)%len(months)] for i in range(min(batch,len(months)))]
 health={"last_attempt_at":c.stamp(clock),"status":"not_attempted",
  "months_available":len(months),"months_with_results":len(stored),
  "first_possible_month":"2011-12","source":SOURCE,
  "methodology":"Month totals only when API hits.total relation=eq; issue/product breakdown is capped first-page sample, NOT a total or representative sample",
  "monthly_request_cap":c.API_PAGE_SIZE,"selected_months":selected,
  "errors":{},
 }
 if os.environ.get("CFPB_HISTORY_OFFLINE")=="1":
  health["status"]="offline_not_scanned"
 else:
  ok=0
  for month in selected:
   try:
    entry=monthly_query(month)
    stored[month]=entry;ok+=1
   except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
    health["errors"][month]=type(exc).__name__
  health["status"]="ok" if ok==len(selected) else "partial_error" if ok else "error"
  health["months_fetched_this_run"]=ok
  health["months_failed_this_run"]=len(selected)-ok
  # Advance regardless of failure; next rotation retries unfilled months.
  c.save(STATE,{"next_cursor":(cursor+len(selected))%len(months) if months else 0})
 results=sorted(stored.values(),key=lambda x:x["month"])
 health["months_with_results"]=len(results)
 health["months_with_exact_totals"]=sum(x.get("monthly_total_status")=="exact_api_total" for x in results)
 health["months_with_unverified_counts"]=sum(x.get("monthly_total_status")=="unverified_date_scope" for x in results)
 health["earliest_fetched_month"]=results[0]["month"] if results else None
 health["latest_fetched_month"]=results[-1]["month"] if results else None
 c.save(OUT,{
  "updated_at":c.stamp(clock),"source":SOURCE,"earliest_possible_month":"2011-12",
  "months":results,
  "methodology":"Only month totals with exact API counts are population counts. Each month's issue and product categories reflect up to 100 most recently indexed complaints and are nonrepresentative. Not all historical months have been downloaded.",
 })
 c.save(STATUS,health)
 print(json.dumps({k:health[k] for k in ("status","months_available","months_with_results","months_with_exact_totals")}))
if __name__=="__main__":run()
