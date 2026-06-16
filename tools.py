#!/usr/bin/env python3
"""Tool handlers for LinkedIn DM Setter plugin."""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

PLUGIN_DIR = Path(__file__).parent
SCRIPTS_DIR = PLUGIN_DIR / "data" / "scripts"
TEMPLATES_DIR = PLUGIN_DIR / "data" / "templates"

def _run_script(script_name, args=None, timeout=300):
    """Run a plugin script and return its output."""
    # Try multiple paths
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        # Try relative to plugin dir
        script_path = PLUGIN_DIR / "data" / "scripts" / script_name
    if not script_path.exists():
        return json.dumps({"status": "error", "error": "Script not found: " + script_name + " (looked in " + str(SCRIPTS_DIR) + " and " + str(PLUGIN_DIR / "data" / "scripts") + ")"})
    
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SCRIPTS_DIR)
        )
        if result.returncode == 0:
            return json.dumps({"status": "ok", "output": result.stdout.strip()})
        else:
            return json.dumps({"status": "error", "error": result.stderr.strip(), "output": result.stdout.strip()})
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "error", "error": "Script timed out"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def _get_profile_dir(profile_name="linkedin-setter"):
    """Get the profile directory path."""
    return Path.home() / ".hermes" / "profiles" / profile_name


def _config_has_plugin(profile_name: str, plugin_name: str) -> bool:
    cfg = _get_profile_dir(profile_name) / "config.yaml"
    return cfg.exists() and plugin_name in cfg.read_text(errors="ignore")


def _run_hermes_cmd(cmd: list[str], timeout: int = 30) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


def _enable_root_plugin_on_profile(profile_name: str, plugin_name: str) -> list[str]:
    results = []
    enabled = _run_hermes_cmd(["hermes", "-p", profile_name, "plugins", "enable", plugin_name])
    if enabled["returncode"] == 0 or _config_has_plugin(profile_name, plugin_name):
        results.append(f"enabled root-level plugin on profile: {plugin_name}")
    else:
        shared = Path.home() / ".hermes" / "plugins" / plugin_name
        pdir = _get_profile_dir(profile_name)
        local = pdir / "plugins"
        local.mkdir(parents=True, exist_ok=True)
        link = local / plugin_name
        try:
            if shared.exists() and not link.exists():
                link.symlink_to(shared, target_is_directory=True)
                results.append("profile-local symlink created for plugin discovery")
            enabled2 = _run_hermes_cmd(["hermes", "-p", profile_name, "plugins", "enable", plugin_name])
            results.append("enabled after symlink" if enabled2["returncode"] == 0 else f"enable warning: {(enabled2['stderr'] or enabled2['stdout'])[:160]}")
        except Exception as e:
            results.append(f"enable fallback warning: {e}")
    return results


def _get_db_path(profile_name="linkedin-setter"):
    """Get the database path."""
    return _get_profile_dir(profile_name) / "data" / "conversations.db"


