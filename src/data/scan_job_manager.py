"""
ScanJobManager: Persistent scan job tracking with resume capability.

Provides a clean API for creating, updating, and resuming scan jobs.
State is persisted to SQLite so scans can survive server restarts.
"""

import sqlite3
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class ScanJob:
    """Represents a scan job's current state."""
    id: int = 0
    target_path: str = ""
    status: str = "pending"      # pending, running, paused, completed, failed
    total_files: int = 0
    processed_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    force_reprocess: bool = False
    current_file: str = ""
    started_at: float = 0.0
    updated_at: float = 0.0
    completed_at: float = 0.0
    last_processed_path: str = ""

    @property
    def progress_percent(self) -> float:
        if self.total_files <= 0:
            return 0.0
        done = self.processed_count + self.skipped_count + self.error_count
        return min((done / self.total_files) * 100, 100.0)

    @property
    def eta_seconds(self) -> float:
        done = self.processed_count + self.skipped_count + self.error_count
        if done <= 0 or self.started_at <= 0:
            return 0.0
        elapsed = time.time() - self.started_at
        remaining = self.total_files - done
        avg_per_item = elapsed / done
        return remaining * avg_per_item


@dataclass
class ScanError:
    """A single per-file error record."""
    id: int = 0
    job_id: int = 0
    file_path: str = ""
    error_message: str = ""
    traceback: str = ""
    occurred_at: float = 0.0


