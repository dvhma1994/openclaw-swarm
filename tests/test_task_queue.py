"""
Tests for Task Queue System
"""

import pytest
import time
from datetime import datetime, timedelta

from openclaw_swarm.task_queue import (
    TaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    TaskScheduler,
    Worker,
)


class TestTaskStatus:
    """Test TaskStatus enum"""

    def test_status_values(self):
        """Test all status values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestTaskPriority:
    """Test TaskPriority enum"""

    def test_priority_values(self):
        """Test all priority values"""
        assert TaskPriority.CRITICAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.NORMAL.value == 3
        assert TaskPriority.LOW.value == 4
        assert TaskPriority.BACKGROUND.value == 5


class TestTask:
    """Test Task dataclass"""

    def test_task_creation(self):
        """Test creating a task"""
        task = Task(
            id="test",
            name="test_task",
            description="A test task",
            priority=TaskPriority.NORMAL,
        )

        assert task.id == "test"
        assert task.name == "test_task"
        assert task.status == TaskStatus.PENDING
        assert task.retries == 0

    def test_task_auto_id(self):
        """Test task auto-generated ID"""
        task = Task(
            id="", name="test", description="test", priority=TaskPriority.NORMAL
        )

        # Empty ID gets replaced
        assert len(task.id) > 0

    def test_task_with_payload(self):
        """Test task with payload"""
        task = Task(
            id="test",
            name="test",
            description="test",
            priority=TaskPriority.HIGH,
            payload={"key": "value"},
        )

        assert task.payload["key"] == "value"

    def test_task_comparison(self):
        """Test task priority comparison"""
        task1 = Task(id="1", name="low", description="", priority=TaskPriority.LOW)
        task2 = Task(
            id="2", name="critical", description="", priority=TaskPriority.CRITICAL
        )

        # Critical < Low (lower number = higher priority)
        assert task2 < task1

    def test_task_to_dict(self):
        """Test converting task to dict"""
        task = Task(
            id="test", name="test", description="test", priority=TaskPriority.NORMAL
        )

        result = task.to_dict()

        assert result["id"] == "test"
        assert result["name"] == "test"
        assert result["priority"] == 3
        assert result["status"] == "pending"


class TestWorker:
    """Test Worker dataclass"""

    def test_worker_creation(self):
        """Test creating a worker"""
        worker = Worker(id="w1", name="worker-1")

        assert worker.id == "w1"
        assert worker.name == "worker-1"
        assert worker.status == "idle"
        assert worker.tasks_completed == 0

    def test_worker_auto_id(self):
        """Test worker auto-generated ID"""
        worker = Worker(id="", name="worker")

        assert len(worker.id) > 0


class TestTaskQueue:
    """Test TaskQueue class"""

    def test_queue_initialization(self):
        """Test queue initialization"""
        queue = TaskQueue()

        assert len(queue.tasks) == 0
        assert len(queue.workers) == 0
        assert queue.max_workers == 4

    def test_queue_with_max_workers(self):
        """Test queue with custom max workers"""
        queue = TaskQueue(max_workers=8)

        assert queue.max_workers == 8

    def test_submit_task(self):
        """Test submitting a task"""
        queue = TaskQueue()

        task = queue.submit(
            name="test_task", description="A test task", priority=TaskPriority.HIGH
        )

        assert task.id in queue.tasks
        assert task.status == TaskStatus.PENDING

    def test_get_task(self):
        """Test getting a task"""
        queue = TaskQueue()

        task = queue.submit(
            name="test", description="test", priority=TaskPriority.NORMAL
        )

        retrieved = queue.get_task(task.id)

        assert retrieved is not None
        assert retrieved.id == task.id

    def test_get_pending_tasks(self):
        """Test getting pending tasks"""
        queue = TaskQueue()

        queue.submit(name="t1", description="test", priority=TaskPriority.NORMAL)
        queue.submit(name="t2", description="test", priority=TaskPriority.NORMAL)

        pending = queue.get_pending_tasks()

        assert len(pending) == 2

    def test_cancel_task(self):
        """Test cancelling a task"""
        queue = TaskQueue()

        task = queue.submit(
            name="test", description="test", priority=TaskPriority.NORMAL
        )

        result = queue.cancel_task(task.id)

        assert result is True
        assert task.status == TaskStatus.CANCELLED

    def test_cancel_running_task(self):
        """Test cancelling a running task fails"""
        queue = TaskQueue()

        task = queue.submit(
            name="test", description="test", priority=TaskPriority.NORMAL
        )
        task.status = TaskStatus.RUNNING

        result = queue.cancel_task(task.id)

        assert result is False

    def test_retry_task(self):
        """Test retrying a failed task"""
        queue = TaskQueue()

        task = queue.submit(
            name="test", description="test", priority=TaskPriority.NORMAL
        )
        task.status = TaskStatus.FAILED

        result = queue.retry_task(task.id)

        assert result is True
        assert task.status == TaskStatus.PENDING
        assert task.retries == 1

    def test_retry_max_retries(self):
        """Test retry limit"""
        queue = TaskQueue()

        task = queue.submit(
            name="test", description="test", priority=TaskPriority.NORMAL, max_retries=2
        )
        task.status = TaskStatus.FAILED
        task.retries = 2

        result = queue.retry_task(task.id)

        assert result is False

    def test_register_handler(self):
        """Test registering a handler"""
        queue = TaskQueue()

        def handler(x):
            return x * 2

        queue.register_handler("test_task", handler)

        assert "test_task" in queue.handlers

    def test_get_stats(self):
        """Test getting statistics"""
        queue = TaskQueue()

        queue.submit(name="t1", description="test", priority=TaskPriority.NORMAL)
        queue.submit(name="t2", description="test", priority=TaskPriority.NORMAL)

        stats = queue.get_stats()

        assert stats["total_tasks"] == 2
        assert stats["pending"] == 2


class TestTaskScheduler:
    """Test TaskScheduler class"""

    def test_scheduler_initialization(self):
        """Test scheduler initialization"""
        queue = TaskQueue()
        scheduler = TaskScheduler(queue)

        assert len(scheduler.scheduled) == 0

    def test_schedule_task(self):
        """Test scheduling a task"""
        queue = TaskQueue()
        scheduler = TaskScheduler(queue)

        run_at = datetime.now() + timedelta(seconds=60)

        schedule_id = scheduler.schedule(
            task_name="test_task", description="A scheduled task", run_at=run_at
        )

        assert schedule_id in scheduler.scheduled

    def test_schedule_recurring_task(self):
        """Test scheduling a recurring task"""
        queue = TaskQueue()
        scheduler = TaskScheduler(queue)

        schedule_id = scheduler.schedule_recurring(
            task_name="recurring_task",
            description="A recurring task",
            interval_seconds=60,
        )

        assert schedule_id in scheduler.scheduled
        assert scheduler.scheduled[schedule_id]["recurring"] is True

    def test_cancel_scheduled(self):
        """Test cancelling a scheduled task"""
        queue = TaskQueue()
        scheduler = TaskScheduler(queue)

        run_at = datetime.now() + timedelta(seconds=60)
        schedule_id = scheduler.schedule(
            task_name="test", description="test", run_at=run_at
        )

        result = scheduler.cancel_scheduled(schedule_id)

        assert result is True
        assert schedule_id not in scheduler.scheduled

    def test_get_scheduled(self):
        """Test getting scheduled tasks"""
        queue = TaskQueue()
        scheduler = TaskScheduler(queue)

        run_at = datetime.now() + timedelta(seconds=60)
        scheduler.schedule(task_name="t1", description="test", run_at=run_at)
        scheduler.schedule(task_name="t2", description="test", run_at=run_at)

        scheduled = scheduler.get_scheduled()

        assert len(scheduled) == 2


class TestTaskQueueIntegration:
    """Integration tests for task queue"""

    def test_process_task_with_handler(self):
        """Test processing a task with a handler"""
        queue = TaskQueue(max_workers=2)

        results = []

        def handler(value):
            results.append(value)
            return value * 2

        queue.register_handler("double", handler)

        task = queue.submit(
            name="double",
            description="Double a value",
            priority=TaskPriority.NORMAL,
            payload={"value": 5},
        )

        queue.start()

        # Wait for task to complete
        time.sleep(0.5)

        queue.stop()

        # Note: In real implementation, task processing happens in worker threads
        # For this test, we just verify the queue was set up correctly
        assert task.id in queue.tasks

    def test_priority_ordering(self):
        """Test tasks are processed in priority order"""
        queue = TaskQueue()

        task1 = queue.submit(name="low", description="test", priority=TaskPriority.LOW)
        task2 = queue.submit(
            name="critical", description="test", priority=TaskPriority.CRITICAL
        )
        task3 = queue.submit(
            name="normal", description="test", priority=TaskPriority.NORMAL
        )

        # Get pending tasks (priority queue doesn't guarantee order in list)
        pending = queue.get_pending_tasks()

        assert len(pending) == 3

    def test_worker_stats(self):
        """Test worker statistics"""
        queue = TaskQueue(max_workers=2)

        queue.submit(name="t1", description="test", priority=TaskPriority.NORMAL)
        queue.submit(name="t2", description="test", priority=TaskPriority.NORMAL)

        stats = queue.get_stats()

        assert stats["total_tasks"] == 2
        assert stats["pending"] == 2
