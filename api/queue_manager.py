import asyncio
from models import Job

class JobQueue:
    def __init__(self, max_size=100):
        self.queue = asyncio.PriorityQueue(maxsize=max_size)

    async def push(self, job: Job):
        # PriorityQueue uses (priority, item). Lower number is higher priority.
        # We assume job.priority is higher = more important? 
        # Usually 1 is high, 10 is low. Let's assume user follows standard convention or adjust.
        # If user code says priority=10 (default), maybe 1 is higher.
        # Let's just store (priority, job).
        # Note: Job object needs to be comparable if priorities are equal.
        # We can wrap it in a tuple.
        await self.queue.put((job.priority, job))

    async def pop(self) -> Job:
        _, job = await self.queue.get()
        return job

    def size(self):
        return self.queue.qsize()

    def empty(self):
        return self.queue.empty()

job_queue = JobQueue()
