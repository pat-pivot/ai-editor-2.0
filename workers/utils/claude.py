"""
Claude API Client for AI Editor 2.0 Workers
Used for: Slot Selection (Step 2), Decoration (Step 3), Summaries (Step 4)

Prompts are loaded from PostgreSQL database via utils.prompts
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic

from .prompts import get_prompt, get_prompt_with_metadata

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Claude API wrapper for AI Editor 2.0"""

    def __init__(self):
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = Anthropic(api_key=self.api_key)

        # Default model (can be overridden by prompt metadata)
        self.default_model = "claude-sonnet-4-5-20250929"

    # =========================================================================
    # STEP 2: SLOT SELECTION
    # =========================================================================

    def select_slot(
        self,
        slot: int,
        candidates: List[dict],
        yesterday_data: dict,
        cumulative_state: dict
    ) -> dict:
        """
        Step 2, Nodes 18-22: Claude agent for slot selection

        Args:
            slot: Slot number (1-5)
            candidates: List of story candidates for this slot
            yesterday_data: {headlines, storyIds, pivotIds, slot1Company}
            cumulative_state: {selectedToday, selectedCompanies, selectedSources}

        Returns:
            {selected_storyId, selected_pivotId, selected_headline, company, source_id, reasoning}
        """
        system_prompt = self._build_slot_system_prompt(slot, yesterday_data, cumulative_state)
        user_prompt = self._build_slot_user_prompt(candidates)

        response = self.client.messages.create(
            model=self.default_model,
            max_tokens=2000,
            temperature=0.5,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        try:
            result = json.loads(response.content[0].text)
            return result
        except json.JSONDecodeError:
            return self._parse_slot_response(response.content[0].text, candidates)

    def _build_slot_system_prompt(self, slot: int, yesterday_data: dict, cumulative_state: dict) -> str:
        """
        Build slot-specific system prompt from database with Python variable substitution.

        Database prompts use {variable} syntax for Python .format() substitution.
        """
        # Load the base prompt from database
        prompt_key = f"slot_{slot}_agent"
        prompt_template = get_prompt(prompt_key)

        # Build dynamic context values
        yesterday_headlines = yesterday_data.get('headlines', [])
        selected_today = cumulative_state.get('selectedToday', [])
        selected_companies = cumulative_state.get('selectedCompanies', [])
        selected_sources = cumulative_state.get('selectedSources', [])
        yesterday_slot = yesterday_headlines[slot - 1] if len(yesterday_headlines) >= slot else "(none)"

        if prompt_template:
            try:
                # Substitute variables using Python .format()
                # Note: {candidates} will be filled in by _build_slot_user_prompt
                prompt = prompt_template.format(
                    candidates="(See candidates below)",
                    selected_stories=', '.join(selected_today) if selected_today else '(none yet)',
                    selected_companies=', '.join(selected_companies) if selected_companies else '(none yet)',
                    selected_sources=', '.join(selected_sources) if selected_sources else '(none yet)',
                    yesterday_slot=yesterday_slot
                )

                # Add slot 1 special rule
                if slot == 1 and yesterday_data.get('slot1Company'):
                    prompt += f"\n\nTWO-DAY ROTATION (Slot 1): Do NOT feature {yesterday_data['slot1Company']} (yesterday's Slot 1 company)."

                return prompt
            except KeyError as e:
                logger.warning(f"Missing variable in {prompt_key} prompt: {e}, using fallback")

        # Fallback to hardcoded if database prompt not available
        logger.warning(f"Prompt {prompt_key} not found in database, using fallback")
        slot_focus = {
            1: "Jobs, economy, stock market, broad societal impact. Must be FRESH (0-24 hours).",
            2: "Tier 1 AI companies (OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon), economic themes, research breakthroughs.",
            3: "Industry verticals: Healthcare, Government, Education, Legal, Accounting, Retail, Security, Transportation, Manufacturing, Real Estate, Agriculture, Energy.",
            4: "Emerging companies: product launches, fundraising, acquisitions, new AI tools. Must be FRESH (0-48 hours).",
            5: "Consumer AI, human interest, ethics, entertainment, societal impact, fun/quirky uses."
        }

        context = f"""You are a senior editor for Pivot 5. SLOT {slot} FOCUS: {slot_focus.get(slot, '')}

CURRENT CONTEXT:
1. YESTERDAY'S HEADLINES - Do NOT select stories covering same topics:
{chr(10).join(f"   - {h}" for h in yesterday_headlines) if yesterday_headlines else '   (none)'}

2. ALREADY SELECTED TODAY - Do NOT select these storyIDs:
   {', '.join(selected_today) if selected_today else '(none yet)'}

3. COMPANY DIVERSITY - Each company appears at most ONCE across all 5 slots:
   Already featured today: {', '.join(selected_companies) if selected_companies else '(none yet)'}

4. SOURCE DIVERSITY - Max 2 stories per source per day:
   Already used today: {', '.join(selected_sources) if selected_sources else '(none yet)'}
"""

        # Slot 1 has special two-day rotation rule
        if slot == 1 and yesterday_data.get('slot1Company'):
            context += f"""
5. TWO-DAY ROTATION (Slot 1 only) - Do NOT feature this company:
   Yesterday's Slot 1 company: {yesterday_data['slot1Company']}
"""

        context += """

Return JSON with:
- selected_storyId: the chosen story's storyID
- selected_pivotId: the chosen story's pivotId
- selected_headline: the chosen story's headline
- company: primary company mentioned (or null)
- source_id: the story's source
- reasoning: 1-2 sentence explanation"""

        return context

    def _build_slot_user_prompt(self, candidates: List[dict]) -> str:
        """Build user prompt with candidate stories"""
        prompt = "CANDIDATE STORIES:\n\n"

        for i, candidate in enumerate(candidates, 1):
            fields = candidate.get('fields', candidate)
            prompt += f"""Story {i}:
- storyID: {fields.get('storyID', '')}
- pivotId: {fields.get('pivotId', '')}
- headline: {fields.get('headline', '')}
- source: {fields.get('source_id', '')}
- published: {fields.get('date_og_published', '')}

"""

        prompt += "Select the BEST story for this slot. Return JSON only."
        return prompt

    def _parse_slot_response(self, text: str, candidates: List[dict]) -> dict:
        """Fallback parser for non-JSON responses"""
        import re

        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Default to first candidate
        if candidates:
            fields = candidates[0].get('fields', candidates[0])
            return {
                "selected_storyId": fields.get('storyID', ''),
                "selected_pivotId": fields.get('pivotId', ''),
                "selected_headline": fields.get('headline', ''),
                "company": None,
                "source_id": fields.get('source_id', ''),
                "reasoning": "Fallback: selected first candidate"
            }

        return {"error": "No candidates available"}

    def generate_subject_line(self, headlines: List[str]) -> str:
        """
        Step 2, Node 29: Generate email subject line from 5 headlines

        Database prompts use {variable} syntax for Python .format() substitution.
        """
        # Load base prompt from database
        prompt_template = get_prompt('subject_line')

        if prompt_template:
            try:
                # Substitute variables using Python .format()
                prompt = prompt_template.format(
                    slot1_headline=headlines[0] if len(headlines) > 0 else '(none)',
                    slot2_headline=headlines[1] if len(headlines) > 1 else '(none)',
                    slot3_headline=headlines[2] if len(headlines) > 2 else '(none)',
                    slot4_headline=headlines[3] if len(headlines) > 3 else '(none)',
                    slot5_headline=headlines[4] if len(headlines) > 4 else '(none)',
                    recent_subject_lines='(not available)'  # Could be enhanced to load from database
                )
            except KeyError as e:
                logger.warning(f"Missing variable in subject_line prompt: {e}, using fallback")
                prompt_template = None

        if not prompt_template:
            logger.warning("subject_line prompt not found in database, using fallback")
            prompt = f"""Generate a compelling email subject line for this daily AI newsletter.

TODAY'S HEADLINES:
1. {headlines[0] if len(headlines) > 0 else ''}
2. {headlines[1] if len(headlines) > 1 else ''}
3. {headlines[2] if len(headlines) > 2 else ''}
4. {headlines[3] if len(headlines) > 3 else ''}
5. {headlines[4] if len(headlines) > 4 else ''}

REQUIREMENTS:
- Maximum 60 characters
- Create urgency and curiosity
- Reference 1-2 key stories
- Avoid clickbait, be substantive
- Match professional newsletter tone

Return ONLY the subject line, no quotes or explanation."""

        # Get model/temperature from database if available
        prompt_meta = get_prompt_with_metadata('subject_line')
        model = prompt_meta.get('model', self.default_model) if prompt_meta else self.default_model
        temperature = prompt_meta.get('temperature', 0.7) if prompt_meta else 0.7

        response = self.client.messages.create(
            model=model,
            max_tokens=100,
            temperature=float(temperature),
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip().strip('"\'')

    # =========================================================================
    # STEP 3: DECORATION
    # =========================================================================

    def decorate_story(self, story_data: dict, cleaned_content: str) -> dict:
        """
        Step 3: Generate headline, dek, bullets, and image prompt

        Database prompts use {variable} syntax for Python .format() substitution.

        Args:
            story_data: {headline, source, url, topic, slot_number}
            cleaned_content: Cleaned article markdown

        Returns:
            {ai_headline, ai_dek, b1, b2, b3, image_prompt, label}
        """
        # Extract story data
        original_headline = story_data.get('headline', '')
        source = story_data.get('source', '')
        topic = story_data.get('topic', '')
        slot_number = story_data.get('slot_number', 0)

        # Slot focus descriptions
        slot_focus_map = {
            1: "Jobs & Economy",
            2: "Big Tech / Tier 1 AI",
            3: "Industry Verticals",
            4: "Emerging Tech",
            5: "Consumer AI"
        }
        slot_focus = slot_focus_map.get(slot_number, "AI News")

        # Truncate content for prompt
        content_summary = cleaned_content[:6000]

        # Load prompts from database
        headline_template = get_prompt('headline_generator')
        bullet_template = get_prompt('bullet_generator')
        image_prompt_template = get_prompt('image_prompt')

        # Build combined prompt by substituting variables in each
        combined_parts = []

        if headline_template:
            try:
                combined_parts.append(headline_template.format(
                    original_headline=original_headline,
                    summary=content_summary[:2000],
                    slot_number=slot_number,
                    slot_focus=slot_focus
                ))
            except KeyError as e:
                logger.warning(f"Missing variable in headline_generator prompt: {e}")

        if bullet_template:
            try:
                combined_parts.append(bullet_template.format(
                    headline=original_headline,
                    content=content_summary
                ))
            except KeyError as e:
                logger.warning(f"Missing variable in bullet_generator prompt: {e}")

        if image_prompt_template:
            try:
                combined_parts.append(image_prompt_template.format(
                    headline=original_headline,
                    summary=content_summary[:2000],
                    slot_number=slot_number
                ))
            except KeyError as e:
                logger.warning(f"Missing variable in image_prompt prompt: {e}")

        if combined_parts:
            # Combine all prompts with story context
            prompt = "\n\n".join(combined_parts)
            prompt += f"""

FULL ARTICLE CONTENT:
{content_summary}

Generate all of the above in JSON format with keys: ai_headline, ai_dek, b1, b2, b3, label, image_prompt

Return JSON only."""
        else:
            # Fallback to hardcoded prompt
            logger.warning("Decoration prompts not found in database, using fallback")
            prompt = f"""You are decorating a story for Pivot 5, a professional AI newsletter.

ORIGINAL HEADLINE: {original_headline}
SOURCE: {source}
TOPIC: {topic}

ARTICLE CONTENT:
{content_summary}

Generate the following in JSON format:

1. ai_headline: Punchy headline in Title Case. Max 80 characters. Create intrigue.

2. ai_dek: One sentence hook that expands on headline. Professional tone.

3. b1: First bullet - Main announcement (2 sentences, max 260 characters). Start with action verb.

4. b2: Second bullet - Key details/context (2 sentences, max 260 characters).

5. b3: Third bullet - Business impact or "why it matters" (2 sentences, max 260 characters).

6. label: Topic label in ALL CAPS (e.g., "JOBS & ECONOMY", "BIG TECH", "HEALTHCARE AI", "EMERGING TECH", "CONSUMER AI")

7. image_prompt: Description for AI image generation. Professional, editorial style. Abstract representation of the story theme. No text, logos, or faces.

Return JSON only."""

        # Get model/temperature from headline_generator prompt metadata
        prompt_meta = get_prompt_with_metadata('headline_generator')
        model = prompt_meta.get('model', self.default_model) if prompt_meta else self.default_model
        temperature = prompt_meta.get('temperature', 0.5) if prompt_meta else 0.5

        response = self.client.messages.create(
            model=model,
            max_tokens=1500,
            temperature=float(temperature),
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            return json.loads(response.content[0].text)
        except json.JSONDecodeError:
            return self._parse_decoration_response(response.content[0].text)

    def apply_bolding(self, bullets: List[str]) -> List[str]:
        """
        Step 3: Apply markdown bold to key phrases in bullets

        Database prompt uses {bullets} variable for Python .format() substitution.
        """
        # Load bold_formatter prompt from database
        prompt_template = get_prompt('bold_formatter')

        # Format bullets as text
        bullets_text = '\n'.join([f"- {b}" for b in bullets])

        prompt = None
        if prompt_template:
            try:
                prompt = prompt_template.format(
                    bullets=bullets_text
                )
            except KeyError as e:
                logger.warning(f"Missing variable in bold_formatter prompt: {e}, using fallback")
                prompt_template = None

        if not prompt:
            logger.warning("bold_formatter prompt not found in database, using fallback")
            prompt = f"""Apply markdown bold (**text**) to 1-2 key phrases in each bullet point.
Bold the most impactful/newsworthy phrases.

BULLETS:
{bullets_text}

Return JSON only:
{{
  "formatted_bullets": [
    "Bullet with **key phrase** bolded...",
    "Another bullet with **important stat** highlighted...",
    "Third bullet with **company name** emphasized..."
  ]
}}"""

        # Get model/temperature from database
        prompt_meta = get_prompt_with_metadata('bold_formatter')
        model = prompt_meta.get('model', self.default_model) if prompt_meta else self.default_model
        temperature = prompt_meta.get('temperature', 0.3) if prompt_meta else 0.3

        response = self.client.messages.create(
            model=model,
            max_tokens=500,
            temperature=float(temperature),
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            result = json.loads(response.content[0].text)
            # Handle both JSON object with formatted_bullets key and plain array
            if isinstance(result, dict) and 'formatted_bullets' in result:
                return result['formatted_bullets']
            elif isinstance(result, list):
                return result
            else:
                logger.warning("Unexpected bold_formatter response format")
                return bullets
        except json.JSONDecodeError:
            return bullets  # Return original if parsing fails

    def _parse_decoration_response(self, text: str) -> dict:
        """Fallback parser for decoration response"""
        import re

        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {
            "ai_headline": "",
            "ai_dek": "",
            "b1": "",
            "b2": "",
            "b3": "",
            "label": "AI NEWS",
            "image_prompt": "",
            "error": "Failed to parse response"
        }

    # =========================================================================
    # STEP 4: SUMMARIES
    # =========================================================================

    def generate_summary(self, headlines: List[str], max_words: int = 15) -> str:
        """
        Step 4: Generate newsletter summary (15-word or 20-word)

        Database prompt uses {slot1_headline} through {slot5_headline} for Python .format() substitution.
        """
        # Load summary_generator prompt from database
        prompt_template = get_prompt('summary_generator')

        prompt = None
        if prompt_template:
            try:
                prompt = prompt_template.format(
                    slot1_headline=headlines[0] if len(headlines) > 0 else '(none)',
                    slot2_headline=headlines[1] if len(headlines) > 1 else '(none)',
                    slot3_headline=headlines[2] if len(headlines) > 2 else '(none)',
                    slot4_headline=headlines[3] if len(headlines) > 3 else '(none)',
                    slot5_headline=headlines[4] if len(headlines) > 4 else '(none)'
                )
            except KeyError as e:
                logger.warning(f"Missing variable in summary_generator prompt: {e}, using fallback")
                prompt_template = None

        if not prompt:
            logger.warning("summary_generator prompt not found in database, using fallback")
            headlines_text = "\n".join([f"{i+1}. {h}" for i, h in enumerate(headlines[:5])])
            prompt = f"""Generate a {max_words}-word summary of today's newsletter for the email preview text.

TODAY'S STORIES:
{headlines_text}

GUIDELINES:
- Exactly {max_words} words
- Mention 1-2 key stories
- Create interest to open the email
- Professional tone

Return JSON only:
{{
  "summary": "Your {max_words}-word summary here..."
}}"""

        # Get model/temperature from database
        prompt_meta = get_prompt_with_metadata('summary_generator')
        model = prompt_meta.get('model', self.default_model) if prompt_meta else self.default_model
        temperature = prompt_meta.get('temperature', 0.5) if prompt_meta else 0.5

        response = self.client.messages.create(
            model=model,
            max_tokens=100,
            temperature=float(temperature),
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response or extract text
        response_text = response.content[0].text.strip()
        try:
            result = json.loads(response_text)
            if isinstance(result, dict) and 'summary' in result:
                return result['summary']
            return response_text
        except json.JSONDecodeError:
            # Return raw text if not JSON
            return response_text
