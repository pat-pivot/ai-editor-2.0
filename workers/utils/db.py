"""
PostgreSQL Database Client for AI Editor 2.0 Workers
Loads system prompts and configuration from the database

Updated 12/31/25: Added retry logic for SSL connection failures
Updated 12/31/25: Fixed recurring SSL issues with proper sslmode and keepalives
"""

import os
import logging
import time
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Retry configuration for SSL connection failures
# Increased from 3 to 5 retries with longer delays for Render cold starts
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 3  # Start with 3s, exponential backoff


class DatabaseClient:
    """PostgreSQL database client for AI Editor 2.0 workers"""

    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

    def _create_connection(self):
        """Create a new database connection with proper SSL and keepalive settings.

        Key fixes for Render Postgres SSL issues:
        1. Always use sslmode='require' - Render requires SSL
        2. TCP keepalives prevent "SSL connection closed unexpectedly" errors
        3. Longer connect_timeout for cold starts
        """
        return psycopg2.connect(
            self.database_url,
            cursor_factory=RealDictCursor,
            # SSL Settings - ALWAYS require SSL for Render Postgres
            sslmode='require',
            # Connection timeout - allow for cold starts
            connect_timeout=30,
            # TCP Keepalive settings - CRITICAL for preventing SSL drops
            # These prevent Render's infrastructure from killing idle connections
            keepalives=1,           # Enable TCP keepalives
            keepalives_idle=30,     # Seconds before sending keepalive probe
            keepalives_interval=10, # Seconds between keepalive probes
            keepalives_count=5,     # Number of failed probes before disconnect
            # Query timeout
            options='-c statement_timeout=60000'  # 60 second query timeout
        )

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor with retry logic"""
        last_error = None

        for attempt in range(MAX_RETRIES):
            conn = None
            cursor = None
            try:
                # Create fresh connection each time
                conn = self._create_connection()
                cursor = conn.cursor()
                yield cursor
                conn.commit()
                return  # Success - exit the retry loop

            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # SSL connection failures, connection drops
                last_error = e
                logger.warning(f"Database connection error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))  # Exponential backoff
                continue

            except Exception as e:
                # Other database errors (query errors, etc.)
                if conn:
                    conn.rollback()
                logger.error(f"Database error: {e}")
                raise

            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

        # All retries exhausted
        logger.error(f"Database connection failed after {MAX_RETRIES} retries: {last_error}")
        raise last_error

    def close(self):
        """No-op for backwards compatibility - connections are closed per query"""
        pass

    # =========================================================================
    # PROMPT QUERIES
    # =========================================================================

    def get_prompt_by_key(self, prompt_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a prompt by its key with current content

        Returns:
            {
                id, prompt_key, step_id, name, description,
                model, temperature, slot_number, is_active,
                content, current_version, last_modified_by
            }
        """
        sql = """
            SELECT
                sp.id,
                sp.prompt_key,
                sp.step_id,
                sp.name,
                sp.description,
                sp.model,
                sp.temperature,
                sp.slot_number,
                sp.is_active,
                sp.created_at,
                sp.updated_at,
                spv.content,
                spv.version as current_version,
                spv.created_by_email as last_modified_by
            FROM system_prompts sp
            LEFT JOIN system_prompt_versions spv ON sp.id = spv.prompt_id AND spv.is_current = true
            WHERE sp.prompt_key = %s AND sp.is_active = true
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, (prompt_key,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_prompts_by_step(self, step_id: int) -> List[Dict[str, Any]]:
        """Get all prompts for a specific step"""
        sql = """
            SELECT
                sp.id,
                sp.prompt_key,
                sp.step_id,
                sp.name,
                sp.description,
                sp.model,
                sp.temperature,
                sp.slot_number,
                sp.is_active,
                spv.content,
                spv.version as current_version,
                spv.created_by_email as last_modified_by
            FROM system_prompts sp
            LEFT JOIN system_prompt_versions spv ON sp.id = spv.prompt_id AND spv.is_current = true
            WHERE sp.step_id = %s AND sp.is_active = true
            ORDER BY sp.slot_number NULLS LAST, sp.name
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, (step_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_prompts(self) -> List[Dict[str, Any]]:
        """Get all active prompts across all steps"""
        sql = """
            SELECT
                sp.id,
                sp.prompt_key,
                sp.step_id,
                sp.name,
                sp.model,
                sp.temperature,
                sp.slot_number,
                spv.content
            FROM system_prompts sp
            LEFT JOIN system_prompt_versions spv ON sp.id = spv.prompt_id AND spv.is_current = true
            WHERE sp.is_active = true
            ORDER BY sp.step_id, sp.slot_number NULLS LAST
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # JOB TRACKING
    # =========================================================================

    def create_job(self, job_type: str, step_id: int, payload: Dict = None) -> str:
        """Create a job record and return the job ID"""
        sql = """
            INSERT INTO jobs (job_type, step_id, status, payload)
            VALUES (%s, %s, 'pending', %s)
            RETURNING id
        """
        import json
        with self.get_cursor() as cursor:
            cursor.execute(sql, (job_type, step_id, json.dumps(payload or {})))
            row = cursor.fetchone()
            return str(row['id'])

    def update_job_status(self, job_id: str, status: str, result: Dict = None, error: str = None):
        """Update job status"""
        sql = """
            UPDATE jobs
            SET status = %s, result = %s, error_message = %s, updated_at = NOW()
            WHERE id = %s
        """
        import json
        with self.get_cursor() as cursor:
            cursor.execute(sql, (status, json.dumps(result) if result else None, error, job_id))

    # =========================================================================
    # AUDIT LOGGING
    # =========================================================================

    def log_audit(self, action: str, entity_type: str, entity_id: str = None,
                  details: Dict = None, user_email: str = None):
        """Log an audit event"""
        sql = """
            INSERT INTO audit_log (action, entity_type, entity_id, details, user_email)
            VALUES (%s, %s, %s, %s, %s)
        """
        import json
        with self.get_cursor() as cursor:
            cursor.execute(sql, (action, entity_type, entity_id,
                                 json.dumps(details) if details else None, user_email))

    # =========================================================================
    # RAW SQL EXECUTION (for migrations and admin)
    # =========================================================================

    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_update(self, sql: str, params: tuple = None) -> int:
        """Execute an INSERT/UPDATE/DELETE and return rows affected"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount


# Singleton instance
_db_client: Optional[DatabaseClient] = None


def get_db() -> DatabaseClient:
    """Get or create the database client singleton"""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client
