"""
Background Task Management System
Handles background task execution, progress tracking, and database persistence.
"""

import threading
import time
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from logging_config import get_logger
from budget_db_postgres import BudgetDb


class BackgroundTaskManager:
    """Manages background task execution and status"""
    
    def __init__(self, db: BudgetDb):
        self.db = db
        self.logger = get_logger(f'{__name__}.BackgroundTaskManager')
        self._current_task_lock = threading.Lock()
        self._current_task_thread = None
        self._shutdown_requested = False
        
    def create_task(self, task_type: str, task_name: str, user_id: int, 
                   total: int = 0, metadata: Dict[str, Any] = None) -> int:
        """
        Create a new background task
        Returns the task ID
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO background_tasks 
                    (task_type, task_name, status, total, user_id, result_data)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (task_type, task_name, 'pending', total, user_id, 
                     json.dumps(metadata or {})))
                
                task_id = cur.fetchone()[0]
                self.db.conn.commit()
                
                self.logger.info(f"Created background task {task_id}: {task_name}")
                return task_id
                
        except Exception as e:
            self.logger.error(f"Failed to create background task: {e}")
            self.db.conn.rollback()
            raise
    
    def is_task_running(self) -> bool:
        """Check if any task is currently running"""
        with self._current_task_lock:
            # Check if thread exists and is alive
            if self._current_task_thread and self._current_task_thread.is_alive():
                return True
            
            # If thread is dead or None, clean up any stuck running tasks  
            if self._current_task_thread is not None and not self._current_task_thread.is_alive():
                self.logger.warning("Found dead thread, cleaning up stuck tasks")
                self._current_task_thread = None
                self._cleanup_stuck_tasks()
            
            return False
    
    def _cleanup_stuck_tasks(self):
        """Clean up tasks that are marked as running but have no active thread"""
        try:
            cur = self.db.conn.cursor()
            cur.execute("""
                UPDATE background_tasks 
                SET status = 'failed', 
                    error_message = 'Task thread died unexpectedly',
                    completed_at = NOW()
                WHERE status = 'running'
            """)
            self.db.conn.commit()
            self.logger.info("Cleaned up stuck running tasks")
        except Exception as e:
            self.logger.error(f"Failed to cleanup stuck tasks: {e}")
    
    def recover_system(self):
        """Recover the background task system from inconsistent state"""
        with self._current_task_lock:
            if self._current_task_thread and not self._current_task_thread.is_alive():
                self._current_task_thread = None
            self._cleanup_stuck_tasks()
    
    def get_running_task(self) -> Optional[Dict[str, Any]]:
        """Get the currently running task info"""
        try:
            with self.db.get_cursor() as cur:
                cur.execute("""
                    SELECT id, task_type, task_name, status, progress, total, 
                           current_item, created_at, started_at
                    FROM background_tasks 
                    WHERE status = 'running'
                    ORDER BY started_at DESC 
                    LIMIT 1
                """)
                
                row = cur.fetchone()
                if not row:
                    return None
                
                return {
                    'id': row[0],
                    'task_type': row[1],
                    'task_name': row[2],
                    'status': row[3],
                    'progress': row[4],
                    'total': row[5],
                    'current_item': row[6],
                    'created_at': row[7].isoformat() if row[7] else None,
                    'started_at': row[8].isoformat() if row[8] else None
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get running task: {e}")
            return None
    
    def get_task_status(self, task_id: int) -> Dict[str, Any]:
        """Get the current status of a task"""
        try:
            with self.db.get_cursor() as cur:
                cur.execute("""
                    SELECT id, task_type, task_name, status, progress, total, 
                           current_item, result_data, error_message,
                           created_at, started_at, completed_at
                    FROM background_tasks 
                    WHERE id = %s
                """, (task_id,))
                
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Task {task_id} not found")
                
                result_data = {}
                if row[7]:  # result_data
                    try:
                        result_data = json.loads(row[7])
                    except (json.JSONDecodeError, TypeError):
                        result_data = {'raw': row[7]}
                
                return {
                    'id': row[0],
                    'task_type': row[1],
                    'task_name': row[2],
                    'status': row[3],
                    'progress': row[4],
                    'total': row[5],
                    'current_item': row[6],
                    'result_data': result_data,
                    'error_message': row[8],
                    'created_at': row[9].isoformat() if row[9] else None,
                    'started_at': row[10].isoformat() if row[10] else None,
                    'completed_at': row[11].isoformat() if row[11] else None
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get task status for {task_id}: {e}")
            raise
    
    def get_all_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all tasks, most recent first"""
        try:
            with self.db.get_cursor() as cur:
                cur.execute("""
                    SELECT id, task_type, task_name, status, progress, total, 
                           current_item, result_data, error_message,
                           created_at, started_at, completed_at
                    FROM background_tasks 
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                
                tasks = []
                for row in cur.fetchall():
                    result_data = {}
                    if row[7]:  # result_data
                        try:
                            result_data = json.loads(row[7])
                        except (json.JSONDecodeError, TypeError):
                            result_data = {'raw': row[7]}
                    
                    tasks.append({
                        'id': row[0],
                        'task_type': row[1],
                        'task_name': row[2],
                        'status': row[3],
                        'progress': row[4],
                        'total': row[5],
                        'current_item': row[6],
                        'result_data': result_data,
                        'error_message': row[8],
                        'created_at': row[9].isoformat() if row[9] else None,
                        'started_at': row[10].isoformat() if row[10] else None,
                        'completed_at': row[11].isoformat() if row[11] else None
                    })
                
                return tasks
                
        except Exception as e:
            self.logger.error(f"Failed to get all tasks: {e}")
            return []
    
    def start_task(self, task_id: int):
        """Mark task as started"""
        try:
            with self.db.get_cursor() as cur:
                cur.execute("""
                    UPDATE background_tasks 
                    SET status = 'running', started_at = NOW()
                    WHERE id = %s
                """, (task_id,))
                self.db.conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to start task {task_id}: {e}")
            raise
    
    def update_task_progress(self, task_id: int, progress: int, current_item: str = None):
        """Update task progress"""
        try:
            with self.db.get_cursor() as cur:
                cur.execute("""
                    UPDATE background_tasks 
                    SET progress = %s, current_item = %s
                    WHERE id = %s
                """, (progress, current_item, task_id))
                self.db.conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to update task {task_id} progress: {e}")
    
    def complete_task(self, task_id: int, result_data: Dict[str, Any] = None):
        """Mark task as completed"""
        try:
            with self.db.get_cursor() as cur:
                cur.execute("""
                    UPDATE background_tasks 
                    SET status = 'completed', completed_at = NOW(), progress = total,
                        result_data = %s
                    WHERE id = %s
                """, (json.dumps(result_data or {}), task_id))
                self.db.conn.commit()
                self.logger.info(f"Completed task {task_id}")
        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {e}")
            raise
    
    def fail_task(self, task_id: int, error_message: str):
        """Mark task as failed"""
        try:
            with self.db.get_cursor() as cur:
                cur.execute("""
                    UPDATE background_tasks 
                    SET status = 'failed', completed_at = NOW(), error_message = %s
                    WHERE id = %s
                """, (error_message, task_id))
                self.db.conn.commit()
                self.logger.error(f"Failed task {task_id}: {error_message}")
        except Exception as e:
            self.logger.error(f"Failed to fail task {task_id}: {e}")
            raise
    
    def execute_task(self, task_id: int, task_function: Callable, *args, **kwargs):
        """Execute a task in a background thread"""
        if self.is_task_running():
            raise Exception("Another task is already running")
        
        def task_runner():
            try:
                self.logger.info(f"Starting task {task_id}")
                self.start_task(task_id)
                
                # Create progress callback
                def progress_callback(current: int, total: int, current_item: str = None):
                    progress = int((current / total) * 100) if total > 0 else 0
                    self.update_task_progress(task_id, progress, current_item)
                
                # Execute the actual task
                result = task_function(progress_callback, *args, **kwargs)
                
                # Ensure result is valid
                if result is None:
                    result = {'message': 'Task completed successfully'}
                
                self.complete_task(task_id, result)
                self.logger.info(f"Completed task {task_id}")
                
            except Exception as e:
                self.logger.error(f"Task {task_id} failed: {e}")
                import traceback
                self.logger.error(f"Task {task_id} traceback: {traceback.format_exc()}")
                self.fail_task(task_id, str(e))
            
            finally:
                # Ensure thread reference is always cleared
                with self._current_task_lock:
                    if self._current_task_thread and self._current_task_thread == threading.current_thread():
                        self._current_task_thread = None
                self.logger.info(f"Cleaned up task thread for task {task_id}")
        
        with self._current_task_lock:
            self._current_task_thread = threading.Thread(target=task_runner, name=f"BackgroundTask-{task_id}")
            self._current_task_thread.daemon = True
            self._current_task_thread.start()
    
    def shutdown(self):
        """Shutdown the task manager gracefully"""
        self._shutdown_requested = True
        
        with self._current_task_lock:
            if self._current_task_thread and self._current_task_thread.is_alive():
                # Give the thread time to finish naturally
                self._current_task_thread.join(timeout=30.0)


class AutoClassificationTask:
    """Auto-classification background task implementation"""
    
    def __init__(self, db: BudgetDb, logic):
        self.db = db
        self.logic = logic
        self.logger = get_logger(f'{__name__}.AutoClassificationTask')
    
    def run(self, progress_callback: Callable, confidence_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Execute auto-classification task
        Returns result data with classification statistics
        """
        try:
            # Store the progress callback for the logic method
            self.progress_callback = progress_callback
            
            # Use the existing auto_classify_uncategorized method
            # Note: confidence_threshold is not used by the logic method currently
            result = self.logic.auto_classify_uncategorized(
                progress_callback=self.progress_callback
            )
            
            # Return classification statistics
            return {
                'message': 'Auto-classification completed successfully',
                'result': result or 'No uncategorized transactions to classify'
            }
            
        except Exception as e:
            self.logger.error(f"Auto-classification failed: {e}")
            raise
