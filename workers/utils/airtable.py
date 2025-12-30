"""
Airtable API Client for AI Editor 2.0 Workers
Handles all Airtable read/write operations
"""

import os
from typing import List, Optional, Dict, Any
from pyairtable import Api, Table


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
        self.source_scores_table_id = os.environ.get('AI_EDITOR_SOURCE_SCORES_TABLE', 'tbl3Zkdl1No2edDLK')
        self.queued_stories_table_id = os.environ.get('AI_EDITOR_QUEUED_STORIES_TABLE', 'tblkVBP5mKq3sBpkv')

        # Table IDs - P5 Social Posts
        self.p5_social_posts_table_id = os.environ.get('P5_SOCIAL_POSTS_TABLE', 'tbllJMN2QBPJoG3jA')

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
        Lookup article details by pivotId
        Returns: source_id, original_url, markdown
        """
        table = self._get_table(self.pivot_media_base_id, self.articles_table_id)

        records = table.all(
            formula=f"{{pivot_Id}}='{pivot_id}'",
            max_records=1,
            fields=['pivot_Id', 'source_id', 'original_url', 'markdown']
        )

        return records[0] if records else None

    def get_articles_batch(self, pivot_ids: List[str]) -> Dict[str, dict]:
        """
        Batch lookup articles by pivotIds
        Returns: dict mapping pivotId -> article record

        Updated to include core_url (n8n Gap #6 - Pre-Filter Log uses core_url)
        """
        if not pivot_ids:
            return {}

        table = self._get_table(self.pivot_media_base_id, self.articles_table_id)

        # Build OR formula for batch lookup
        conditions = [f"{{pivot_Id}}='{pid}'" for pid in pivot_ids]
        filter_formula = f"OR({','.join(conditions)})"

        records = table.all(
            formula=filter_formula,
            fields=['pivot_Id', 'source_id', 'original_url', 'core_url', 'markdown']
        )

        return {r['fields'].get('pivot_Id'): r for r in records}

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

    def get_source_scores(self, max_records: int = 500) -> List[dict]:
        """
        Step 1, Node 6: Get source credibility scores
        Returns: list of {source_name, credibility_score}
        """
        table = self._get_table(self.ai_editor_base_id, self.source_scores_table_id)

        records = table.all(
            max_records=max_records,
            fields=['source_name', 'credibility_score']
        )

        return records

    def build_source_lookup(self) -> Dict[str, int]:
        """
        Step 1, Node 7: Build source_name -> score lookup map
        Keys are lowercased for case-insensitive matching
        """
        records = self.get_source_scores()
        return {
            r['fields'].get('source_name', '').lower(): r['fields'].get('credibility_score', 3)
            for r in records
            if r['fields'].get('source_name')
        }

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
        Get all sent issues from the last N days for comprehensive duplicate checking.

        Updated 12/26/25: Added to match n8n workflow behavior.
        n8n uses a 14-day lookback (line 1190) to check for recently used stories.

        Args:
            lookback_days: Number of days to look back (default 14 per n8n)

        Returns:
            List of sent issue records from the last N days
        """
        table = self._get_table(self.ai_editor_base_id, self.selected_slots_table_id)

        filter_formula = f"AND({{status}}='sent', IS_AFTER({{issue_date}}, DATEADD(TODAY(), -{lookback_days}, 'days')))"

        records = table.all(
            formula=filter_formula,
            sort=['-issue_date']
        )

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
        table = self._get_table(self.ai_editor_base_id, self.prefilter_log_table_id)

        # batch_create accepts raw field dicts
        created = table.batch_create(records)
        return [r['id'] for r in created]

    def get_prefilter_candidates(self, slot: int, freshness_days: int) -> List[dict]:
        """
        Step 2, Nodes 3-7: Get pre-filter candidates for a specific slot

        Updated 12/30/25:
        - Uses date_og_published (original publish date) instead of date_prefiltered
        - This matches n8n workflow behavior for freshness filtering
        - Uses core_url instead of original_url (n8n Gap #6)
        """
        table = self._get_table(self.ai_editor_base_id, self.prefilter_log_table_id)

        # Filter on date_og_published (article's original publish date), not date_prefiltered
        filter_formula = f"AND({{slot}}={slot}, IS_AFTER({{date_og_published}}, DATEADD(TODAY(), -{freshness_days}, 'days')))"

        records = table.all(
            formula=filter_formula,
            fields=['storyID', 'pivotId', 'headline', 'core_url', 'source_id', 'date_og_published', 'slot']
        )

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
