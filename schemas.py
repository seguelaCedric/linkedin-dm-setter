#!/usr/bin/env python3
"""Tool schemas for LinkedIn DM Setter plugin."""

LINKEDIN_SETUP_PROFILE = {
    "name": "linkedin_setup_profile",
    "description": "Set up the LinkedIn DM Setter Hermes profile with SOUL.md, cron jobs, and database. Run once during installation.",
    "parameters": {
        "type": "object",
        "properties": {
            "profile_name": {
                "type": "string",
                "description": "Name for the Hermes profile (default: linkedin-setter)",
                "default": "linkedin-setter"
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
            "telegram_bot_token": {
                "type": "string",
                "description": "Telegram bot token for notifications"
            },
            "telegram_chat_id": {
                "type": "string",
                "description": "Telegram chat ID for notifications"
            }
        },
        "required": ["unipile_api_key", "unipile_base_url", "unipile_account_id", "telegram_bot_token", "telegram_chat_id"]
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

ALL_SCHEMAS = [
    LINKEDIN_SETUP_PROFILE,
    LINKEDIN_DISCOVER_POSTS,
    LINKEDIN_SEND_CONNECTIONS,
    LINKEDIN_CHECK_REPLIES,
    LINKEDIN_QUEUE_DRAFTS,
    LINKEDIN_APPROVE_MESSAGE,
    LINKEDIN_SEND_APPROVED,
    LINKEDIN_THROTTLE_STATUS,
    LINKEDIN_FUNNEL_REPORT,
    LINKEDIN_ADD_LEAD,
]
