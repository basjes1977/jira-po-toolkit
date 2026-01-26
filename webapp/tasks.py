"""
Simple task manager using SQLite for background task tracking.

No Redis, no Celery - just SQLite and threading for simplicity.
"""

import sqlite3
import threading
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# SQLite database file in current working directory
DB_PATH = Path.cwd() / '.jira_tool_tasks.db'


class TaskManager:
    """Simple task manager using SQLite for persistence."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Create tasks table if it doesn't exist."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT,
                status TEXT,
                progress TEXT,
                created_at TEXT,
                updated_at TEXT,
                params TEXT,
                result TEXT,
                error TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"Task database initialized at {DB_PATH}")

    def create_task(self, task_type: str, params: Dict[str, Any]) -> str:
        """
        Create a new task and start background thread.

        Args:
            task_type: Type of task ('powerpoint', 'forecast', etc.)
            params: Task parameters dict

        Returns:
            task_id: UUID string
        """
        task_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            INSERT INTO tasks (id, type, status, progress, created_at, updated_at, params)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, task_type, 'queued', '', now, now, json.dumps(params)))
        conn.commit()
        conn.close()

        logger.info(f"Created task {task_id} (type={task_type})")

        # Start background thread
        thread = threading.Thread(target=self._run_task, args=(task_id,))
        thread.daemon = True
        thread.start()

        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status and result.

        Args:
            task_id: UUID string

        Returns:
            Task dict or None if not found
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0],
                'type': row[1],
                'status': row[2],
                'progress': row[3],
                'created_at': row[4],
                'updated_at': row[5],
                'params': json.loads(row[6]) if row[6] else {},
                'result': json.loads(row[7]) if row[7] else None,
                'error': row[8]
            }
        return None

    def update_task(self, task_id: str, **updates):
        """
        Update task fields.

        Args:
            task_id: UUID string
            **updates: Fields to update (status, progress, result, error)
        """
        conn = sqlite3.connect(DB_PATH)
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [datetime.utcnow().isoformat(), task_id]

        conn.execute(f'''
            UPDATE tasks SET {set_clause}, updated_at = ? WHERE id = ?
        ''', values)
        conn.commit()
        conn.close()

    def _run_task(self, task_id: str):
        """
        Execute task in background thread.

        Args:
            task_id: UUID string
        """
        try:
            task = self.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            logger.info(f"Starting task {task_id} (type={task['type']})")
            self.update_task(task_id, status='running')

            # Dispatch based on type
            if task['type'] == 'powerpoint':
                result = self._run_powerpoint(task_id, task['params'])
            elif task['type'] == 'forecast':
                result = self._run_forecast(task_id, task['params'])
            elif task['type'] == 'sanity_check_refine':
                result = self._run_sanity_check_refine(task_id, task['params'])
            elif task['type'] == 'sanity_check_ready':
                result = self._run_sanity_check_ready(task_id, task['params'])
            else:
                raise ValueError(f"Unknown task type: {task['type']}")

            if result['success']:
                logger.info(f"Task {task_id} completed successfully")
                self.update_task(task_id, status='completed', result=json.dumps(result))
            else:
                logger.error(f"Task {task_id} failed: {result.get('error')}")
                self.update_task(task_id, status='failed', error=result.get('error', 'Unknown error'))

        except Exception as e:
            logger.exception(f"Task {task_id} failed with exception")
            self.update_task(task_id, status='failed', error=str(e))

    def _run_powerpoint(self, task_id: str, params: Dict) -> Dict:
        """Run PowerPoint generation using core module."""
        try:
            from core.powerpoint import generate_sprint_presentation

            def progress_callback(message):
                self.update_task(task_id, progress=message)

            result = generate_sprint_presentation(
                sprint_id=params.get('sprint_id'),
                output_dir=Path.cwd(),
                progress_callback=progress_callback
            )

            # Convert Path to string for JSON serialization
            if result.get('file_path'):
                result['file_path'] = str(result['file_path'])

            return result

        except Exception as e:
            logger.exception("PowerPoint generation failed")
            return {'success': False, 'error': str(e)}

    def _run_forecast(self, task_id: str, params: Dict) -> Dict:
        """Run forecast generation using core module."""
        try:
            from core.forecast import generate_sprint_forecast

            def progress_callback(message):
                self.update_task(task_id, progress=message)

            result = generate_sprint_forecast(
                team_availability=params.get('team_availability', {}),
                output_dir=Path.cwd(),
                max_sprints=params.get('max_sprints', 10),
                progress_callback=progress_callback
            )

            # Convert Path to string for JSON serialization
            if result.get('file_path'):
                result['file_path'] = str(result['file_path'])

            return result

        except Exception as e:
            logger.exception("Forecast generation failed")
            return {'success': False, 'error': str(e)}

    def _run_sanity_check_refine(self, task_id: str, params: Dict) -> Dict:
        """Run 'To Refine' sanity check (Phase 2)."""
        return {
            'success': False,
            'error': 'Sanity check not yet implemented (Phase 2)'
        }

    def _run_sanity_check_ready(self, task_id: str, params: Dict) -> Dict:
        """Run 'Ready' sanity check (Phase 2)."""
        return {
            'success': False,
            'error': 'Sanity check not yet implemented (Phase 2)'
        }


# Global instance
task_manager = TaskManager()
