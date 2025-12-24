"""
Gemini API Client for AI Editor 2.0 Workers
Used for: Pre-filtering (Step 1), Content cleaning (Step 3)

Prompts are loaded from PostgreSQL database via utils.prompts
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai

from .prompts import get_prompt, get_prompt_with_metadata

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini API wrapper for AI Editor 2.0"""

    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=self.api_key)

        # Model for pre-filtering (fast, cheap)
        self.flash_model = genai.GenerativeModel('gemini-3-flash-preview')

    def prefilter_story(self, story_data: dict, yesterday_headlines: list, source_score: int) -> dict:
        """
        Step 1, Node 13: Gemini pre-filter for slot eligibility

        Args:
            story_data: {storyId, pivotId, headline, dek, topic, source, hoursAgo, originalUrl}
            yesterday_headlines: List of 5 headlines from yesterday's issue
            source_score: Credibility score 1-5

        Returns:
            {eligible_slots: [1,2,3], primary_slot: 2, reasoning: "..."}
        """
        prompt = self._build_prefilter_prompt(story_data, yesterday_headlines, source_score)

        response = self.flash_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=256,
                response_mime_type="application/json"
            )
        )

        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from response
            return self._parse_prefilter_response(response.text)

    def _build_prefilter_prompt(self, story: dict, yesterday_headlines: list, source_score: int) -> str:
        """
        Build the pre-filter prompt from database with Python variable substitution.

        Database prompts use {variable} syntax for Python .format() substitution.
        """
        # Try to load prompt from database
        prompt_template = get_prompt('slot_1_prefilter')

        if prompt_template:
            try:
                # Substitute variables using Python .format()
                prompt = prompt_template.format(
                    headline=story.get('headline', ''),
                    content=story.get('dek', ''),  # Use dek as content summary
                    date_published=story.get('date_published', ''),
                    hours_ago=story.get('hoursAgo', 0),
                    source=story.get('source', ''),
                    credibility=source_score,
                    topic=story.get('topic', ''),
                    yesterday_headlines='\n'.join(f"- {h}" for h in yesterday_headlines)
                )
                return prompt
            except KeyError as e:
                logger.warning(f"Missing variable in prefilter prompt: {e}, using fallback")

        # Fallback to hardcoded prompt if database prompt not available
        logger.warning("Prefilter prompt not found in database, using fallback")
        return f"""Analyze this news article and determine which newsletter slots it's eligible for.

ARTICLE:
Headline: {story.get('headline', '')}
Summary: {story.get('dek', '')}
Published: {story.get('date_published', '')}
Hours Old: {story.get('hoursAgo', 0)}
Source: {story.get('source', '')}
Source Credibility: {source_score}/5

SLOT CRITERIA:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

YESTERDAY'S HEADLINES (avoid similar topics):
{chr(10).join(f"- {h}" for h in yesterday_headlines)}

Return JSON only:
{{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 1,
  "reasoning": "Brief explanation"
}}"""

    def _parse_prefilter_response(self, text: str) -> dict:
        """Fallback parser for non-JSON responses"""
        import re

        # Try to find JSON in the response
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Default: no eligible slots
        return {
            "eligible_slots": [],
            "primary_slot": None,
            "reasoning": "Failed to parse response"
        }

    def clean_content(self, markdown: str) -> str:
        """
        Step 3: Clean article content (remove navigation, ads, footers)

        Args:
            markdown: Raw article markdown

        Returns:
            Cleaned markdown content
        """
        # Load content_cleaner prompt from database
        base_prompt = get_prompt('content_cleaner')

        if base_prompt:
            prompt = f"""{base_prompt}

ARTICLE:
{markdown[:8000]}

Return ONLY the cleaned article content, no explanations."""
        else:
            logger.warning("content_cleaner prompt not found in database, using fallback")
            prompt = f"""Clean the following article content by removing:
- Navigation elements
- Advertisements
- Footer content
- Subscription prompts
- Social media buttons
- Related articles sections
- Author bios (keep byline if part of story)

Keep ONLY the main article content. Preserve the article structure and formatting.

ARTICLE:
{markdown[:8000]}

Return ONLY the cleaned article content, no explanations."""

        # Get temperature from database if available
        prompt_meta = get_prompt_with_metadata('content_cleaner')
        temperature = float(prompt_meta.get('temperature', 0.1)) if prompt_meta else 0.1

        response = self.flash_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=4096
            )
        )

        return response.text.strip()
