#!/usr/bin/env python3
"""
LinkedIn Trending Post Discovery
Finds viral posts about outbound/SDR/agency topics by:
1. Checking seed influencers for viral posts
2. Discovering new influencers from viral post commenters
3. Expanding the influencer list automatically
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_schema import get_conn
from unipile_client import Unipile, load_env

# Config
INFLUENCERS_FILE = Path(os.path.expanduser('~/.hermes/profiles/linkedin-setter/data/influencers.json'))
VIRAL_THRESHOLD_COMMENTS = 20
VIRAL_THRESHOLD_REACTIONS = 50

# Topics to search for
TOPICS = [
    'outbound', 'cold email', 'sdr', 'sales development', 'lead generation',
    'pipeline', 'booked calls', 'agency growth', 'b2b sales', 'cold outreach',
    'sales automation', 'revenue operations', 'gtm', 'go-to-market',
]

def load_influencers():
    """Load influencer list from JSON file."""
    if INFLUENCERS_FILE.exists():
        try:
            return json.loads(INFLUENCERS_FILE.read_text())
        except:
            pass
    # Default seed list
    seeds = [
        {'name': 'Vanesa Ponce', 'public_id': 'vanesa-ponce-a5103a295', 'provider_id': None, 'topics': ['SDR', 'outbound', 'AI'], 'discovered_from': 'seed'},
        {'name': 'Cedric Seguela', 'public_id': 'cedric-seguela-18b61b226', 'provider_id': 'ACoAADiwRDsB2IXCLa4nD9agOf4A4NJsaqun2g0', 'topics': ['outbound', 'cold email', 'agency'], 'discovered_from': 'seed'},
    ]
    save_influencers(seeds)
    return seeds

def save_influencers(influencers):
    """Save influencer list to JSON file."""
    INFLUENCERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    INFLUENCERS_FILE.write_text(json.dumps(influencers, indent=2))

def resolve_provider_id(api, public_id):
    """Get provider_id from public LinkedIn identifier."""
    res = api.request('GET', '/users/' + public_id, {'account_id': api.account_id})
    if res.get('status') == 200:
        return res['data'].get('provider_id')
    return None

def get_user_posts(api, provider_id, limit=10):
    """Get recent posts from a user."""
    res = api.request('GET', '/users/' + provider_id + '/posts', {
        'account_id': api.account_id,
        'limit': str(limit),
    })
    if res.get('status') != 200:
        return []
    return res['data'].get('items', [])

def is_viral(post):
    """Check if post meets viral thresholds."""
    comments = post.get('comment_counter', 0)
    reactions = post.get('reaction_counter', 0)
    return comments >= VIRAL_THRESHOLD_COMMENTS and reactions >= VIRAL_THRESHOLD_REACTIONS

def is_relevant(post):
    """Check if post is about relevant topics."""
    text = (post.get('text') or '').lower()
    return any(topic in text for topic in TOPICS)

def get_post_commenters(api, post_urn, limit=50):
    """Get commenters from a post."""
    res = api.request('GET', '/posts/' + post_urn + '/comments', {
        'account_id': api.account_id,
        'limit': str(limit),
    })
    if res.get('status') != 200:
        return []
    return res['data'].get('items', [])

def is_potential_influencer(commenter):
    """Check if a commenter could be an influencer worth tracking."""
    details = commenter.get('author_details', {})
    headline = (details.get('headline') or '').lower()
    
    # High-profile indicators
    indicators = ['founder', 'ceo', 'cto', 'vp', 'director', 'head of',
                  'chief', 'president', 'partner', 'owner']
    return any(ind in headline for ind in indicators)

def discover_trending(max_posts_per_influencer=5, max_commenters_per_post=30, auto_expand=True):
    """
    Main discovery flow:
    1. Check all influencers for viral posts
    2. Scrape commenters from viral posts
    3. Optionally discover new influencers from commenters
    4. Return viral posts and new leads
    """
    load_env()
    api = Unipile()
    influencers = load_influencers()
    
    viral_posts = []
    new_influencers = []
    processed_urns = set()
    
    # Track which influencer we're checking
    for i, inf in enumerate(influencers):
        # Resolve provider_id if missing
        if not inf.get('provider_id'):
            provider_id = resolve_provider_id(api, inf['public_id'])
            if provider_id:
                inf['provider_id'] = provider_id
                save_influencers(influencers)
            else:
                print('[' + str(i+1) + '/' + str(len(influencers)) + '] ' + inf['name'] + ': could not resolve')
                continue
        
        # Get recent posts
        posts = get_user_posts(api, inf['provider_id'], limit=max_posts_per_influencer)
        print('[' + str(i+1) + '/' + str(len(influencers)) + '] ' + inf['name'] + ': ' + str(len(posts)) + ' posts')
        
        for post in posts:
            post_urn = post.get('social_id') or post.get('post_urn')
            if post_urn in processed_urns:
                continue
            processed_urns.add(post_urn)
            
            if not is_viral(post):
                continue
            if not is_relevant(post):
                continue
            
            text = (post.get('text') or '')[:100]
            comments = post.get('comment_counter', 0)
            reactions = post.get('reaction_counter', 0)
            
            print('  VIRAL: ' + text)
            print('  Comments: ' + str(comments) + ' | Reactions: ' + str(reactions))
            
            viral_posts.append({
                'influencer': inf['name'],
                'text': text,
                'urn': post_urn,
                'comments': comments,
                'reactions': reactions,
            })
            
            # Get commenters
            commenters = get_post_commenters(api, post_urn, limit=max_commenters_per_post)
            print('  Commenters: ' + str(len(commenters)))
            
            # Check for potential new influencers
            if auto_expand:
                for commenter in commenters:
                    if is_potential_influencer(commenter):
                        details = commenter.get('author_details', {})
                        public_id = details.get('profile_url', '').split('/in/')[-1] if '/in/' in details.get('profile_url', '') else ''
                        
                        # Check if already in influencer list
                        already_tracked = any(inf['public_id'] == public_id for inf in influencers)
                        if public_id and not already_tracked:
                            new_inf = {
                                'name': commenter.get('author', 'Unknown'),
                                'public_id': public_id,
                                'provider_id': details.get('id'),
                                'topics': inf.get('topics', []),
                                'discovered_from': 'viral_commenter',
                                'discovered_on': datetime.utcnow().isoformat(),
                                'source_post': post_urn,
                            }
                            new_influencers.append(new_inf)
                            influencers.append(new_inf)
                            print('  New influencer: ' + new_inf['name'])
    
    # Save expanded influencer list
    if new_influencers:
        save_influencers(influencers)
        print()
        print('Expanded influencer list: ' + str(len(influencers)) + ' total (+' + str(len(new_influencers)) + ' new)')
    
    print()
    print('Discovery complete:')
    print('  Influencers checked: ' + str(len(influencers)))
    print('  Viral posts found: ' + str(len(viral_posts)))
    print('  New influencers discovered: ' + str(len(new_influencers)))
    
    return viral_posts, new_influencers

def show_influencers():
    """Show current influencer list."""
    influencers = load_influencers()
    print('INFLUENCERS (' + str(len(influencers)) + ' total):')
    print('-' * 60)
    for i, inf in enumerate(influencers):
        source = inf.get('discovered_from', 'unknown')
        print(str(i+1) + '. ' + inf['name'] + ' | ' + inf['public_id'])
        print('   Topics: ' + ', '.join(inf.get('topics', [])))
        print('   Source: ' + source)
        print()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        show_influencers()
    else:
        posts, new_inf = discover_trending(max_posts_per_influencer=5, max_commenters_per_post=20)
