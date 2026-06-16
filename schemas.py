#!/usr/bin/env python3
"""Tool schemas for LinkedIn DM Setter plugin."""

LINKEDIN_SETUP_PROFILE = {
    "name": "linkedin_setup_profile",
    "description": "Set up the LinkedIn DM Setter Hermes profile with SOUL.md, cron jobs, and database. Asks the onboarding questionnaire to configure mode, ICP, voice, volume, and accounts. Run once during installation.",
    "parameters": {
        "type": "object",
        "properties": {
            "profile_name": {
                "type": "string",
                "description": "Name for the Hermes profile (default: linkedin-setter)",
                "default": "linkedin-setter"
            },
            "mode": {
                "type": "string",
                "enum": ["aca", "telegram", "both"],
                "description": "Deployment mode: 'aca' (ACA auto-pilot pushes to sequences), 'telegram' (human-in-the-loop approval), or 'both' (ACA for Tier 2, Telegram for Tier 1)",
                "default": "telegram"
            },
            "icp_industries": {
                "type": "string",
                "description": "Target industries, comma-separated (e.g. 'B2B SaaS, marketing agencies, wealth management')"
            },
            "icp_titles": {
                "type": "string",
                "description": "Target job titles, comma-separated (e.g. 'founder, CEO, head of growth, VP sales')"
            },
            "icp_company_size": {
                "type": "string",
                "description": "Target company size range (e.g. '1-10', '10-50', '50-200')"
            },
            "icp_geography": {
                "type": "string",
                "description": "Target geography (e.g. 'US only', 'North America', 'global')"
            },
            "icp_pain_points": {
                "type": "string",
                "description": "Pain points you solve, comma-separated (e.g. 'too many tools, low reply rates, cannot scale outbound')"
            },
            "voice_tone": {
                "type": "string",
                "enum": ["casual", "professional", "direct"],
                "description": "Message voice: 'casual' (DM from a peer, lowercase), 'professional' (warm but formal), 'direct' (punchy, minimal words)",
                "default": "casual"
            },
            "volume_target": {
                "type": "string",
                "enum": ["conservative", "standard", "aggressive"],
                "description": "Weekly volume: 'conservative' (20-50/week), 'standard' (50-100/week), 'aggressive' (100-200/week)",
                "default": "standard"
            },
            "content_angle": {
                "type": "string",
                "description": "Hook strategy for openers (e.g. 'commenting on their posts', 'referencing mutual connections', 'industry insight')"
            },
            "aca_org_id": {
                "type": "string",
                "description": "ACA organization ID (required for 'aca' or 'both' modes)"
            },
            "aca_lead_list_id": {
                "type": "string",
                "description": "ACA lead list ID to push leads into (required for 'aca' or 'both' modes)"
            },
            "aca_sequence_id": {
                "type": "string",
                "description": "ACA sequence or campaign ID for auto-enrollment (required for 'aca' or 'both' modes)"
            },
            "unipile_api_key": {
                "type": "string",
                "description": "Unipile API key"
            },
            "unipile_base_url": {
                "type": "string",
                "description": "Unipile API base URL"
            },
            "unipile_account_id": {
                "type": "string",
                "description": "Primary LinkedIn account ID from Unipile"
            },
            "unipile_account_id_backup": {
                "type": "string",
                "description": "Backup LinkedIn account ID from Unipile (optional)"
            },
            "account_count": {
                "type": "integer",
                "description": "Number of LinkedIn accounts in Unipile (default: 1)",
                "default": 1
            },
            "daily_limit_per_account": {
                "type": "integer",
                "description": "Daily send limit per account (default: 20)",
                "default": 20
            },
            "global_daily_limit": {
                "type": "integer",
                "description": "Global daily limit across all accounts (default: 35)",
                "default": 35
            },
            "telegram_bot_token": {
                "type": "string",
                "description": "Telegram bot token for notifications and approvals"
            },
            "telegram_chat_id": {
                "type": "string",
                "description": "Telegram chat ID for notifications"
            }
        },
        "required": ["unipile_api_key", "unipile_base_url", "unipile_account_id", "telegram_bot_token", "telegram_chat_id"]
    }
}

