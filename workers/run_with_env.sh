#!/bin/bash
# Load environment variables from parent .env.local and run prefilter test

ENV_FILE="/Users/patsimmons/client-coding/pivot-5-website_11.19.25/ai-editor-2.0-full-stack-application/.env.local"

# Source the env file (handles special chars properly)
set -a
source "$ENV_FILE"
set +a

# Run the test
python3 run_prefilter_test.py
