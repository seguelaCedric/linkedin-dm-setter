# Installation Guide -- LinkedIn DM Setter Plugin

## Two Deployment Modes

This plugin supports two modes. Pick one (or both):

| Mode | How it works | Best for | Monthly cost |
|------|-------------|----------|-------------|
| **Mode A: ACA Auto-Pilot** | Hermes sources/scored leads, pushes to ACA lead lists, ACA handles sequences/follow-ups/replies/booking | Volume outreach with proven messaging | Unipile $49 + ACA $67 = **$116** |
| **Mode B: Telegram Human-in-the-Loop** | Hermes sources/scored/drafts, you approve every message via Telegram before sending | High-value leads, custom messaging, dialing in your voice | Unipile $49 = **$49** |

**Hermes + Unipile costs $49/month for 10 LinkedIn accounts.** Compare to HeyReach at $590/month for the same capacity. That's a 92% cost reduction.

## Prerequisites

1. **Hermes Agent** installed and running on a VPS
2. **Unipile account** with LinkedIn connected
3. **Telegram bot** created via @BotFather
4. **ACA account** (only for Mode A)
5. **LLM API key** (DeepSeek, OpenAI, etc.) for draft generation

## Step 1: Get Unipile Credentials

1. Sign up at [unipile.com](https://unipile.com)
2. Connect your LinkedIn account(s)
3. Note your:
   - API Key
   - Base URL (from your Unipile dashboard)
   - Account ID(s) for each LinkedIn account

## Step 2: Create Telegram Bot

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the bot token
5. Start a chat with your new bot (send any message)
6. Get your chat ID: visit `https://api.telegram.org/bot<TOKEN>/getUpdates`

## Step 3: (Mode A Only) Prepare ACA

1. Create a lead list in ACA for Hermes inbound leads
2. Create or select a campaign with LinkedIn connection + DM steps
3. Note your org ID, lead list ID, and sequence/campaign ID

## Step 4: Install Plugin

```bash
hermes plugins install seguelaCedric/linkedin-dm-setter --enable
```

## Step 5: Run Setup (Onboarding Questionnaire)

The setup tool asks 7 questions that configure your entire pipeline. Answer them all.

```bash
hermes run linkedin_setup_profile \
  --mode "telegram" \
  --icp_industries "B2B SaaS, marketing agencies, wealth management" \
  --icp_titles "founder, CEO, head of growth, VP sales" \
  --icp_company_size "10-200" \
  --icp_geography "US, Canada, UK" \
  --icp_pain_points "too many tools, low reply rates, cannot scale outbound" \
  --voice_tone "casual" \
  --volume_target "standard" \
  --content_angle "commenting on their posts and content" \
  --account_count 1 \
  --daily_limit_per_account 20 \
  --global_daily_limit 35 \
  --unipile_api_key "YOUR_KEY" \
  --unipile_base_url "YOUR_URL" \
  --unipile_account_id "YOUR_ACCOUNT_ID" \
  --telegram_bot_token "YOUR_BOT_TOKEN" \
  --telegram_chat_id "YOUR_CHAT_ID"
```

### Mode A: add these extra flags
```bash
  --mode "aca" \
  --aca_org_id "YOUR_ACA_ORG_ID" \
  --aca_lead_list_id "YOUR_LEAD_LIST_UUID" \
  --aca_sequence_id "YOUR_SEQUENCE_UUID"
```

### Mode B (both): use both sets

This will:
- Create the `linkedin-setter` Hermes profile
- Write `.env` with all credentials
- Generate SOUL.md from your questionnaire answers (no manual editing needed)
- Copy scripts to the profile
- Initialize the SQLite database

## Step 6: Add Influencers

Edit the influencers list to track who posts about your niche:

```bash
hermes -p linkedin-setter config edit data/influencers.json
```

Format:
```json
[
  {
    "name": "Influencer Name",
    "public_id": "linkedin-public-id",
    "provider_id": null,
    "topics": ["outbound", "SDR", "agency"]
  }
]
```

The system will auto-expand this list by discovering new influencers from viral post commenters.

## Step 7: Test Connection

```bash
# Check Unipile connection
hermes -p linkedin-setter run linkedin_throttle_status

# Test Telegram (Mode B)
hermes -p linkedin-setter run linkedin_queue_drafts

# Test ACA connection (Mode A)
hermes -p linkedin-setter run linkedin_aca_status --aca_org_id "YOUR_ORG_ID"
```

## Step 8: Start the System

Cron jobs are auto-created during setup:

| Job | Schedule | Mode |
|-----|----------|------|
| Post discovery | 08:00 UTC daily | Both |
| Connection sender | Every 4 hours | Both |
| Reply monitor | Every 30 min | Both |
| Draft queue (Telegram) | 09:00 UTC daily | Mode B |
| ACA push + enroll | Every 4 hours | Mode A |
| Weekly report | Fri 17:00 UTC | Both |

### Mode A: Push Leads to ACA

```bash
# Push scored leads to ACA lead list
hermes -p linkedin-setter run linkedin_push_to_aca \
  --aca_org_id "YOUR_ORG_ID" \
  --aca_lead_list_id "YOUR_LIST_ID" \
  --min_icp_score 7

# Auto-enroll in sequence
hermes -p linkedin-setter run linkedin_aca_auto_enroll \
  --aca_org_id "YOUR_ORG_ID" \
  --aca_lead_list_id "YOUR_LIST_ID" \
  --aca_sequence_id "YOUR_SEQUENCE_ID" \
  --confirm_enroll true
```

### Mode B: Manual Triggers

```bash
# Discover posts and add leads
hermes -p linkedin-setter run linkedin_discover_posts

# Send connection requests
hermes -p linkedin-setter run linkedin_send_connections --limit 10 --dry_run false

# Approve a draft from Telegram
hermes -p linkedin-setter run linkedin_approve_message --message_id 48 --action approve
```

## Cost Comparison

| Tool | Accounts | Monthly cost | Per-account cost |
|------|----------|-------------|-----------------|
| **Hermes + Unipile** | 10 | **$49** | **$4.90** |
| HeyReach | 10 | $590 | $59.00 |
| Lemlist | 1 | $39 | $39.00 |
| Waalaxy | 1 | $64 | $64.00 |
| Expandi | 1 | $99 | $99.00 |

Hermes: $0 in per-lead fees, $0 in token markup, no vendor lock-in. BYOK.

## Troubleshooting

### "No active conversations to monitor"
Normal if no connection requests have been accepted yet.

### "Daily limit reached"
The throttle stopped sending. Wait until tomorrow or add more accounts.

### Telegram not receiving messages
1. Verify bot token is correct
2. Make sure you've sent a message to the bot (starts the chat)
3. Check chat ID matches

### ACA push failing (Mode A)
1. Verify ACA_ORG_ID is in your .env
2. Confirm the lead list and sequence exist in ACA
3. Run `hermes -p linkedin-setter run linkedin_aca_status` for diagnostics

### Adding More LinkedIn Accounts
1. Connect new account in Unipile
2. Update `.env` with the new account ID
3. The throttle system auto-distributes sends across all accounts
