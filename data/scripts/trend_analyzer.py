#!/usr/bin/env python3
"""
LinkedIn Trend Analyzer
Extracts trending themes, pain points, and content ideas from viral posts.
"""

import json
import sys
import os
from pathlib import Path
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_schema import get_conn
from unipile_client import Unipile, load_env

# Theme categories
THEME_CATEGORIES = {
    'pain_points': [
        'struggling', 'frustrated', 'expensive', 'cost', 'complexity',
        'deliverability', 'tool sprawl', 'too many tools', 'hiring sdr',
        'scaling', 'broke', 'failing', 'not working', 'waste', 'burnout',
        'overwhelmed', 'stuck', 'plateau', 'churn', 'attrition'
    ],
    'solutions': [
        'ai', 'automation', 'agent', 'claude', 'gpt', 'system', 'stack',
        'workflow', 'pipeline', 'framework', 'playbook', 'template',
        'consolidate', 'replace', 'automate', 'scale', 'optimize'
    ],
    'tools_mentioned': [
        'apollo', 'clay', 'smartlead', 'instantly', 'heyreach', 'salesloft',
        'outreach', 'hubspot', 'salesforce', 'pipedrive', 'lemlist',
        'mailshake', 'reply.io', 'phantombuster', 'clearbit', 'zoominfo'
    ],
    'topics': [
        'cold email', 'outbound', 'sdr', 'sales development', 'lead generation',
        'pipeline', 'booked calls', 'agency', 'consultancy', 'b2b', 'saas',
        'prospecting', 'cold outreach', 'gtm', 'go-to-market', 'revenue',
        'growth', 'scaling', 'fractional', 'revops'
    ],
    'emotions': [
        'love', 'hate', 'excited', 'frustrated', 'amazed', 'shocked',
        'worried', 'confident', 'skeptical', 'hopeful', 'desperate'
    ]
}

def load_viral_posts():
    """Load viral posts from influencers.json and recent discovery data."""
    load_env()
    api = Unipile()
    
    inf_file = Path(os.path.expanduser('~/.hermes/profiles/linkedin-setter/data/influencers.json'))
    if not inf_file.exists():
        return []
    
    influencers = json.loads(inf_file.read_text())
    all_posts = []
    
    for inf in influencers:
        if not inf.get('provider_id'):
            continue
        
        res = api.request('GET', '/users/' + inf['provider_id'] + '/posts', {
            'account_id': api.account_id,
            'limit': '10',
        })
        
        if res.get('status') != 200:
            continue
        
        for post in res['data'].get('items', []):
            comments = post.get('comment_counter', 0)
            reactions = post.get('reaction_counter', 0)
            
            if comments >= 20 and reactions >= 50:
                all_posts.append({
                    'influencer': inf['name'],
                    'text': post.get('text', ''),
                    'comments': comments,
                    'reactions': reactions,
                    'date': post.get('date', ''),
                    'urn': post.get('social_id', ''),
                })
    
    return all_posts

def extract_themes(posts):
    """Extract themes from post texts."""
    theme_counts = {category: Counter() for category in THEME_CATEGORIES}
    
    for post in posts:
        text = (post['text'] or '').lower()
        
        for category, keywords in THEME_CATEGORIES.items():
            for keyword in keywords:
                if keyword in text:
                    theme_counts[category][keyword] += 1
    
    return theme_counts

def extract_hook_patterns(posts):
    """Extract common hook patterns from viral posts."""
    hooks = []
    
    for post in posts:
        text = post['text'] or ''
        lines = text.split('\n')
        
        # First line is usually the hook
        if lines:
            hook = lines[0].strip()
            if len(hook) > 10:
                hooks.append(hook[:100])
    
    return hooks

def extract_pain_points_from_comments(api, posts, max_comments_per_post=20):
    """Extract pain points from commenters on viral posts."""
    pain_comments = []
    pain_keywords = THEME_CATEGORIES['pain_points']
    
    for post in posts[:10]:  # Check top 10 posts
        if not post.get('urn'):
            continue
        
        res = api.request('GET', '/posts/' + post['urn'] + '/comments', {
            'account_id': api.account_id,
            'limit': str(max_comments_per_post),
        })
        
        if res.get('status') != 200:
            continue
        
        for comment in res['data'].get('items', []):
            text = (comment.get('text') or '').lower()
            
            # Check if comment mentions pain
            if any(kw in text for kw in pain_keywords):
                pain_comments.append({
                    'comment': comment.get('text', '')[:200],
                    'author': comment.get('author', 'Unknown'),
                    'post_influencer': post['influencer'],
                    'post_hook': post['text'][:50],
                })
    
    return pain_comments

