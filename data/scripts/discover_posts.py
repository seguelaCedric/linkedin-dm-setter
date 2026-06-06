#!/usr/bin/env python3
"""
LinkedIn Viral Post Discovery
Finds high-engagement posts from outbound/SDR influencers.
Scrapes commenters and scores them against ICP.
"""

import json
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_schema import add_lead, get_lead, get_conn
from unipile_client import Unipile, load_env

# Influencer list file
from pathlib import Path
INFLUENCERS_FILE = Path(os.path.expanduser('~/.hermes/profiles/linkedin-setter/data/influencers.json'))

def load_influencers():
    """Load influencers from JSON file."""
    if INFLUENCERS_FILE.exists():
        try:
            return json.loads(INFLUENCERS_FILE.read_text())
        except:
            pass
    # Fallback
    return [
        {'name': 'Vanesa Ponce', 'public_id': 'vanesa-ponce-a5103a295', 'provider_id': None, 'topics': ['SDR', 'outbound', 'AI']},
        {'name': 'Cedric Seguela', 'public_id': 'cedric-seguela-18b61b226', 'provider_id': 'ACoAADiwRDsB2IXCLa4nD9agOf4A4NJsaqun2g0', 'topics': ['outbound', 'cold email', 'agency']},
    ]

INFLUENCERS = load_influencers()

# Keywords that signal viral posts worth scraping
VIRAL_KEYWORDS = [
    'outbound', 'cold email', 'sdr', 'sales development', 'lead generation',
    'pipeline', 'booked calls', 'agency', 'consultancy', 'b2b', 'saas',
    'prospecting', 'cold outreach', 'sales', 'growth', 'revenue',
    'apollo', 'clay', 'smartlead', 'instantly', 'heyreach',
]

# Minimum engagement to qualify as viral
MIN_COMMENTS = 20
MIN_REACTIONS = 50

def get_influencer_posts(api, provider_id, limit=10):
    """Get recent posts from an influencer."""
    res = api.request('GET', '/users/' + provider_id + '/posts', {
        'account_id': api.account_id,
        'limit': str(limit),
    })
    if res.get('status') != 200:
        return []
    return res['data'].get('items', [])

def is_viral_post(post):
    """Check if a post meets viral thresholds and is relevant."""
    comments = post.get('comment_counter', 0)
    reactions = post.get('reaction_counter', 0)
    text = (post.get('text') or '').lower()
    
    # Check engagement thresholds
    if comments < MIN_COMMENTS or reactions < MIN_REACTIONS:
        return False
    
    # Check if post is about relevant topics
    has_keyword = any(kw in text for kw in VIRAL_KEYWORDS)
    return has_keyword

def get_post_commenters(api, post_urn, limit=50):
    """Get commenters from a post."""
    res = api.request('GET', '/posts/' + post_urn + '/comments', {
        'account_id': api.account_id,
        'limit': str(limit),
    })
    if res.get('status') != 200:
        return []
    return res['data'].get('items', [])

def score_commenter(comment):
    """Score a commenter against ICP criteria."""
    details = comment.get('author_details', {})
    headline = (details.get('headline') or '').lower()
    
    score = 0
    criteria = {}
    
    # Decision-maker (0-3)
    decision_kw = ['founder', 'ceo', 'cto', 'cfo', 'coo', 'owner', 'partner',
                   'managing director', 'head of', 'vp', 'vice president',
                   'director', 'president', 'principal']
    if any(kw in headline for kw in decision_kw):
        score += 3
        criteria['decision_maker'] = True
    
    # Running outbound (0-3)
    outbound_kw = ['outbound', 'cold email', 'sdr', 'lead gen', 'prospecting',
                   'pipeline', 'agency', 'consultancy', 'b2b', 'saas', 'growth',
                   'sales', 'revenue', 'marketing']
    if any(kw in headline for kw in outbound_kw):
        score += 3
        criteria['running_outbound'] = True
    
    # Service business (0-2)
    service_kw = ['agency', 'consultancy', 'consulting', 'services', 'saas',
                  'professional services', 'marketing', 'sales', 'growth', 'b2b']
    if any(kw in headline for kw in service_kw):
        score += 2
        criteria['service_business'] = True
    
    # Pain visible - comment text (0-2)
    text = (comment.get('text') or '').lower()
    pain_kw = ['struggling', 'frustrated', 'expensive', 'cost', 'complexity',
               'deliverability', 'tool sprawl', 'hiring sdr', 'scaling',
               'need more leads', 'pipeline', 'booked calls']
    if any(kw in text for kw in pain_kw):
        score += 2
        criteria['pain_visible'] = True
    
    return score, criteria

