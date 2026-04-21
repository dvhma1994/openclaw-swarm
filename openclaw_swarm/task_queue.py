"""
OpenClaw Swarm - Task Queue System
Priority-based task queue with workers
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import PriorityQueue
import uuid


class TaskStatus(Enum):
    """Task status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class Task:
    """A task in the queue"""

    id: str
    name: str
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    max_retries: int = 3
    timeout: int = 300  # seconds

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.id:
            self.id = str(uuid.uuid4())

    def __lt__(self, other):
        """For priority queue comparison"""
        return self.priority.value < other.priority.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "payload": self.payload,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "retries": self.retries,
            "max_retries": self.max_retries,
        }


@dataclass
class Worker:
    """A worker that processes tasks"""

    id: str
    name: str
    status: str = "idle"
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


class TaskQueue:
    """Priority-based task queue"""

    def __init__(self, max_workers: int = 4):
        self.queue: PriorityQueue = PriorityQueue()
        self.tasks: Dict[str, Task] = {}
        self.workers: Dict[str, Worker] = {}
        self.max_workers = max_workers
        self.handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._running = False
        self._worker_threads: List[threading.Thread] = []

    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a task type"""
        self.handlers[task_type] = handler

    def submit(
        self,
        name: str,
        description: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout: int = 300,
    ) -> Task:
        """Submit a task to the queue"""
        task = Task(
            id="",
            name=name,
            description=description,
            priority=priority,
            payload=payload or {},
            max_retries=max_retries,
            timeout=timeout,
        )

        with self._lock:
            self.tasks[task.id] = task
            self.queue.put(task)

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.tasks.get(task_id)

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks"""
        return [
            task for task in self.tasks.values() if task.status == TaskStatus.PENDING
        ]

    def get_running_tasks(self) -> List[Task]:
        """Get all running tasks"""
        return [
            task for task in self.tasks.values() if task.status == TaskStatus.RUNNING
        ]

    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks"""
        return [
            task for task in self.tasks.values() if task.status == TaskStatus.COMPLETED
        ]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        task = self.tasks.get(task_id)

        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True

        return False

    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        task = self.tasks.get(task_id)

        if (
            task
            and task.status == TaskStatus.FAILED
            and task.retries < task.max_retries
        ):
            task.status = TaskStatus.PENDING
            task.retries += 1
            task.error = None

            with self._lock:
                self.queue.put(task)

            return True

        return False

    def _process_task(self, task: Task, worker: Worker):
        """Process a single task"""
        worker.status = "busy"
        worker.current_task = task.id
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            # Find handler
            handler = self.handlers.get(task.name)

            if handler:
                result = handler(**task.payload)
                task.result = result
                task.status = TaskStatus.COMPLETED
                worker.tasks_completed += 1
            else:
                # No handler - just mark as completed
                task.result = {"status": "no_handler", "task": task.name}
                task.status = TaskStatus.COMPLETED
                worker.tasks_completed += 1

        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            worker.tasks_failed += 1

            # Auto-retry if possible
            if task.retries < task.max_retries:
                task.retries += 1
                task.status = TaskStatus.PENDING
                with self._lock:
                    self.queue.put(task)

        finally:
            task.completed_at = datetime.now()
            worker.status = "idle"
            worker.current_task = None

    def _worker_loop(self, worker: Worker):
        """Worker thread main loop"""
        while self._running:
            try:
                # Get task with timeout
                task = self.queue.get(timeout=1.0)

                if task.status == TaskStatus.CANCELLED:
                    continue

                self._process_task(task, worker)

            except:
                # Queue empty or timeout
                continue

    def start(self):
        """Start the task queue"""
        if self._running:
            return

        self._running = True

        # Create workers
        for i in range(self.max_workers):
            worker = Worker(id="", name=f"worker-{i}")
            self.workers[worker.id] = worker

            thread = threading.Thread(
                target=self._worker_loop, args=(worker,), daemon=True
            )
            thread.start()
            self._worker_threads.append(thread)

    def stop(self, wait: bool = True):
        """Stop the task queue"""
        self._running = False

        if wait:
            for thread in self._worker_threads:
                thread.join(timeout=5.0)

        self._worker_threads.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            "total_tasks": len(self.tasks),
            "pending": len(self.get_pending_tasks()),
            "running": len(self.get_running_tasks()),
            "completed": len(self.get_completed_tasks()),
            "failed": len(
                [t for t in self.tasks.values() if t.status == TaskStatus.FAILED]
            ),
            "cancelled": len(
                [t for t in self.tasks.values() if t.status == TaskStatus.CANCELLED]
            ),
            "workers": len(self.workers),
            "active_workers": len(
                [w for w in self.workers.values() if w.status == "busy"]
            ),
        }


class TaskScheduler:
    """Schedule tasks for future execution"""

    def __init__(self, queue: TaskQueue):
        self.queue = queue
        self.scheduled: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def schedule(
        self,
        task_name: str,
        description: str,
        run_at: datetime,
        priority: TaskPriority = TaskPriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Schedule a task for future execution"""
        schedule_id = str(uuid.uuid4())

        self.scheduled[schedule_id] = {
            "id": schedule_id,
            "task_name": task_name,
            "description": description,
            "run_at": run_at,
            "priority": priority,
            "payload": payload or {},
            "submitted": False,
        }

        return schedule_id

    def schedule_recurring(
        self,
        task_name: str,
        description: str,
        interval_seconds: int,
        priority: TaskPriority = TaskPriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Schedule a recurring task"""
        schedule_id = str(uuid.uuid4())

        self.scheduled[schedule_id] = {
            "id": schedule_id,
            "task_name": task_name,
            "description": description,
            "interval_seconds": interval_seconds,
            "priority": priority,
            "payload": payload or {},
            "recurring": True,
            "next_run": datetime.now(),
            "submitted": False,
        }

        return schedule_id

    def cancel_scheduled(self, schedule_id: str) -> bool:
        """Cancel a scheduled task"""
        if schedule_id in self.scheduled:
            del self.scheduled[schedule_id]
            return True
        return False

    def _scheduler_loop(self):
        """Scheduler main loop"""
        while self._running:
            now = datetime.now()

            for schedule_id, schedule in list(self.scheduled.items()):
                if schedule.get("submitted"):
                    continue

                run_at = schedule.get("run_at")
                next_run = schedule.get("next_run")

                should_run = False

                if run_at and now >= run_at:
                    should_run = True
                elif next_run and now >= next_run:
                    should_run = True

                if should_run:
                    # Submit task
                    self.queue.submit(
                        name=schedule["task_name"],
                        description=schedule["description"],
                        priority=schedule["priority"],
                        payload=schedule["payload"],
                    )

                    if schedule.get("recurring"):
                        # Update next run time
                        schedule["next_run"] = datetime.now() + timedelta(
                            seconds=schedule["interval_seconds"]
                        )
                    else:
                        schedule["submitted"] = True

            time.sleep(1.0)

    def start(self):
        """Start the scheduler"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def get_scheduled(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks"""
        return list(self.scheduled.values())
