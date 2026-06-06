# Installation Guide -- LinkedIn DM Setter Plugin

## Prerequisites

1. **Hermes Agent** installed and running
2. **Unipile account** with LinkedIn connected
3. **Telegram bot** created via @BotFather
4. **Obsidian vault** (optional, for tracking)

## Step 1: Get Unipile Credentials

1. Sign up at [unipile.com](https://unipile.com)
2. Connect your LinkedIn account(s)
3. Note your:
   - API Key
   - Base URL (e.g. `https://api13.unipile.com:14389/api/v1`)
   - Account ID(s) for each LinkedIn account

## Step 2: Create Telegram Bot

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the bot token
5. Start a chat with your new bot (send any message)
6. Get your chat ID: visit `https://api.telegram.org/bot<TOKEN>/getUpdates`

## Step 3: Install Plugin

```bash
hermes plugins install your-org/linkedin-dm-setter --enable
```

## Step 4: Run Setup

```bash
hermes run linkedin_setup_profile \
  --unipile_api_key "YOUR_UNIPILE_API_KEY" \
  --unipile_base_url "https://apiN.unipile.com:PORT/api/v1" \
  --unipile_account_id "YOUR_PRIMARY_ACCOUNT_ID" \
  --unipile_account_id_backup "YOUR_BACKUP_ACCOUNT_ID" \
  --telegram_bot_token "YOUR_TELEGRAM_BOT_TOKEN" \
  --telegram_chat_id "YOUR_TELEGRAM_CHAT_ID"
```

This will:
- Create the `linkedin-setter` Hermes profile
- Write `.env` with your credentials
- Copy SOUL.md template
- Initialize the SQLite database
- Create data directories

## Step 5: Customize SOUL.md

Edit the profile's SOUL.md to fill in your business details:

```bash
hermes -p linkedin-setter config edit SOUL.md
```

Replace these placeholders:
- `{{FOUNDER_NAME}}` -- your name
- `{{COMPANY_NAME}}` -- your company name
- `{{ONE_LINE_OFFER}}` -- your one-line offer
- `{{OFFER_OUTCOME}}` -- the outcome you deliver
- `{{PROOF_POINT_1}}` -- first proof point
- `{{PROOF_POINT_2}}` -- second proof point
- `{{PROOF_POINT_3}}` -- third proof point
- `{{OBSIDIAN_VAULT_PATH}}` -- path to your Obsidian vault
- `{{COMPANY_SLUG}}` -- company name slug (e.g. "automatedclientacquisition")

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

# Test Telegram
hermes -p linkedin-setter run linkedin_queue_drafts
```

## Step 8: Start the System

The cron jobs are automatically created during setup. They will run:
- Post discovery: 08:00 UTC daily
- Reply monitor: every 30 minutes
- Draft queue: 09:00 UTC daily
- Weekly report: Friday 17:00 UTC

To manually trigger:

```bash
# Discover posts and add leads
hermes -p linkedin-setter run linkedin_discover_posts

# Send connection requests
hermes -p linkedin-setter run linkedin_send_connections --limit 10 --dry_run false
```

## Troubleshooting

### "No active conversations to monitor"
Normal if no connection requests have been accepted yet. The system waits for accepts before monitoring.

### "Daily limit reached"
The throttle has stopped sending to avoid LinkedIn bans. Wait until tomorrow or add more accounts.

### Telegram not receiving messages
1. Verify bot token is correct
2. Make sure you've sent a message to the bot (starts the chat)
3. Check chat ID matches

### Unipile API errors
1. Verify API key is valid
2. Check base URL format
3. Ensure LinkedIn account is connected in Unipile dashboard

## Adding More LinkedIn Accounts

1. Connect the new account in Unipile
2. Get the account ID
3. Add to `.env`:
   ```
   UNIPILE_LINKEDIN_ACCOUNT_ID_BACKUP=NEW_ACCOUNT_ID
   ```
4. Update `shared_throttle.py` LIMITS dict
5. Update `send_connections.py` ACCOUNTS list

The throttle system will automatically distribute sends across all accounts.
