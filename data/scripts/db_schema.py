#!/usr/bin/env python3
"""
LinkedIn DM Setter -- SQLite Database Schema & Helpers
Conversation state machine for tracking leads through 9 stages.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = '/root/.hermes/profiles/linkedin-setter/data/conversations.db'

def get_conn():
    """Get database connection, creating data dir and DB if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init_db():
    """Create all tables if they don't exist."""
    conn = get_conn()
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        linkedin_url TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        title TEXT,
        company TEXT,
        company_url TEXT,
        industry TEXT,
        location TEXT,
        headline TEXT,
        icp_score INTEGER DEFAULT 0,
        icp_criteria_met TEXT DEFAULT '{}',
        personalization_hook TEXT,
        source TEXT,
        source_detail TEXT,
        connected_at TEXT,
        last_contact_at TEXT,
        next_followup_at TEXT,
        disqualify_reason TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL,
        stage INTEGER DEFAULT 0,
        stage_name TEXT DEFAULT 'Connect',
        opener_variant TEXT DEFAULT 'A',
        status TEXT DEFAULT 'active',
        thread_context TEXT DEFAULT '[]',
        booked_at TEXT,
        showed_at TEXT,
        meeting_link TEXT,
        meeting_email TEXT,
        meeting_phone TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (lead_id) REFERENCES leads(id)
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        direction TEXT NOT NULL,
        stage INTEGER,
        draft_text TEXT,
        approved_text TEXT,
        sent_text TEXT,
        status TEXT DEFAULT 'draft',
        opener_variant TEXT,
        sent_at TEXT,
        approved_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS funnel_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period TEXT NOT NULL,
        connects_sent INTEGER DEFAULT 0,
        connects_accepted INTEGER DEFAULT 0,
        replies_received INTEGER DEFAULT 0,
        calls_booked INTEGER DEFAULT 0,
        calls_showed INTEGER DEFAULT 0,
        accept_rate REAL,
        reply_rate REAL,
        book_rate REAL,
        show_rate REAL,
        opener_a_sends INTEGER DEFAULT 0,
        opener_a_replies INTEGER DEFAULT 0,
        opener_b_sends INTEGER DEFAULT 0,
        opener_b_replies INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hypothesis TEXT,
        variant_a TEXT,
        variant_b TEXT,
        start_date TEXT,
        end_date TEXT,
        sends_a INTEGER DEFAULT 0,
        replies_a INTEGER DEFAULT 0,
        sends_b INTEGER DEFAULT 0,
        replies_b INTEGER DEFAULT 0,
        winner TEXT,
        action_taken TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    ''')
    
    # Indexes for common queries
    c.execute('CREATE INDEX IF NOT EXISTS idx_leads_linkedin_url ON leads(linkedin_url)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(icp_score)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_conversations_lead ON conversations(lead_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_conversations_stage ON conversations(stage)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status)')
    
    conn.commit()
    conn.close()
    print(f'Database initialized at {DB_PATH}')

# --- Lead helpers ---

def add_lead(linkedin_url, full_name, title=None, company=None, 
             company_url=None, industry=None, location=None, headline=None,
             icp_score=0, icp_criteria_met=None, personalization_hook=None,
             source=None, source_detail=None):
    """Add a new lead. Returns lead_id. Skips if URL already exists."""
    conn = get_conn()
    c = conn.cursor()
    
    # Check if exists
    c.execute('SELECT id FROM leads WHERE linkedin_url = ?', (linkedin_url,))
    existing = c.fetchone()
    if existing:
        conn.close()
        return existing['id']
    
    first_name = full_name.split()[0] if full_name else None
    last_name = ' '.join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else None
    
    c.execute('''
    INSERT INTO leads (linkedin_url, full_name, first_name, last_name, title, company,
                       company_url, industry, location, headline, icp_score, 
                       icp_criteria_met, personalization_hook, source, source_detail)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (linkedin_url, full_name, first_name, last_name, title, company,
          company_url, industry, location, headline, icp_score,
          json.dumps(icp_criteria_met or {}), personalization_hook, source, source_detail))
    
    lead_id = c.lastrowid
    
    # Auto-create conversation at stage 0
    c.execute('''
    INSERT INTO conversations (lead_id, stage, stage_name, opener_variant)
    VALUES (?, 0, 'Connect', 'A')
    ''', (lead_id,))
    
    conn.commit()
    conn.close()
    return lead_id

def get_lead(lead_id=None, linkedin_url=None):
    """Get lead by ID or URL."""
    conn = get_conn()
    c = conn.cursor()
    if lead_id:
        c.execute('SELECT * FROM leads WHERE id = ?', (lead_id,))
    elif linkedin_url:
        c.execute('SELECT * FROM leads WHERE linkedin_url = ?', (linkedin_url,))
    else:
        conn.close()
        return None
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_lead(lead_id, **kwargs):
    """Update lead fields."""
    conn = get_conn()
    c = conn.cursor()
    kwargs['updated_at'] = datetime.utcnow().isoformat()
    sets = ', '.join(f'{k} = ?' for k in kwargs)
    vals = list(kwargs.values()) + [lead_id]
    c.execute(f'UPDATE leads SET {sets} WHERE id = ?', vals)
    conn.commit()
    conn.close()

# --- Conversation helpers ---

