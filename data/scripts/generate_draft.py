#!/usr/bin/env python3
"""
LinkedIn Message Draft Generator -- Creates stage-appropriate messages.
Uses lead data and conversation context to generate personalized drafts.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_schema import get_lead, get_conversation, queue_draft, get_conn

# Stage templates with placeholders
STAGE_TEMPLATES = {
    0: {
        'name': 'Connect',
        'variants': {
            'A': '',  # Blank connection request
            'B': 'hey {first_name}, saw your work on {hook}. would love to connect.'
        }
    },
    1: {
        'name': 'Open',
        'variants': {
            'A': 'hey {first_name}, {hook}?',
            'B': '{first_name} quick one, {hook}?'
        }
    },
    2: {
        'name': 'Filter Intent',
        'variants': {
            'A': 'are you more focused on {option_a} or {option_b} right now?',
            'B': "curious -- are you currently {option_a} or {option_b}?"
        }
    },
    3: {
        'name': 'Diagnose',
        'variants': {
            'A': 'that makes sense. how is {current_state} working out for you?',
            'B': 'nice. when you look at {current_state}, what would you change if you could?'
        }
    },
    4: {
        'name': 'Frame',
        'variants': {
            'A': "that's a common pattern when {situation}. ever thought about {solution_area}?",
            'B': "i see that a lot with {situation}. have you explored {solution_area}?"
        }
    },
    5: {
        'name': 'Qualify',
        'variants': {
            'A': 'if there was a way to {outcome}, would that be worth a conversation?',
            'B': "what if {outcome}? worth exploring?"
        }
    },
    6: {
        'name': 'Earn the Right',
        'variants': {
            'A': 'we had a similar setup -- {proof_point}. worth a quick look?',
            'B': '{proof_point}. could show you how that works if you want.'
        }
    },
    7: {
        'name': 'Book',
        'variants': {
            'A': "i've got {time_a} or {time_b} this week. which works better for you?",
            'B': "how about {time_a}? if not, {time_b} works too."
        }
    },
    8: {
        'name': 'Nurture',
        'variants': {
            'A': 'looking forward to chatting on {call_date}. in the meantime, {resource} might be useful.',
            'B': "see you {call_date}! quick heads up -- {reminder}."
        }
    }
}

# Proof points (from ACA's actual results)
PROOF_POINTS = [
    "one of our clients, a 3-person agency doing $15K/mo, went from 1-2 calls/week to 11 booked calls in their first 2 weeks",
    "we replaced Smartlead + Apollo + Clay for one founder and cut their stack cost from $7,000/mo to $0.66/inbox",
    "first qualified meeting in 11 days or you don't pay -- that's the guarantee"
]

def generate_draft(lead_id, stage=None, variant=None, context=None):
    """
    Generate a draft message for a lead at a specific stage.
    
    Args:
        lead_id: The lead's ID in the DB
        stage: Override stage (default: read from conversation)
        variant: 'A' or 'B' (default: read from conversation)
        context: Dict with additional context for template filling
    
    Returns: (message_id, draft_text, stage, variant)
    """
    lead = get_lead(lead_id=lead_id)
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")
    
    conv = get_conversation(lead_id)
    if not conv:
        raise ValueError(f"No active conversation for lead {lead_id}")
    
    if stage is None:
        stage = conv['stage']
    if variant is None:
        variant = conv['opener_variant'] or 'A'
    
    template_data = STAGE_TEMPLATES.get(stage)
    if not template_data:
        raise ValueError(f"Invalid stage: {stage}")
    
    template = template_data['variants'].get(variant)
    if template is None:
        raise ValueError(f"Invalid variant {variant} for stage {stage}")
    
    # Build fill values from lead data + context
    fills = {
        'first_name': lead.get('first_name') or lead['full_name'].split()[0],
        'hook': lead.get('personalization_hook') or 'your recent work',
        'specific_detail': (context or {}).get('specific_detail', 'the part about tool complexity'),
        'their_thing': (context or {}).get('their_thing', 'outbound systems'),
        'open_question': (context or {}).get('open_question', "what's been your biggest challenge with outbound lately?"),
        'option_a': (context or {}).get('option_a', 'scaling outbound'),
        'option_b': (context or {}).get('option_b', 'tightening what you have'),
        'current_state': (context or {}).get('current_state', 'your current outbound setup'),
        'situation': (context or {}).get('situation', 'running multiple outreach tools'),
        'solution_area': (context or {}).get('solution_area', 'consolidating the whole stack into one system'),
        'outcome': (context or {}).get('outcome', 'get all that done in one system and cut the tool cost by 80%'),
        'proof_point': PROOF_POINTS[0],
        'time_a': (context or {}).get('time_a', 'Tuesday at 2pm ET'),
        'time_b': (context or {}).get('time_b', 'Thursday at 10am ET'),
        'call_date': (context or {}).get('call_date', 'Tuesday'),
        'resource': (context or {}).get('resource', 'this breakdown of how we handle deliverability'),
        'reminder': (context or {}).get('reminder', "looking forward to it"),
    }
    
    # Fill template
    try:
        draft_text = template.format(**fills)
    except KeyError as e:
        # If a key is missing, use a safe fallback
        draft_text = template
        for k, v in fills.items():
            draft_text = draft_text.replace('{' + k + '}', str(v))
    
    # Queue the draft
    msg_id = queue_draft(conv['id'], stage, draft_text, variant)
    
    return msg_id, draft_text, stage, variant

def generate_stage_advance_draft(lead_id, inbound_message=None):
    """
    Generate a draft based on the prospect's reply and stage advancement logic.
    Analyzes the inbound message to determine if stage should advance.
    
    Returns: (message_id, draft_text, new_stage, variant) or None if no draft needed
    """
    lead = get_lead(lead_id=lead_id)
    conv = get_conversation(lead_id)
    
    if not lead or not conv:
        return None
    
    current_stage = conv['stage']
    
    # If there's an inbound message, analyze it for stage advancement
    if inbound_message:
        msg_lower = inbound_message.lower()
        
        # Stage 0 -> 1: Connection accepted (any reply means accepted)
        if current_stage == 0:
            new_stage = 1
        # Stage 1 -> 2: Reply with substance (not just "thanks" or "sure")
        elif current_stage == 1 and len(msg_lower) > 20:
            new_stage = 2
        # Stage 2 -> 3: They indicated their focus area
        elif current_stage == 2 and any(w in msg_lower for w in ['focus', 'working on', 'trying', 'building', 'scaling']):
            new_stage = 3
        # Stage 3 -> 4: They named a problem
        elif current_stage == 3 and any(w in msg_lower for w in ['struggle', 'problem', 'issue', 'challenge', 'hard', 'difficult', 'expensive', 'frustrating']):
            new_stage = 4
        # Stage 4 -> 5: They're curious about solutions
        elif current_stage == 4 and any(w in msg_lower for w in ['how', 'what', 'tell me', 'interested', 'curious', 'yes']):
            new_stage = 5
        # Stage 5 -> 6: They confirmed fit
        elif current_stage == 5 and any(w in msg_lower for w in ['yes', 'sure', 'absolutely', 'definitely', 'worth', 'sounds good']):
            new_stage = 6
        # Stage 6 -> 7: They want to book
        elif current_stage == 6 and any(w in msg_lower for w in ['let\'s do it', 'book', 'schedule', 'when', 'calendar', 'yes']):
            new_stage = 7
        # Stage 7 -> 8: Call booked
        elif current_stage == 7 and any(w in msg_lower for w in ['tuesday', 'thursday', 'works', 'confirmed', 'booked']):
            new_stage = 8
        else:
            new_stage = current_stage  # Stay at current stage
    else:
        # No inbound message -- this is a follow-up at current stage
        new_stage = current_stage
    
    # Generate draft for the (possibly new) stage
    variant = conv['opener_variant'] or 'A'
    context = {}
    
    if inbound_message and new_stage > current_stage:
        # Stage advanced -- generate next stage message
        msg_id, draft_text, _, _ = generate_draft(lead_id, stage=new_stage, variant=variant, context=context)
        return msg_id, draft_text, new_stage, variant
    elif inbound_message and new_stage == current_stage:
        # Stage didn't advance -- generate follow-up at current stage
        # Use the other variant for variety
        other_variant = 'B' if variant == 'A' else 'A'
        msg_id, draft_text, _, _ = generate_draft(lead_id, stage=current_stage, variant=other_variant, context=context)
        return msg_id, draft_text, current_stage, other_variant
    else:
        # No inbound -- follow-up at current stage
        msg_id, draft_text, _, _ = generate_draft(lead_id, stage=current_stage, variant=variant, context=context)
        return msg_id, draft_text, current_stage, variant

if __name__ == '__main__':
    # Test: create a test lead and generate a draft
    from research_lead import research_and_add_lead
    
    sample = {
        'linkedin_url': 'https://linkedin.com/in/test-draft-user',
        'full_name': 'Jane Smith',
        'title': 'Founder at Growth Agency',
        'company': 'Growth Agency',
        'headline': 'Helping B2B agencies scale outbound with Apollo + Clay',
        'about': 'Running outbound for 15+ agency clients. Struggling with tool sprawl.'
    }
    
    lead_id, score, criteria, qualifies = research_and_add_lead(sample, source='test')
    print(f'Lead: {sample["full_name"]} (Score: {score}, Qualifies: {qualifies})')
    
    if qualifies:
        for stage in range(4):
            result = generate_draft(lead_id, stage=stage)
            if result:
                msg_id, draft, s, v = result
                print(f'\nStage {s} (variant {v}):')
                print(f'  {draft}')
