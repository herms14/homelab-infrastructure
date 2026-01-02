"""
Sentinel Bot Database Layer
Async SQLite database for task queue, update history, and download tracking.
"""

import logging
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

logger = logging.getLogger('sentinel.database')


class Database:
    """Async SQLite database manager."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize database and create tables."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info(f"Database initialized at {self.db_path}")

    async def _create_tables(self) -> None:
        """Create all required tables."""
        await self._connection.executescript('''
            -- Claude Tasks (from Athena)
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                instance_id TEXT,
                instance_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                claimed_at TIMESTAMP,
                completed_at TIMESTAMP,
                notes TEXT,
                submitted_by TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);

            -- Task Audit Log
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER REFERENCES tasks(id),
                action TEXT NOT NULL,
                details TEXT,
                instance_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Claude Instance Registry
            CREATE TABLE IF NOT EXISTS instances (
                id TEXT PRIMARY KEY,
                name TEXT,
                last_seen TIMESTAMP,
                current_task_id INTEGER,
                status TEXT DEFAULT 'idle'
            );

            -- Container Update History
            CREATE TABLE IF NOT EXISTS update_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_name TEXT NOT NULL,
                host_ip TEXT NOT NULL,
                old_image TEXT,
                new_image TEXT,
                update_status TEXT,
                updated_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_updates_container ON update_history(container_name);
            CREATE INDEX IF NOT EXISTS idx_updates_status ON update_history(update_status);

            -- Download Tracking
            CREATE TABLE IF NOT EXISTS download_tracking (
                id TEXT PRIMARY KEY,
                media_type TEXT NOT NULL,
                title TEXT NOT NULL,
                poster_url TEXT,
                size_bytes INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified_milestones TEXT DEFAULT '[]',
                completed_at TIMESTAMP
            );

            -- Service Onboarding Status Cache
            CREATE TABLE IF NOT EXISTS onboarding_cache (
                service_name TEXT PRIMARY KEY,
                terraform_ok INTEGER DEFAULT 0,
                ansible_ok INTEGER DEFAULT 0,
                dns_ok INTEGER DEFAULT 0,
                traefik_ok INTEGER DEFAULT 0,
                ssl_ok INTEGER DEFAULT 0,
                authentik_ok INTEGER,
                docs_ok INTEGER DEFAULT 0,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        await self._connection.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            logger.info("Database connection closed")

    # ==================== Task Queue Methods ====================

    async def create_task(
        self,
        description: str,
        priority: str = 'medium',
        submitted_by: str = None
    ) -> int:
        """Create a new task and return its ID."""
        cursor = await self._connection.execute(
            '''INSERT INTO tasks (description, priority, submitted_by, status)
               VALUES (?, ?, ?, 'pending')''',
            (description, priority, submitted_by)
        )
        await self._connection.commit()
        task_id = cursor.lastrowid

        await self._log_task_action(task_id, 'created', f'Priority: {priority}')
        return task_id

    async def get_pending_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending tasks ordered by priority."""
        priority_order = "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END"
        cursor = await self._connection.execute(
            f'''SELECT * FROM tasks WHERE status = 'pending'
                ORDER BY {priority_order}, created_at ASC LIMIT ?''',
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get the next available task (highest priority, oldest first)."""
        tasks = await self.get_pending_tasks(limit=1)
        return tasks[0] if tasks else None

    async def claim_task(
        self,
        task_id: int,
        instance_id: str,
        instance_name: str = None
    ) -> bool:
        """Claim a task for processing. Returns True if successful."""
        cursor = await self._connection.execute(
            '''UPDATE tasks SET status = 'in_progress', instance_id = ?,
               instance_name = ?, claimed_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status = 'pending' ''',
            (instance_id, instance_name, task_id)
        )
        await self._connection.commit()

        if cursor.rowcount > 0:
            await self._log_task_action(task_id, 'claimed', f'Instance: {instance_name}', instance_id)
            return True
        return False

    async def complete_task(
        self,
        task_id: int,
        instance_id: str,
        notes: str = None
    ) -> bool:
        """Mark a task as completed."""
        cursor = await self._connection.execute(
            '''UPDATE tasks SET status = 'completed', notes = ?,
               completed_at = CURRENT_TIMESTAMP
               WHERE id = ? AND instance_id = ?''',
            (notes, task_id, instance_id)
        )
        await self._connection.commit()

        if cursor.rowcount > 0:
            await self._log_task_action(task_id, 'completed', notes, instance_id)
            return True
        return False

    async def cancel_task(self, task_id: int) -> bool:
        """Cancel a pending task."""
        cursor = await self._connection.execute(
            '''UPDATE tasks SET status = 'cancelled'
               WHERE id = ? AND status = 'pending' ''',
            (task_id,)
        )
        await self._connection.commit()

        if cursor.rowcount > 0:
            await self._log_task_action(task_id, 'cancelled')
            return True
        return False

    async def get_completed_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently completed tasks."""
        cursor = await self._connection.execute(
            '''SELECT * FROM tasks WHERE status = 'completed'
               ORDER BY completed_at DESC LIMIT ?''',
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_task_stats(self) -> Dict[str, int]:
        """Get task queue statistics."""
        cursor = await self._connection.execute(
            '''SELECT status, COUNT(*) as count FROM tasks GROUP BY status'''
        )
        rows = await cursor.fetchall()
        return {row['status']: row['count'] for row in rows}

    async def reset_stale_tasks(self, hours: int = 2) -> int:
        """Reset tasks stuck in_progress for more than X hours."""
        cursor = await self._connection.execute(
            '''UPDATE tasks SET status = 'pending', instance_id = NULL,
               instance_name = NULL, claimed_at = NULL
               WHERE status = 'in_progress'
               AND claimed_at < datetime('now', ? || ' hours')''',
            (f'-{hours}',)
        )
        await self._connection.commit()
        return cursor.rowcount

    async def _log_task_action(
        self,
        task_id: int,
        action: str,
        details: str = None,
        instance_id: str = None
    ) -> None:
        """Log a task action."""
        await self._connection.execute(
            '''INSERT INTO task_logs (task_id, action, details, instance_id)
               VALUES (?, ?, ?, ?)''',
            (task_id, action, details, instance_id)
        )
        await self._connection.commit()

    # ==================== Instance Registry Methods ====================

    async def update_instance_heartbeat(
        self,
        instance_id: str,
        instance_name: str,
        status: str = 'idle'
    ) -> None:
        """Update or create instance heartbeat."""
        await self._connection.execute(
            '''INSERT OR REPLACE INTO instances (id, name, last_seen, status)
               VALUES (?, ?, CURRENT_TIMESTAMP, ?)''',
            (instance_id, instance_name, status)
        )
        await self._connection.commit()

    async def get_active_instances(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get instances active in the last X minutes."""
        cursor = await self._connection.execute(
            '''SELECT * FROM instances
               WHERE last_seen > datetime('now', ? || ' minutes')''',
            (f'-{minutes}',)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ==================== Update History Methods ====================

    async def record_update(
        self,
        container_name: str,
        host_ip: str,
        status: str = 'pending',
        updated_by: str = None
    ) -> int:
        """Record a container update."""
        cursor = await self._connection.execute(
            '''INSERT INTO update_history (container_name, host_ip, update_status, updated_by)
               VALUES (?, ?, ?, ?)''',
            (container_name, host_ip, status, updated_by)
        )
        await self._connection.commit()
        return cursor.lastrowid

    async def update_update_status(
        self,
        update_id: int,
        status: str,
        completed: bool = False
    ) -> None:
        """Update the status of an update record."""
        if completed:
            await self._connection.execute(
                '''UPDATE update_history SET update_status = ?, completed_at = CURRENT_TIMESTAMP
                   WHERE id = ?''',
                (status, update_id)
            )
        else:
            await self._connection.execute(
                '''UPDATE update_history SET update_status = ? WHERE id = ?''',
                (status, update_id)
            )
        await self._connection.commit()

    async def get_recent_updates(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent update history."""
        cursor = await self._connection.execute(
            '''SELECT * FROM update_history ORDER BY created_at DESC LIMIT ?''',
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ==================== Download Tracking Methods ====================

    async def start_download_tracking(
        self,
        download_id: str,
        media_type: str,
        title: str,
        poster_url: str = None,
        size_bytes: int = None
    ) -> None:
        """Start tracking a download (preserves existing milestones)."""
        await self._connection.execute(
            '''INSERT OR IGNORE INTO download_tracking
               (id, media_type, title, poster_url, size_bytes, notified_milestones)
               VALUES (?, ?, ?, ?, ?, '[]')''',
            (download_id, media_type, title, poster_url, size_bytes)
        )
        await self._connection.commit()

    async def get_download_milestones(self, download_id: str) -> List[int]:
        """Get notified milestones for a download."""
        cursor = await self._connection.execute(
            '''SELECT notified_milestones FROM download_tracking WHERE id = ?''',
            (download_id,)
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row['notified_milestones'])
        return []

    async def add_download_milestone(self, download_id: str, milestone: int) -> None:
        """Add a milestone to the notified list."""
        milestones = await self.get_download_milestones(download_id)
        if milestone not in milestones:
            milestones.append(milestone)
            await self._connection.execute(
                '''UPDATE download_tracking SET notified_milestones = ? WHERE id = ?''',
                (json.dumps(milestones), download_id)
            )
            await self._connection.commit()

    async def complete_download(self, download_id: str) -> None:
        """Mark a download as completed."""
        await self._connection.execute(
            '''UPDATE download_tracking SET completed_at = CURRENT_TIMESTAMP WHERE id = ?''',
            (download_id,)
        )
        await self._connection.commit()

    async def cleanup_old_downloads(self, hours: int = 24) -> int:
        """Remove completed downloads older than X hours."""
        cursor = await self._connection.execute(
            '''DELETE FROM download_tracking
               WHERE completed_at IS NOT NULL
               AND completed_at < datetime('now', ? || ' hours')''',
            (f'-{hours}',)
        )
        await self._connection.commit()
        return cursor.rowcount