LINKEDIN_STATUS = {
    "name": "linkedin_status",
    "description": "Check LinkedIn DM Setter readiness: root-level plugin install, dedicated profile, plugin enabled on that profile, SOUL.md, .env credentials, and local database.",
    "parameters": {
        "type": "object",
        "properties": {
            "profile_name": {"type": "string", "description": "Dedicated profile to check (default: linkedin-setter)."}
        },
        "required": []
    }
}

LINKEDIN_SMOKE_TEST = {
    "name": "linkedin_smoke_test",
    "description": "Run the smallest safe LinkedIn DM Setter proof: verify config/profile/database state. No LinkedIn sends, no scraping, no paid calls.",
    "parameters": {
        "type": "object",
        "properties": {
            "profile_name": {"type": "string", "description": "Dedicated profile to test (default: linkedin-setter)."}
        },
        "required": []
    }
}

LINKEDIN_DISCOVER_POSTS = {
    "name": "linkedin_discover_posts",
    "description": "Find viral posts from tracked influencers, scrape commenters, score against ICP, and add qualified leads to the database.",
    "parameters": {
        "type": "object",
        "properties": {
            "max_posts_per_influencer": {
                "type": "integer",
                "description": "Max posts to check per influencer (default: 5)",
                "default": 5
            },
            "max_commenters_per_post": {
                "type": "integer",
                "description": "Max commenters to scrape per post (default: 30)",
                "default": 30
            },
            "auto_expand": {
                "type": "boolean",
                "description": "Auto-discover new influencers from commenters (default: true)",
                "default": True
            }
        }
    }
}

LINKEDIN_SEND_CONNECTIONS = {
    "name": "linkedin_send_connections",
    "description": "Send blank connection requests to stage-0 leads via Unipile. Throttled across accounts with random delays.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max connection requests to send (default: 10)",
                "default": 10
            },
            "dry_run": {
                "type": "boolean",
                "description": "If true, show what would be sent without actually sending (default: true)",
                "default": True
            }
        }
    }
}

