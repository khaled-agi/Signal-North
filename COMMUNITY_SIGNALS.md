# Community fraud signals (Reddit and Telegram)

This is a **source-licensed, opt-in early-warning collection feature**, not an incident database.

## Why this layer exists
Public discussions can reveal emerging phishing lures, fake bank support calls, stolen credentials,
payment-account takeovers and new scam narratives. Posts are **not verified** and may be inaccurate,
coordinated or malicious. No social post can automatically create an enforcement record, source-reviewed
incident, individual victim profile or bank control-failure allegation.

Signal North keeps this layer distinct from:
- regulator-published enforcement,
- source-reviewed cases,
- syndicated news discovery, and
- official reported-loss statistics.

## Reddit approval and configuration

Reddit's 2026 Responsible Builder Policy requires **explicit approved API access**. Business/commercial
use requires additional express written approval. Academic research uses Reddit's dedicated Reddit for
Researchers (RFR) program, not the normal developer API. Do **not** scrape Reddit or use unauthenticated
JSON endpoints, alternate IPs, unofficial APIs, or multiple credentials to circumvent limits.

Only after approval for this exact use case, configure repository Actions secrets and variables:

| Name | GitHub Actions setting | Purpose |
| --- | --- | --- |
| `REDDIT_API_APPROVED` | Variable, set to `1` after approved | Prevent unapproved collection |
| `REDDIT_CLIENT_ID` | Secret | Approved OAuth client |
| `REDDIT_CLIENT_SECRET` | Secret | Approved OAuth secret |
| `REDDIT_USER_AGENT` | Variable | Distinct app/version with `(by /u/username)` |

Approved communities live in `data/community_sources.json`. The initial candidate list includes
`r/Scams`, `r/PersonalFinanceCanada`, `r/Wealthsimple`, `r/phishing`, `r/rbc`, `r/CIBC`, and `r/Scotiabank`.
The first collector reads only the official OAuth /new endpoint, filters recent titles **in memory**,
and publishes only topic labels, institution references, dates and source links. It never stores
post body, user handles, comment text, private messages, direct-message contacts or raw headlines.
An institution reference means **only that it was named in a post**.

To avoid long-lived copies of deleted content, Reddit posts are not persisted between scans.
The site will show the current approved scan, if available, not a comprehensive historic archive.
Review and adjust retention/deletion obligations to match your approval before enabling collection.

Reddit official policies:
- https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data
- https://mods.reddithelp.com/hc/en-us/articles/16693988535309-Moderation-Bots-Tooling
- https://redditinc.com/policies/data-api-terms

## Telegram configuration

Telegram's Bot API offers updates from channels where the bot is present.
It does **not** provide unrestricted discovery of arbitrary channels. Do not use it to access
private chats, scrape illicit marketplaces, evade invitation controls, or capture personal details.

For each **public channel you own or are explicitly authorized to monitor**:
1. Add a **dedicated** Telegram bot to that channel with permissions sufficient to receive posts.
2. Put its public username (e.g., `@channelname`) in `telegram_channels` in `data/community_sources.json`.
3. Set Actions Secret `TELEGRAM_BOT_TOKEN`.
4. Set Actions Variable `TELEGRAM_DEDICATED_BOT=1`.
5. Ensure no other webhook/poller is using the same bot. This collector rejects active webhooks.

Only `channel_post` and `edited_channel_post` from whitelisted public channels are processed.
No group messages, DM contents, channel members, posters, user handles, media, or raw messages are
persisted. Since the Bot API does not guarantee automatic deletion notices for channel posts,
the public short-retention index expires after **seven days**. A channel owner should notify
the project if a referenced public message needs earlier removal.

Telegram documentation:
- https://core.telegram.org/bots/api
- https://core.telegram.org/bots/faq

## Public output and safeguards

Files:
- `data/community_signals.json`: short-lived derived metadata, original post links only.
- `data/community_status.json`: independent collector statuses, available without secrets.
- `data/community_state.json`: Telegram getUpdates cursor only (no message bodies).
- `data/community_sources.json`: selected public-source allowlists.

The GitHub Actions pipeline refreshes them on the normal site schedule, **only when credentials,
approvals and channels have been configured**. Without those, the feed presents an honest
not-connected status and no invented records.

This system does not automatically estimate fraud prevalence, count victims, allege weak bank
controls, publish suspects, report monetary losses or infer that repeated posts are independent
corroboration. It is a **lead discovery** tool and requires manual corroboration.

## Run checks

```bash
python -m unittest discover -s tests -p 'test_community_signals.py'
python scripts/collect_community.py
```

Without approved credentials, the collector exits successfully, publishes zero records, and
sets each source's explanatory status. Never commit environment secrets.
