# LinkedIn DM Setter Plugin for Hermes Agent

Automated LinkedIn outreach system that finds viral posts, scrapes commenters, scores ICP, sends throttled connection requests, drafts personalized messages, and manages conversations through a 9-stage state machine.

## Features

- **Viral Post Discovery**: Automatically finds high-engagement posts from tracked influencers
- **ICP Scoring**: Scores leads against 4 criteria (decision-maker, outbound, service business, pain visible)
- **Throttled Sending**: Per-account daily limits with random delays to avoid LinkedIn bans
- **Conversation Threading**: Each conversation bound to the account that initiated it
- **Draft Approval**: All messages queued to Telegram for approval before sending
- **Reply Monitoring**: Checks Unipile chats every 30 minutes for new replies
- **Stage Advancement**: Automatically advances conversations through 9 stages
- **Funnel Reporting**: Weekly reports with conversion rates and A/B test results

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Hermes Agent (linkedin-setter profile)                      │
├─────────────────────────────────────────────────────────────┤
│  Plugin Tools                                                │
│  ├── linkedin_discover_posts    (find viral posts)           │
│  ├── linkedin_send_connections  (throttled sending)          │
│  ├── linkedin_check_replies     (reply monitoring)           │
│  ├── linkedin_queue_drafts      (Telegram approval)          │
│  ├── linkedin_approve_message   (approve/reject)             │
│  ├── linkedin_send_approved     (send via Unipile)           │
│  ├── linkedin_throttle_status   (rate limit check)           │
│  ├── linkedin_funnel_report     (conversion metrics)         │
│  └── linkedin_add_lead          (manual lead entry)          │
├─────────────────────────────────────────────────────────────┤
│  Unipile API                                                 │
│  ├── Connection requests                                    │
│  ├── Message sending                                        │
│  ├── Chat monitoring                                        │
│  └── Profile lookup                                         │
├─────────────────────────────────────────────────────────────┤
│  SQLite Database                                             │
│  ├── leads (profiles, ICP scores)                           │
│  ├── conversations (stage state, account binding)           │
│  ├── messages (drafts, approvals, sent)                     │
│  └── funnel_stats (weekly metrics)                          │
├─────────────────────────────────────────────────────────────┤
│  Telegram Bot                                                │
│  ├── Draft approval notifications                           │
│  ├── Reply alerts                                           │
│  └── Weekly funnel reports                                  │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
hermes plugins install your-org/linkedin-dm-setter --enable
```

Then run setup:

```bash
hermes run linkedin_setup_profile \
  --unipile_api_key "YOUR_KEY" \
  --unipile_base_url "https://apiN.unipile.com:PORT/api/v1" \
  --unipile_account_id "YOUR_ACCOUNT_ID" \
  --telegram_bot_token "YOUR_BOT_TOKEN" \
  --telegram_chat_id "YOUR_CHAT_ID"
```

## Cron Jobs

The plugin creates 4 cron jobs:

| Job | Schedule | Purpose |
|-----|----------|---------|
| Post Discovery | 08:00 UTC daily | Find viral posts, add leads, send connections |
| Reply Monitor | Every 30m | Check for replies, advance stages, queue drafts |
| Draft Queue | 09:00 UTC daily | Send pending drafts to Telegram |
| Weekly Report | Fri 17:00 UTC | Full funnel snapshot |

## Commands

```bash
# Check throttle status
hermes run linkedin_throttle_status

# Discover viral posts
hermes run linkedin_discover_posts

# Send connection requests (dry run)
hermes run linkedin_send_connections --limit 10

# Send connection requests (actually send)
hermes run linkedin_send_connections --limit 10 --dry_run false

# Check for replies
hermes run linkedin_check_replies

# Queue drafts to Telegram
hermes run linkedin_queue_drafts

# Approve a message
hermes run linkedin_approve_message --message_id 5 --action approve

# Send approved messages
hermes run linkedin_send_approved

# Funnel report
hermes run linkedin_funnel_report --days 7

# Add lead manually
hermes run linkedin_add_lead --linkedin_url "https://linkedin.com/in/name" --full_name "Name"
```

## Throttle Limits

| Account | Daily Limit |
|---------|-------------|
| Per account | 20/day |
| Global total | 35/day |
| Delay between requests | 45-120 seconds (random) |

## Conversation Threading

Each conversation is bound to the LinkedIn account that sent the connection request. All subsequent messages for that conversation go through the same account. No cross-threading.

## License

MIT