LINKEDIN_CHECK_REPLIES = {
    "name": "linkedin_check_replies",
    "description": "Check Unipile chats for new replies, record them in DB, advance conversation stages, and queue drafts.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

LINKEDIN_QUEUE_DRAFTS = {
    "name": "linkedin_queue_drafts",
    "description": "Send all pending drafts to Cedric's Telegram for approval.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

LINKEDIN_APPROVE_MESSAGE = {
    "name": "linkedin_approve_message",
    "description": "Approve, reject, or edit a draft message.",
    "parameters": {
        "type": "object",
        "properties": {
            "message_id": {
                "type": "integer",
                "description": "ID of the message to approve/reject"
            },
            "action": {
                "type": "string",
                "enum": ["approve", "reject"],
                "description": "Action to take"
            },
            "edited_text": {
                "type": "string",
                "description": "Edited text if approving with changes (optional)"
            }
        },
        "required": ["message_id", "action"]
    }
}

LINKEDIN_SEND_APPROVED = {
    "name": "linkedin_send_approved",
    "description": "Send all approved messages via Unipile. Uses conversation threading (same account that sent connection request).",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

LINKEDIN_THROTTLE_STATUS = {
    "name": "linkedin_throttle_status",
    "description": "Show current throttle status for all LinkedIn accounts.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

LINKEDIN_FUNNEL_REPORT = {
    "name": "linkedin_funnel_report",
    "description": "Generate funnel report with conversion rates for a given period.",
    "parameters": {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days to report on (default: 7)",
                "default": 7
            }
        }
    }
}

LINKEDIN_ADD_LEAD = {
    "name": "linkedin_add_lead",
    "description": "Manually add a lead to the database with ICP scoring.",
    "parameters": {
        "type": "object",
        "properties": {
            "linkedin_url": {
                "type": "string",
                "description": "LinkedIn profile URL"
            },
            "full_name": {
                "type": "string",
                "description": "Lead's full name"
            },
            "title": {
                "type": "string",
                "description": "Job title"
            },
            "company": {
                "type": "string",
                "description": "Company name"
            },
            "headline": {
                "type": "string",
                "description": "LinkedIn headline"
            },
            "personalization_hook": {
                "type": "string",
                "description": "Hook for personalized messaging"
            },
            "source": {
                "type": "string",
                "description": "Where this lead came from"
            }
        },
        "required": ["linkedin_url", "full_name"]
    }
}

LINKEDIN_PUSH_TO_ACA = {
    "name": "linkedin_push_to_aca",
    "description": "Push ICP-scored leads from the pipeline database into an ACA lead list for auto-enrollment. Creates ACA email leads with LinkedIn URLs. Mode A (ACA auto-pilot) operation.",
    "parameters": {
        "type": "object",
        "properties": {
            "min_icp_score": {
                "type": "integer",
                "description": "Minimum ICP score to push (default: 7)",
                "default": 7
            },
            "aca_org_id": {
                "type": "string",
                "description": "ACA organization ID"
            },
            "aca_lead_list_id": {
                "type": "string",
                "description": "ACA lead list UUID to add contacts into"
            },
            "max_leads": {
                "type": "integer",
                "description": "Maximum leads to push in this batch (default: 50)",
                "default": 50
            },
            "stage_filter": {
                "type": "string",
                "description": "Only push leads at this pipeline stage (default: 'connected')",
                "default": "connected"
            }
        },
        "required": ["aca_org_id", "aca_lead_list_id"]
    }
}

LINKEDIN_ACA_AUTO_ENROLL = {
    "name": "linkedin_aca_auto_enroll",
    "description": "Auto-enroll leads from an ACA lead list into a campaign or sequence. This triggers ACA's campaign engine: sequences, follow-ups, reply detection, and calendar booking. Mode A (ACA auto-pilot) operation.",
    "parameters": {
        "type": "object",
        "properties": {
            "aca_org_id": {
                "type": "string",
                "description": "ACA organization ID"
            },
            "aca_lead_list_id": {
                "type": "string",
                "description": "ACA lead list UUID containing leads to enroll"
            },
            "aca_sequence_id": {
                "type": "string",
                "description": "ACA sequence or campaign UUID for enrollment"
            },
            "confirm_enroll": {
                "type": "boolean",
                "description": "Must be true to perform enrollment. Safety gate.",
                "default": False
            },
            "max_leads": {
                "type": "integer",
                "description": "Maximum leads to enroll (default: 50)",
                "default": 50
            }
        },
        "required": ["aca_org_id", "aca_lead_list_id", "aca_sequence_id", "confirm_enroll"]
    }
}

LINKEDIN_ACA_STATUS = {
    "name": "linkedin_aca_status",
    "description": "Check ACA campaign/sequence status: reply counts, booked calls, enrollment progress, and conversation stages. For Mode A (ACA auto-pilot) monitoring.",
    "parameters": {
        "type": "object",
        "properties": {
            "aca_org_id": {
                "type": "string",
                "description": "ACA organization ID"
            },
            "aca_sequence_id": {
                "type": "string",
                "description": "ACA sequence or campaign UUID to check"
            },
            "days": {
                "type": "integer",
                "description": "Number of days to report on (default: 7)",
                "default": 7
            }
        },
        "required": ["aca_org_id"]
    }
}

ALL_SCHEMAS = [
    LINKEDIN_SETUP_PROFILE,
    LINKEDIN_STATUS,
    LINKEDIN_SMOKE_TEST,
    LINKEDIN_DISCOVER_POSTS,
    LINKEDIN_SEND_CONNECTIONS,
    LINKEDIN_CHECK_REPLIES,
    LINKEDIN_QUEUE_DRAFTS,
    LINKEDIN_APPROVE_MESSAGE,
    LINKEDIN_SEND_APPROVED,
    LINKEDIN_THROTTLE_STATUS,
    LINKEDIN_FUNNEL_REPORT,
    LINKEDIN_ADD_LEAD,
    LINKEDIN_PUSH_TO_ACA,
    LINKEDIN_ACA_AUTO_ENROLL,
    LINKEDIN_ACA_STATUS,
]
