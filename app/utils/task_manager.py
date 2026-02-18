"""In-memory async task manager for tracking pipeline jobs."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from loguru import logger

from app.models.schemas import (
    TaskStatus,
    TaskStatusResponse,
    PipelineStage,
    ProcessingResult,
)


class TaskManager:
    """Simple in-memory task store.  Replace with Redis / DB for production."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskStatusResponse] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, task_id: str) -> TaskStatusResponse:
        task = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            current_stage=PipelineStage.UPLOAD,
            progress_pct=0.0,
            created_at=datetime.utcnow(),
        )
        async with self._lock:
            self._tasks[task_id] = task
        logger.info(f"Task created: {task_id}")
        return task

    async def update_stage(
        self, task_id: str, stage: PipelineStage, progress: float
    ) -> None:
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].current_stage = stage
                self._tasks[task_id].progress_pct = min(progress, 100.0)
                self._tasks[task_id].status = TaskStatus.PROCESSING
        logger.debug(f"Task {task_id}: stage={stage.value}, progress={progress:.0f}%")

    async def complete_task(self, task_id: str, result: ProcessingResult) -> None:
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.COMPLETED
                self._tasks[task_id].current_stage = PipelineStage.DONE
                self._tasks[task_id].progress_pct = 100.0
                self._tasks[task_id].result = result
                self._tasks[task_id].completed_at = datetime.utcnow()
        logger.info(f"Task completed: {task_id}")

    async def fail_task(self, task_id: str, error: str) -> None:
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.FAILED
                self._tasks[task_id].error = error
                self._tasks[task_id].completed_at = datetime.utcnow()
        logger.error(f"Task failed: {task_id} — {error}")

    async def get_task(self, task_id: str) -> TaskStatusResponse | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def delete_task(self, task_id: str) -> bool:
        async with self._lock:
            return self._tasks.pop(task_id, None) is not None
