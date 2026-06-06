#!/usr/bin/env python3
"""
LinkedIn DM Setter -- Throttled Connection Request Sender
Sends connection requests with per-account limits and delays.
"""

import json
import sys
import os
import time
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_schema import get_conn, get_lead, update_lead, queue_draft, get_conversation
from unipile_client import Unipile, load_env
from shared_throttle import ThrottleLock, LIMITS

# Throttle config
MIN_DELAY_SECONDS = 45            # Minimum delay between requests
MAX_DELAY_SECONDS = 120           # Maximum delay between requests (randomized)

def get_leads_at_stage0(limit=10):
    """Get leads at stage 0 (Connect) that haven't been sent a request yet."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
    SELECT l.*, c.id as conv_id, c.opener_variant
    FROM leads l
    JOIN conversations c ON c.lead_id = l.id
    WHERE c.stage = 0 AND c.status = 'active'
    AND l.icp_score >= 3
    AND l.connected_at IS NULL
    ORDER BY l.icp_score DESC, l.created_at ASC
    LIMIT ?
    ''', (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def send_connection_requests(limit=10, dry_run=True, agent_name='linkedin-setter'):
    """
    Send connection requests with throttling.
    Uses shared throttle lock so multiple agents respect global limits.
    
    Args:
        limit: Max requests to send this run
        dry_run: If True, just show what would be sent
        agent_name: Name of the calling agent (for tracking)
    """
    load_env()
    api = Unipile()
    lock = ThrottleLock(agent_name=agent_name)
    
    # Check global daily limits
    status = lock.get_status()
    global_remaining = status['global_remaining']
    if global_remaining <= 0:
        print('Global daily limit reached: ' + str(status['global_today']) + '/' + str(status['global_limit']))
        print('Wait until tomorrow.')
        lock.release()
        return 0
    
    # Adjust limit to remaining daily capacity
    effective_limit = min(limit, global_remaining)
    
    leads = get_leads_at_stage0(effective_limit)
    if not leads:
        print('No leads at stage 0 ready for connection requests.')
        return 0
    
    if dry_run:
        print('DRY RUN: Would send ' + str(len(leads)) + ' connection requests')
        print('Daily budget: ' + str(status['global_today']) + '/' + str(status['global_limit']) + ' used')
        for acc_id, acc in status['accounts'].items():
            print('  ' + acc['name'] + ': ' + str(acc['today']) + '/' + str(acc['limit']))
        print()
        for l in leads:
            print('  - ' + l['full_name'] + ' | ' + str(l['title']) + ' | Score: ' + str(l['icp_score']))
        print()
        print('Add --confirm-send to actually send.')
        lock.release()
        return len(leads)
    
    sent_count = 0
    
    for i, lead in enumerate(leads):
        # Pick best account via shared throttle
        ok, reason, account_id = lock.can_send()
        if not ok:
            print(reason + '. Stopping.')
            break
        
        public_id = lead['linkedin_url'].split('/in/')[-1].strip('/')
        
        # Get provider_id from Unipile
        profile_res = api.request('GET', '/users/' + public_id, {
            'account_id': account_id
        })
        
        if profile_res.get('status') != 200:
            print('Failed to get profile for ' + public_id + ': ' + str(profile_res.get('error')))
            continue
        
        provider_id = profile_res['data'].get('provider_id') or profile_res['data'].get('id')
        if not provider_id:
            print('No provider_id for ' + public_id)
            continue
        
        # Send blank connection request (no note)
        body = {
            'provider_id': provider_id,
            'account_id': account_id,
            'message': '',  # Blank -- per the goal prompt
        }
        
        res = api.request('POST', '/users/invite', body=body)
        
        if res.get('status') in (200, 201):
            # Mark as connected (request sent)
            update_lead(lead['id'], connected_at=datetime.utcnow().isoformat())
            
            # Record in shared throttle (prevents other agents from over-sending)
            lock.record_send(account_id, lead['linkedin_url'])
            
            # Record the message AND bind account to conversation (threading)
            conn = get_conn()
            c = conn.cursor()
            conv = get_conversation(lead['id'])
            if conv:
                c.execute('''
                INSERT INTO messages (conversation_id, direction, stage, draft_text, approved_text, sent_text, status, opener_variant, sent_at, account_id)
                VALUES (?, 'outbound', 0, '', '', '', 'sent', 'A', ?, ?)
                ''', (conv['id'], datetime.utcnow().isoformat(), account_id))
                # Bind this account to the conversation (threading)
                c.execute('UPDATE conversations SET account_id = ? WHERE id = ?', (account_id, conv['id']))
                conn.commit()
            conn.close()
            
            sent_count += 1
            acc_name = LIMITS.get(account_id, {}).get('name', account_id[:8])
            print('[' + acc_name + '] Sent to ' + lead['full_name'] + ' (' + str(sent_count) + '/' + str(len(leads)) + ')')
            
            # Throttle: random delay between requests (skip on last)
            if i < len(leads) - 1:
                delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                print('  Waiting ' + str(delay) + 's before next request...')
                time.sleep(delay)
        else:
            print('Failed to send to ' + lead['full_name'] + ': ' + str(res.get('error')))
    
    lock.release()
    print()
    print('Sent ' + str(sent_count) + '/' + str(len(leads)) + ' connection requests.')
    return sent_count

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=10, help='Max requests to send')
    p.add_argument('--confirm-send', action='store_true', help='Actually send (default is dry run)')
    args = p.parse_args()
    
    send_connection_requests(args.limit, dry_run=not args.confirm_send)
