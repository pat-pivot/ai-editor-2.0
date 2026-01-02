#!/usr/bin/env python3
"""Quick test to check data structure from get_newsletter_selects"""

from utils.airtable import AirtableClient
from datetime import datetime, timedelta

airtable = AirtableClient()
seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
stories = airtable.get_newsletter_selects(since_date=seven_days_ago)

print(f"Found {len(stories)} stories")
if stories:
    sample = stories[0]
    print(f"Keys in story: {list(sample.keys())}")
    print(f"Has 'fields' key: {'fields' in sample}")

    if 'fields' in sample:
        fields = sample['fields']
        print(f"  source_id in fields: {fields.get('source_id', 'MISSING')}")
        print(f"  core_url in fields: {fields.get('core_url', 'MISSING')}")
    else:
        print(f"  source_id direct: {sample.get('source_id', 'MISSING')}")
        print(f"  core_url direct: {sample.get('core_url', 'MISSING')}")
