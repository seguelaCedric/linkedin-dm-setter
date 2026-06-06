# LinkedIn DM Setter -- Complete Setup Course

## What You'll Build

An automated LinkedIn outreach system that:
- Finds viral posts in your niche
- Scrapes commenters who are potential leads
- Scores them against your ideal customer profile
- Sends connection requests (throttled to avoid bans)
- Drafts personalized messages for your approval
- Manages conversations through a 9-stage pipeline
- Reports funnel metrics weekly

## Prerequisites

Before starting, you need:
1. A LinkedIn account (Premium recommended)
2. A Unipile subscription ($49/month)
3. A Telegram account (free)
4. Hermes Agent installed on a VPS

## Module 1: Unipile Setup (10 minutes)

### What is Unipile?

Unipile is an API service that lets you programmatically send LinkedIn messages, connection requests, and monitor chats without browser automation. It's safer than scraping because it uses LinkedIn's official messaging layer.

### Step 1.1: Create Unipile Account

1. Go to [unipile.com](https://unipile.com)
2. Click "Get Started"
3. Choose a plan (Starter is fine for 1-2 accounts)
4. Complete payment

### Step 1.2: Connect LinkedIn

1. In Unipile dashboard, click "Add Account"
2. Select "LinkedIn"
3. Log in with your LinkedIn credentials
4. Unipile will create a secure connection
5. Note your Account ID (shown in the dashboard)

### Step 1.3: Get API Credentials

1. In Unipile dashboard, go to Settings > API
2. Copy your API Key
3. Note your Base URL (e.g. `https://api13.unipile.com:14389/api/v1`)

Save these -- you'll need them in Module 3.

## Module 2: Telegram Bot Setup (5 minutes)

### What is the Telegram Bot For?

The bot sends you:
- Draft messages for approval (before sending to leads)
- Reply alerts (when someone responds)
- Weekly funnel reports

### Step 2.1: Create Bot

1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Name your bot (e.g. "LinkedIn DM Setter")
5. Choose a username (e.g. "YourCompanyLinkedinBot")
6. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2.2: Start Chat

1. Search for your new bot in Telegram
2. Send any message (e.g. "/start")
3. This creates the chat ID the bot needs

### Step 2.3: Get Chat ID

1. Open browser, visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   (Replace `<TOKEN>` with your bot token)
2. Look for `"chat":{"id":123456789}`
3. That number is your chat ID

Save both the token and chat ID -- you'll need them in Module 3.

## Module 3: Plugin Installation (5 minutes)

### Step 3.1: Install Plugin

```bash
hermes plugins install your-org/linkedin-dm-setter --enable
```

### Step 3.2: Run Setup

```bash
hermes run linkedin_setup_profile \
  --unipile_api_key "YOUR_UNIPILE_API_KEY" \
  --unipile_base_url "https://apiN.unipile.com:PORT/api/v1" \
  --unipile_account_id "YOUR_ACCOUNT_ID" \
  --telegram_bot_token "YOUR_BOT_TOKEN" \
  --telegram_chat_id "YOUR_CHAT_ID"
```

Replace the placeholders with your actual credentials.

This creates:
- A Hermes profile called `linkedin-setter`
- Database for tracking conversations
- SOUL.md template (you'll customize next)
- Cron jobs for automation

### Step 3.3: Verify

```bash
hermes -p linkedin-setter run linkedin_throttle_status
```

Should show your account with 0/20 daily usage.

## Module 4: Customize Your Profile (10 minutes)

### Step 4.1: Edit SOUL.md

```bash
hermes -p linkedin-setter config edit SOUL.md
```

Replace these placeholders:

| Placeholder | What to Put |
|-------------|-------------|
| `{{FOUNDER_NAME}}` | Your name |
| `{{COMPANY_NAME}}` | Your company name |
| `{{ONE_LINE_OFFER}}` | Your one-line offer |
| `{{OFFER_OUTCOME}}` | The outcome you deliver |
| `{{PROOF_POINT_1}}` | A specific client result |
| `{{PROOF_POINT_2}}` | Another specific result |
| `{{PROOF_POINT_3}}` | Your guarantee or third result |
| `{{OBSIDIAN_VAULT_PATH}}` | Path to your Obsidian vault (e.g. `/root/obsidian-vault`) |
| `{{COMPANY_SLUG}}` | Company name lowercase (e.g. `yourcompany`) |

### Step 4.2: Example

```markdown
## The Offer (internal context -- do NOT lead with this)

ACA: Outbound + inbound + content + replies, all in one system, built in minutes.
Outcome: First qualified meeting in 11 days or you don't pay. Cancel anytime.

Proof points (ONLY surface at Stage 6):
1. "One of our clients, a 3-person agency doing $15K/mo, went from 1-2 calls/week to 11 booked calls in their first 2 weeks."
2. "We replaced Smartlead + Apollo + Clay for one founder and cut their stack cost from $7,000/mo to $0.66/inbox."
3. "First qualified meeting in 11 days or you don't pay -- that's the guarantee."
```

## Module 5: Add Influencers (5 minutes)

### What Are Influencers?

Influencers are LinkedIn users who post about topics relevant to your business. The system monitors their posts for viral content, then scrapes commenters as potential leads.

### Step 5.1: Edit Influencer List

```bash
hermes -p linkedin-setter config edit data/influencers.json
```

### Step 5.2: Add Your Influencers

```json
[
  {
    "name": "Influencer Name",
    "public_id": "their-linkedin-id",
    "provider_id": null,
    "topics": ["outbound", "SDR", "agency"]
  }
]
```

To find someone's `public_id`:
1. Go to their LinkedIn profile
2. Look at the URL: `linkedin.com/in/THIS-IS-THE-PUBLIC-ID`

### Step 5.3: Auto-Expansion

The system automatically discovers new influencers from viral post commenters. You just need to seed it with 2-3 initial influencers.

## Module 6: First Run (5 minutes)

### Step 6.1: Discover Posts

```bash
hermes -p linkedin-setter run linkedin_discover_posts
```

This will:
- Check your influencers for viral posts
- Scrape commenters
- Score them against your ICP
- Add qualified leads to the database

### Step 6.2: Send Connection Requests

```bash
# Dry run first (see what would be sent)
hermes -p linkedin-setter run linkedin_send_connections --limit 10

# Actually send
hermes -p linkedin-setter run linkedin_send_connections --limit 10 --dry_run false
```

### Step 6.3: Check Telegram

You should receive a notification with the leads found and connections sent.

## Module 7: Daily Operations

### What Happens Automatically

| Time (UTC) | Action |
|------------|--------|
| 08:00 | Post discovery: finds viral posts, adds leads, sends connections |
| Every 30m | Reply monitor: checks for accepts/replies, advances stages |
| 09:00 | Draft queue: sends pending drafts to your Telegram |
| Fri 17:00 | Weekly report: full funnel snapshot |

### Approval Flow

1. Someone accepts your connection request
2. Within 30 minutes, you get a draft on Telegram
3. Reply: `approve 5` to send as-is
4. Or: `approve 5 hey Bob, saw your post about X` to edit
5. Or: `reject 5` to discard
6. After approving, reply: `send` to dispatch via Unipile

### Manual Commands

```bash
# Check throttle status
hermes -p linkedin-setter run linkedin_throttle_status

# Check for replies
hermes -p linkedin-setter run linkedin_check_replies

# Queue drafts
hermes -p linkedin-setter run linkedin_queue_drafts

# Send approved messages
hermes -p linkedin-setter run linkedin_send_approved

# Funnel report
hermes -p linkedin-setter run linkedin_funnel_report --days 7
```

## Module 8: Understanding the Pipeline

### Stage 0: Connect
Blank connection request sent. Waiting for acceptance.

### Stage 1: Open
Accepted. First message: genuine question about them (no pitching).

### Stage 2: Filter Intent
This-or-that question to score where they are.

### Stage 3: Diagnose
Validate their win, surface gap with questions, let THEM name the problem.

### Stage 4: Frame
Tie their problem to your area. Move from problem-aware to solution-aware.

### Stage 5: Qualify
Confirm fit. Make pain tangible vs. current state.

### Stage 6: Earn the Right
Share ONE proof point showing this is solvable.

### Stage 7: Book
Propose specific times. Get email. Send calendar invite.

### Stage 8: Nurture
Stay in DMs. Share resource. 24h reminder. Goal: 80%+ show-up.

## Module 9: Throttle Limits

### Why Throttling Matters

LinkedIn bans accounts that send too many connection requests too fast. The throttle system:
- Limits each account to 20 requests/day
- Limits total to 35 requests/day across all accounts
- Adds 45-120 second random delays between requests
- Round-robins across accounts by capacity

### Adding More Accounts

1. Connect the new account in Unipile
2. Get the account ID
3. Edit `shared_throttle.py` LIMITS dict
4. Edit `send_connections.py` ACCOUNTS list

The system automatically distributes sends across all accounts.

## Module 10: Tracking

### Where to See What's Happening

1. **Telegram**: Real-time notifications, draft approvals, reply alerts
2. **Obsidian**: Pipeline state, lead counts, throttle status (if configured)
3. **SQLite**: Raw data at `~/.hermes/profiles/linkedin-setter/data/conversations.db`

### Weekly Report

Every Friday at 17:00 UTC, you'll receive:
- Funnel: connects sent -> accepted -> replied -> booked -> showed
- Conversion rates for each stage
- A/B test results (if running)
- Three suggestions for next week

## Troubleshooting

### "No active conversations to monitor"
Normal if no connection requests have been accepted yet.

### "Daily limit reached"
Wait until tomorrow or add more LinkedIn accounts.

### Telegram not receiving messages
1. Verify bot token
2. Make sure you've sent a message to the bot
3. Check chat ID

### Unipile API errors
1. Verify API key
2. Check base URL format
3. Ensure LinkedIn is connected in Unipile dashboard

### Messages sound too AI-like
Edit the Stage 1 templates in `generate_draft.py`. Keep them short, casual, no em dashes.

## Cost Breakdown

| Service | Cost |
|---------|------|
| Unipile | ~$49/month |
| Hermes Agent | Free (self-hosted) |
| Telegram | Free |
| LinkedIn Premium | ~$30/month (optional) |
| **Total** | **~$49-79/month** |

## Next Steps

1. Run for 2 weeks with DRAFT_FOR_APPROVAL mode
2. Review message quality and adjust templates
3. Add more influencers to expand lead sources
4. Consider adding more LinkedIn accounts for higher volume
5. Switch to AUTO_SEND only after 2+ weeks of approved drafts