def get_conversation(lead_id):
    """Get active conversation for a lead."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM conversations WHERE lead_id = ? AND status = ? ORDER BY id DESC LIMIT 1',
              (lead_id, 'active'))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def advance_stage(conversation_id, new_stage, stage_name):
    """Advance conversation to next stage."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
    UPDATE conversations 
    SET stage = ?, stage_name = ?, updated_at = ?
    WHERE id = ?
    ''', (new_stage, stage_name, datetime.utcnow().isoformat(), conversation_id))
    conn.commit()
    conn.close()

def update_thread_context(conversation_id, context_list):
    """Update thread context (last N messages)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE conversations SET thread_context = ?, updated_at = ? WHERE id = ?',
              (json.dumps(context_list), datetime.utcnow().isoformat(), conversation_id))
    conn.commit()
    conn.close()

# --- Message helpers ---

def queue_draft(conversation_id, stage, draft_text, opener_variant=None):
    """Queue a message draft for approval."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
    INSERT INTO messages (conversation_id, direction, stage, draft_text, status, opener_variant)
    VALUES (?, 'outbound', ?, ?, 'draft', ?)
    ''', (conversation_id, stage, draft_text, opener_variant))
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id

def approve_message(message_id, approved_text=None):
    """Approve a draft message."""
    conn = get_conn()
    c = conn.cursor()
    if approved_text:
        c.execute('UPDATE messages SET approved_text = ?, status = ?, approved_at = ? WHERE id = ?',
                  (approved_text, 'approved', datetime.utcnow().isoformat(), message_id))
    else:
        c.execute('UPDATE messages SET approved_text = draft_text, status = ?, approved_at = ? WHERE id = ?',
                  ('approved', datetime.utcnow().isoformat(), message_id))
    conn.commit()
    conn.close()

def mark_sent(message_id, sent_text=None):
    """Mark message as sent."""
    conn = get_conn()
    c = conn.cursor()
    text = sent_text or ''
    c.execute('UPDATE messages SET sent_text = ?, status = ?, sent_at = ? WHERE id = ?',
              (text, 'sent', datetime.utcnow().isoformat(), message_id))
    conn.commit()
    conn.close()

def record_reply(conversation_id, reply_text):
    """Record an inbound reply."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
    INSERT INTO messages (conversation_id, direction, stage, draft_text, status)
    VALUES (?, 'inbound', (SELECT stage FROM conversations WHERE id = ?), ?, 'received')
    ''', (conversation_id, conversation_id, reply_text))
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id

def get_pending_drafts():
    """Get all drafts awaiting approval."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
    SELECT m.*, c.lead_id, c.stage as conv_stage, l.full_name, l.company, l.title
    FROM messages m
    JOIN conversations c ON m.conversation_id = c.id
    JOIN leads l ON c.lead_id = l.id
    WHERE m.status = 'draft' AND m.direction = 'outbound'
    ORDER BY m.created_at ASC
    ''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_approved_unsent():
    """Get all approved messages not yet sent."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
    SELECT m.*, c.lead_id, l.full_name, l.linkedin_url
    FROM messages m
    JOIN conversations c ON m.conversation_id = c.id
    JOIN leads l ON c.lead_id = l.id
    WHERE m.status = 'approved' AND m.direction = 'outbound'
    ORDER BY m.approved_at ASC
    ''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

# --- Funnel stats ---

def calculate_funnel(period_start=None, period_end=None):
    """Calculate funnel metrics for a period."""
    conn = get_conn()
    c = conn.cursor()
    
    if not period_start:
        period_start = (datetime.utcnow() - timedelta(days=7)).isoformat()
    if not period_end:
        period_end = datetime.utcnow().isoformat()
    
    # Connection requests sent (stage 0 outbound messages)
    c.execute('''
    SELECT COUNT(*) as cnt FROM messages 
    WHERE direction = 'outbound' AND stage = 0 AND status = 'sent'
    AND sent_at BETWEEN ? AND ?
    ''', (period_start, period_end))
    connects_sent = c.fetchone()['cnt']
    
    # Accepted (moved past stage 0)
    c.execute('''
    SELECT COUNT(DISTINCT c.id) as cnt FROM conversations c
    JOIN messages m ON m.conversation_id = c.id
    WHERE c.stage > 0 AND m.status = 'sent' AND m.stage = 0
    AND m.sent_at BETWEEN ? AND ?
    ''', (period_start, period_end))
    accepted = c.fetchone()['cnt']
    
    # Replies received
    c.execute('''
    SELECT COUNT(*) as cnt FROM messages
    WHERE direction = 'inbound' AND status = 'received'
    AND created_at BETWEEN ? AND ?
    ''', (period_start, period_end))
    replies = c.fetchone()['cnt']
    
    # Calls booked (stage >= 7)
    c.execute('''
    SELECT COUNT(*) as cnt FROM conversations
    WHERE stage >= 7 AND updated_at BETWEEN ? AND ?
    ''', (period_start, period_end))
    booked = c.fetchone()['cnt']
    
    # Calls showed
    c.execute('''
    SELECT COUNT(*) as cnt FROM conversations
    WHERE showed_at IS NOT NULL AND showed_at BETWEEN ? AND ?
    ''', (period_start, period_end))
    showed = c.fetchone()['cnt']
    
    conn.close()
    
    accept_rate = (accepted / connects_sent * 100) if connects_sent > 0 else 0
    reply_rate = (replies / accepted * 100) if accepted > 0 else 0
    book_rate = (booked / replies * 100) if replies > 0 else 0
    show_rate = (showed / booked * 100) if booked > 0 else 0
    
    return {
        'period_start': period_start,
        'period_end': period_end,
        'connects_sent': connects_sent,
        'accepted': accepted,
        'replies': replies,
        'booked': booked,
        'showed': showed,
        'accept_rate': round(accept_rate, 1),
        'reply_rate': round(reply_rate, 1),
        'book_rate': round(book_rate, 1),
        'show_rate': round(show_rate, 1),
    }

# --- Init on import ---
if __name__ == '__main__':
    init_db()
