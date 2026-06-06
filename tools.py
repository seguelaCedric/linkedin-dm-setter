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


def _get_db_path(profile_name="linkedin-setter"):
    """Get the database path."""
    return _get_profile_dir(profile_name) / "data" / "conversations.db"


def handle_setup(args, **kwargs):
    """Set up the LinkedIn DM Setter profile."""
    profile_name = args.get("profile_name", "linkedin-setter")
    unipile_api_key = args.get("unipile_api_key")
    unipile_base_url = args.get("unipile_base_url")
    unipile_account_id = args.get("unipile_account_id")
    unipile_account_id_backup = args.get("unipile_account_id_backup", "")
    telegram_bot_token = args.get("telegram_bot_token")
    telegram_chat_id = args.get("telegram_chat_id")
    
    results = []
    
    # 1. Create profile
    try:
        subprocess.run(["hermes", "profile", "create", profile_name], capture_output=True, text=True, timeout=30)
        results.append("Profile created: " + profile_name)
    except Exception as e:
        results.append("Profile creation note: " + str(e))
    
    profile_dir = _get_profile_dir(profile_name)
    
    # 2. Write .env
    env_content = "\n".join([
        "UNIPILE_API_KEY=" + unipile_api_key,
        "UNIPILE_BASE_URL=" + unipile_base_url,
        "UNIPILE_LINKEDIN_ACCOUNT_ID=" + unipile_account_id,
        "UNIPILE_LINKEDIN_ACCOUNT_ID_BACKUP=" + unipile_account_id_backup,
        "TELEGRAM_BOT_TOKEN=" + telegram_bot_token,
        "TELEGRAM_HOME_CHAT_ID=" + telegram_chat_id,
        "HERMES_HOME=/root/.hermes",
    ])
    (profile_dir / ".env").write_text(env_content)
    results.append(".env written")
    
    # 3. Write SOUL.md
    soul_template = TEMPLATES_DIR / "SOUL.md.template"
    if soul_template.exists():
        (profile_dir / "SOUL.md").write_text(soul_template.read_text())
        results.append("SOUL.md written")
    
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
    
    return json.dumps({"status": "ok", "results": results})


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


HANDLERS = {
    "linkedin_setup_profile": handle_setup,
    "linkedin_discover_posts": handle_discover_posts,
    "linkedin_send_connections": handle_send_connections,
    "linkedin_check_replies": handle_check_replies,
    "linkedin_queue_drafts": handle_queue_drafts,
    "linkedin_approve_message": handle_approve_message,
    "linkedin_send_approved": handle_send_approved,
    "linkedin_throttle_status": handle_throttle_status,
    "linkedin_funnel_report": handle_funnel_report,
    "linkedin_add_lead": handle_add_lead,
}