def generate_trend_report(posts, themes, hooks, pain_comments):
    """Generate a trend report."""
    report = []
    report.append('# LinkedIn Trend Report')
    report.append('')
    report.append('Generated: ' + datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))
    report.append('Posts analyzed: ' + str(len(posts)))
    report.append('')
    
    # Top themes by category
    report.append('## Trending Themes')
    report.append('')
    
    for category, counts in themes.items():
        if not counts:
            continue
        
        report.append('### ' + category.replace('_', ' ').title())
        for keyword, count in counts.most_common(10):
            report.append('- ' + keyword + ': ' + str(count) + ' mentions')
        report.append('')
    
    # Hook patterns
    report.append('## Viral Hook Patterns')
    report.append('')
    report.append('These hooks got high engagement:')
    report.append('')
    for i, hook in enumerate(hooks[:15], 1):
        report.append(str(i) + '. ' + hook)
    report.append('')
    
    # Pain points from comments
    if pain_comments:
        report.append('## Pain Points (from comments)')
        report.append('')
        report.append('What people are struggling with:')
        report.append('')
        for pc in pain_comments[:20]:
            report.append('- "' + pc['comment'][:100] + '..."')
            report.append('  -- ' + pc['author'] + ' on ' + pc['post_influencer'] + '\'s post')
        report.append('')
    
    # Top posts by engagement
    report.append('## Top Viral Posts')
    report.append('')
    sorted_posts = sorted(posts, key=lambda x: x['comments'] + x['reactions'], reverse=True)
    for post in sorted_posts[:10]:
        report.append('- ' + post['influencer'] + ': ' + post['text'][:80])
        report.append('  Comments: ' + str(post['comments']) + ' | Reactions: ' + str(post['reactions']))
    report.append('')
    
    # Content ideas
    report.append('## Content Ideas (based on trends)')
    report.append('')
    
    # Generate content ideas from top themes
    top_pains = themes.get('pain_points', {}).most_common(5)
    top_solutions = themes.get('solutions', {}).most_common(5)
    top_tools = themes.get('tools_mentioned', {}).most_common(5)
    
    if top_pains:
        report.append('### Address These Pain Points:')
        for pain, count in top_pains:
            report.append('- Write about: "Why ' + pain + ' is killing your outbound"')
    
    if top_solutions:
        report.append('')
        report.append('### Position Against These Solutions:')
        for solution, count in top_solutions:
            report.append('- Write about: "Why ' + solution + ' alone won\'t fix your pipeline"')
    
    if top_tools:
        report.append('')
        report.append('### Tool Comparison Content:')
        for tool, count in top_tools:
            report.append('- Write about: "' + tool + ' alternative that actually works"')
    
    report.append('')
    report.append('---')
    report.append('')
    report.append('Use these trends to:')
    report.append('1. Write LinkedIn posts that resonate with current pain')
    report.append('2. Craft outreach messages that reference what they\'re already talking about')
    report.append('3. Position ACA against the solutions they\'re frustrated with')
    report.append('4. Create content that rides the viral wave')
    
    return '\n'.join(report)

def analyze_trends(save_to_obsidian=True):
    """Main trend analysis flow."""
    print('Loading viral posts...')
    posts = load_viral_posts()
    print('Found ' + str(len(posts)) + ' viral posts')
    
    if not posts:
        print('No viral posts found. Run discover_posts.py first.')
        return None
    
    print('Extracting themes...')
    themes = extract_themes(posts)
    
    print('Extracting hook patterns...')
    hooks = extract_hook_patterns(posts)
    
    print('Analyzing comments for pain points...')
    load_env()
    api = Unipile()
    pain_comments = extract_pain_points_from_comments(api, posts)
    print('Found ' + str(len(pain_comments)) + ' pain-point comments')
    
    print('Generating report...')
    report = generate_trend_report(posts, themes, hooks, pain_comments)
    
    # Save to Obsidian
    if save_to_obsidian:
        vault_path = Path(os.path.expanduser('~/obsidian-vault'))
        if vault_path.exists():
            report_path = vault_path / 'clients' / 'automatedclientacquisition' / 'growth' / 'social' / 'linkedin-trend-report.md'
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report)
            print('Report saved to: ' + str(report_path))
    
    # Also save to plugin data
    local_path = Path(os.path.expanduser('~/.hermes/profiles/linkedin-setter/data/trend-report.md'))
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(report)
    print('Report saved to: ' + str(local_path))
    
    return report

if __name__ == '__main__':
    report = analyze_trends()
    if report:
        print()
        print(report)
