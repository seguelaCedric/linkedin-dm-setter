#!/usr/bin/env python3
"""
LinkedIn Shared Throttle Lock
Prevents multiple agents from blowing rate limits on the same Unipile accounts.

Usage:
  from shared_throttle import ThrottleLock
  lock = ThrottleLock(agent_name='linkedin-setter')
  if lock.can_send(account_id):
      # send
      lock.record_send(account_id, lead_url)
  lock.release()
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOCK_DIR = Path(os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes')))
LOCK_FILE = LOCK_DIR / '.linkedin-throttle.json'

# Global limits (shared across ALL agents)
LIMITS = {
    'ULqyubVUQFijEEczkgMycQ': {'name': 'Cedric (FR)', 'per_day': 20},
    'O1XcMLVeREiMULFu1zzaRQ': {'name': 'Cedric (US)', 'per_day': 20},
}
TOTAL_PER_DAY = 35

def _load_state():
    if LOCK_FILE.exists():
        try:
            return json.loads(LOCK_FILE.read_text())
        except:
            pass
    return {'accounts': {}, 'global_today': {}, 'last_reset': ''}

def _save_state(state):
    LOCK_FILE.write_text(json.dumps(state, indent=2))

def _today():
    return datetime.utcnow().strftime('%Y-%m-%d')

def _cleanup_old(state):
    """Remove entries older than 2 days."""
    cutoff = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d')
    for acc_id in list(state.get('accounts', {}).keys()):
        sends = state['accounts'][acc_id].get('sends', [])
        state['accounts'][acc_id]['sends'] = [s for s in sends if s.get('date', '') >= cutoff]
    # Clean global
    state['global_today'] = {k: v for k, v in state.get('global_today', {}).items() if k >= cutoff}
    return state

class ThrottleLock:
    def __init__(self, agent_name='unknown'):
        self.agent = agent_name
        self.state = _cleanup_old(_load_state())
        self._ensure_account_structures()

    def _ensure_account_structures(self):
        for acc_id in LIMITS:
            if acc_id not in self.state['accounts']:
                self.state['accounts'][acc_id] = {'sends': []}

    def get_today_count(self, account_id):
        """How many sends today from this account (all agents combined)."""
        today = _today()
        sends = self.state['accounts'].get(account_id, {}).get('sends', [])
        return sum(1 for s in sends if s.get('date') == today)

    def get_global_today_count(self):
        """Total sends today across all accounts (all agents combined)."""
        total = 0
        for acc_id in LIMITS:
            total += self.get_today_count(acc_id)
        return total

    def get_account_remaining(self, account_id):
        """Remaining capacity for this account today."""
        limit = LIMITS.get(account_id, {}).get('per_day', 20)
        return max(0, limit - self.get_today_count(account_id))

    def get_global_remaining(self):
        """Remaining capacity across all accounts today."""
        return max(0, TOTAL_PER_DAY - self.get_global_today_count())

    def can_send(self, account_id=None):
        """Check if we can send. Returns (ok, reason, best_account)."""
        # Check global limit
        global_remaining = self.get_global_today_count()
        if global_remaining >= TOTAL_PER_DAY:
            return False, 'Global daily limit reached (' + str(TOTAL_PER_DAY) + ')', None

        if account_id:
            # Specific account requested
            remaining = self.get_account_remaining(account_id)
            if remaining <= 0:
                return False, 'Account ' + account_id[:8] + ' at daily limit', None
            return True, 'ok', account_id
        else:
            # Pick best account
            best = None
            best_remaining = 0
            for acc_id in LIMITS:
                rem = self.get_account_remaining(acc_id)
                if rem > best_remaining:
                    best = acc_id
                    best_remaining = rem
            if best:
                return True, 'ok', best
            return False, 'All accounts at daily limit', None

    def record_send(self, account_id, lead_url, agent=None):
        """Record a send. Call AFTER successfully sending."""
        today = _today()
        now = datetime.utcnow().isoformat()
        entry = {
            'date': today,
            'time': now,
            'agent': agent or self.agent,
            'lead_url': lead_url,
        }
        self.state['accounts'][account_id]['sends'].append(entry)
        _save_state(self.state)

    def get_status(self):
        """Return current throttle status for reporting."""
        status = {
            'global_today': self.get_global_today_count(),
            'global_limit': TOTAL_PER_DAY,
            'global_remaining': self.get_global_remaining(),
            'accounts': {}
        }
        for acc_id in LIMITS:
            today_count = self.get_today_count(acc_id)
            limit = LIMITS[acc_id]['per_day']
            status['accounts'][acc_id] = {
                'name': LIMITS[acc_id]['name'],
                'today': today_count,
                'limit': limit,
                'remaining': max(0, limit - today_count),
            }
        return status

    def release(self):
        """Save state. Always call when done."""
        _save_state(self.state)

if __name__ == '__main__':
    lock = ThrottleLock(agent_name='cli')
    status = lock.get_status()
    print('LinkedIn Throttle Status')
    print('=' * 40)
    print('Global: ' + str(status['global_today']) + '/' + str(status['global_limit']) + ' used, ' + str(status['global_remaining']) + ' remaining')
    for acc_id, acc in status['accounts'].items():
        print(acc['name'] + ': ' + str(acc['today']) + '/' + str(acc['limit']) + ' used, ' + str(acc['remaining']) + ' remaining')
    lock.release()
