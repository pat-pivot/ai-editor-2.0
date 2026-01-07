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
        recent_data: dict,
        cumulative_state: dict
    ) -> dict:
        """
        Step 2, Nodes 18-22: Claude agent for slot selection

        Args:
            slot: Slot number (1-5)
            candidates: List of story candidates for this slot
            recent_data: {headlines, storyIds, pivotIds, slot1Headline} from 14-day lookback
            cumulative_state: {selectedToday, selectedCompanies, selectedSources}

        Returns:
            {selected_id, selected_headline, selected_company, selected_source, reasoning}
            Note: Field names match n8n workflow output format (12/31/25 audit fix)

        Updated 1/1/26: Removed source_lookup - credibility guidance now in system prompts
        """
        system_prompt = self._build_slot_system_prompt(slot, recent_data, cumulative_state, len(candidates))
        user_prompt = self._build_slot_user_prompt(candidates)

        response = self.client.messages.create(
            model=self.default_model,
            max_tokens=2000,
            temperature=0.3,  # n8n uses 0.3 for deterministic selection
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        try:
            result = json.loads(response.content[0].text)
            return result
        except json.JSONDecodeError:
            return self._parse_slot_response(response.content[0].text, candidates)

    def _format_story_summaries_for_prompt(self, story_summaries: List[dict]) -> str:
        """
        Format story summaries for inclusion in Claude prompt.

        Added 1/7/26: For semantic deduplication to catch same news events
        with different headlines/IDs.

        Args:
            story_summaries: List of story summary dicts with headline, bullets, dek, company

        Returns:
            Formatted string to append to system prompt
        """
        if not story_summaries:
            return ""

        output = "\n\n## RECENT STORY SUMMARIES (for semantic deduplication)\n"
        output += "**CRITICAL:** Do NOT select stories about the SAME NEWS EVENT as these, even if headlines differ:\n\n"

        for i, summary in enumerate(story_summaries[:20], 1):  # Limit to 20
            output += f"### Recent Story {i}\n"
            output += f"- Headline: {summary.get('headline', 'N/A')}\n"
            bullets = [b for b in summary.get('bullets', []) if b]
            if bullets:
                output += f"- Key Points: {'; '.join(bullets)}\n"
            if summary.get('company'):
                output += f"- Company: {summary.get('company')}\n"
            output += "\n"

        return output

    def _build_slot_system_prompt(self, slot: int, recent_data: dict, cumulative_state: dict, candidate_count: int = 0) -> str:
        """
        Build slot-specific system prompt from database with Python variable substitution.

        Database prompts use {variable} syntax for Python .format() substitution.

        Updated 12/30/25: Changed from yesterday_data to recent_data (14-day lookback)
        to prevent story repetition within a 2-week window.

        Updated 12/31/25: Added candidate_count parameter to populate {candidate_count} placeholder.
        """
        # Load the base prompt from database
        prompt_key = f"slot_{slot}_agent"
        prompt_template = get_prompt(prompt_key)

        # Build dynamic context values from 14-day lookback
        recent_headlines = recent_data.get('headlines', [])
        recent_story_ids = recent_data.get('storyIds', [])
        selected_today = cumulative_state.get('selectedToday', [])
        selected_companies = cumulative_state.get('selectedCompanies', [])
        selected_sources = cumulative_state.get('selectedSources', {})  # Dict with counts

        # Format selected sources for display (n8n format: {"TechCrunch": 1, "Bloomberg": 1})
        if isinstance(selected_sources, dict) and selected_sources:
            sources_display = ', '.join([f"{src}: {cnt}" for src, cnt in selected_sources.items()])
        elif isinstance(selected_sources, list):
            # Legacy list format fallback
            sources_display = ', '.join(selected_sources) if selected_sources else '(none yet)'
        else:
            sources_display = '(none yet)'

        # For yesterday_slot context, use recent headlines if available
        # (showing the first 5 most recent as a sample)
        sample_headlines = recent_headlines[:5] if recent_headlines else []
        yesterday_slot = sample_headlines[slot - 1] if len(sample_headlines) >= slot else "(none)"

        if prompt_template:
            try:
                # Build recent headlines display for the prompt
                if recent_headlines:
                    headlines_display = ""
                    for i, headline in enumerate(recent_headlines[:30], 1):
                        headlines_display += f"\n{i}. {headline}"
                    if len(recent_headlines) > 30:
                        headlines_display += f"\n... and {len(recent_headlines) - 30} more"
                else:
                    headlines_display = "(none - this is the first issue)"

                # Substitute variables using Python .format()
                # CRITICAL: All placeholders in database prompts must be provided here
                prompt = prompt_template.format(
                    candidates="(See candidates in user prompt below)",
                    candidate_count=candidate_count,  # Actual count passed from select_slot()
                    recent_headlines=headlines_display,
                    selected_stories=', '.join(selected_today) if selected_today else '(none yet)',
                    selected_companies=', '.join(selected_companies) if selected_companies else '(none yet)',
                    selected_sources=sources_display,
                    yesterday_slot=yesterday_slot
                )

                # Add slot 1 special rule (two-day company rotation)
                # Claude infers the company name from yesterday's Slot 1 headline
                if slot == 1 and recent_data.get('slot1Headline'):
                    prompt += f"\n\nTWO-DAY COMPANY ROTATION (Slot 1 Only): Yesterday's Slot 1 featured: \"{recent_data['slot1Headline']}\"\nIdentify which company was featured in that headline, then do NOT select a story about the same company today. This ensures company diversity across consecutive days."

                # Note: recent_headlines are now included via {recent_headlines} placeholder
                # in the database prompt template - no longer appended separately.

                # Add storyIDs as a backup check (in addition to semantic headline dedup)
                if recent_story_ids:
                    prompt += f"\n\nSTORY IDs TO AVOID (already sent in last 14 days): {', '.join(recent_story_ids[:30])}{'...' if len(recent_story_ids) > 30 else ''}"

                # NEW 1/7/26: Add story summaries for semantic deduplication
                story_summaries = recent_data.get('story_summaries', [])
                if story_summaries:
                    prompt += self._format_story_summaries_for_prompt(story_summaries)

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

        # Build recent headlines list for semantic deduplication
        headlines_list = ""
        if recent_headlines:
            for i, headline in enumerate(recent_headlines[:30], 1):
                headlines_list += f"\n   {i}. {headline}"
            if len(recent_headlines) > 30:
                headlines_list += f"\n   ... and {len(recent_headlines) - 30} more"
        else:
            headlines_list = "\n   (none)"

        context = f"""You are a senior editor for Pivot 5. SLOT {slot} FOCUS: {slot_focus.get(slot, '')}

CURRENT CONTEXT:

### Rule 1: Recent Headlines (Last 14 Days) - CRITICAL SEMANTIC DEDUPLICATION
Do NOT select any story about the same topic/event as these recent headlines.
Even if worded differently, if it's the SAME underlying news, treat as duplicate:{headlines_list}

### Rule 2: Already Selected Today
Do NOT select these storyIDs: {', '.join(selected_today) if selected_today else '(none yet)'}

### Rule 3: Company Diversity
Each company appears at most ONCE across all 5 slots.
Already featured today: {', '.join(selected_companies) if selected_companies else '(none yet)'}

### Rule 4: Source Diversity
Max 2 stories per source per day.
Already used today: {sources_display}
"""

        # Slot 1 has special two-day rotation rule (infer company from headline)
        if slot == 1 and recent_data.get('slot1Headline'):
            context += f"""
5. TWO-DAY COMPANY ROTATION (Slot 1 only):
   Yesterday's Slot 1 headline: "{recent_data['slot1Headline']}"
   Identify which company was featured in that headline, then do NOT select the same company today.
"""

        context += """

Return ONLY valid JSON with no additional text:
{
  "selected_id": "storyID of chosen story",
  "selected_headline": "headline of chosen story",
  "selected_source": "source_name",
  "selected_company": "primary company featured or null",
  "reasoning": "1-2 sentence explanation"
}"""

        # NEW 1/7/26: Add story summaries for semantic deduplication (fallback path)
        story_summaries = recent_data.get('story_summaries', [])
        if story_summaries:
            context += self._format_story_summaries_for_prompt(story_summaries)

        return context

    def _build_slot_user_prompt(self, candidates: List[dict]) -> str:
        """
        Build user prompt with candidate stories.

        Updated 1/1/26: Removed credibility_score - now in system prompts
        Note: primary_company is NOT in Pre-Filter Log table, skipped
        """
        prompt = f"## CANDIDATE STORIES ({len(candidates)} stories)\n\n"

        for i, candidate in enumerate(candidates, 1):
            fields = candidate.get('fields', candidate)

            prompt += f"""Story {i}:
- storyID: {fields.get('storyID', '')}
- pivotId: {fields.get('pivotId', '')}
- headline: {fields.get('headline', '')}
- source_name: {fields.get('source_id', '')}
- date_og_published: {fields.get('date_og_published', '')}
- url: {fields.get('core_url', '')}

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

        # Default to first candidate (field names match n8n output format)
        if candidates:
            fields = candidates[0].get('fields', candidates[0])
            return {
                "selected_id": fields.get('storyID', ''),
                "selected_headline": fields.get('headline', ''),
                "selected_company": None,
                "selected_source": fields.get('source_id', ''),
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

    def decorate_story(self, story_data: dict, cleaned_content: str, newsletter: str = 'pivot_ai') -> dict:
        """
        Step 3: Generate headline, dek, bullets, label, and image prompt using MASTER PROMPT

        Uses the Content Creator prompt from n8n workflow HCbd2g852rkQgSqr.
        Database prompts use {variable} syntax for Python .format() substitution.

        Args:
            story_data: {headline, source, url, topic, slot_number, core_url, date_published, source_id}
            cleaned_content: Cleaned article markdown
            newsletter: Newsletter variant ('pivot_ai', 'pivot_build', 'pivot_invest')

        Returns:
            {ai_headline, ai_dek, ai_bullet_1, ai_bullet_2, ai_bullet_3, image_prompt, label, source, clean_url}
        """
        # Extract story data
        original_headline = story_data.get('headline', '')
        source_id = story_data.get('source_id', story_data.get('source', ''))
        core_url = story_data.get('core_url', story_data.get('url', ''))
        date_published = story_data.get('date_published', '')

        # Truncate content for prompt (8KB limit per n8n)
        content_summary = cleaned_content[:8000]

        # Load newsletter style prompt from database
        style_key = f"{newsletter}_style"
        newsletter_style = get_prompt(style_key)
        if not newsletter_style:
            # Default to pivot_ai style
            newsletter_style = get_prompt('pivot_ai_style')
        if not newsletter_style:
            # Hardcoded fallback
            newsletter_style = """Audience: professionals following the AI field, not just technology broadly.
Focus: capabilities, limitations, ecosystem dynamics, and real-world impact.
Tone: sharp, skeptical of hype, but accessible to a broad tech/business audience.

Global Writing Rules:
- Write for busy CEOs - clear, confident, direct.
- Present tense, active voice.
- No jargon, no "could/might/possibly".
- Avoid vague terms like "impact" or "transformation".
- Stick to business consequences.
- EXACTLY 2 sentences per bullet.
- Headline: Title Case, one sentence, NO colons or semi-colons."""

        # Load master Content Creator prompt from database (stored as headline_generator)
        prompt_template = get_prompt('headline_generator')

        if prompt_template:
            try:
                prompt = prompt_template.format(
                    newsletter_style=newsletter_style,
                    core_url=core_url,
                    headline=original_headline,
                    source_id=source_id,
                    date_published=date_published,
                    newsletter=newsletter,
                    cleaned_content=content_summary
                )
            except KeyError as e:
                logger.warning(f"Missing variable in headline_generator prompt: {e}, using fallback")
                prompt_template = None

        if not prompt_template:
            # Fallback to hardcoded MASTER PROMPT from n8n
            logger.warning("Decoration prompts not found in database, using n8n fallback")
            prompt = f"""MASTER PROMPT — PIVOT 5 AI NEWSLETTER CONTENT CREATION

## YOUR ROLE
You are an expert newsletter editor creating content for Pivot 5's AI-focused newsletter.

## AUDIENCE
- CEOs, founders, general managers, and senior business leaders
- They are busy, strategic thinkers who want actionable insights
- They care about business impact, competitive dynamics, and what matters for decision-making

## VOICE & STYLE
- Confident, clear, informed — like a trusted advisor briefing an executive
- Present tense, active voice
- No jargon, no hedging (avoid "could/might/possibly")
- Avoid vague terms like "impact" or "transformation" — stick to concrete business consequences
- Professional but not stiff

## OUTPUT FORMAT
Return ONLY valid JSON with these exact fields:

{{
  "label": "CATEGORY from list below",
  "ai_headline": "Title Case headline, one sentence, NO colons or semi-colons",
  "ai_dek": "One sentence hook/subtitle",
  "ai_bullet_1": "EXACTLY 2 sentences - the main announcement or news",
  "ai_bullet_2": "EXACTLY 2 sentences - additional context or details",
  "ai_bullet_3": "EXACTLY 2 sentences - key insight, implication, or what happens next",
  "source": "Publication name (e.g., TechCrunch, The Information)",
  "clean_url": "Original URL without tracking parameters",
  "image_prompt": "Brief visual description for an illustrative image"
}}

## LABEL OPTIONS (choose exactly one):
WORK, EDUCATION, INFRASTRUCTURE, POLICY, TALENT, HEALTH, RETAIL, ENTERPRISE, COMPETITION, FUNDING, SECURITY, TOOLS, SEARCH, INVESTORS, CHINA, REGULATION, ETHICS, LAWSUITS

## CRITICAL RULES FOR BULLETS
1. Each bullet MUST be EXACTLY 2 sentences. Not 1. Not 3. Exactly 2.
2. Bullet 1: Lead with the news — what happened, who did it, what changed
3. Bullet 2: Context — why this matters, what it means, relevant background
4. Bullet 3: Forward-looking — implications, what to watch, competitive dynamics
5. Keep each bullet concise but complete — typically 25-45 words per bullet

## HEADLINE RULES
- Title Case (capitalize major words)
- One complete sentence
- NO colons, semi-colons, or em-dashes
- Focus on the most newsworthy element
- Make it scannable and specific

=== NEWSLETTER STYLE ===
{newsletter_style}

=== ARTICLE METADATA ===
URL: {core_url}
Headline: {original_headline}
Source: {source_id}
Published: {date_published}
Newsletter: {newsletter}

=== ARTICLE CONTENT ===
{content_summary}

Return ONLY the JSON object. No commentary, no code fences, no explanation."""

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

    def apply_bolding(self, decoration: dict) -> dict:
        """
        Step 3: Apply HTML <b> tags to key phrases in bullets

        Takes the full decoration dict and applies HTML bold formatting to ai_bullet_1/2/3.
        Uses the bold_formatter prompt from n8n workflow HCbd2g852rkQgSqr.

        Args:
            decoration: Dict with ai_bullet_1, ai_bullet_2, ai_bullet_3 fields

        Returns:
            Dict with same fields but bullets containing <b>phrase</b> HTML tags
        """
        # Load bold_formatter prompt from database
        prompt_template = get_prompt('bold_formatter')

        prompt = None
        if prompt_template:
            try:
                prompt = prompt_template.format(
                    label=decoration.get('label', ''),
                    ai_headline=decoration.get('ai_headline', ''),
                    ai_dek=decoration.get('ai_dek', ''),
                    ai_bullet_1=decoration.get('ai_bullet_1', ''),
                    ai_bullet_2=decoration.get('ai_bullet_2', ''),
                    ai_bullet_3=decoration.get('ai_bullet_3', ''),
                    source=decoration.get('source', ''),
                    clean_url=decoration.get('clean_url', '')
                )
            except KeyError as e:
                logger.warning(f"Missing variable in bold_formatter prompt: {e}, using fallback")
                prompt_template = None

        if not prompt:
            logger.warning("bold_formatter prompt not found in database, using fallback")
            # Fallback: HTML <b> tags, matching n8n workflow HCbd2g852rkQgSqr
            prompt = f"""You are a formatting assistant. Your task is to add HTML bold tags to highlight the most important phrase in each bullet point.

## INSTRUCTIONS

For each bullet field (ai_bullet_1, ai_bullet_2, ai_bullet_3):
1. Identify the SINGLE most important phrase (5-15 words) that captures the key information
2. Wrap that phrase in HTML bold tags: <b>phrase here</b>
3. Only bold ONE phrase per bullet
4. Do NOT bold entire sentences
5. Do NOT change any wording, punctuation, or content

## INPUT JSON
{{
  "label": "{decoration.get('label', '')}",
  "ai_headline": "{decoration.get('ai_headline', '')}",
  "ai_dek": "{decoration.get('ai_dek', '')}",
  "ai_bullet_1": "{decoration.get('ai_bullet_1', '')}",
  "ai_bullet_2": "{decoration.get('ai_bullet_2', '')}",
  "ai_bullet_3": "{decoration.get('ai_bullet_3', '')}",
  "source": "{decoration.get('source', '')}",
  "clean_url": "{decoration.get('clean_url', '')}"
}}

## OUTPUT FORMAT
Return the COMPLETE JSON object with only the bullet fields modified to include <b></b> tags.

## EXAMPLE
Input bullet: "Netflix launched a new AI-powered recommendation engine. The feature uses machine learning to predict viewing preferences."
Output bullet: "Netflix <b>launched a new AI-powered recommendation engine</b>. The feature uses machine learning to predict viewing preferences."

Return ONLY the JSON object. No code fences, no commentary."""

        # Get model/temperature from database
        prompt_meta = get_prompt_with_metadata('bold_formatter')
        model = prompt_meta.get('model', self.default_model) if prompt_meta else self.default_model
        temperature = prompt_meta.get('temperature', 0.3) if prompt_meta else 0.3

        response = self.client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=float(temperature),
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            result = json.loads(response.content[0].text)
            # Return the bolded decoration dict
            if isinstance(result, dict):
                return result
            else:
                logger.warning("Unexpected bold_formatter response format")
                return decoration
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse bold_formatter response")
            return decoration  # Return original if parsing fails

    def _parse_decoration_response(self, text: str) -> dict:
        """Fallback parser for decoration response

        Uses correct field names from n8n workflow HCbd2g852rkQgSqr:
        - ai_bullet_1, ai_bullet_2, ai_bullet_3 (NOT b1/b2/b3)
        - Valid label categories from the 18 options
        """
        import re

        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                # Normalize field names if old format is returned
                if 'b1' in parsed and 'ai_bullet_1' not in parsed:
                    parsed['ai_bullet_1'] = parsed.pop('b1', '')
                    parsed['ai_bullet_2'] = parsed.pop('b2', '')
                    parsed['ai_bullet_3'] = parsed.pop('b3', '')
                return parsed
            except json.JSONDecodeError:
                pass

        # Return empty structure with correct field names
        return {
            "ai_headline": "",
            "ai_dek": "",
            "ai_bullet_1": "",
            "ai_bullet_2": "",
            "ai_bullet_3": "",
            "label": "ENTERPRISE",  # Default to valid category from 18 options
            "image_prompt": "",
            "source": "",
            "clean_url": "",
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
