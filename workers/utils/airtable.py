"""
Airtable API Client for AI Editor 2.0 Workers
Handles all Airtable read/write operations
"""

import os
import logging
from typing import List, Optional, Dict, Any
from pyairtable import Api, Table

logger = logging.getLogger(__name__)


class AirtableClient:
    """Airtable API wrapper for AI Editor 2.0"""

    def __init__(self):
        self.api_key = os.environ.get('AIRTABLE_API_KEY')
        if not self.api_key:
            raise ValueError("AIRTABLE_API_KEY environment variable is required")

        self.api = Api(self.api_key)

        # Base IDs
        self.pivot_media_base_id = os.environ.get('AIRTABLE_BASE_ID', 'appwSozYTkrsQWUXB')
        self.ai_editor_base_id = os.environ.get('AI_EDITOR_BASE_ID', 'appglKSJZxmA9iHpl')
        self.p5_social_base_id = os.environ.get('P5_SOCIAL_POSTS_BASE_ID', 'appRUgK44hQnXH1PM')

        # Table IDs - Pivot Media Master
        self.articles_table_id = os.environ.get('AIRTABLE_ARTICLES_TABLE', 'tblGumae8KDpsrWvh')
        self.newsletter_stories_table_id = os.environ.get('AIRTABLE_NEWSLETTER_STORIES_TABLE', 'tblY78ziWp5yhiGXp')
        self.newsletter_issues_table_id = os.environ.get('AIRTABLE_NEWSLETTER_ISSUES_TABLE', 'tbl7mcCCGbjEfli25')
        self.newsletter_issues_archive_table_id = os.environ.get('AIRTABLE_NEWSLETTER_ISSUES_ARCHIVE_TABLE', 'tblHo0xNj8nbzMHNI')

        # Table IDs - AI Editor 2.0
        self.prefilter_log_table_id = os.environ.get('AI_EDITOR_PREFILTER_LOG_TABLE', 'tbl72YMsm9iRHj3sp')
        self.selected_slots_table_id = os.environ.get('AI_EDITOR_SELECTED_SLOTS_TABLE', 'tblzt2z7r512Kto3O')
        self.decoration_table_id = os.environ.get('AI_EDITOR_DECORATION_TABLE', 'tbla16LJCf5Z6cRn3')
        # NOTE: source_scores_table_id removed 1/1/26 - credibility now in system prompts
        self.queued_stories_table_id = os.environ.get('AI_EDITOR_QUEUED_STORIES_TABLE', 'tblkVBP5mKq3sBpkv')
        self.newsletter_selects_table_id = os.environ.get('AIRTABLE_NEWSLETTER_SELECTS_TABLE', 'tblKhICCdWnyuqgry')

        # Table IDs - Step 4 HTML Compile & Send (AI Editor 2.0 base)
        # Added 1/2/26 for n8n migration
        self.newsletter_issues_final_table_id = os.environ.get('AI_EDITOR_NEWSLETTER_ISSUES_FINAL_TABLE', 'tblPBfWZzRdLuiqYr')
        self.newsletter_issues_archive_ai_table_id = os.environ.get('AI_EDITOR_NEWSLETTER_ISSUES_ARCHIVE_TABLE', 'tblB7j5qGcTxyXmfa')

        # Table IDs - P5 Social Posts
        self.p5_social_posts_table_id = os.environ.get('P5_SOCIAL_POSTS_TABLE', 'tbllJMN2QBPJoG3jA')

        # Signal Newsletter Base (SEPARATE from AI Editor 2.0)
        # Signal uses its own Airtable base for slots and stories
        self.signal_base_id = os.environ.get('SIGNAL_BASE_ID', 'appWGkUBuyrzmFnFM')

        # Table IDs - Signal Newsletter
        self.signal_selected_slots_table_id = os.environ.get('SIGNAL_SELECTED_SLOTS_TABLE', 'tblNxfdFYRxXtBBO2')
        self.signal_issue_stories_table_id = os.environ.get('SIGNAL_ISSUE_STORIES_TABLE', 'tbltUl5QYSBoWbnbD')

    def _get_table(self, base_id: str, table_id: str) -> Table:
        """Get a table instance"""
        return self.api.table(base_id, table_id)

    # =========================================================================
    # PIVOT MEDIA MASTER BASE
    # =========================================================================

    def get_fresh_stories(self, days: int = 7, max_records: Optional[int] = None) -> List[dict]:
        """
        Step 1, Node 2: Get fresh stories from Newsletter Stories table
        Filter: Last N days with ai_headline populated

        Updated to include all fields needed by n8n workflow (Gap #3):
        - ai_bullet_1, ai_bullet_2, ai_bullet_3 for summary building
        - core_url, image_url for media
        - fit_score, sentiment, tags for filtering

        NOTE: max_records defaults to None (no limit) to match n8n behavior.
        The n8n workflow pulls ALL eligible stories for evaluation.
        """
        table = self._get_table(self.pivot_media_base_id, self.newsletter_stories_table_id)

        # Updated 12/26/25: Include all 3 newsletters to match n8n workflow
        filter_formula = f"AND(IS_AFTER({{date_og_published}}, DATEADD(TODAY(), -{days}, 'days')), {{ai_headline}}!='', OR({{newsletter}}='pivot_ai', {{newsletter}}='pivot_build', {{newsletter}}='pivot_invest'))"

        # All fields needed by n8n workflow
        # Note: 'headline' field does not exist in this table - only 'ai_headline'
        fields = [
            'storyID', 'pivotId', 'ai_headline', 'ai_dek',
            'ai_bullet_1', 'ai_bullet_2', 'ai_bullet_3',  # For summary building
            'date_og_published', 'newsletter', 'topic',
            'core_url', 'image_url',  # Media fields
            'fit_score', 'sentiment', 'tags',  # Filtering fields
        ]

        # Build query kwargs - only include max_records if specified
        query_kwargs = {
            'formula': filter_formula,
            'sort': ['-date_og_published'],
            'fields': fields
        }
        if max_records is not None:
            query_kwargs['max_records'] = max_records

        records = table.all(**query_kwargs)

        return records

    def get_article_by_pivot_id(self, pivot_id: str) -> Optional[dict]:
        """
        Lookup article details by pivotId from Newsletter Selects table.

        FIXED 1/1/26: Was using wrong base (Pivot Media Master) and wrong table (Articles).
        Now uses AI Editor 2.0 base and Newsletter Selects table.

        Returns fields compatible with decoration.py:
        - pivot_id (mapped to pivot_Id for backwards compat)
        - source_name (mapped to source_id for backwards compat)
        - core_url (mapped to original_url for backwards compat)
        - raw (mapped to markdown for backwards compat)
        """
        table = self._get_table(self.ai_editor_base_id, self.newsletter_selects_table_id)

        records = table.all(
            formula=f"{{pivot_id}}='{pivot_id}'",  # lowercase pivot_id in Newsletter Selects
            max_records=1,
            fields=['pivot_id', 'source_name', 'core_url', 'raw', 'headline']
        )

        if not records:
            return None

        # Map Newsletter Selects fields to expected field names for backwards compatibility
        record = records[0]
        original_fields = record.get('fields', {})

        # Return record with mapped field names
        return {
            'id': record['id'],
            'fields': {
                'pivot_Id': original_fields.get('pivot_id', ''),  # Map to capital I for compat
                'source_id': original_fields.get('source_name', ''),  # Map source_name -> source_id
                'original_url': original_fields.get('core_url', ''),  # Map core_url -> original_url
                'markdown': original_fields.get('raw', ''),  # Map raw -> markdown
                'headline': original_fields.get('headline', ''),
            }
        }

    def get_articles_batch(self, pivot_ids: List[str]) -> Dict[str, dict]:
        """
        Batch lookup articles by pivotIds from Newsletter Selects table.
        Returns: dict mapping pivotId -> article record

        FIXED 1/1/26: Was using wrong base (Pivot Media Master) and wrong table (Articles).
        Now uses AI Editor 2.0 base and Newsletter Selects table.
        """
        if not pivot_ids:
            return {}

        table = self._get_table(self.ai_editor_base_id, self.newsletter_selects_table_id)

        # Build OR formula for batch lookup (lowercase pivot_id in Newsletter Selects)
        conditions = [f"{{pivot_id}}='{pid}'" for pid in pivot_ids]
        filter_formula = f"OR({','.join(conditions)})"

        records = table.all(
            formula=filter_formula,
            fields=['pivot_id', 'source_name', 'core_url', 'raw', 'headline']
        )

        # Map fields for backwards compatibility
        result = {}
        for r in records:
            original_fields = r.get('fields', {})
            pivot_id_value = original_fields.get('pivot_id', '')
            result[pivot_id_value] = {
                'id': r['id'],
                'fields': {
                    'pivot_Id': pivot_id_value,
                    'source_id': original_fields.get('source_name', ''),
                    'original_url': original_fields.get('core_url', ''),
                    'core_url': original_fields.get('core_url', ''),
                    'markdown': original_fields.get('raw', ''),
                    'headline': original_fields.get('headline', ''),
                }
            }
        return result

    def write_newsletter_issue(self, issue_data: dict) -> str:
        """
        Step 4: Write compiled newsletter issue
        Returns: record ID
        """
        table = self._get_table(self.pivot_media_base_id, self.newsletter_issues_table_id)
        record = table.create(issue_data)
        return record['id']

    def update_newsletter_issue(self, record_id: str, fields: dict) -> dict:
        """Update a newsletter issue record"""
        table = self._get_table(self.pivot_media_base_id, self.newsletter_issues_table_id)
        return table.update(record_id, fields)

    def archive_newsletter_issue(self, archive_data: dict) -> str:
        """
        Step 4: Archive sent newsletter issue
        Returns: record ID
        """
        table = self._get_table(self.pivot_media_base_id, self.newsletter_issues_archive_table_id)
        record = table.create(archive_data)
        return record['id']

    # =========================================================================
    # AI EDITOR 2.0 BASE
    # =========================================================================

    def get_newsletter_selects(self, since_date: str = None) -> List[Dict[str, Any]]:
        """
        Get newsletter selects from AI Editor 2.0 base.

        This is the new data source for pre-filter agents, replacing Newsletter Stories.
        Fields are transformed to maintain compatibility with existing prefilter code.

        Added 12/31/25: Migrated from Newsletter Stories to Newsletter Selects table.
        """
        table = self._get_table(self.ai_editor_base_id, self.newsletter_selects_table_id)

        formula = None
        if since_date:
            # Changed 1/8/26: Use date_ai_process instead of date_og_published
            # This catches all newly AI-processed articles regardless of original publish date
            # Slot eligibility still uses date_og_published for freshness rules
            formula = f"IS_AFTER({{date_ai_process}}, '{since_date}')"

        records = table.all(formula=formula)

        # Transform fields to match expected format for prefilter agents
        # IMPORTANT: Return format must match get_fresh_stories() -> {id, fields: {...}}
        transformed = []
        for r in records:
            original_fields = r['fields']
            raw_content = original_fields.get('raw', '')

            # Extract summary from raw content (first ~300 chars, break at sentence)
            summary = self._extract_summary(raw_content, max_length=300)

            # Build fields dict that matches Newsletter Stories format
            transformed_fields = {
                'storyID': r['id'],  # Use record ID as storyID (no storyID in new table)
                'pivotId': original_fields.get('pivot_id'),  # snake_case in new table
                'ai_headline': original_fields.get('headline'),  # Map headline -> ai_headline
                'ai_dek': summary,  # Derived from raw
                'raw': raw_content,
                'source_id': original_fields.get('source_name'),  # Alias for compatibility
                'source_name': original_fields.get('source_name'),
                'date_og_published': original_fields.get('date_og_published'),
                'topic': original_fields.get('topic'),
                'interest_score': original_fields.get('interest_score'),
                'sentiment': original_fields.get('sentiment'),
                'core_url': original_fields.get('core_url'),
                'ai_complete': original_fields.get('ai_complete'),
            }

            # Return in same format as get_fresh_stories() for prefilter compatibility
            transformed.append({
                'id': r['id'],
                'fields': transformed_fields
            })

        return transformed

    def _extract_summary(self, raw_content: str, max_length: int = 300) -> str:
        """Extract a clean summary from raw content, breaking at sentence boundary."""
        if not raw_content:
            return ''

        # Take first portion of content
        if len(raw_content) <= max_length:
            return raw_content

        # Try to break at a sentence boundary
        truncated = raw_content[:max_length]
        last_period = truncated.rfind('.')
        last_question = truncated.rfind('?')
        last_exclaim = truncated.rfind('!')

        # Find the last sentence boundary
        last_boundary = max(last_period, last_question, last_exclaim)

        if last_boundary > max_length // 2:  # At least half the length
            return truncated[:last_boundary + 1]

        return truncated.rstrip() + '...'

    # NOTE: Source Scores table removed 1/1/26
    # Credibility guidance is now baked into the Claude system prompts in the database.
    # Removed: get_source_scores(), build_source_lookup()

    def get_queued_stories(self) -> List[dict]:
        """
        Step 1, Node 4: Get manually queued stories
        Filter: status='pending'

        Note: AI Editor Queue table has different structure than originally expected.
        Actual fields: 'original slot', 'status'
        Returns pending records for manual story queuing.
        """
        table = self._get_table(self.ai_editor_base_id, self.queued_stories_table_id)

        # Filter: pending status only (table doesn't have expires_date field)
        filter_formula = "{status}='pending'"

        # Don't specify fields - let it return whatever exists in the table
        records = table.all(
            formula=filter_formula
        )

        return records

    def get_yesterday_issue(self) -> Optional[dict]:
        """
        Step 1, Node 8 / Step 2, Node 2: Get yesterday's sent issue
        Filter: status='sent', sorted by issue_date DESC

        NOTE: For comprehensive duplicate checking, use get_recent_sent_issues() instead.
        """
        table = self._get_table(self.ai_editor_base_id, self.selected_slots_table_id)

        records = table.all(
            formula="{status}='sent'",
            sort=['-issue_date'],
            max_records=1
        )

        return records[0] if records else None

    def get_recent_sent_issues(self, lookback_days: int = 14) -> List[dict]:
        """
        Get all issues from the last N days for comprehensive duplicate checking.

        Updated 12/31/25: FIXED to match n8n workflow behavior.
        n8n does NOT filter by status - it gets ALL issues from the last 14 days.
        This ensures we catch headlines from pending/decorated/sent issues for deduplication.

        Args:
            lookback_days: Number of days to look back (default 14 per n8n)

        Returns:
            List of issue records from the last N days (any status)
        """
        table = self._get_table(self.ai_editor_base_id, self.selected_slots_table_id)

        # n8n filter: IS_AFTER({issue_date}, DATEADD(TODAY(), -14, 'days'))
        # NO status filter - gets all issues regardless of status
        filter_formula = f"IS_AFTER({{issue_date}}, DATEADD(TODAY(), -{lookback_days}, 'days'))"

        records = table.all(
            formula=filter_formula,
            sort=['-issue_date']
        )

        return records

    def get_recent_decorated_stories(self, lookback_days: int = 14, max_records: int = 50) -> List[dict]:
        """
        Get recently decorated stories with full content for semantic deduplication.

        Uses Newsletter Issue Stories (Decoration) table which has:
        - headline, b1, b2, b3, ai_dek for semantic comparison
        - storyID for exact match fallback (camelCase per Airtable convention)
        - company for entity matching
        - issue_id for date filtering

        Added 1/7/26: For semantic deduplication to catch same news events
        with different headlines/IDs.

        Args:
            lookback_days: Number of days to look back (default 14)
            max_records: Maximum records to return (default 50)

        Returns:
            List of decorated story records from recent issues
        """
        # Newsletter Issue Stories table in AI Editor 2.0 base
        table = self._get_table(
            self.ai_editor_base_id,
            self.decoration_table_id  # tbla16LJCf5Z6cRn3
        )

        # Filter for stories that have been decorated (have headline)
        # Note: Airtable doesn't have created_at - use issue_id date filter
        # issue_id format is "Pivot 5 - Jan 07" - sort by it descending
        filter_formula = "{headline}!=''"

        records = table.all(
            formula=filter_formula,
            sort=['-issue_id'],  # Most recent issues first
            max_records=max_records,
            fields=[
                'story_id', 'headline',  # Note: Newsletter Issue Stories uses snake_case
                'b1', 'b2', 'b3',
                'ai_dek', 'label',  # FIXED 1/7/26: 'company' field doesn't exist, use 'label' instead
                'issue_id'
            ]
        )

        logger.info(f"[Airtable] get_recent_decorated_stories: Found {len(records)} stories")

        # Log first 3 for debugging
        for i, r in enumerate(records[:3]):
            fields = r.get('fields', {})
            headline = fields.get('headline', 'N/A')[:50]
            has_b1 = bool(fields.get('b1'))
            has_b2 = bool(fields.get('b2'))
            has_b3 = bool(fields.get('b3'))
            logger.info(f"[Airtable] Decorated story {i+1}: '{headline}...' b1={has_b1}, b2={has_b2}, b3={has_b3}")

        return records

    def write_prefilter_log(self, record_data: dict) -> str:
        """
        Step 1, Node 17: Write to Pre-Filter Log table
        Returns: record ID
        """
        table = self._get_table(self.ai_editor_base_id, self.prefilter_log_table_id)
        record = table.create(record_data)
        return record['id']

    def write_prefilter_log_batch(self, records: List[dict]) -> List[str]:
        """
        Batch write to Pre-Filter Log table

        Updated 12/26/25: Uses batch_create for initial implementation.
        Each story can have multiple records (one per eligible slot).

        Note: For deduplication, the n8n workflow uses "Create or Update" with storyID
        as the match field. However, this requires the table to have no duplicate storyIDs.
        For now, we use batch_create and allow multiple records per story+slot.

        Returns: list of record IDs created
        """
        print(f"[Airtable] write_prefilter_log_batch called with {len(records)} records", flush=True)

        if not records:
            print("[Airtable] write_prefilter_log_batch: No records to write, returning empty list", flush=True)
            return []

        # Log first record for debugging
        print(f"[Airtable] First record sample: {records[0]}", flush=True)

        print(f"[Airtable] Getting table: base={self.ai_editor_base_id}, table={self.prefilter_log_table_id}", flush=True)
        table = self._get_table(self.ai_editor_base_id, self.prefilter_log_table_id)
        print(f"[Airtable] Table object obtained: {table}", flush=True)

        # batch_create accepts raw field dicts
        print(f"[Airtable] Calling table.batch_create() with {len(records)} records...", flush=True)
        try:
            created = table.batch_create(records)
            print(f"[Airtable] ✓ batch_create SUCCESS: {len(created)} records created", flush=True)

            record_ids = [r['id'] for r in created]
            print(f"[Airtable] Record IDs: {record_ids[:5]}{'...' if len(record_ids) > 5 else ''}", flush=True)
            return record_ids
        except Exception as e:
            print(f"[Airtable] ✗ batch_create FAILED: {type(e).__name__}: {e}", flush=True)
            import traceback
            print(f"[Airtable] Traceback: {traceback.format_exc()}", flush=True)
            raise

    def get_prefilter_candidates(self, slot: int, freshness_days: int, max_records: int = 200) -> List[dict]:
        """
        Step 2, Nodes 3-7: Get pre-filter candidates for a specific slot

        Updated 12/31/25:
        - FIXED: Slot 1 now uses exact n8n formula with NOW() + hours (not TODAY() + days)
        - Slots 1, 2, 4 use hours-based filtering for precision
        - Slots 3, 5 use days-based filtering (7-day windows)
        - Weekend extension (72h) is embedded in Airtable formula for slots 1, 2, 4
        - Uses core_url instead of original_url (n8n Gap #6)
        - Sorted by date_og_published DESC so freshest candidates are prioritized

        n8n Slot 1 formula reference:
        AND({slot}="1", IS_AFTER({date_og_published}, DATEADD(NOW(), IF(OR(WEEKDAY(NOW())=0, WEEKDAY(NOW())=1), -72, -24), 'hours')))
        """
        table = self._get_table(self.ai_editor_base_id, self.prefilter_log_table_id)

        # Build slot-specific filter formulas matching n8n workflow exactly
        if slot == 1:
            # Slot 1: 24 hours (72h on Sunday=0 or Monday=1)
            # Exact n8n formula from "Pull Slot 1 Candidates" node
            filter_formula = 'AND({slot}="1", IS_AFTER({date_og_published}, DATEADD(NOW(), IF(OR(WEEKDAY(NOW())=0, WEEKDAY(NOW())=1), -72, -24), \'hours\')))'
        elif slot == 2:
            # Slot 2: 48 hours (72h on weekends)
            filter_formula = 'AND({slot}="2", IS_AFTER({date_og_published}, DATEADD(NOW(), IF(OR(WEEKDAY(NOW())=0, WEEKDAY(NOW())=1), -72, -48), \'hours\')))'
        elif slot == 4:
            # Slot 4: 48 hours (72h on weekends)
            filter_formula = 'AND({slot}="4", IS_AFTER({date_og_published}, DATEADD(NOW(), IF(OR(WEEKDAY(NOW())=0, WEEKDAY(NOW())=1), -72, -48), \'hours\')))'
        else:
            # Slots 3 and 5: 7-day windows (no weekend extension needed)
            filter_formula = f'AND({{slot}}="{slot}", IS_AFTER({{date_og_published}}, DATEADD(TODAY(), -7, \'days\')))'

        logger.info(f"[Slot {slot}] Filter formula: {filter_formula}")

        # Note: primary_company field does NOT exist in Pre-Filter Log table
        records = table.all(
            formula=filter_formula,
            sort=['-date_og_published'],  # Freshest first
            max_records=max_records,  # Safety cap for Claude context
            fields=['storyID', 'pivotId', 'headline', 'core_url', 'source_id', 'date_og_published', 'slot']
        )

        logger.info(f"[Slot {slot}] Found {len(records)} candidates")
        return records

    def write_selected_slots(self, issue_data: dict) -> str:
        """
        Step 2, Nodes 30-31: Write selected slots for today's issue
        Returns: record ID
        """
        table = self._get_table(self.ai_editor_base_id, self.selected_slots_table_id)
        record = table.create(issue_data)
        return record['id']

    def get_pending_issue(self) -> Optional[dict]:
        """
        Step 3: Get pending issue for decoration
        """
        table = self._get_table(self.ai_editor_base_id, self.selected_slots_table_id)

        records = table.all(
            formula="{status}='pending'",
            sort=['-issue_date'],
            max_records=1
        )

        return records[0] if records else None

    def write_decoration(self, decoration_data: dict) -> str:
        """
        Step 3: Write decorated story to Newsletter Issue Stories
        Returns: record ID
        """
        table = self._get_table(self.ai_editor_base_id, self.decoration_table_id)
        record = table.create(decoration_data)
        return record['id']

    def update_decoration(self, record_id: str, fields: dict) -> dict:
        """Update a decoration record"""
        table = self._get_table(self.ai_editor_base_id, self.decoration_table_id)
        return table.update(record_id, fields)

    def get_decorations_for_compile(self, max_records: int = 5) -> List[dict]:
        """
        Step 4: Get decorated stories ready for HTML compilation
        Filter: image_status='generated'
        """
        table = self._get_table(self.ai_editor_base_id, self.decoration_table_id)

        records = table.all(
            formula="{image_status}='generated'",
            sort=['slot_order'],
            max_records=max_records
        )

        return records

    def get_decorations_for_social(self, max_records: int = 10) -> List[dict]:
        """
        Step 5: Get decorated stories ready for social sync
        Filter: image_status='generated' AND (social_status='' OR social_status='pending')
        """
        table = self._get_table(self.ai_editor_base_id, self.decoration_table_id)

        filter_formula = "AND({image_status}='generated', OR({social_status}='', {social_status}='pending'))"

        records = table.all(
            formula=filter_formula,
            max_records=max_records
        )

        return records

    def mark_social_synced(self, record_id: str) -> dict:
        """
        Step 5: Mark decoration record as synced to social
        """
        return self.update_decoration(record_id, {"social_status": "synced"})

    # =========================================================================
    # STEP 4: HTML COMPILE & SEND (AI Editor 2.0 base)
    # Added 1/2/26 for n8n migration
    # =========================================================================

    def get_decorated_stories_for_compile(self, issue_id: str) -> List[dict]:
        """
        Step 4, Node 2 (List2): Get decorated stories ready for HTML compilation.

        Query: Newsletter Issue Stories (Decoration) table
        Filter: image_status='generated' AND issue_id='{issue_id}'
        Sort: slot_order ASC

        Args:
            issue_id: Issue identifier (e.g., "Pivot 5 - Jan 02")
                      Note: Day must be zero-padded (MMM dd format)

        Returns:
            List of decorated story records with fields:
            - issue_id, slot_order, story_id, headline, label
            - b1, b2, b3 (bullet points)
            - pivotnews_url, image_url, image_status
        """
        table = self._get_table(self.ai_editor_base_id, self.decoration_table_id)

        # Match n8n List2 node filter exactly
        filter_formula = f"AND({{image_status}} = 'generated', {{issue_id}} = '{issue_id}')"

        records = table.all(
            formula=filter_formula,
            sort=['slot_order'],
            fields=[
                'issue_id', 'slot_order', 'story_id', 'headline', 'label',
                'b1', 'b2', 'b3', 'pivotnews_url', 'image_url', 'image_status'
            ]
        )

        logger.info(f"[Step 4] Found {len(records)} decorated stories for issue: {issue_id}")
        return records

    def get_subject_line_for_issue(self, issue_id: str) -> Optional[str]:
        """
        Step 4, Node 3 (Fetch Subject Line): Get subject line from Selected Slots table.

        Query: AI Editor - Selected Slots table
        Filter: issue_id='{issue_id}'

        Args:
            issue_id: Issue identifier (e.g., "Pivot 5 - Jan 02")

        Returns:
            Subject line string, or None if not found
            Fallback: "5 headlines. 5 minutes. 5 days a week."
        """
        table = self._get_table(self.ai_editor_base_id, self.selected_slots_table_id)

        records = table.all(
            formula=f"{{issue_id}} = '{issue_id}'",
            max_records=1,
            fields=['issue_id', 'subject_line']
        )

        if records and records[0].get('fields', {}).get('subject_line'):
            return records[0]['fields']['subject_line']

        # Return fallback subject line as per n8n workflow
        return "5 headlines. 5 minutes. 5 days a week."

    def create_newsletter_issue_final(self, data: dict) -> dict:
        """
        Step 4, Node 11 (Create a record): Create record in Newsletter Issues Final.

        Table: Newsletter Issues Final (tblPBfWZzRdLuiqYr)
        Base: AI Editor 2.0 (appglKSJZxmA9iHpl)

        Expected data:
            - issue_id: str (e.g., "Pivot 5 - Jan 02")
            - newsletter_id: str ("pivot_ai")
            - html: str (full compiled HTML)
            - subject_line: str
            - status: str ("next-send")
            - summary: str (15-word summary)
            - summary_plus: str (20-word summary)

        Returns:
            Created record with 'id' field
        """
        table = self._get_table(self.ai_editor_base_id, self.newsletter_issues_final_table_id)

        record = table.create(data)
        logger.info(f"[Step 4] Created Newsletter Issues Final record: {record['id']}")
        return record

    def get_newsletter_issue_for_send(self) -> Optional[dict]:
        """
        Step 4b, Node 1 (List6): Get newsletter issue ready for send.

        Query: Newsletter Issues Final table
        Filter: status='next-send'

        Returns:
            Newsletter issue record or None
        """
        table = self._get_table(self.ai_editor_base_id, self.newsletter_issues_final_table_id)

        records = table.all(
            formula="{status}='next-send'",
            max_records=1,
            fields=['issue_id', 'newsletter_id', 'html', 'subject_line', 'status', 'summary', 'summary_plus']
        )

        if records:
            logger.info(f"[Step 4] Found issue for send: {records[0].get('fields', {}).get('issue_id')}")
            return records[0]

        logger.info("[Step 4] No issues with status='next-send'")
        return None

    def archive_newsletter_issue_ai_editor(self, data: dict) -> dict:
        """
        Step 4b, Node 9 (Update Newsletter Issues Archive): Upsert to archive table.

        Table: Newsletter Issues Archive (tblB7j5qGcTxyXmfa)
        Base: AI Editor 2.0 (appglKSJZxmA9iHpl)
        Operation: UPSERT (match on issue_id)

        Expected data:
            - issue_id: str
            - newsletter_id: str ("pivot_ai")
            - send_date: str (date)
            - sent_at: str (datetime, ET timezone)
            - subject_line: str
            - status: str ("sent" / "failed" / "partial_failure")
            - html: str
            - summary: str
            - mautic_sent_count: int
            - mautic_failed_recipients: int
            - mautic_send_status: str
            - mautic_response_raw: str (JSON)

        Returns:
            Created or updated record
        """
        table = self._get_table(self.ai_editor_base_id, self.newsletter_issues_archive_ai_table_id)

        # Use upsert with issue_id as match field
        issue_id = data.get('issue_id')
        if not issue_id:
            raise ValueError("issue_id is required for archive upsert")

        # Check if record exists
        existing = table.all(
            formula=f"{{issue_id}} = '{issue_id}'",
            max_records=1
        )

        if existing:
            # Update existing record
            record = table.update(existing[0]['id'], data)
            logger.info(f"[Step 4] Updated archive record: {record['id']}")
        else:
            # Create new record
            record = table.create(data)
            logger.info(f"[Step 4] Created archive record: {record['id']}")

        return record

    def delete_newsletter_issue_final(self, record_id: str) -> bool:
        """
        Step 4b, Node 10 (Delete a record3): Delete record from Newsletter Issues Final.

        Called after successful send to clean up the queue.

        Args:
            record_id: Airtable record ID

        Returns:
            True if deleted successfully
        """
        table = self._get_table(self.ai_editor_base_id, self.newsletter_issues_final_table_id)

        try:
            table.delete(record_id)
            logger.info(f"[Step 4] Deleted Newsletter Issues Final record: {record_id}")
            return True
        except Exception as e:
            logger.error(f"[Step 4] Failed to delete record {record_id}: {e}")
            return False

    # =========================================================================
    # P5 SOCIAL POSTS BASE
    # =========================================================================

    def find_existing_social_post(self, source_record_id: str) -> Optional[dict]:
        """
        Step 5: Check if social post already exists for this source record
        """
        table = self._get_table(self.p5_social_base_id, self.p5_social_posts_table_id)

        filter_formula = f'AND({{source_record_id}}="{source_record_id}",{{source_record_id}}!="")'

        records = table.all(
            formula=filter_formula,
            max_records=1
        )

        return records[0] if records else None

    def create_social_post(self, post_data: dict) -> str:
        """
        Step 5: Create new record in P5 Social Posts table
        Returns: record ID
        """
        table = self._get_table(self.p5_social_base_id, self.p5_social_posts_table_id)
        record = table.create(post_data)
        return record['id']

    # =========================================================================
    # STEP 0.6: BROWSERBASE RETRY (AI Editor 2.0 base)
    # Added 1/8/26 for paywalled site scraping retry
    # =========================================================================

    def get_newsletter_selects_by_formula(self, formula: str) -> List[dict]:
        """
        Query Newsletter Selects table with a custom formula.

        Used by browserbase_retry job to find articles needing re-extraction.

        Args:
            formula: Airtable filter formula

        Returns:
            List of matching records
        """
        table = self._get_table(self.ai_editor_base_id, self.newsletter_selects_table_id)

        records = table.all(
            formula=formula,
            fields=[
                'pivot_id', 'source_name', 'core_url', 'raw',
                'headline', 'date_ai_process', 'interest_score'
            ]
        )

        logger.info(f"[Airtable] get_newsletter_selects_by_formula: Found {len(records)} records")
        return records

    def update_newsletter_select(self, record_id: str, fields: dict) -> dict:
        """
        Update a Newsletter Selects record.

        Used by browserbase_retry job to update raw content after re-extraction.

        Args:
            record_id: Airtable record ID
            fields: Fields to update (e.g., {'raw': content, 'browserbase_extracted': True})

        Returns:
            Updated record
        """
        table = self._get_table(self.ai_editor_base_id, self.newsletter_selects_table_id)
        record = table.update(record_id, fields)
        logger.info(f"[Airtable] Updated Newsletter Select record: {record_id}")
        return record

    # =========================================================================
    # SIGNAL NEWSLETTER (Signal Newsletter base - appWGkUBuyrzmFnFM)
    # Added 1/12/26 for Signal Newsletter pipeline
    #
    # IMPORTANT: Signal uses a SEPARATE Airtable base from AI Editor 2.0
    # - Pre-Filter Log table is SHARED (in AI Editor 2.0 base)
    # - Signal Selected Slots and Issue Stories are in Signal base
    # =========================================================================

    def create_signal_issue(self, issue_data: dict) -> str:
        """
        Create a new Signal newsletter issue in Signal Selected Slots.

        Expected issue_data fields:
            - issue_id: str (e.g., "Signal - Jan 12")
            - issue_date: str (date, e.g., "2026-01-12")
            - status: str ("pending")
            - top_story_story_id, top_story_pivot_id
            - ai_at_work_story_id, ai_at_work_pivot_id
            - emerging_story_id, emerging_pivot_id
            - beyond_story_id, beyond_pivot_id
            - signal_1_story_id through signal_5_story_id
            - signal_1_pivot_id through signal_5_pivot_id

        Returns:
            Record ID of created issue
        """
        table = self._get_table(self.signal_base_id, self.signal_selected_slots_table_id)
        record = table.create(issue_data)
        logger.info(f"[Signal] Created Signal issue: {issue_data.get('issue_id')} -> {record['id']}")
        return record['id']

    def get_signal_pending_issue(self) -> Optional[dict]:
        """
        Get Signal issue with status='pending' for decoration.

        Returns:
            Most recent pending Signal issue record, or None
        """
        table = self._get_table(self.signal_base_id, self.signal_selected_slots_table_id)

        records = table.all(
            formula="{status}='pending'",
            sort=['-issue_date'],
            max_records=1
        )

        if records:
            logger.info(f"[Signal] Found pending issue: {records[0].get('fields', {}).get('issue_id')}")
        else:
            logger.info("[Signal] No pending issues found")

        return records[0] if records else None

    def get_signal_issue_by_id(self, issue_id: str) -> Optional[dict]:
        """
        Get Signal issue by issue_id.

        Args:
            issue_id: Issue identifier (e.g., "Signal - Jan 12")

        Returns:
            Signal issue record or None
        """
        table = self._get_table(self.signal_base_id, self.signal_selected_slots_table_id)

        records = table.all(
            formula=f"{{issue_id}}='{issue_id}'",
            max_records=1
        )

        return records[0] if records else None

    def get_signal_recent_issues(self, lookback_days: int = 14) -> List[dict]:
        """
        Get Signal issues from the last N days for duplicate checking.

        Similar to get_recent_sent_issues() for Pivot 5, but queries Signal base.
        Used for headline/company deduplication across recent issues.

        Args:
            lookback_days: Number of days to look back (default 14)

        Returns:
            List of Signal issue records from the last N days
        """
        table = self._get_table(self.signal_base_id, self.signal_selected_slots_table_id)

        filter_formula = f"IS_AFTER({{issue_date}}, DATEADD(TODAY(), -{lookback_days}, 'days'))"

        records = table.all(
            formula=filter_formula,
            sort=['-issue_date']
        )

        logger.info(f"[Signal] Found {len(records)} issues in last {lookback_days} days")
        return records

    def update_signal_issue(self, record_id: str, fields: dict) -> dict:
        """
        Update a Signal issue record.

        Common updates:
            - status: 'pending' -> 'decorated' -> 'compiled' -> 'sent'
            - subject_line: After decoration completes
            - sent_at: After send completes

        Args:
            record_id: Airtable record ID
            fields: Fields to update

        Returns:
            Updated record
        """
        table = self._get_table(self.signal_base_id, self.signal_selected_slots_table_id)
        record = table.update(record_id, fields)
        logger.info(f"[Signal] Updated Signal issue: {record_id}")
        return record

    def write_signal_story(self, story_data: dict) -> str:
        """
        Write decorated story to Signal Issue Stories table.

        Expected story_data fields:
            - story_id: str (unique identifier)
            - issue_id: str (links to Signal Selected Slots)
            - section: str ('top_story', 'ai_at_work', 'emerging_moves', 'beyond_business', 'signal_1'..'signal_5')
            - headline: str (max 80 chars)
            - one_liner: str (1 sentence for at-a-glance)
            - lead: str (2-3 sentences intro)
            - signal_blurb: str (2 sentences, signals only)
            - why_it_matters: str (2 sentences)
            - whats_next: str (2 sentences)
            - source_attribution: str (e.g., "via TechCrunch")
            - pivot_id: str (original article reference)
            - raw: str (cleaned article content)
            - decoration_status: str ('pending', 'decorated', 'error')

        Returns:
            Record ID of created story
        """
        table = self._get_table(self.signal_base_id, self.signal_issue_stories_table_id)
        record = table.create(story_data)
        logger.info(f"[Signal] Created Signal story: {story_data.get('section')} -> {record['id']}")
        return record['id']

    def get_signal_stories_for_issue(self, issue_id: str) -> List[dict]:
        """
        Get all decorated stories for a Signal issue.

        Args:
            issue_id: Issue identifier (e.g., "Signal - Jan 12")

        Returns:
            List of story records sorted by section
            (section names sort correctly: ai_at_work, beyond_business, emerging_moves, signal_1-5, top_story)
        """
        table = self._get_table(self.signal_base_id, self.signal_issue_stories_table_id)

        records = table.all(
            formula=f"{{issue_id}}='{issue_id}'",
            sort=['section'],
            fields=[
                'story_id', 'issue_id', 'section',
                'headline', 'one_liner', 'lead', 'signal_blurb',
                'why_it_matters', 'whats_next',
                'source_attribution', 'pivot_id', 'decoration_status'
            ]
        )

        logger.info(f"[Signal] Found {len(records)} stories for issue: {issue_id}")
        return records

    def update_signal_story(self, record_id: str, fields: dict) -> dict:
        """
        Update a Signal story record.

        Common updates:
            - decoration_status: 'pending' -> 'decorated' or 'error'
            - headline, summary, paragraph, b1, b2, b3: After decoration

        Args:
            record_id: Airtable record ID
            fields: Fields to update

        Returns:
            Updated record
        """
        table = self._get_table(self.signal_base_id, self.signal_issue_stories_table_id)
        record = table.update(record_id, fields)
        logger.info(f"[Signal] Updated Signal story: {record_id}")
        return record

    def get_signal_stories_for_compile(self, issue_id: str) -> List[dict]:
        """
        Get decorated stories ready for HTML compilation.

        Filter: decoration_status='decorated' AND issue_id='{issue_id}'
        Sort: section ASC (use SIGNAL_SECTION_ORDER for proper display order)

        Args:
            issue_id: Issue identifier (e.g., "Signal - Jan 12")

        Returns:
            List of decorated story records ready for HTML compilation
            NOTE: Records are sorted alphabetically by section. The caller should
            reorder using SIGNAL_SECTION_ORDER for proper display:
            [top_story, ai_at_work, emerging_moves, beyond_business, signal_1..5]
        """
        table = self._get_table(self.signal_base_id, self.signal_issue_stories_table_id)

        filter_formula = f"AND({{decoration_status}}='decorated', {{issue_id}}='{issue_id}')"

        records = table.all(
            formula=filter_formula,
            sort=['section'],
            fields=[
                'pivot_id', 'issue_id', 'section',
                'headline', 'one_liner', 'lead', 'signal_blurb',
                'why_it_matters', 'whats_next',
                'source_attribution'
            ]
        )

        logger.info(f"[Signal] Found {len(records)} decorated stories for compile: {issue_id}")
        return records

    def get_signal_candidates(self, slot: int, freshness_hours: int = 72) -> List[dict]:
        """
        Get pre-filter candidates for Signal slot selection.

        IMPORTANT: Uses SHARED Pre-Filter Log table in AI Editor 2.0 base.
        Signal uses different freshness rules than Pivot 5:
            - Slot 1 (TOP STORY): 24 hours (no weekend extension)
            - All other slots: 72 hours

        Args:
            slot: Slot number (1-5)
            freshness_hours: Hours of freshness (24 for slot 1, 72 for others)

        Returns:
            List of candidate records from Pre-Filter Log
        """
        table = self._get_table(self.ai_editor_base_id, self.prefilter_log_table_id)

        # Signal freshness: 24h for slot 1, 72h for all others
        # No weekend extension for Signal (simpler rules)
        filter_formula = f'AND({{slot}}="{slot}", IS_AFTER({{date_og_published}}, DATEADD(NOW(), -{freshness_hours}, \'hours\')))'

        logger.info(f"[Signal Slot {slot}] Filter formula: {filter_formula}")

        records = table.all(
            formula=filter_formula,
            sort=['-date_og_published'],  # Freshest first
            max_records=200,  # Safety cap for Claude context
            fields=['storyID', 'pivotId', 'headline', 'core_url', 'source_id', 'date_og_published', 'slot']
        )

        logger.info(f"[Signal Slot {slot}] Found {len(records)} candidates")
        return records

    def get_signal_used_pivot_ids(self, lookback_days: int = 14) -> List[str]:
        """
        Get all pivot_ids already used in recent Signal issues.

        Used for deduplication - ensures same story isn't selected twice.

        Args:
            lookback_days: Number of days to look back (default 14)

        Returns:
            List of pivot_id strings that have been used
        """
        recent_issues = self.get_signal_recent_issues(lookback_days)

        used_ids = []
        for issue in recent_issues:
            fields = issue.get('fields', {})

            # Main stories
            for section in ['top_story', 'ai_at_work', 'emerging', 'beyond']:
                pivot_id = fields.get(f'{section}_pivot_id')
                if pivot_id:
                    used_ids.append(pivot_id)

            # Signals (5 items)
            for i in range(1, 6):
                pivot_id = fields.get(f'signal_{i}_pivot_id')
                if pivot_id:
                    used_ids.append(pivot_id)

        logger.info(f"[Signal] Found {len(used_ids)} used pivot_ids in last {lookback_days} days")
        return used_ids

    def get_signal_recent_headlines(self, lookback_days: int = 14) -> List[str]:
        """
        Get headlines from recent Signal issues for semantic deduplication.

        Used to avoid selecting stories with similar headlines.

        Args:
            lookback_days: Number of days to look back (default 14)

        Returns:
            List of headline strings from recent issues
        """
        # Get all recent Signal issue IDs
        recent_issues = self.get_signal_recent_issues(lookback_days)
        issue_ids = [i.get('fields', {}).get('issue_id') for i in recent_issues if i.get('fields', {}).get('issue_id')]

        if not issue_ids:
            return []

        # Query Signal Issue Stories for headlines
        table = self._get_table(self.signal_base_id, self.signal_issue_stories_table_id)

        # Build OR formula for all issue IDs
        conditions = [f"{{issue_id}}='{iid}'" for iid in issue_ids]
        filter_formula = f"OR({','.join(conditions)})"

        records = table.all(
            formula=filter_formula,
            fields=['headline', 'issue_id']
        )

        headlines = [r.get('fields', {}).get('headline') for r in records if r.get('fields', {}).get('headline')]
        logger.info(f"[Signal] Found {len(headlines)} headlines from {len(issue_ids)} recent issues")
        return headlines
