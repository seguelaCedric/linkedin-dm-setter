#!/usr/bin/env python3
"""
LinkedIn DM Setter -- Reply Monitor via Unipile
Checks LinkedIn chats for new replies and advances conversation stages.
"""

import json
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_schema import (get_conn, get_lead, get_conversation, record_reply,
                       advance_stage, update_thread_context, update_lead)
from generate_draft import generate_stage_advance_draft
from unipile_client import Unipile, load_env

# Stage names mapping
STAGE_NAMES = {
    0: 'Connect', 1: 'Open', 2: 'Filter Intent', 3: 'Diagnose',
    4: 'Frame', 5: 'Qualify', 6: 'Earn the Right', 7: 'Book', 8: 'Nurture'
}

def get_all_active_leads():
    """Get all leads with active conversations (stage > 0, status = active)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
    SELECT l.*, c.id as conv_id, c.stage, c.thread_context, c.account_id as bound_account
    FROM leads l
    JOIN conversations c ON c.lead_id = l.id
    WHERE c.status = 'active' AND c.stage > 0
    ORDER BY l.last_contact_at DESC
    ''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def extract_public_id(linkedin_url):
    """Extract public identifier from LinkedIn URL."""
    if '/in/' in linkedin_url:
        return linkedin_url.split('/in/')[-1].strip('/')
    return None

def check_replies():
    """Check Unipile chats for new replies to active conversations.
    Only checks chats from the bound account for each conversation (threading)."""
    load_env()
    api = Unipile()
    
    # Get active leads for matching
    active_leads = get_all_active_leads()
    if not active_leads:
        print("No active conversations to monitor.")
        return 0
    
    # Build lookup: public_id -> lead
    lead_lookup = {}
    for lead in active_leads:
        public_id = extract_public_id(lead['linkedin_url'])
        if public_id:
            lead_lookup[public_id] = lead
    
    # Get unique bound accounts from active conversations
    bound_accounts = set()
    for lead in active_leads:
        if lead.get('bound_account'):
            bound_accounts.add(lead['bound_account'])
    
    if not bound_accounts:
        print("No bound accounts found for active conversations.")
        return 0
    
    # Fetch chats from each bound account
    all_chats = []
    for account_id in bound_accounts:
        chats_res = api.request('GET', '/chats', {
            'account_id': account_id,
            'limit': '50',
        })
        if chats_res.get('status') == 200:
            chats = chats_res['data'].get('items', [])
            all_chats.extend(chats)
    
    if not all_chats:
        print("No chats found.")
        return 0
    
    chats = all_chats
    
    replies_found = 0
    stages_advanced = 0
    drafts_queued = 0
    
    for chat in chats:
        chat_id = chat.get('id')
        attendees = chat.get('attendees', [])
        
        # Find if this chat is with one of our leads
        matched_lead = None
        for att in attendees:
            att_id = att.get('public_identifier') or att.get('provider_id', '')
            if att_id in lead_lookup:
                matched_lead = lead_lookup[att_id]
                break
        
        if not matched_lead:
            continue
        
        # Get recent messages in this chat
        msgs_res = api.request('GET', '/chats/' + chat_id + '/messages', {
            'limit': '5',
        })
        
        if msgs_res.get('status') != 200:
            continue
        
        messages = msgs_res['data'].get('items', [])
        
        # Check for inbound messages (from the lead, not us)
        for msg in messages:
            if msg.get('sender') == 'self':
                continue  # Skip our own messages
            
            # This is an inbound reply
            msg_text = msg.get('text', '')
            msg_timestamp = msg.get('timestamp')
            
            # Check if we already recorded this reply
            conn = get_conn()
            c = conn.cursor()
            c.execute('''
            SELECT id FROM messages 
            WHERE conversation_id = ? AND direction = 'inbound' 
            AND draft_text = ? AND status = 'received'
            ''', (matched_lead['conv_id'], msg_text))
            existing = c.fetchone()
            conn.close()
            
            if existing:
                continue  # Already recorded
            
            # Record the reply
            record_reply(matched_lead['conv_id'], msg_text)
            replies_found += 1
            
            # Update lead's last contact
            update_lead(matched_lead['id'], last_contact_at=msg_timestamp or datetime.utcnow().isoformat())
            
            # Try to advance stage and generate draft
            old_stage = matched_lead['stage']
            result = generate_stage_advance_draft(matched_lead['id'], inbound_message=msg_text)
            
            if result:
                msg_id, draft_text, new_stage, variant = result
                if new_stage > old_stage:
                    advance_stage(matched_lead['conv_id'], new_stage, STAGE_NAMES.get(new_stage, 'Unknown'))
                    stages_advanced += 1
                drafts_queued += 1
                
                # Update thread context
                context = json.loads(matched_lead.get('thread_context') or '[]')
                context.append({'role': 'inbound', 'text': msg_text, 'timestamp': msg_timestamp})
                context.append({'role': 'outbound', 'text': draft_text, 'stage': new_stage})
                # Keep last 10 messages
                update_thread_context(matched_lead['conv_id'], context[-10:])
            
            print("Reply from " + matched_lead['full_name'] + " (stage " + str(old_stage) + " -> " + str(matched_lead['stage']) + ")")
            break  # Only process one reply per chat per run
    
    print("Replies: " + str(replies_found) + " | Stages advanced: " + str(stages_advanced) + " | Drafts queued: " + str(drafts_queued))
    return replies_found

if __name__ == '__main__':
    count = check_replies()
    print("Total replies processed: " + str(count))
