"""
TEMPORARY: Claude Prefilter Client for AI Editor 2.0 Workers
============================================================
Date: January 6, 2026
Reason: Gemini API quota exhausted (429 RESOURCE_EXHAUSTED)
Status: TEMPORARY - Revert to Gemini when quota restored

TODO(gemini-quota): Revert to GeminiClient when Gemini quota is restored
See docs/Gemini-Temporary-Swap-1-6-26.md for details

Uses Claude Sonnet 4.5 (claude-sonnet-4-5-20250929) as drop-in replacement.
Same interface as GeminiClient.prefilter_batch_slot_X() methods.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

import anthropic

from .prompts import get_prompt

logger = logging.getLogger(__name__)

# Log level for temporary swap visibility
TEMP_SWAP_NOTICE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║  TEMPORARY: Using Claude Sonnet 4.5 for pre-filter (Gemini quota exhausted)  ║
║  TODO(gemini-quota): Revert to GeminiClient when quota restored              ║
║  See: docs/Gemini-Temporary-Swap-1-6-26.md                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


class ClaudePrefilterClient:
    """
    TEMPORARY Claude API wrapper for pre-filtering.

    Drop-in replacement for GeminiClient's prefilter_batch_slot_X() methods.
    Uses Claude Sonnet 4.5 (200K context, 64K output).

    TODO(gemini-quota): Delete this file and revert to GeminiClient when Gemini quota restored.
    """

    def __init__(self):
        print(TEMP_SWAP_NOTICE, flush=True)
        logger.warning("[TEMPORARY] Using Claude Sonnet 4.5 for pre-filter (Gemini quota exhausted)")

        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-5-20250929"

        # Chunk size - Claude can handle more than Gemini, but keeping conservative
        self.chunk_size = 100

    def prefilter_batch_slot_1(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 1 Batch Pre-Filter: Jobs/Economy
        TEMPORARY: Using Claude instead of Gemini
        """
        return self._run_slot_prefilter(
            slot_num=1,
            slot_name="Jobs/Economy",
            articles=articles,
            yesterday_headlines=yesterday_headlines,
            criteria="""Review these candidates and identify ONLY stories about:
1. AI impact on JOBS (layoffs, hiring, workforce changes, labor market shifts)
2. AI impact on ECONOMY (GDP, productivity, economic shifts, market trends)
3. AI STOCK MARKET / VALUATIONS (market moves, IPOs, funding rounds, valuations)
4. BROAD AI IMPACT (societal, regulatory impact - NOT company-specific product launches)

IMPORTANT EXCLUSIONS:
- Do NOT include simple product launches or feature updates
- Do NOT include stories that are primarily about a single company's products
- Focus on BROAD impact stories that affect multiple companies or the industry"""
        )

    def prefilter_batch_slot_2(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 2 Batch Pre-Filter: Tier 1 / Insight
        TEMPORARY: Using Claude instead of Gemini
        """
        return self._run_slot_prefilter(
            slot_num=2,
            slot_name="Tier 1 / Insight",
            articles=articles,
            yesterday_headlines=yesterday_headlines,
            criteria="""Review these candidates and identify stories about:
1. TIER 1 AI COMPANIES: OpenAI, Google/DeepMind, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon
2. Major product launches, updates, or news from these Tier 1 companies
3. AI research papers, studies, or insight pieces from credible sources
4. Broad AI industry analysis or trends

IMPORTANT:
- Tier 1 company news belongs HERE, not in Slot 4 (Emerging Companies)
- Research/insight pieces should be from credible sources
- Product launches from Tier 1 companies go here"""
        )

    def prefilter_batch_slot_3(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 3 Batch Pre-Filter: Industry Impact
        TEMPORARY: Using Claude instead of Gemini
        """
        return self._run_slot_prefilter(
            slot_num=3,
            slot_name="Industry Impact",
            articles=articles,
            yesterday_headlines=yesterday_headlines,
            criteria="""Review these candidates and identify stories about AI's impact on NON-TECH INDUSTRIES:
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
- Focus on how AI is transforming traditional industries"""
        )

    def prefilter_batch_slot_4(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 4 Batch Pre-Filter: Emerging Companies
        TEMPORARY: Using Claude instead of Gemini
        """
        return self._run_slot_prefilter(
            slot_num=4,
            slot_name="Emerging Companies",
            articles=articles,
            yesterday_headlines=yesterday_headlines,
            criteria="""Review these candidates and identify stories about:
1. Smaller/emerging AI companies (NOT Tier 1 giants)
2. AI startup news: funding rounds, acquisitions, partnerships
3. New AI product launches from non-Tier-1 companies
4. Innovative AI tools and applications from emerging players

TIER 1 COMPANIES TO EXCLUDE (these go in Slot 2):
OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon

IMPORTANT EXCLUSIONS:
- Do NOT include Tier 1 company news (goes to Slot 2)
- Do NOT include industry-specific verticals (goes to Slot 3)
- Do NOT include human interest or consumer lifestyle stories (goes to Slot 5)"""
        )

    def prefilter_batch_slot_5(self, articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]:
        """
        Slot 5 Batch Pre-Filter: Consumer AI
        TEMPORARY: Using Claude instead of Gemini
        """
        return self._run_slot_prefilter(
            slot_num=5,
            slot_name="Consumer AI",
            articles=articles,
            yesterday_headlines=yesterday_headlines,
            criteria="""Review these candidates and identify stories about:
1. AI's impact on HUMANITY and SOCIETY (philosophical, ethical)
2. Consumer AI products (apps, tools for everyday people)
3. AI in ARTS, ENTERTAINMENT, and CREATIVITY
4. AI ethics and philosophical questions
5. Fun, quirky, surprising, or unusual uses of AI
6. "Nice to know" stories (not "need to know" business news)

This slot is for lighter, more human-interest stories that readers will enjoy."""
        )

    def _run_slot_prefilter(
        self,
        slot_num: int,
        slot_name: str,
        articles: List[Dict],
        yesterday_headlines: List[str],
        criteria: str
    ) -> List[Dict]:
        """
        Execute pre-filter for a specific slot using Claude.

        TEMPORARY: This uses Claude Sonnet 4.5 instead of Gemini.
        TODO(gemini-quota): Revert to GeminiClient when quota restored.
        """
        if not articles:
            return []

        print(f"[TEMPORARY Claude slot_{slot_num}] Using Claude Sonnet 4.5 (Gemini quota exhausted)", flush=True)
        logger.info(f"[TEMPORARY] Slot {slot_num} using Claude instead of Gemini")

        yesterday_text = "\n".join(f"- {h}" for h in yesterday_headlines) if yesterday_headlines else "None"

        # Try database prompt first
        prompt_template = get_prompt(f'slot_{slot_num}_prefilter')

        # Chunk articles for processing
        all_matches = []
        chunks = self._chunk_articles(articles, self.chunk_size)
        print(f"[TEMPORARY Claude slot_{slot_num}] Processing {len(articles)} articles in {len(chunks)} chunks...", flush=True)

        for i, chunk in enumerate(chunks):
            print(f"[TEMPORARY Claude slot_{slot_num}] Chunk {i+1}/{len(chunks)} ({len(chunk)} articles)...", flush=True)

            candidates_json = json.dumps(chunk, indent=2)

            # Build prompt
            if prompt_template:
                try:
                    prompt = prompt_template.format(
                        yesterday_headlines=yesterday_text,
                        candidates=candidates_json
                    )
                    logger.info(f"[TEMPORARY Claude slot_{slot_num}] Using prompt from database")
                except KeyError as e:
                    logger.warning(f"[TEMPORARY Claude slot_{slot_num}] Missing variable in database prompt: {e}, using fallback")
                    prompt_template = None

            if not prompt_template:
                prompt = f"""You are a pre-filter for an AI newsletter's Slot {slot_num}: {slot_name}.

{criteria}

YESTERDAY'S HEADLINES (avoid similar topics):
{yesterday_text}

CANDIDATES:
{candidates_json}

Return ONLY valid JSON with matching story IDs:
{{"matches": [{{"story_id": "recXXX", "headline": "headline text"}}]}}

If no stories match, return: {{"matches": []}}"""

            matches = self._execute_claude_prefilter(prompt, f"slot_{slot_num}_chunk_{i+1}")
            all_matches.extend(matches)

        return all_matches

    def _execute_claude_prefilter(self, prompt: str, slot_name: str, retry_count: int = 0) -> List[Dict]:
        """
        Execute a batch pre-filter call to Claude with retry logic.

        TEMPORARY: Using Claude instead of Gemini.
        """
        import time

        print(f"[TEMPORARY Claude {slot_name}] Calling Claude API (attempt {retry_count + 1}/3)...", flush=True)
        print(f"[TEMPORARY Claude {slot_name}] Prompt length: {len(prompt)} chars", flush=True)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,  # Claude Sonnet 4.5 supports up to 64K output
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = response.content[0].text.strip()
            response_len = len(response_text)
            print(f"[TEMPORARY Claude {slot_name}] Response received, length: {response_len} chars", flush=True)
            print(f"[TEMPORARY Claude {slot_name}] Response preview: {response_text[:200]}...", flush=True)

            # Parse JSON response
            result = json.loads(response_text)
            matches = result.get('matches', [])

            print(f"[TEMPORARY Claude {slot_name}] Found {len(matches)} matches", flush=True)
            logger.info(f"[TEMPORARY Claude {slot_name}] Found {len(matches)} matches")
            return matches

        except json.JSONDecodeError as e:
            response_text = response.content[0].text if hasattr(response, 'content') else ''
            print(f"[TEMPORARY Claude {slot_name}] JSON parse error: {e}", flush=True)
            logger.error(f"[TEMPORARY Claude {slot_name}] JSON error: {e}")

            # Try to extract matches from malformed response
            partial_matches = self._parse_batch_response(response_text)
            if partial_matches:
                print(f"[TEMPORARY Claude {slot_name}] Recovered {len(partial_matches)} matches from response", flush=True)
                return partial_matches

            # Retry with backoff
            if retry_count < 2:
                wait_time = (retry_count + 1) * 2
                print(f"[TEMPORARY Claude {slot_name}] Retrying in {wait_time}s...", flush=True)
                time.sleep(wait_time)
                return self._execute_claude_prefilter(prompt, slot_name, retry_count + 1)
            return []

        except anthropic.RateLimitError as e:
            print(f"[TEMPORARY Claude {slot_name}] Rate limit error: {e}", flush=True)
            logger.error(f"[TEMPORARY Claude {slot_name}] Rate limit: {e}")
            if retry_count < 2:
                wait_time = (retry_count + 1) * 5  # Longer wait for rate limits
                print(f"[TEMPORARY Claude {slot_name}] Retrying in {wait_time}s...", flush=True)
                time.sleep(wait_time)
                return self._execute_claude_prefilter(prompt, slot_name, retry_count + 1)
            return []

        except Exception as e:
            print(f"[TEMPORARY Claude {slot_name}] Error: {type(e).__name__}: {e}", flush=True)
            logger.error(f"[TEMPORARY Claude {slot_name}] Error: {e}")
            if retry_count < 2:
                wait_time = (retry_count + 1) * 2
                print(f"[TEMPORARY Claude {slot_name}] Retrying in {wait_time}s...", flush=True)
                time.sleep(wait_time)
                return self._execute_claude_prefilter(prompt, slot_name, retry_count + 1)
            return []

    def _chunk_articles(self, articles: List[Dict], chunk_size: int = 100) -> List[List[Dict]]:
        """Split articles into smaller chunks for processing."""
        return [articles[i:i + chunk_size] for i in range(0, len(articles), chunk_size)]

    def _parse_batch_response(self, text: str) -> List[Dict]:
        """
        Robust fallback parser for responses that aren't clean JSON.
        Same logic as GeminiClient._parse_batch_response().
        """
        import re

        matches = []

        # First, try to parse complete JSON
        json_match = re.search(r'\{[\s\S]*"matches"\s*:\s*\[[\s\S]*\]\s*\}', text)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result.get('matches', [])
            except json.JSONDecodeError:
                pass

        # Extract individual match objects
        match_pattern = r'\{\s*"story_id"\s*:\s*"([^"]+)"\s*,\s*"headline"\s*:\s*"([^"]+)"\s*\}'
        individual_matches = re.findall(match_pattern, text)

        for story_id, headline in individual_matches:
            matches.append({
                "story_id": story_id,
                "headline": headline
            })

        if matches:
            logger.info(f"[TEMPORARY] Recovered {len(matches)} matches from response using regex extraction")

        return matches
