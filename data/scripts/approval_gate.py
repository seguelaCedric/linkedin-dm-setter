#!/usr/bin/env python3
"""
LinkedIn DM Setter -- Telegram Approval Gate + Unipile Sending
Sends draft messages to Cedric for approval, then sends via Unipile.
"""

import json
import sys
import os
import urllib.request
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_schema import get_pending_drafts, approve_message, mark_sent, get_conn, get_lead, get_conversation, update_lead

# Import Unipile client (also loads .env)
from unipile_client import Unipile, load_env

# Load env vars from profile .env
from pathlib import Path
ENV_FILE = Path(os.path.expanduser('~/.hermes/profiles/linkedin-setter/.env'))
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

# Telegram config from env
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TELEGRAM_HOME_CHAT_ID', '')

def send_telegram(text, parse_mode='HTML'):
    """Send a message to Cedric's Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_HOME_CHAT_ID not set")
        return False
    
    url = 'https://api.telegram.org/bot' + BOT_TOKEN + '/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': parse_mode,
    }
    
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return result.get('ok', False)
    except Exception as e:
        print("Telegram error: " + str(e))
        return False

def format_draft_for_approval(draft):
    """Format a draft message for Telegram approval."""
    lead_name = draft.get('full_name', 'Unknown')
    company = draft.get('company', '')
    title = draft.get('title', '')
    stage = draft.get('stage', 0)
    draft_text = draft.get('draft_text', '')
    msg_id = draft.get('id', 0)
    
    lines = [
        '<b>LinkedIn Draft #' + str(msg_id) + '</b>',
        '',
        '<b>Lead:</b> ' + lead_name,
        '<b>Title:</b> ' + str(title),
        '<b>Company:</b> ' + str(company),
        '<b>Stage:</b> ' + str(stage),
        '',
        '<b>Draft:</b>',
        '<i>' + str(draft_text) + '</i>',
        '',
        '<b>Reply with:</b>',
        '- <code>approve ' + str(msg_id) + '</code> to send as-is',
        '- <code>approve ' + str(msg_id) + ' [edited text]</code> to edit and send',
        '- <code>reject ' + str(msg_id) + '</code> to discard',
    ]
    
    return chr(10).join(lines)

def queue_drafts_for_approval():
    """Send all pending drafts to Cedric for approval."""
    drafts = get_pending_drafts()
    
    if not drafts:
        print("No pending drafts to approve.")
        return 0
    
    # Send header
    send_telegram('<b>' + str(len(drafts)) + ' LinkedIn drafts awaiting approval</b>')
    
    # Send each draft
    for draft in drafts:
        text = format_draft_for_approval(draft)
        send_telegram(text)
    
    print("Queued " + str(len(drafts)) + " drafts for approval.")
    return len(drafts)

def send_approved_via_unipile():
    """Send all approved (unsent) messages via Unipile."""
    from db_schema import get_approved_unsent
    
    approved = get_approved_unsent()
    if not approved:
        print("No approved messages to send.")
        return 0
    
    load_env()
    api = Unipile()
    sent_count = 0
    
    for msg in approved:
        lead_id = msg['lead_id']
        lead = get_lead(lead_id=lead_id)
        if not lead:
            print("Lead not found for message #" + str(msg['id']))
            continue
        
        # Get the conversation to find the bound account_id (threading)
        conv = get_conversation(lead_id)
        if not conv or not conv.get('account_id'):
            print("No account bound to conversation for " + lead['full_name'] + " -- cannot send")
            continue
        
        # Use the bound account, not the default
        bound_account_id = conv['account_id']
        
        linkedin_url = lead['linkedin_url']
        public_id = linkedin_url.split('/in/')[-1].strip('/')
        
        # Get profile to find provider_id, using the BOUND account
        profile_res = api.request('GET', '/users/' + urllib.parse.quote(public_id), {
            'account_id': bound_account_id
        })
        
        if profile_res.get('status') != 200:
            print("Failed to get profile for " + public_id + ": " + str(profile_res.get('error')))
            continue
        
        provider_id = profile_res['data'].get('provider_id') or profile_res['data'].get('id')
        if not provider_id:
            print("No provider_id found for " + public_id)
            continue
        
        # Send the message using the BOUND account (threading)
        text = msg['approved_text'] or msg['draft_text']
        send_res = api.request('POST', '/chats', form={
            'account_id': bound_account_id,
            'text': text,
            'attendees_ids': provider_id,
        })
        
        if send_res.get('status') in (200, 201):
            mark_sent(msg['id'], text)
            update_lead(lead_id, last_contact_at=__import__('datetime').datetime.utcnow().isoformat())
            sent_count += 1
            print("Sent to " + lead['full_name'] + " (stage " + str(msg['stage']) + ")")
        else:
            print("Failed to send to " + lead['full_name'] + ": " + str(send_res.get('error')))
    
    print("Sent " + str(sent_count) + "/" + str(len(approved)) + " messages via Unipile.")
    return sent_count

def handle_approval_command(command_text):
    """
    Parse and handle an approval command from Telegram.
    
    Commands:
    - approve <id> -- approve draft as-is
    - approve <id> <edited text> -- approve with edits
    - reject <id> -- reject draft
    - send -- send all approved messages via Unipile
    """
    parts = command_text.strip().split(maxsplit=2)
    if not parts:
        return None
    
    action = parts[0].lower()
    
    if action == 'send':
        count = send_approved_via_unipile()
        return ('send', count, None)
    
    if len(parts) < 2:
        return None
    
    try:
        msg_id = int(parts[1])
    except ValueError:
        return None
    
    edited_text = parts[2] if len(parts) > 2 else None
    
    if action == 'approve':
        approve_message(msg_id, edited_text)
        return ('approve', msg_id, edited_text)
    elif action == 'reject':
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE messages SET status = 'rejected' WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()
        return ('reject', msg_id, None)
    
    return None

if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = ' '.join(sys.argv[1:])
        result = handle_approval_command(cmd)
        if result:
            action = result[0]
            if action == 'send':
                print("Sent " + str(result[1]) + " messages via Unipile.")
            else:
                print("Processed: " + action + " message #" + str(result[1]))
        else:
            print("Invalid command: " + cmd)
    else:
        count = queue_drafts_for_approval()
        print("Queued " + str(count) + " drafts.")
