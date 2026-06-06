#!/usr/bin/env python3
"""Small Unipile client for ACA LinkedIn operations.

Reads credentials from /root/.hermes/profiles/sdr/.env by default:
- UNIPILE_API_KEY
- UNIPILE_BASE_URL, e.g. https://api13.unipile.com:14389/api/v1
- UNIPILE_LINKEDIN_ACCOUNT_ID

Safe commands are read-only. Mutating commands require --confirm-send.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DEFAULT_ENV = Path('/root/.hermes/profiles/sdr/.env')


def load_env(path: Path = DEFAULT_ENV):
    if not path.exists():
        return
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())


def redacted(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = k.lower()
            if any(s in kl for s in ('token', 'key', 'secret', 'password', 'cookie', 'credential')):
                out[k] = '<redacted>'
            elif kl in ('email', 'username') and isinstance(v, str):
                out[k] = v[:2] + '***' + v[-8:] if len(v) > 10 else '<redacted>'
            else:
                out[k] = redacted(v)
        return out
    if isinstance(obj, list):
        return [redacted(x) for x in obj]
    return obj


class Unipile:
    def __init__(self):
        load_env()
        self.base = os.environ.get('UNIPILE_BASE_URL', '').rstrip('/')
        self.key = os.environ.get('UNIPILE_API_KEY', '')
        self.account_id = os.environ.get('UNIPILE_LINKEDIN_ACCOUNT_ID', '')
        if not self.base or not self.key:
            raise SystemExit('Missing UNIPILE_BASE_URL or UNIPILE_API_KEY in sdr .env')

    def request(self, method, path, params=None, body=None, form=None):
        url = self.base + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        data = None
        headers = {'X-API-KEY': self.key, 'accept': 'application/json'}
        if body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['content-type'] = 'application/json'
        if form is not None:
            boundary = '----aca-unipile-' + uuid.uuid4().hex
            chunks = []
            for k, v in form.items():
                vals = v if isinstance(v, list) else [v]
                for val in vals:
                    chunks.append(f'--{boundary}\r\n'.encode())
                    chunks.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
                    chunks.append(str(val).encode('utf-8'))
                    chunks.append(b'\r\n')
            chunks.append(f'--{boundary}--\r\n'.encode())
            data = b''.join(chunks)
            headers['content-type'] = f'multipart/form-data; boundary={boundary}'
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                raw = r.read().decode('utf-8', 'replace')
                return {'status': r.status, 'data': json.loads(raw) if raw else None}
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', 'replace')
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw
            return {'status': e.code, 'error': parsed}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('accounts')

    prof = sub.add_parser('profile')
    prof.add_argument('identifier', help='LinkedIn public identifier, e.g. satyanadella')
    prof.add_argument('--account-id')

    inv = sub.add_parser('invite')
    inv.add_argument('provider_id')
    inv.add_argument('--message', default='')
    inv.add_argument('--account-id')
    inv.add_argument('--confirm-send', action='store_true')

    chats = sub.add_parser('chats')
    chats.add_argument('--account-id')
    chats.add_argument('--limit', default='20')

    msg = sub.add_parser('message-user')
    msg.add_argument('provider_id')
    msg.add_argument('--text', required=True)
    msg.add_argument('--account-id')
    msg.add_argument('--inmail', action='store_true')
    msg.add_argument('--confirm-send', action='store_true')

    chatmsg = sub.add_parser('message-chat')
    chatmsg.add_argument('chat_id')
    chatmsg.add_argument('--text', required=True)
    chatmsg.add_argument('--confirm-send', action='store_true')

    args = p.parse_args()
    api = Unipile()

    if args.cmd == 'accounts':
        res = api.request('GET', '/accounts')
    elif args.cmd == 'profile':
        res = api.request('GET', f'/users/{urllib.parse.quote(args.identifier)}', {
            'account_id': args.account_id or api.account_id
        })
    elif args.cmd == 'invite':
        if not args.confirm_send:
            raise SystemExit('Refusing to send invitation without --confirm-send')
        res = api.request('POST', '/users/invite', body={
            'provider_id': args.provider_id,
            'account_id': args.account_id or api.account_id,
            'message': args.message,
        })
    elif args.cmd == 'chats':
        params = {'account_id': args.account_id or api.account_id, 'limit': args.limit}
        res = api.request('GET', '/chats', params)
    elif args.cmd == 'message-user':
        if not args.confirm_send:
            raise SystemExit('Refusing to send message without --confirm-send')
        form = {
            'account_id': args.account_id or api.account_id,
            'text': args.text,
            'attendees_ids': args.provider_id,
        }
        if args.inmail:
            form['linkedin[api]'] = 'classic'
            form['linkedin[inmail]'] = 'true'
        res = api.request('POST', '/chats', form=form)
    elif args.cmd == 'message-chat':
        if not args.confirm_send:
            raise SystemExit('Refusing to send chat message without --confirm-send')
        res = api.request('POST', f'/chats/{urllib.parse.quote(args.chat_id)}/messages', form={'text': args.text})
    else:
        raise SystemExit('unknown command')

    print(json.dumps(redacted(res), indent=2, ensure_ascii=False))
    if res.get('status', 500) >= 400:
        sys.exit(1)


if __name__ == '__main__':
    main()
