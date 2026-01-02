#!/usr/bin/env python3
"""Quick prefilter test"""
from jobs.prefilter import prefilter_stories

print("Starting prefilter test...")
result = prefilter_stories()
print("\n=== RESULT ===")
print(result)
