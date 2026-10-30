#!/usr/bin/env python3
"""Opt-in social FRAUD DISCOVERY, never evidence of institutional wrongdoing.

Reddit: approved OAuth API access only. No unauthorized scraping.
Telegram: dedicated Bot API bot, explicitly whitelisted PUBLIC channels only.
Publish only coarse topic labels and links, never raw user text or authors.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = DATA / "community_sources.json"
OUTPUT = DATA / "community_signals.json"
STATUS = DATA / "community_status.json"
STATE = DATA / "community_state.json"
MAX_DAYS = 7
MAX_SIGNALS = 150

THEMES = [
    ("Bank impersonation", re.compile(r"\b(impersonat\w*|spoof\w*|fake (?:bank|support|agent)|fraud department call|fake customer service)\b", re.I)),
    ("Phishing / smishing", re.compile(r"\b(phish\w*|smish\w*|malicious link|fake (?:website|email|text|login)|credential harvest)\b", re.I)),
    ("Account takeover", re.compile(r"\b(account takeover|account hack\w*|hacked (?:account|bank)|unauthori[sz]ed login|otp|2fa|one.time password|verification code)\b", re.I)),
    ("Payment / e-transfer", re.compile(r"\b(e.transfers?|interac|wire fraud|unauthori[sz]ed transfer|payment scam|ach fraud|zelle)\b", re.I)),
    ("Investment / crypto scam", re.compile(r"\b(investment scam|crypto scam|pig butcher\w*|fake investment|romance investment)\b", re.I)),
    ("Identity fraud", re.compile(r"\b(identity theft|identity fraud|stolen identity|synthetic identity)\b", re.I)),
    ("Other scam warning", re.compile(r"\b(scam\w*|fraud\w*|fraude|escroquerie|arnaque|money mule|stolen funds|money laundering)\b", re.I)),
]
RELEVANT = re.compile(
    r"\b(fraud\w*|scam\w*|phish\w*|smish\w*|impersonat\w*|spoof\w*|"
    r"money laundering|money mule|account takeover|hacked account|unauthori[sz]ed|"
    r"identity theft|stolen funds|e.transfer|interac|otp|2fa|fraude|arnaque|escroquerie)\b", re.I
)
BANKS = {
    "Wealthsimple": ["wealthsimple"],
    "TD Bank": ["td bank", "td canada trust", "toronto-dominion"],
    "RBC": ["rbc", "royal bank of canada"],
    "Scotiabank": ["scotiabank", "bank of nova scotia"],
    "CIBC": ["cibc", "simplii"],
    "BMO": ["bmo", "bank of montreal"],
    "Tangerine": ["tangerine"],
    "Desjardins": ["desjardins"],
    "National Bank of Canada": ["national bank of canada"],
    "Interac": ["interac"],
    "Zelle": ["zelle"],
    "Chase": ["chase bank", "jpmorgan chase"],
    "Bank of America": ["bank of america"],
}
COUNTRY_MARKERS = [
    ("CA", re.compile(r"\b(canada|canadian|ontario|quebec|québec|toronto|montreal|vancouver|interac)\b", re.I)),
    ("US", re.compile(r"\b(united states|usa|u\.s\.a\.|u\.s\.|american|zelle)\b", re.I)),
]

def utcnow():
    return datetime.now(timezone.utc)

def timestamp(date):
    return date.astimezone(timezone.utc).isoformat(timespec="seconds")

def read(path, fallback):
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return fallback

def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", "utf-8")

def mention(text, phrase):
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I) is not None

def classify(text):
    """Derive non-personal, conservative labels. Do NOT retain input text."""
    if not isinstance(text, str) or not RELEVANT.search(text):
        return None
    institutions = [name for name, aliases in BANKS.items() if any(mention(text, alias) for alias in aliases)]
    named_impersonation = bool(institutions) and bool(re.search(
        r"\b(fake|spoof\w*|impersonat\w*|pretend\w*|posing as|posed as)\b", text, re.I))
    topic = "Bank impersonation" if named_impersonation else next(
        (label for label, rx in THEMES if rx.search(text)), "Other scam warning")
    countries = [country for country, rx in COUNTRY_MARKERS if rx.search(text)]
    country = countries[0] if len(countries) == 1 else None
    return {"topic": topic, "institutions_mentioned": institutions[:5], "country_hint": country}

def make_signal(platform, community, source_url, text, date, now=None):
    now = now or utcnow()
    if not isinstance(date, datetime) or date.tzinfo is None or not (now - timedelta(days=MAX_DAYS) <= date <= now + timedelta(hours=1)):
        return None
    labels = classify(text)
    parts = urlsplit(str(source_url))
    if not labels or parts.scheme != "https" or not parts.netloc:
        return None
    if platform == "reddit" and parts.netloc != "www.reddit.com":
        return None
    if platform == "telegram" and parts.netloc != "t.me":
        return None
    event_id = hashlib.sha256((platform + "|" + source_url).encode()).hexdigest()[:20]
    return {
        "id": "community-" + event_id,
        "platform": platform,
        "community": community,
        "source_url": source_url,
        "published_at": timestamp(date),
        "topic": labels["topic"],
        "institutions_mentioned": labels["institutions_mentioned"],
        "country_hint": labels["country_hint"],
        "label": "Public post concerning " + labels["topic"].lower(),
        "evidence_status": "unverified_social_signal",
        "review_status": "not_reviewed",
        "source_provenance": "authorized_api_metadata",
        "notice": "Not proof of an incident, fraud losses or any named institution's liability. No author or raw message content stored.",
    }

def reddit_scan(config, now):
    communities = [x for x in config.get("reddit_communities", []) if re.fullmatch(r"[A-Za-z0-9_]{2,21}", str(x))]
    approved = os.getenv("REDDIT_API_APPROVED") == "1"
    client, secret = os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")
    agent = os.getenv("REDDIT_USER_AGENT")
    if not approved:
        return [], {"status": "pending_approval", "reason": "Approved Reddit API usage is required; no scraping performed."}
    if not (client and secret and agent and "by /u/" in agent):
        return [], {"status": "not_configured", "reason": "Need approved OAuth app credentials and identifiable User-Agent."}
    if not communities:
        return [], {"status": "no_communities"}
    session = requests.Session()
    token_resp = session.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client, secret), data={"grant_type": "client_credentials"},
        headers={"User-Agent": agent}, timeout=20
    )
    token_resp.raise_for_status()
    token = token_resp.json()["access_token"]
    headers = {"Authorization": "bearer " + token, "User-Agent": agent}
    result, problems = [], []
    for community in communities[:8]:
        try:
            response = session.get(
                "https://oauth.reddit.com/r/" + community + "/new",
                headers=headers, params={"limit": 75, "raw_json": 1},
                timeout=20
            )
            response.raise_for_status()
            posts = response.json().get("data", {}).get("children", [])
            for entry in posts:
                item = entry.get("data", {})
                if item.get("over_18") or item.get("removed_by_category") or item.get("is_self") is False and not item.get("title"):
                    continue
                post_id = str(item.get("id") or "")
                if not re.fullmatch(r"[a-z0-9]{5,10}", post_id):
                    continue
                title = str(item.get("title") or "")
                # Avoid bodies, usernames, comments, user IDs and sensitive details.
                date = datetime.fromtimestamp(float(item.get("created_utc") or 0), timezone.utc)
                url = "https://www.reddit.com/r/" + community + "/comments/" + post_id + "/"
                signal = make_signal("reddit", "r/" + community, url, title, date, now)
                if signal:
                    result.append(signal)
        except (requests.RequestException, ValueError, KeyError) as exc:
            problems.append(community + ": " + type(exc).__name__)
    return result, {
        "status": "partial" if problems else "ok",
        "communities_checked": len(communities[:8]),
        "accepted": len(result),
        "errors": problems[:8]
    }

def telegram_scan(config, state, now):
    bot = os.getenv("TELEGRAM_BOT_TOKEN")
    dedicated = os.getenv("TELEGRAM_DEDICATED_BOT") == "1"
    channels = [str(x).lstrip("@").lower() for x in config.get("telegram_channels", [])
                if re.fullmatch(r"@?[A-Za-z0-9_]{5,32}", str(x))]
    if not (bot and dedicated):
        return [], {"status": "not_configured", "reason": "Dedicated Bot API token and explicit opt-in required."}
    if not channels:
        return [], {"status": "no_channels", "reason": "Whitelist public channels where the bot has been added."}
    if not re.fullmatch(r"\d{5,15}:[\w-]{25,}", bot):
        return [], {"status": "invalid_token_format"}
    api = "https://api.telegram.org/bot" + bot
    # Do not print request URLs, exceptions or response bodies: they contain a bot token.
    session = requests.Session()
    try:
        webhook = session.get(api + "/getWebhookInfo", timeout=20).json()
        if not webhook.get("ok") or webhook.get("result", {}).get("url"):
            return [], {"status": "webhook_conflict", "reason": "Use a dedicated bot without an active webhook."}
        offset = max(0, int(state.get("telegram_next_update_id", 0)))
        response = session.get(api + "/getUpdates", params={
            "offset": offset, "limit": 100, "timeout": 0,
            "allowed_updates": json.dumps(["channel_post", "edited_channel_post"])
        }, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            return [], {"status": "api_error"}
        result = []
        for update in payload.get("result", []):
            offset = max(offset, int(update.get("update_id", 0)) + 1)
            post = update.get("channel_post") or update.get("edited_channel_post") or {}
            chat = post.get("chat") or {}
            username = str(chat.get("username") or "").lower()
            if chat.get("type") != "channel" or username not in channels:
                continue
            mid = post.get("message_id")
            if not isinstance(mid, int) or mid <= 0:
                continue
            # Only a public channel's own posts are accepted. No private messages or group chats.
            raw_text = str(post.get("text") or post.get("caption") or "")
            date = datetime.fromtimestamp(float(post.get("date") or 0), timezone.utc)
            link = "https://t.me/" + username + "/" + str(mid)
            signal = make_signal("telegram", "@" + username, link, raw_text, date, now)
            if signal:
                result.append(signal)
        state["telegram_next_update_id"] = offset
        return result, {"status": "ok", "whitelisted_channels": len(channels),
                        "accepted": len(result)}
    except (requests.RequestException, ValueError, KeyError) as exc:
        return [], {"status": "api_error", "error_type": type(exc).__name__}

def run():
    DATA.mkdir(parents=True, exist_ok=True)
    now = utcnow()
    config = read(CONFIG, {})
    state = read(STATE, {})
    prior = read(OUTPUT, {}).get("signals", [])
    status = {"last_attempt_at": timestamp(now), "retention_days": MAX_DAYS, "sources": {}}
    try:
        reddit, status["sources"]["reddit"] = reddit_scan(config, now)
    except (requests.RequestException, ValueError, KeyError) as exc:
        reddit = []
        status["sources"]["reddit"] = {"status": "api_error", "error_type": type(exc).__name__}
    telegram, status["sources"]["telegram"] = telegram_scan(config, state, now)
    # Reddit results are a current API snapshot, not an indefinite archive.
    # Telegram bot results arrive incrementally and live for at most 7 days.
    retained = [x for x in prior if x.get("platform") == "telegram" and
                x.get("evidence_status") == "unverified_social_signal" and
                isinstance(x.get("published_at"), str) and
                timestamp(now - timedelta(days=MAX_DAYS)) <= x["published_at"] <= timestamp(now)]
    # When an approved collector is temporarily unavailable, do not assert that old
    # Reddit links are current or retain potentially removed Reddit content.
    merged = {}
    for item in retained + telegram + reddit:
        if item.get("id"):
            merged[item["id"]] = item
    out = sorted(merged.values(), key=lambda x: x["published_at"], reverse=True)[:MAX_SIGNALS]
    write(OUTPUT, {
        "updated_at": timestamp(now),
        "methodology": "Approved public-source, short-retention metadata only. No author, raw post text, private messages or inferred bank wrongdoing.",
        "signals": out
    })
    write(STATE, state)
    status["stored_signals"] = len(out)
    status["last_completed_at"] = timestamp(now)
    write(STATUS, status)
    print(json.dumps({"stored_signals": len(out), "source_status":
                      {k: v.get("status") for k, v in status["sources"].items()}}))
    return 0

if __name__ == "__main__":
    raise SystemExit(run())