def discover_viral_posts_and_commenters(max_posts=10, max_commenters_per_post=30):
    """
    Main discovery flow:
    1. Get recent posts from influencers
    2. Filter for viral posts
    3. Scrape commenters
    4. Score and add qualified leads
    """
    load_env()
    api = Unipile()
    
    total_added = 0
    total_skipped = 0
    viral_posts_found = []
    
    for influencer in INFLUENCERS:
        provider_id = influencer.get('provider_id')
        if not provider_id:
            # Try to resolve provider_id from public_id
            prof_res = api.request('GET', '/users/' + influencer['public_id'], {
                'account_id': api.account_id
            })
            if prof_res.get('status') == 200:
                provider_id = prof_res['data'].get('provider_id')
                influencer['provider_id'] = provider_id
            else:
                print('Could not resolve provider_id for ' + influencer['name'])
                continue
        
        posts = get_influencer_posts(api, provider_id, limit=max_posts)
        print(influencer['name'] + ': ' + str(len(posts)) + ' posts fetched')
        
        for post in posts:
            if not is_viral_post(post):
                continue
            
            post_text = (post.get('text') or '')[:100]
            comments = post.get('comment_counter', 0)
            reactions = post.get('reaction_counter', 0)
            post_urn = post.get('social_id') or post.get('post_urn')
            
            print('  VIRAL: ' + post_text)
            print('  Comments: ' + str(comments) + ' | Reactions: ' + str(reactions))
            
            viral_posts_found.append({
                'influencer': influencer['name'],
                'text': post_text,
                'urn': post_urn,
                'comments': comments,
                'reactions': reactions,
            })
            
            # Get commenters
            commenters = get_post_commenters(api, post_urn, limit=max_commenters_per_post)
            print('  Commenters: ' + str(len(commenters)))
            
            for commenter in commenters:
                details = commenter.get('author_details', {})
                public_id = details.get('profile_url', '').split('/in/')[-1] if '/in/' in details.get('profile_url', '') else ''
                
                if not public_id:
                    total_skipped += 1
                    continue
                
                # Check if already in DB
                linkedin_url = 'https://linkedin.com/in/' + public_id
                existing = get_lead(linkedin_url=linkedin_url)
                if existing:
                    total_skipped += 1
                    continue
                
                # Score
                score, criteria = score_commenter(commenter)
                
                if score < 5:  # Minimum threshold
                    total_skipped += 1
                    continue
                
                # Add to DB
                name = commenter.get('author', 'Unknown')
                lead_id = add_lead(
                    linkedin_url=linkedin_url,
                    full_name=name,
                    title=details.get('headline', ''),
                    icp_score=score,
                    icp_criteria_met=criteria,
                    personalization_hook='saw you on ' + influencer['name'] + '\'s post about ' + post_text[:40],
                    source='viral_post',
                    source_detail=post_urn,
                )
                total_added += 1
                print('  Added: ' + name + ' (score ' + str(score) + ')')
    
    print()
    print('Discovery complete:')
    print('  Viral posts found: ' + str(len(viral_posts_found)))
    print('  Leads added: ' + str(total_added))
    print('  Skipped (existing/low-score): ' + str(total_skipped))
    
    return viral_posts_found, total_added

if __name__ == '__main__':
    posts, added = discover_viral_posts_and_commenters(max_posts=5, max_commenters_per_post=20)