def handle_setup(args, **kwargs):
    """Set up the LinkedIn DM Setter profile with onboarding questionnaire."""
    profile_name = args.get("profile_name", "linkedin-setter")
    mode = args.get("mode", "telegram")

    # Credentials
    unipile_api_key = args.get("unipile_api_key", "")
    unipile_base_url = args.get("unipile_base_url", "")
    unipile_account_id = args.get("unipile_account_id", "")
    unipile_account_id_backup = args.get("unipile_account_id_backup", "")
    telegram_bot_token = args.get("telegram_bot_token", "")
    telegram_chat_id = args.get("telegram_chat_id", "")

    # Questionnaire
    icp_industries = args.get("icp_industries", "")
    icp_titles = args.get("icp_titles", "")
    icp_company_size = args.get("icp_company_size", "")
    icp_geography = args.get("icp_geography", "")
    icp_pain_points = args.get("icp_pain_points", "")
    voice_tone = args.get("voice_tone", "casual")
    volume_target = args.get("volume_target", "standard")
    content_angle = args.get("content_angle", "")
    aca_org_id = args.get("aca_org_id", "")
    aca_lead_list_id = args.get("aca_lead_list_id", "")
    aca_sequence_id = args.get("aca_sequence_id", "")
    account_count = args.get("account_count", 1)
    daily_limit = args.get("daily_limit_per_account", 20)
    global_limit = args.get("global_daily_limit", 35)

    # Volume mapping
    volume_map = {"conservative": 35, "standard": 70, "aggressive": 140}
    weekly_volume = volume_map.get(volume_target, 70)

    results = []

    # 1. Create profile
    try:
        subprocess.run(["hermes", "profile", "create", profile_name], capture_output=True, text=True, timeout=30)
        results.append("Profile created: " + profile_name)
    except Exception as e:
        results.append("Profile creation note: " + str(e))

    profile_dir = _get_profile_dir(profile_name)

    # 2. Write .env with all credentials
    env_lines = [
        "UNIPILE_API_KEY=" + unipile_api_key,
        "UNIPILE_BASE_URL=" + unipile_base_url,
        "UNIPILE_LINKEDIN_ACCOUNT_ID=" + unipile_account_id,
        "UNIPILE_LINKEDIN_ACCOUNT_ID_BACKUP=" + unipile_account_id_backup,
        "TELEGRAM_BOT_TOKEN=" + telegram_bot_token,
        "TELEGRAM_HOME_CHAT_ID=" + telegram_chat_id,
    ]
    if aca_org_id:
        env_lines.append("ACA_ORG_ID=" + aca_org_id)
    (profile_dir / ".env").write_text("\n".join(env_lines) + "\n")
    results.append(".env written" + (" (with ACA)" if aca_org_id else ""))

    # 3. Generate SOUL.md from questionnaire
    mode_labels = {"aca": "ACA Auto-Pilot (push scored leads to sequences)", "telegram": "Telegram Human-in-the-Loop (approve every message)", "both": "Hybrid: ACA for Tier 2, Telegram for Tier 1"}
    voice_labels = {"casual": "short, lowercase, no em dashes, sound like a DM from a peer", "professional": "warm but formal, slightly more polished", "direct": "punchy, minimal words, maximum impact"}

    soul_content = f"""# LinkedIn DM Setter

## Identity
You are an autonomous LinkedIn DM outreach agent operating in **{mode_labels.get(mode, mode)}** mode.

## ICP Definition
- Industries: {icp_industries or 'B2B SaaS, marketing agencies, consultancies'}
- Titles: {icp_titles or 'founder, CEO, head of growth, VP sales'}
- Company size: {icp_company_size or '10-200'}
- Geography: {icp_geography or 'US, Canada, UK'}
- Pain points: {icp_pain_points or 'too many tools, low reply rates, cannot scale outbound'}

## Voice & Tone
{voice_labels.get(voice_tone, 'casual')}
Content angle: {content_angle or 'commenting on their posts and referencing what they DID'}

## Volume
{weekly_volume} connection requests per week, {account_count} LinkedIn account(s), {daily_limit}/day per account, {global_limit}/day global max.

## Operating Mode: {mode.upper()}
"""
    if mode in ("aca", "both"):
        soul_content += f"""
### Mode A: ACA Auto-Pilot
- Push leads to ACA list: {aca_lead_list_id or 'set in config'}
- Auto-enroll in sequence: {aca_sequence_id or 'set in config'}
- ACA handles: sequences, follow-ups, reply detection, calendar booking
- You check the ACA dashboard, not Telegram
"""
    if mode in ("telegram", "both"):
        soul_content += """
### Mode B: Telegram Human-in-the-Loop
- Every message goes through Telegram for approval
- You control every stage transition
- Use for high-value leads and custom messaging
"""

    (profile_dir / "SOUL.md").write_text(soul_content)
    results.append("SOUL.md generated from questionnaire")

    # 4. Copy scripts
    scripts_dest = profile_dir / "scripts"
    scripts_dest.mkdir(parents=True, exist_ok=True)
    import shutil
    for script in SCRIPTS_DIR.glob("*.py"):
        shutil.copy2(script, scripts_dest / script.name)
    results.append("Scripts copied")

    # 5. Initialize database
    db_schema = scripts_dest / "db_schema.py"
    if db_schema.exists():
        subprocess.run([sys.executable, str(db_schema)], capture_output=True, text=True, timeout=30)
        results.append("Database initialized")

    # 6. Create data directories
    (profile_dir / "data").mkdir(parents=True, exist_ok=True)
    results.append("Data directories created")
    results.extend(_enable_root_plugin_on_profile(profile_name, "linkedin-dm-setter"))

    return json.dumps({
        "status": "ok",
        "mode": mode,
        "weekly_volume": weekly_volume,
        "voice_tone": voice_tone,
        "has_aca": bool(aca_org_id),
        "results": results,
        "live_use_bridge": [
            "Plugin code is installed once at root-level ~/.hermes/plugins/linkedin-dm-setter",
            "The dedicated profile only enables that shared plugin and stores SOUL.md/.env",
            "Run linkedin_status, then linkedin_smoke_test before any scraping or sends"
        ],
        "next_step": "Run 'hermes -p " + profile_name + "' and test with linkedin_status, then linkedin_smoke_test."
    })


