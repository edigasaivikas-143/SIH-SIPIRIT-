"""
Lightweight async job queue for long-running AI/validation jobs
(Section 10: "Async processing — Task queue / workers").

For the hackathon MVP this runs in-process with asyncio, so the whole
stack works with zero extra infra (no Redis/Celery needed on stage).
The interface is small enough to swap for a real broker later without
touching the routes.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("ulpin3d.job_queue")


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class Job:
    job_id: str
    job_type: str
    status: JobStatus = JobStatus.QUEUED
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None


class JobQueue:
    """In-process async job queue. One worker loop drains a single queue.

    job_type examples (align with ml_pipeline modules):
      building_extraction | floor_segmentation | unit_delineation |
      underground_detection | topology_validation | change_detection
    """

    def __init__(self, max_concurrency: int = 2):
        self._queue: "asyncio.Queue[tuple[Job, Callable, tuple, dict]]" = asyncio.Queue()
        self._jobs: Dict[str, Job] = {}
        self._max_concurrency = max_concurrency
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(i)) for i in range(self._max_concurrency)
        ]
        logger.info("Job queue started with %d workers", self._max_concurrency)

    async def stop(self):
        self._running = False
        for w in self._workers:
            w.cancel()
        self._workers = []

    def submit(self, job_type: str, fn: Callable, *args, **kwargs) -> Job:
        job = Job(job_id=str(uuid.uuid4()), job_type=job_type)
        self._jobs[job.job_id] = job
        self._queue.put_nowait((job, fn, args, kwargs))
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_jobs(self):
        return list(self._jobs.values())

    async def _worker_loop(self, worker_index: int):
        while self._running:
            job, fn, args, kwargs = await self._queue.get()
            job.status = JobStatus.RUNNING
            logger.info("[worker %d] running job %s (%s)", worker_index, job.job_id, job.job_type)
            try:
                if asyncio.iscoroutinefunction(fn):
                    result = await fn(*args, **kwargs)
                else:
                    result = await asyncio.get_event_loop().run_in_executor(None, fn, *args)
                job.result = result
                job.status = JobStatus.DONE
            except Exception as e:  # noqa: BLE001 — surface any pipeline error to the job record
                logger.exception("Job %s failed", job.job_id)
                job.error = str(e)
                job.status = JobStatus.FAILED
            finally:
                job.finished_at = datetime.utcnow()
                self._queue.task_done()


# module-level singleton used by main.py and routes
job_queue = JobQueue()
