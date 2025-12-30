"""
Gemini API Client for AI Editor 2.0 Workers
Used for: Pre-filtering (Step 1), Content cleaning (Step 3)

Prompts are loaded from PostgreSQL database via utils.prompts

n8n Workflow Architecture (IMPLEMENTED):
- 5 SEPARATE Gemini calls, one per slot, with slot-specific prompts
- Each slot gets ALL eligible articles in a BATCH for comparison
- Response format: {matches: [{story_id, headline}]}
- Matches n8n workflow exactly
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Set
import google.generativeai as genai

from .prompts import get_prompt, get_prompt_with_metadata

logger = logging.getLogger(__name__)

# Slot-specific criteria matching n8n workflow prompts
SLOT_CRITERIA = {
    1: {
        "name": "Jobs/Economy",
        "description": "AI impact on JOBS (layoffs, hiring, workforce changes), ECONOMY (GDP, productivity), STOCK MARKET (market moves, IPOs, funding), BROAD AI IMPACT (societal, regulatory - not product launches)",
        "tier1_only": False,
        "max_hours": 24,
    },
    2: {
        "name": "Tier 1 / Insight",
        "description": "Tier 1 companies: OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon. Also: broad economic themes, AI research/insight pieces (studies, reports, analysis)",
        "tier1_only": True,
        "max_hours": 48,
    },
    3: {
        "name": "Industry Impact",
        "description": "NON-TECH industries: Healthcare, Government, Education, Legal, Accounting, Retail, Security, Transportation, Manufacturing, Real Estate, Agriculture, Energy. NOT: tech companies, startups, human interest",
        "tier1_only": False,
        "max_hours": 168,  # 7 days
    },
    4: {
        "name": "Emerging Companies",
        "description": "Smaller/emerging AI companies (NOT Tier 1 giants). Product launches, fundraising, acquisitions, new AI tools. NOT: Tier 1 companies, industry-specific, human interest",
        "tier1_only": False,
        "max_hours": 48,
    },
    5: {
        "name": "Consumer AI",
        "description": "AI's impact on humanity and society. Consumer AI products, arts, entertainment, creativity. AI ethics, philosophical questions. Fun, quirky, surprising uses. 'Nice to know' not 'need to know'",
        "tier1_only": False,
        "max_hours": 168,  # 7 days
    },
}


class GeminiClient:
    """Gemini API wrapper for AI Editor 2.0"""

    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=self.api_key)

        # Model for pre-filtering (fast, cheap)
        # CRITICAL: Use gemini-3-flash-preview - NOT gemini-2.0-flash
        self.flash_model = genai.GenerativeModel('gemini-3-flash-preview')

    def prefilter_story(self, story_data: dict, yesterday_headlines: list, source_score: int) -> dict:
        """
        Step 1, Node 13: Gemini pre-filter for slot eligibility

        Args:
            story_data: {
                storyId, pivotId, headline, dek, topic, source, hoursAgo, coreUrl,
                bullet1, bullet2, bullet3,  # For summary building (n8n Gap #3)
                eligibleSlots  # Pre-calculated from freshness (n8n Gap #4)
            }
            yesterday_headlines: List of 5 headlines from yesterday's issue
            source_score: Credibility score 1-5

        Returns:
            {eligible_slots: [1,2,3], primary_slot: 2, reasoning: "..."}

        Note: Gemini should only evaluate slots in eligibleSlots (freshness pre-calc)
        """
        # Build summary from bullets if available (n8n Gap #3)
        summary_parts = [
            story_data.get('dek', ''),
            story_data.get('bullet1', ''),
            story_data.get('bullet2', ''),
            story_data.get('bullet3', '')
        ]
        story_data['summary'] = ' | '.join(p for p in summary_parts if p)

        prompt = self._build_prefilter_prompt(story_data, yesterday_headlines, source_score)

        try:
            response = self.flash_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=256,
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from response
            return self._parse_prefilter_response(response.text)
        except Exception as e:
            logger.error(f"Gemini prefilter error for {story_data.get('storyId')}: {e}")
            return {
                "eligible_slots": [],
                "primary_slot": None,
                "reasoning": f"Error: {str(e)}"
            }

    def _build_prefilter_prompt(self, story: dict, yesterday_headlines: list, source_score: int) -> str:
        """
        Build the pre-filter prompt from database with Python variable substitution.

        Database prompts use {variable} syntax for Python .format() substitution.

        Updated to use SLOT_CRITERIA matching n8n workflow (Gap #1)
        """
        # Get pre-calculated eligible slots based on freshness
        freshness_eligible = story.get('eligibleSlots', [1, 2, 3, 4, 5])

        # Try to load prompt from database
        prompt_template = get_prompt('prefilter_combined')  # Combined prompt for all slots

        if prompt_template:
            try:
                # Substitute variables using Python .format()
                prompt = prompt_template.format(
                    headline=story.get('headline', ''),
                    summary=story.get('summary', story.get('dek', '')),
                    content=story.get('dek', ''),
                    date_published=story.get('date_published', ''),
                    hours_ago=story.get('hoursAgo', 0),
                    source=story.get('source', ''),
                    credibility=source_score,
                    topic=story.get('topic', ''),
                    eligible_slots=freshness_eligible,
                    yesterday_headlines='\n'.join(f"- {h}" for h in yesterday_headlines)
                )
                return prompt
            except KeyError as e:
                logger.warning(f"Missing variable in prefilter prompt: {e}, using fallback")

        # Fallback to hardcoded prompt with slot-specific criteria
        # Build slot criteria section dynamically from SLOT_CRITERIA
        slot_criteria_text = ""
        for slot_num in freshness_eligible:
            criteria = SLOT_CRITERIA.get(slot_num, {})
            slot_criteria_text += f"\n{slot_num}. {criteria.get('name', 'Unknown')}: {criteria.get('description', '')}"

        logger.warning("Prefilter prompt not found in database, using comprehensive fallback")
        return f"""You are an AI news editor for the Pivot 5 AI newsletter. Analyze this article and determine which newsletter slots it's eligible for.

ARTICLE:
Headline: {story.get('headline', '')}
Summary: {story.get('summary', story.get('dek', ''))}
Topic: {story.get('topic', '')}
Hours Since Published: {story.get('hoursAgo', 0)}
Source: {story.get('source', '')}
Source Credibility: {source_score}/5

ELIGIBLE SLOTS (based on freshness):
Only evaluate for these slots: {freshness_eligible}
{slot_criteria_text}

CRITICAL EXCLUSION RULES:
- Stories about Tier 1 companies (OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon) should NOT go in Slot 4 (Emerging Companies)
- Stories about tech companies should NOT go in Slot 3 (Industry Impact)
- Product launches from Tier 1 companies go in Slot 2, not Slot 4
- Low credibility sources (score < 3) should be limited to Slot 5 only

YESTERDAY'S HEADLINES (avoid similar topics):
{chr(10).join(f"- {h}" for h in yesterday_headlines) if yesterday_headlines else "None provided"}

INSTRUCTIONS:
1. Only return slots that are in the eligible list: {freshness_eligible}
2. Choose the BEST primary slot for this article
3. An article can be eligible for multiple slots if it fits multiple criteria

Return JSON only:
{{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 1,
  "reasoning": "Brief explanation of why this article fits these slots"
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

    # =========================================================================
    # BATCH PROCESSING METHODS (Matches n8n Workflow Exactly)
    # =========================================================================

    def prefilter_batch_slot_1(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 1 Batch Pre-Filter: Jobs/Economy

        n8n Workflow: Node 13 - Gemini Slot 1 Pre-Filter

        Args:
            articles: List of article dicts with story_id, headline, summary, source_score, freshness_hours
            yesterday_headlines: Headlines from yesterday's issue for diversity

        Returns:
            List of matching articles: [{story_id, headline}]

        Uses chunking for large batches to prevent Gemini response truncation.
        """
        if not articles:
            return []

        yesterday_text = "\n".join(f"- {h}" for h in yesterday_headlines) if yesterday_headlines else "None"

        # Try to load prompt template from database
        prompt_template = get_prompt('slot_1_prefilter')
        use_db_prompt = False

        if prompt_template:
            use_db_prompt = True
            logger.info("[Gemini slot_1] Using prompt from database")

        # Chunk large batches to prevent Gemini response truncation
        all_matches = []
        chunks = self._chunk_articles(articles, chunk_size=15)

        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                logger.info(f"[Gemini slot_1] Processing chunk {i+1}/{len(chunks)} ({len(chunk)} articles)")

            candidates_json = json.dumps(chunk, indent=2)

            if use_db_prompt:
                try:
                    prompt = prompt_template.format(
                        yesterday_headlines=yesterday_text,
                        candidates=candidates_json
                    )
                except KeyError as e:
                    logger.warning(f"[Gemini slot_1] Missing variable in database prompt: {e}, using fallback")
                    use_db_prompt = False

            if not use_db_prompt:
                prompt = f"""You are a pre-filter for an AI newsletter's LEAD STORY slot (Slot 1: Jobs/Economy).

Review these candidates and identify ONLY stories about:
1. AI impact on JOBS (layoffs, hiring, workforce changes, labor market shifts)
2. AI impact on ECONOMY (GDP, productivity, economic shifts, market trends)
3. AI STOCK MARKET / VALUATIONS (market moves, IPOs, funding rounds, valuations)
4. BROAD AI IMPACT (societal, regulatory impact - NOT company-specific product launches)

IMPORTANT EXCLUSIONS:
- Do NOT include simple product launches or feature updates
- Do NOT include stories that are primarily about a single company's products
- Focus on BROAD impact stories that affect multiple companies or the industry

YESTERDAY'S HEADLINES (avoid similar topics):
{yesterday_text}

CANDIDATES:
{candidates_json}

Return ONLY valid JSON with matching story IDs:
{{"matches": [{{"story_id": "recXXX", "headline": "headline text"}}]}}

If no stories match, return: {{"matches": []}}"""

            matches = self._execute_batch_prefilter(prompt, f"slot_1_chunk_{i+1}")
            all_matches.extend(matches)

        return all_matches

    def prefilter_batch_slot_2(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 2 Batch Pre-Filter: Tier 1 / Insight

        n8n Workflow: Node 17 - Gemini Slot 2 Pre-Filter

        Uses chunking for large batches to prevent Gemini response truncation.
        """
        if not articles:
            return []

        yesterday_text = "\n".join(f"- {h}" for h in yesterday_headlines) if yesterday_headlines else "None"

        # Try to load prompt template from database
        prompt_template = get_prompt('slot_2_prefilter')
        use_db_prompt = False

        if prompt_template:
            use_db_prompt = True
            logger.info("[Gemini slot_2] Using prompt from database")

        # Chunk large batches to prevent Gemini response truncation
        all_matches = []
        chunks = self._chunk_articles(articles, chunk_size=15)

        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                logger.info(f"[Gemini slot_2] Processing chunk {i+1}/{len(chunks)} ({len(chunk)} articles)")

            candidates_json = json.dumps(chunk, indent=2)

            if use_db_prompt:
                try:
                    prompt = prompt_template.format(
                        yesterday_headlines=yesterday_text,
                        candidates=candidates_json
                    )
                except KeyError as e:
                    logger.warning(f"[Gemini slot_2] Missing variable in database prompt: {e}, using fallback")
                    use_db_prompt = False

            if not use_db_prompt:
                prompt = f"""You are a pre-filter for an AI newsletter's Slot 2: Tier 1 Companies / Insight.

Review these candidates and identify stories about:
1. TIER 1 AI COMPANIES: OpenAI, Google/DeepMind, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon
2. Major product launches, updates, or news from these Tier 1 companies
3. AI research papers, studies, or insight pieces from credible sources
4. Broad AI industry analysis or trends

IMPORTANT:
- Tier 1 company news belongs HERE, not in Slot 4 (Emerging Companies)
- Research/insight pieces should be from credible sources
- Product launches from Tier 1 companies go here

YESTERDAY'S HEADLINES (avoid similar topics):
{yesterday_text}

CANDIDATES:
{candidates_json}

Return ONLY valid JSON with matching story IDs:
{{"matches": [{{"story_id": "recXXX", "headline": "headline text"}}]}}

If no stories match, return: {{"matches": []}}"""

            matches = self._execute_batch_prefilter(prompt, f"slot_2_chunk_{i+1}")
            all_matches.extend(matches)

        return all_matches

    def prefilter_batch_slot_3(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 3 Batch Pre-Filter: Industry Impact

        n8n Workflow: Node 21 - Gemini Slot 3 Pre-Filter

        Uses chunking for large batches to prevent Gemini response truncation.
        """
        if not articles:
            return []

        yesterday_text = "\n".join(f"- {h}" for h in yesterday_headlines) if yesterday_headlines else "None"

        # Try to load prompt template from database
        prompt_template = get_prompt('slot_3_prefilter')
        use_db_prompt = False

        if prompt_template:
            use_db_prompt = True
            logger.info("[Gemini slot_3] Using prompt from database")

        # Chunk large batches to prevent Gemini response truncation
        all_matches = []
        chunks = self._chunk_articles(articles, chunk_size=15)

        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                logger.info(f"[Gemini slot_3] Processing chunk {i+1}/{len(chunks)} ({len(chunk)} articles)")

            candidates_json = json.dumps(chunk, indent=2)

            if use_db_prompt:
                try:
                    prompt = prompt_template.format(
                        yesterday_headlines=yesterday_text,
                        candidates=candidates_json
                    )
                except KeyError as e:
                    logger.warning(f"[Gemini slot_3] Missing variable in database prompt: {e}, using fallback")
                    use_db_prompt = False

            if not use_db_prompt:
                prompt = f"""You are a pre-filter for an AI newsletter's Slot 3: Industry Impact.

Review these candidates and identify stories about AI's impact on NON-TECH INDUSTRIES:
- Healthcare / Medical
- Government / Public Sector
- Education
- Legal / Law
- Accounting / Finance (traditional, not fintech)
- Retail / E-commerce
- Security / Defense
- Transportation / Logistics
- Manufacturing
- Real Estate
- Agriculture
- Energy / Utilities

IMPORTANT EXCLUSIONS:
- Do NOT include stories primarily about TECH companies or startups
- Do NOT include human interest or consumer-focused stories
- Focus on how AI is transforming traditional industries

YESTERDAY'S HEADLINES (avoid similar topics):
{yesterday_text}

CANDIDATES:
{candidates_json}

Return ONLY valid JSON with matching story IDs:
{{"matches": [{{"story_id": "recXXX", "headline": "headline text"}}]}}

If no stories match, return: {{"matches": []}}"""

            matches = self._execute_batch_prefilter(prompt, f"slot_3_chunk_{i+1}")
            all_matches.extend(matches)

        return all_matches

    def prefilter_batch_slot_4(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 4 Batch Pre-Filter: Emerging Companies

        n8n Workflow: Node 25 - Gemini Slot 4 Pre-Filter

        Uses chunking for large batches to prevent Gemini response truncation.
        """
        if not articles:
            return []

        yesterday_text = "\n".join(f"- {h}" for h in yesterday_headlines) if yesterday_headlines else "None"

        # Try to load prompt template from database
        prompt_template = get_prompt('slot_4_prefilter')
        use_db_prompt = False

        if prompt_template:
            use_db_prompt = True
            logger.info("[Gemini slot_4] Using prompt from database")

        # Chunk large batches to prevent Gemini response truncation
        all_matches = []
        chunks = self._chunk_articles(articles, chunk_size=15)

        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                logger.info(f"[Gemini slot_4] Processing chunk {i+1}/{len(chunks)} ({len(chunk)} articles)")

            candidates_json = json.dumps(chunk, indent=2)

            if use_db_prompt:
                try:
                    prompt = prompt_template.format(
                        yesterday_headlines=yesterday_text,
                        candidates=candidates_json
                    )
                except KeyError as e:
                    logger.warning(f"[Gemini slot_4] Missing variable in database prompt: {e}, using fallback")
                    use_db_prompt = False

            if not use_db_prompt:
                prompt = f"""You are a pre-filter for an AI newsletter's Slot 4: Emerging Companies.

Review these candidates and identify stories about:
1. Smaller/emerging AI companies (NOT Tier 1 giants)
2. AI startup news: funding rounds, acquisitions, partnerships
3. New AI product launches from non-Tier-1 companies
4. Innovative AI tools and applications from emerging players

TIER 1 COMPANIES TO EXCLUDE (these go in Slot 2):
OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon

IMPORTANT EXCLUSIONS:
- Do NOT include Tier 1 company news (goes to Slot 2)
- Do NOT include industry-specific verticals (goes to Slot 3)
- Do NOT include human interest or consumer lifestyle stories (goes to Slot 5)

YESTERDAY'S HEADLINES (avoid similar topics):
{yesterday_text}

CANDIDATES:
{candidates_json}

Return ONLY valid JSON with matching story IDs:
{{"matches": [{{"story_id": "recXXX", "headline": "headline text"}}]}}

If no stories match, return: {{"matches": []}}"""

            matches = self._execute_batch_prefilter(prompt, f"slot_4_chunk_{i+1}")
            all_matches.extend(matches)

        return all_matches

    def prefilter_batch_slot_5(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 5 Batch Pre-Filter: Consumer AI

        n8n Workflow: Node 29 - Gemini Slot 5 Pre-Filter

        Uses chunking for large batches to prevent Gemini response truncation.
        """
        if not articles:
            return []

        yesterday_text = "\n".join(f"- {h}" for h in yesterday_headlines) if yesterday_headlines else "None"

        # Try to load prompt template from database
        prompt_template = get_prompt('slot_5_prefilter')
        use_db_prompt = False

        if prompt_template:
            use_db_prompt = True
            logger.info("[Gemini slot_5] Using prompt from database")

        # Chunk large batches to prevent Gemini response truncation
        all_matches = []
        chunks = self._chunk_articles(articles, chunk_size=15)

        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                logger.info(f"[Gemini slot_5] Processing chunk {i+1}/{len(chunks)} ({len(chunk)} articles)")

            candidates_json = json.dumps(chunk, indent=2)

            if use_db_prompt:
                try:
                    prompt = prompt_template.format(
                        yesterday_headlines=yesterday_text,
                        candidates=candidates_json
                    )
                except KeyError as e:
                    logger.warning(f"[Gemini slot_5] Missing variable in database prompt: {e}, using fallback")
                    use_db_prompt = False

            if not use_db_prompt:
                prompt = f"""You are a pre-filter for an AI newsletter's Slot 5: Consumer AI.

Review these candidates and identify stories about:
1. AI's impact on HUMANITY and SOCIETY (philosophical, ethical)
2. Consumer AI products (apps, tools for everyday people)
3. AI in ARTS, ENTERTAINMENT, and CREATIVITY
4. AI ethics and philosophical questions
5. Fun, quirky, surprising, or unusual uses of AI
6. "Nice to know" stories (not "need to know" business news)

This slot is for lighter, more human-interest stories that readers will enjoy.

YESTERDAY'S HEADLINES (avoid similar topics):
{yesterday_text}

CANDIDATES:
{candidates_json}

Return ONLY valid JSON with matching story IDs:
{{"matches": [{{"story_id": "recXXX", "headline": "headline text"}}]}}

If no stories match, return: {{"matches": []}}"""

            matches = self._execute_batch_prefilter(prompt, f"slot_5_chunk_{i+1}")
            all_matches.extend(matches)

        return all_matches

    def _execute_batch_prefilter(self, prompt: str, slot_name: str, retry_count: int = 0) -> List[Dict]:
        """
        Execute a batch pre-filter call to Gemini with retry logic.

        Args:
            prompt: The complete prompt with articles embedded
            slot_name: For logging purposes (e.g., "slot_1")
            retry_count: Current retry attempt (max 2 retries)

        Returns:
            List of matching articles: [{story_id, headline}]
        """
        import time

        try:
            response = self.flash_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=8192,  # Increased from 4096 for large batches
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text)
            matches = result.get('matches', [])
            logger.info(f"[Gemini {slot_name}] Found {len(matches)} matches")
            return matches

        except json.JSONDecodeError as e:
            logger.error(f"[Gemini {slot_name}] JSON parse error: {e}")
            # Try to extract partial matches from truncated response
            partial_matches = self._parse_batch_response(response.text)
            if partial_matches:
                logger.info(f"[Gemini {slot_name}] Recovered {len(partial_matches)} matches from partial response")
                return partial_matches
            # Retry with exponential backoff if we got nothing
            if retry_count < 2:
                wait_time = (retry_count + 1) * 2
                logger.info(f"[Gemini {slot_name}] Retrying in {wait_time}s (attempt {retry_count + 2}/3)")
                time.sleep(wait_time)
                return self._execute_batch_prefilter(prompt, slot_name, retry_count + 1)
            return []
        except Exception as e:
            logger.error(f"[Gemini {slot_name}] Error: {e}")
            # Retry on generic errors too
            if retry_count < 2:
                time.sleep((retry_count + 1) * 2)
                return self._execute_batch_prefilter(prompt, slot_name, retry_count + 1)
            return []

    def _chunk_articles(self, articles: List[Dict], chunk_size: int = 15) -> List[List[Dict]]:
        """Split articles into smaller chunks for reliable Gemini processing."""
        return [articles[i:i + chunk_size] for i in range(0, len(articles), chunk_size)]

    def _parse_batch_response(self, text: str) -> List[Dict]:
        """Fallback parser for batch responses that aren't clean JSON."""
        import re

        # Try to find JSON object in response
        json_match = re.search(r'\{[\s\S]*"matches"[\s\S]*\}', text)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result.get('matches', [])
            except json.JSONDecodeError:
                pass

        return []
