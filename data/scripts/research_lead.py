#!/usr/bin/env python3
"""
LinkedIn Profile Research -- Scrapes profile data for personalization.
Uses Camofox browser to access LinkedIn profiles.
"""

import json
import sys
import os

# Add parent scripts dir to path for db_schema import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_schema import add_lead, get_lead, update_lead, get_conn

def score_icp(profile_data):
    """
    Score a lead against ICP criteria. Returns (score, criteria_met).
    Score 0-10. Threshold 7 to qualify IN.
    """
    score = 0
    criteria = {}
    
    # Criterion 1: Decision-maker (0-3)
    title = (profile_data.get('title') or '').lower()
    headline = (profile_data.get('headline') or '').lower()
    decision_keywords = ['founder', 'ceo', 'cto', 'cfo', 'coo', 'owner', 'partner',
                         'managing director', 'head of', 'vp', 'vice president',
                         'director', 'president', 'principal']
    if any(kw in title or kw in headline for kw in decision_keywords):
        score += 3
        criteria['decision_maker'] = True
    elif any(kw in title or kw in headline for kw in ['manager', 'lead', 'senior']):
        score += 1
        criteria['decision_maker'] = 'partial'
    else:
        criteria['decision_maker'] = False
    
    # Criterion 2: Running outbound (0-3)
    outbound_keywords = ['outbound', 'cold email', 'lead gen', 'sdr', 'sales development',
                         'prospecting', 'apollo', 'clay', 'smartlead', 'instantly',
                         'heystack', 'heyreach', 'cold outreach', 'pipeline']
    about = (profile_data.get('about') or '').lower()
    all_text = f"{title} {headline} {about}"
    outbound_matches = sum(1 for kw in outbound_keywords if kw in all_text)
    if outbound_matches >= 2:
        score += 3
        criteria['running_outbound'] = True
    elif outbound_matches >= 1:
        score += 2
        criteria['running_outbound'] = 'partial'
    else:
        criteria['running_outbound'] = False
    
    # Criterion 3: Service business (0-2)
    service_keywords = ['agency', 'consultancy', 'consulting', 'services', 'saas',
                        'professional services', 'marketing', 'sales', 'growth',
                        'b2b', 'enterprise', 'managed services']
    company = (profile_data.get('company') or '').lower()
    if any(kw in all_text or kw in company for kw in service_keywords):
        score += 2
        criteria['service_business'] = True
    else:
        criteria['service_business'] = False
    
    # Criterion 4: Pain visible (0-2)
    pain_keywords = ['struggling', 'frustrated', 'expensive', 'cost', 'complexity',
                     'deliverability', 'tool sprawl', 'too many tools', 'hiring sdr',
                     'scaling', 'growth', 'need more leads', 'pipeline', 'booked calls']
    pain_matches = sum(1 for kw in pain_keywords if kw in all_text)
    if pain_matches >= 2:
        score += 2
        criteria['pain_visible'] = True
    elif pain_matches >= 1:
        score += 1
        criteria['pain_visible'] = 'partial'
    else:
        criteria['pain_visible'] = False
    
    return score, criteria

def research_and_add_lead(profile_data, source=None, source_detail=None):
    """
    Research a LinkedIn profile, score ICP, and add to DB.
    
    profile_data dict should have:
    - linkedin_url (required)
    - full_name (required)
    - title, company, company_url, industry, location, headline, about
    
    Returns: (lead_id, icp_score, icp_criteria, qualifies)
    """
    # Score ICP
    icp_score, icp_criteria = score_icp(profile_data)
    
    # Find personalization hook
    hook = find_personalization_hook(profile_data)
    
    # Add to DB
    lead_id = add_lead(
        linkedin_url=profile_data['linkedin_url'],
        full_name=profile_data['full_name'],
        title=profile_data.get('title'),
        company=profile_data.get('company'),
        company_url=profile_data.get('company_url'),
        industry=profile_data.get('industry'),
        location=profile_data.get('location'),
        headline=profile_data.get('headline'),
        icp_score=icp_score,
        icp_criteria_met=icp_criteria,
        personalization_hook=hook,
        source=source,
        source_detail=source_detail
    )
    
    qualifies = icp_score >= 7
    
    return lead_id, icp_score, icp_criteria, qualifies

def find_personalization_hook(profile_data):
    """
    Find the best personalization hook from profile data.
    Returns a string or None.
    """
    hooks = []
    
    # Check headline for specific content
    headline = profile_data.get('headline') or ''
    if len(headline) > 20 and 'at ' in headline.lower():
        hooks.append(f"headline mentions: {headline[:100]}")
    
    # Check about section for specific details
    about = profile_data.get('about') or ''
    if about:
        # Look for specific claims, numbers, or unique details
        sentences = about.split('.')
        for s in sentences[:3]:
            s = s.strip()
            if len(s) > 20 and any(c.isdigit() for c in s):
                hooks.append(s[:100])
                break
    
    # Check for recent activity
    recent_posts = profile_data.get('recent_posts', [])
    if recent_posts:
        post = recent_posts[0]
        hooks.append(f"recent post: {post[:100]}")
    
    return hooks[0] if hooks else None

if __name__ == '__main__':
    # Test with sample data
    sample = {
        'linkedin_url': 'https://linkedin.com/in/test-user',
        'full_name': 'Test User',
        'title': 'Founder & CEO at Test Agency',
        'company': 'Test Agency',
        'headline': 'Building outbound systems for B2B agencies',
        'about': 'We help agencies scale their outbound. Running Apollo + Smartlead for 20+ clients.'
    }
    
    lead_id, score, criteria, qualifies = research_and_add_lead(sample, source='test')
    print(f'Lead ID: {lead_id}')
    print(f'ICP Score: {score}/10')
    print(f'Criteria: {json.dumps(criteria, indent=2)}')
    print(f'Qualifies: {qualifies}')