def handle_status(args, **kwargs):
    try:
        profile_name = args.get("profile_name", "linkedin-setter")
        pdir = _get_profile_dir(profile_name)
        env = pdir / ".env"
        env_text = env.read_text(errors="ignore") if env.exists() else ""
        required = ["UNIPILE_API_KEY", "UNIPILE_BASE_URL", "UNIPILE_LINKEDIN_ACCOUNT_ID", "TELEGRAM_BOT_TOKEN"]
        checks = {
            "root_level_plugin_exists": (Path.home()/'.hermes'/'plugins'/'linkedin-dm-setter').exists(),
            "profile_exists": pdir.exists(),
            "plugin_enabled_on_profile": _config_has_plugin(profile_name, "linkedin-dm-setter"),
            "soul_exists": (pdir/'SOUL.md').exists(),
            "env_exists": env.exists(),
            "database_exists": _get_db_path(profile_name).exists(),
            "required_env_present": all(k in env_text and not env_text.split(k+'=',1)[1].split('\n',1)[0].strip()=='' for k in required if env_text),
        }
        missing = [k for k,v in checks.items() if not v]
        return json.dumps({
            "status": "ok",
            "profile_name": profile_name,
            "checks": checks,
            "ready": not missing,
            "missing": missing,
            "next_action": "Run linkedin_setup_profile with credentials and ICP details" if missing else "Run linkedin_smoke_test, then discover posts with a tiny limit."
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_smoke_test(args, **kwargs):
    try:
        profile_name = args.get("profile_name", "linkedin-setter")
        status_payload = json.loads(handle_status({"profile_name": profile_name}))
        report_dir = _get_profile_dir(profile_name) / "data"
        report_dir.mkdir(parents=True, exist_ok=True)
        report = report_dir / "smoke-test.json"
        report.write_text(json.dumps(status_payload, indent=2))
        return json.dumps({
            "status": "ok",
            "paid_calls": False,
            "linkedin_actions": False,
            "side_effects": ["created/updated local smoke-test report only"],
            "saved_to": str(report),
            "ready": status_payload.get("ready", False),
            "next_action": status_payload.get("next_action")
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_discover_posts(args, **kwargs):
    """Find viral posts and scrape commenters."""
    max_posts = args.get("max_posts_per_influencer", 5)
    max_commenters = args.get("max_commenters_per_post", 30)
    auto_expand = args.get("auto_expand", True)
    
    return _run_script("discover_posts.py", [
        "--max-posts", str(max_posts),
        "--max-commenters", str(max_commenters),
        "--auto-expand" if auto_expand else "--no-auto-expand"
    ])


def handle_send_connections(args, **kwargs):
    """Send connection requests."""
    limit = args.get("limit", 10)
    dry_run = args.get("dry_run", True)
    
    cmd_args = ["--limit", str(limit)]
    if not dry_run:
        cmd_args.append("--confirm-send")
    
    return _run_script("send_connections.py", cmd_args)


def handle_check_replies(args, **kwargs):
    """Check for new replies."""
    return _run_script("reply_monitor.py")


def handle_queue_drafts(args, **kwargs):
    """Queue drafts to Telegram."""
    return _run_script("approval_gate.py")


def handle_approve_message(args, **kwargs):
    """Approve or reject a draft."""
    msg_id = args.get("message_id")
    action = args.get("action")
    edited_text = args.get("edited_text")
    
    if action == "approve":
        cmd = "approve " + str(msg_id)
        if edited_text:
            cmd += " " + edited_text
    else:
        cmd = "reject " + str(msg_id)
    
    return _run_script("approval_gate.py", [cmd])


def handle_send_approved(args, **kwargs):
    """Send approved messages via Unipile."""
    return _run_script("approval_gate.py", ["send"])


def handle_throttle_status(args, **kwargs):
    """Show throttle status."""
    return _run_script("shared_throttle.py")


def handle_funnel_report(args, **kwargs):
    """Generate funnel report."""
    days = args.get("days", 7)
    
    # Run inline since it's a simple DB query
    try:
        from datetime import datetime, timedelta
        import sqlite3
        
        db_path = _get_db_path()
        if not db_path.exists():
            return json.dumps({"status": "error", "error": "Database not found"})
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        period_start = (datetime.utcnow() - timedelta(days=days)).isoformat()
        period_end = datetime.utcnow().isoformat()
        
        c.execute("SELECT COUNT(*) FROM messages WHERE direction = 'outbound' AND stage = 0 AND status = 'sent' AND sent_at >= ?", (period_start,))
        connects_sent = c.fetchone()[0]
        
        c.execute("SELECT COUNT(DISTINCT c.id) FROM conversations c JOIN messages m ON m.conversation_id = c.id WHERE c.stage > 0 AND m.status = 'sent' AND m.stage = 0 AND m.sent_at >= ?", (period_start,))
        accepted = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM messages WHERE direction = 'inbound' AND status = 'received' AND created_at >= ?", (period_start,))
        replies = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM conversations WHERE stage >= 7 AND updated_at >= ?", (period_start,))
        booked = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM conversations WHERE showed_at IS NOT NULL AND showed_at >= ?", (period_start,))
        showed = c.fetchone()[0]
        
        conn.close()
        
        accept_rate = round((accepted / connects_sent * 100) if connects_sent > 0 else 0, 1)
        reply_rate = round((replies / accepted * 100) if accepted > 0 else 0, 1)
        book_rate = round((booked / replies * 100) if replies > 0 else 0, 1)
        show_rate = round((showed / booked * 100) if booked > 0 else 0, 1)
        
        return json.dumps({
            "status": "ok",
            "period_days": days,
            "connects_sent": connects_sent,
            "accepted": accepted,
            "replies": replies,
            "booked": booked,
            "showed": showed,
            "accept_rate": accept_rate,
            "reply_rate": reply_rate,
            "book_rate": book_rate,
            "show_rate": show_rate
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def handle_add_lead(args, **kwargs):
    """Add a lead manually."""
    try:
        import sqlite3
        
        db_path = _get_db_path()
        if not db_path.exists():
            return json.dumps({"status": "error", "error": "Database not found"})
        
        linkedin_url = args.get("linkedin_url")
        full_name = args.get("full_name")
        title = args.get("title", "")
        company = args.get("company", "")
        headline = args.get("headline", "")
        hook = args.get("personalization_hook", "")
        source = args.get("source", "manual")
        
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        
        # Check if exists
        c.execute("SELECT id FROM leads WHERE linkedin_url = ?", (linkedin_url,))
        if c.fetchone():
            conn.close()
            return json.dumps({"status": "ok", "message": "Lead already exists", "action": "skipped"})
        
        first_name = full_name.split()[0] if full_name else None
        last_name = " ".join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else None
        
        c.execute("""
        INSERT INTO leads (linkedin_url, full_name, first_name, last_name, title, company, headline, personalization_hook, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (linkedin_url, full_name, first_name, last_name, title, company, headline, hook, source))
        
        lead_id = c.lastrowid
        
        c.execute("""
        INSERT INTO conversations (lead_id, stage, stage_name, opener_variant)
        VALUES (?, 0, 'Connect', 'A')
        """, (lead_id,))
        
        conn.commit()
        conn.close()
        
        return json.dumps({"status": "ok", "lead_id": lead_id, "message": "Lead added"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def handle_push_to_aca(args, **kwargs):
    """Push scored leads from pipeline DB to ACA lead list."""
    import sqlite3

    min_icp_score = args.get("min_icp_score", 7)
    aca_org_id = args.get("aca_org_id")
    aca_lead_list_id = args.get("aca_lead_list_id")
    max_leads = args.get("max_leads", 50)
    stage_filter = args.get("stage_filter", "connected")

    db_path = _get_db_path()
    if not db_path.exists():
        return json.dumps({"status": "error", "error": "Database not found"})

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("""
            SELECT l.linkedin_url, l.full_name, l.first_name, l.last_name,
                   l.title, l.company, l.headline, l.icp_score, c.stage, c.stage_name
            FROM leads l
            JOIN conversations c ON c.lead_id = l.id
            WHERE l.icp_score >= ?
              AND c.stage_name = ?
              AND l.linkedin_url IS NOT NULL
            ORDER BY l.icp_score DESC
            LIMIT ?
        """, (min_icp_score, stage_filter, max_leads))

        leads = [dict(row) for row in c.fetchall()]
        conn.close()

        if not leads:
            return json.dumps({"status": "ok", "pushed": 0, "message": "No leads matching filter"})

        return json.dumps({
            "status": "ok",
            "ready_to_push": len(leads),
            "aca_org_id": aca_org_id,
            "aca_lead_list_id": aca_lead_list_id,
            "leads": leads,
            "next_action": "Use mcp_ACA_bulk_create_leads to create the leads in ACA, then mcp_ACA_add_contacts_to_list to add them to the lead list."
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def handle_aca_auto_enroll(args, **kwargs):
    """Enroll leads from ACA lead list into a sequence/campaign."""
    confirm = args.get("confirm_enroll", False)
    if not confirm:
        return json.dumps({
            "status": "ok",
            "message": "Dry run. Set confirm_enroll=true to execute.",
            "next_action": "Use mcp_ACA_get_lead_list to verify the leads, then mcp_ACA_enroll_leads to enroll them."
        })

    aca_org_id = args.get("aca_org_id")
    aca_lead_list_id = args.get("aca_lead_list_id")
    aca_sequence_id = args.get("aca_sequence_id")
    max_leads = args.get("max_leads", 50)

    return json.dumps({
        "status": "ok",
        "confirmed": True,
        "aca_org_id": aca_org_id,
        "aca_lead_list_id": aca_lead_list_id,
        "aca_sequence_id": aca_sequence_id,
        "max_leads": max_leads,
        "next_action": "Use mcp_ACA_enroll_leads with sequence_id=" + aca_sequence_id + " and lead_ids from the lead list. Then use mcp_ACA_update_campaign_status to activate the campaign."
    })


def handle_aca_status(args, **kwargs):
    """Check ACA campaign status."""
    aca_org_id = args.get("aca_org_id")
    aca_sequence_id = args.get("aca_sequence_id")
    days = args.get("days", 7)

    if not aca_sequence_id:
        return json.dumps({
            "status": "ok",
            "message": "No sequence_id provided. Returning org overview.",
            "next_action": "Use mcp_ACA_list_campaigns, mcp_ACA_list_email_sequences, mcp_ACA_list_conversations with interested intent."
        })

    return json.dumps({
        "status": "ok",
        "aca_org_id": aca_org_id,
        "aca_sequence_id": aca_sequence_id,
        "days": days,
        "next_action": "Use mcp_ACA_get_email_sequence with this sequence_id, mcp_ACA_list_email_enrollments for enrollment stats, and mcp_ACA_list_conversations for reply detection."
    })


HANDLERS = {
    "linkedin_setup_profile": handle_setup,
    "linkedin_status": handle_status,
    "linkedin_smoke_test": handle_smoke_test,
    "linkedin_discover_posts": handle_discover_posts,
    "linkedin_send_connections": handle_send_connections,
    "linkedin_check_replies": handle_check_replies,
    "linkedin_queue_drafts": handle_queue_drafts,
    "linkedin_approve_message": handle_approve_message,
    "linkedin_send_approved": handle_send_approved,
    "linkedin_throttle_status": handle_throttle_status,
    "linkedin_funnel_report": handle_funnel_report,
    "linkedin_add_lead": handle_add_lead,
    "linkedin_push_to_aca": handle_push_to_aca,
    "linkedin_aca_auto_enroll": handle_aca_auto_enroll,
    "linkedin_aca_status": handle_aca_status,
}