class ScanJobManager:
    """
    Manages persistent scan job state via SQLite.

    Usage:
        manager = ScanJobManager(sqlite_path)
        job = manager.create_job("/path/to/scan", total=1000)
        manager.mark_running(job.id)
        # ... for each file:
        manager.increment_processed(job.id, "/path/to/file.jpg")
        # ... on error:
        manager.log_error(job.id, "/bad/file.png", "corrupt", traceback_str)
        # ... done:
        manager.mark_completed(job.id)
    """

    def __init__(self, sqlite_path: str):
        self.sqlite_path = sqlite_path
        self._external_conn: Optional[sqlite3.Connection] = None

    def set_session_conn(self, conn: Optional[sqlite3.Connection]):
        """Hold a shared connection for bulk updates (e.g. during a scan)."""
        self._external_conn = conn

    def _connect(self) -> sqlite3.Connection:
        if self._external_conn is not None:
            return self._external_conn
        conn = sqlite3.connect(self.sqlite_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _close(self, conn: sqlite3.Connection):
        """Close connection only if it's not the shared session one."""
        if self._external_conn is None:
            conn.close()

    # ------------------------------------------------------------------ #
    # Job Lifecycle
    # ------------------------------------------------------------------ #

    def create_job(self, target_path: str, total_files: int = 0,
                   force_reprocess: bool = False) -> ScanJob:
        """Create a new scan job record."""
        now = time.time()
        conn = self._connect()
        try:
            c = conn.cursor()
            c.execute('''
                INSERT INTO scan_jobs
                    (target_path, status, total_files, force_reprocess, started_at, updated_at)
                VALUES (?, 'pending', ?, ?, ?, ?)
            ''', (target_path, total_files, int(force_reprocess), now, now))
            conn.commit()
            job_id = c.lastrowid
        finally:
            self._close(conn)

        return self.get_job(job_id)

    def mark_running(self, job_id: int):
        self._update_status(job_id, 'running')

    def mark_paused(self, job_id: int):
        self._update_status(job_id, 'paused')

    def mark_completed(self, job_id: int):
        now = time.time()
        conn = self._connect()
        try:
            conn.execute('''
                UPDATE scan_jobs SET status='completed', completed_at=?, updated_at=?
                WHERE id=?
            ''', (now, now, job_id))
            conn.commit()
        finally:
            self._close(conn)

    def mark_failed(self, job_id: int, error_msg: str = ""):
        now = time.time()
        conn = self._connect()
        try:
            conn.execute('''
                UPDATE scan_jobs SET status='failed', updated_at=?
                WHERE id=?
            ''', (now, job_id))
            # Log the top-level failure as an error record too
            if error_msg:
                conn.execute('''
                    INSERT INTO scan_errors (job_id, file_path, error_message, traceback, occurred_at)
                    VALUES (?, '[FATAL]', ?, '', ?)
                ''', (job_id, error_msg[:1000], now))
            conn.commit()
        finally:
            self._close(conn)

    # ------------------------------------------------------------------ #
    # Progress Updates (called per-file)
    # ------------------------------------------------------------------ #

    def update_total(self, job_id: int, total_files: int):
        """Set or update the total file count (after pre-scan)."""
        conn = self._connect()
        try:
            conn.execute(
                'UPDATE scan_jobs SET total_files=?, updated_at=? WHERE id=?',
                (total_files, time.time(), job_id)
            )
            conn.commit()
        finally:
            self._close(conn)

    def increment_processed(self, job_id: int, file_path: str):
        """Mark one file as successfully processed."""
        now = time.time()
        conn = self._connect()
        try:
            conn.execute('''
                UPDATE scan_jobs
                SET processed_count = processed_count + 1,
                    current_file = ?,
                    last_processed_path = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (file_path, file_path, now, job_id))
            conn.commit()
        finally:
            self._close(conn)

    def increment_skipped(self, job_id: int):
        """Mark one file as skipped (already processed)."""
        conn = self._connect()
        try:
            conn.execute('''
                UPDATE scan_jobs
                SET skipped_count = skipped_count + 1, updated_at = ?
                WHERE id = ?
            ''', (time.time(), job_id))
            conn.commit()
        finally:
            self._close(conn)

    def log_error(self, job_id: int, file_path: str,
                  error_message: str, traceback_str: str = ""):
        """Log a per-file error and bump the error counter."""
        now = time.time()
        conn = self._connect()
        try:
            conn.execute('''
                INSERT INTO scan_errors (job_id, file_path, error_message, traceback, occurred_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (job_id, file_path, error_message[:1000], traceback_str[:4000], now))
            conn.execute('''
                UPDATE scan_jobs SET error_count = error_count + 1, updated_at = ?
                WHERE id = ?
            ''', (now, job_id))
            conn.commit()
        finally:
            self._close(conn)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def get_job(self, job_id: int) -> Optional[ScanJob]:
        """Fetch a single job by ID."""
        conn = self._connect()
        try:
            row = conn.execute('SELECT * FROM scan_jobs WHERE id=?', (job_id,)).fetchone()
            if not row:
                return None
            return self._row_to_job(row)
        finally:
            self._close(conn)

    def get_latest_job(self) -> Optional[ScanJob]:
        """Get the most recent scan job."""
        conn = self._connect()
        try:
            row = conn.execute(
                'SELECT * FROM scan_jobs ORDER BY id DESC LIMIT 1'
            ).fetchone()
            if not row:
                return None
            return self._row_to_job(row)
        finally:
            self._close(conn)

    def get_resumable_job(self, target_path: str) -> Optional[ScanJob]:
        """
        Find the most recent incomplete job for the given path.
        Returns None if no resumable job exists.
        """
        conn = self._connect()
        try:
            row = conn.execute('''
                SELECT * FROM scan_jobs
                WHERE target_path = ? AND status IN ('running', 'paused', 'failed')
                ORDER BY id DESC LIMIT 1
            ''', (target_path,)).fetchone()
            if not row:
                return None
            return self._row_to_job(row)
        finally:
            self._close(conn)

    def get_errors(self, job_id: int) -> List[ScanError]:
        """Fetch all errors for a given job."""
        conn = self._connect()
        try:
            rows = conn.execute(
                'SELECT * FROM scan_errors WHERE job_id=? ORDER BY id ASC', (job_id,)
            ).fetchall()
            return [ScanError(
                id=r['id'], job_id=r['job_id'], file_path=r['file_path'],
                error_message=r['error_message'], traceback=r['traceback'] or "",
                occurred_at=r['occurred_at']
            ) for r in rows]
        finally:
            self._close(conn)

    def get_all_jobs(self, limit: int = 20) -> List[ScanJob]:
        """Fetch recent jobs."""
        conn = self._connect()
        try:
            rows = conn.execute(
                'SELECT * FROM scan_jobs ORDER BY id DESC LIMIT ?', (limit,)
            ).fetchall()
            return [self._row_to_job(r) for r in rows]
        finally:
            self._close(conn)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _update_status(self, job_id: int, status: str):
        conn = self._connect()
        try:
            conn.execute(
                'UPDATE scan_jobs SET status=?, updated_at=? WHERE id=?',
                (status, time.time(), job_id)
            )
            conn.commit()
        finally:
            self._close(conn)

    @staticmethod
    def _row_to_job(row) -> ScanJob:
        return ScanJob(
            id=row['id'],
            target_path=row['target_path'],
            status=row['status'],
            total_files=row['total_files'] or 0,
            processed_count=row['processed_count'] or 0,
            skipped_count=row['skipped_count'] or 0,
            error_count=row['error_count'] or 0,
            force_reprocess=bool(row['force_reprocess']),
            current_file=row['current_file'] or "",
            started_at=row['started_at'] or 0.0,
            updated_at=row['updated_at'] or 0.0,
            completed_at=row['completed_at'] or 0.0,
            last_processed_path=row['last_processed_path'] or "",
        )
