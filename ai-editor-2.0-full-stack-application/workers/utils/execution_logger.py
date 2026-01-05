"""
Execution Logger for AI Editor 2.0 Workers

Provides structured logging that:
1. Writes to stdout for Render log capture
2. Accumulates log entries in memory
3. Saves execution records to the database upon completion

Usage:
    logger = ExecutionLogger(step_id=0, job_type='ingest')
    logger.info("Starting ingest job")
    logger.set_summary('articles_extracted', 150)
    # ... do work ...
    logger.complete('success')  # or logger.complete('error', 'Error message')
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal

import psycopg2
from psycopg2.extras import RealDictCursor

# Set up module logger
module_logger = logging.getLogger(__name__)


class ExecutionLogger:
    """
    Structured execution logger that mirrors logs to both stdout and database.
    """

    def __init__(
        self,
        step_id: int,
        job_type: str,
        slot_number: Optional[int] = None
    ):
        """
        Initialize execution logger.

        Args:
            step_id: Pipeline step (0 = Ingest, 1 = Pre-filter, etc.)
            job_type: Type of job ('ingest', 'ai_scoring', 'newsletter_links', 'pre_filter')
            slot_number: For pre-filter jobs, the slot number (1-5)
        """
        self.run_id = str(uuid.uuid4())
        self.step_id = step_id
        self.job_type = job_type
        self.slot_number = slot_number
        self.started_at = datetime.utcnow()

        # Accumulated data
        self.entries: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}

        # Database connection
        self._connection = None
        self._database_url = os.environ.get('DATABASE_URL')

        # Log the start
        self.info(f"Starting {job_type} job (run_id: {self.run_id[:8]}...)")

    def _get_connection(self):
        """Get or create database connection."""
        if self._connection is None or self._connection.closed:
            if not self._database_url:
                module_logger.warning("DATABASE_URL not set, execution logs will not be persisted")
                return None
            self._connection = psycopg2.connect(
                self._database_url,
                cursor_factory=RealDictCursor,
                sslmode='require' if os.environ.get('NODE_ENV') == 'production' else 'prefer'
            )
        return self._connection

    def _log(
        self,
        level: Literal['info', 'warn', 'error', 'debug'],
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Internal logging method.

        Args:
            level: Log level
            message: Log message
            metadata: Optional additional data
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'

        entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
        }
        if metadata:
            entry['metadata'] = metadata

        self.entries.append(entry)

        # Also write to stdout for Render logs
        prefix = f"[{level.upper()}]"
        slot_info = f" [Slot {self.slot_number}]" if self.slot_number else ""
        meta_str = f" | {json.dumps(metadata)}" if metadata else ""
        print(f"{prefix}{slot_info} {message}{meta_str}")

    def info(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log an info message."""
        self._log('info', message, metadata)

    def warn(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log a warning message."""
        self._log('warn', message, metadata)

    def error(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log an error message."""
        self._log('error', message, metadata)

    def debug(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log a debug message."""
        self._log('debug', message, metadata)

    def set_summary(self, key: str, value: Any):
        """
        Set a summary metric.

        Args:
            key: Metric name (e.g., 'articles_extracted')
            value: Metric value
        """
        self.summary[key] = value

    def complete(
        self,
        status: Literal['success', 'error'],
        error_message: Optional[str] = None,
        error_stack: Optional[str] = None
    ):
        """
        Complete the execution and save to database.

        Args:
            status: Final status ('success' or 'error')
            error_message: Error message if status is 'error'
            error_stack: Error stack trace if available
        """
        completed_at = datetime.utcnow()
        duration_ms = int((completed_at - self.started_at).total_seconds() * 1000)

        # Log completion
        if status == 'success':
            self.info(f"Completed {self.job_type} job in {duration_ms}ms", self.summary)
        else:
            self.error(f"Failed {self.job_type} job: {error_message}")

        # Save to database
        try:
            conn = self._get_connection()
            if conn is None:
                module_logger.warning("Skipping database persistence - no connection")
                return

            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO execution_logs (
                        step_id, job_type, slot_number, run_id,
                        started_at, completed_at, duration_ms,
                        status, summary, log_entries,
                        error_message, error_stack
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s
                    )
                """
                cursor.execute(sql, (
                    self.step_id,
                    self.job_type,
                    self.slot_number,
                    self.run_id,
                    self.started_at.isoformat(),
                    completed_at.isoformat(),
                    duration_ms,
                    status,
                    json.dumps(self.summary),
                    json.dumps(self.entries),
                    error_message,
                    error_stack
                ))
                conn.commit()
                module_logger.info(f"Saved execution log {self.run_id}")

        except Exception as e:
            module_logger.error(f"Failed to save execution log: {e}")
            # Don't raise - logging should not break the main job
        finally:
            if self._connection and not self._connection.closed:
                self._connection.close()


def create_logger(
    step_id: int,
    job_type: str,
    slot_number: Optional[int] = None
) -> ExecutionLogger:
    """
    Factory function to create an ExecutionLogger.

    Args:
        step_id: Pipeline step number
        job_type: Type of job
        slot_number: Optional slot number for pre-filter

    Returns:
        ExecutionLogger instance
    """
    return ExecutionLogger(step_id, job_type, slot_number)
