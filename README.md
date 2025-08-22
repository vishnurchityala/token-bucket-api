## Asynchronous Token Bucket Rate Limiter

This project demonstrates the implementation of a scalable, asynchronous token bucket rate-limiting system for a FastAPI API. This architecture is designed to manage and control the flow of requests, preventing system overload and ensuring fair access to limited resources, a critical practice in modern backend development.

### Core Concepts

- **Token Bucket Algorithm:** This classic rate-limiting algorithm simulates a bucket with a finite capacity that holds "tokens." Requests consume tokens from the bucket. If a request arrives when the bucket is empty, it is rejected or, in this case, retried. Tokens are added to the bucket at a fixed rate, ensuring a steady, predictable flow of traffic.
- **Asynchronous Processing:** The system is designed to handle tasks in the background, freeing up the main API server. This is achieved using Celery, a distributed task queue, which allows the API to quickly enqueue tasks without waiting for them to complete.
- **Message Broker:** Redis serves as the message broker, facilitating communication between the FastAPI application and the Celery workers. It also acts as the central state store for the token bucket, ensuring a single, synchronized source of truth across all workers.

### Architecture and Components

The system is composed of two main components that communicate via Redis:
- FastAPI API: The user-facing component that receives requests. Instead of processing them directly, it enqueues them as asynchronous tasks to the Celery queue. It also provides endpoints to track the status of these tasks.
- Celery Workers: The backend workers that process the tasks. Each worker checks the Redis token bucket before processing a request. If a token is available, the request is processed; if not, it is put back in the queue to be retried later.

### Key Implementations

- Token Management: A dedicated Celery periodic task (Celery Beat) is configured to automatically and continuously refill the token bucket at a specified interval. This ensures a consistent token supply, regardless of the traffic volume.
- Resource Throttling: The core process_request task checks the token count in Redis. It uses a retry mechanism to handle a "no token" scenario, gracefully re-queuing the task to be processed when a token becomes available. This prevents task failure and ensures eventual completion.
- Live Status Monitoring: The FastAPI API includes an endpoint to check the live status of any task by its ID, providing real-time visibility into the task's progress and results.

### Code Implementation

#### Celery Queue and Beat
This component manages the token bucket and the background task processing. It uses Celery Beat for periodic token refills and a task that consumes a token for each request.


```
import time
import redis
from celery import Celery
import logging

app = Celery("process_queue", broker="redis://localhost:6379/0")
r = redis.Redis()


BUCKET_KEY = "token_bucket"
MAX_TOKENS = 10
REFILL_AMOUNT = 2 
TIME_GAP = 10.0

@app.on_after_configure.connect
def periodic_token_add(sender,**kwargs):
    sender.add_periodic_task(TIME_GAP, refill_tokens.s(), name="refill tokens every 10s")

@app.task
def refill_tokens():
    current = int(r.get(BUCKET_KEY) or 0)
    new_value = min(MAX_TOKENS, current + REFILL_AMOUNT)
    r.set(BUCKET_KEY, new_value)
    logging.info(f"[Refill] Tokens now: {new_value}")

@app.task(bind=True, max_retries=None)
def process_request(self, x):
    tokens = int(r.get(BUCKET_KEY) or 0)
    if tokens > 0:
        r.decr(BUCKET_KEY)
        logging.info(f"[Process] Got token, processing {x}")
        time.sleep(10)
        logging.info(f"[Process] Done {x}")
        return f"Processed {x}"

    else:
        logging.info(f"[Process] No tokens for {x}, retrying in...{2}")
        raise self.retry(countdown=2)
```

#### FastAPI API

This component serves as the interface for clients, allowing them to submit tasks and check their status. It leverages the Celery tasks defined above.


```
from fastapi import APIRouter
from celery.result import AsyncResult

# Import the celery task and app from the worker file
from api.celery_workers import process_request, app as celery_app

# Create an API router with a base prefix for all task-related endpoints
router = APIRouter(prefix="/tasks", tags=["tasks"])

# POST endpoint to enqueue a new task
@router.post("/process/{x}")
def enqueue_task(x: int):
    """
    Enqueues a new request processing task and returns its ID.
    """
    # Use .delay() to send the task to the Celery queue
    task = process_request.delay(x)
    return {"task_id": task.id, "status": "queued"}

# GET endpoint to check the status of a specific task
@router.get("/status/{task_id}")
def get_status(task_id: str):
    """
    Retrieves the current status and result of a task by its ID.
    """
    # Create an AsyncResult object to query the task state
    result = AsyncResult(task_id, app=celery_app)
    # Check if the task has completed
    if result.ready():
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result
        }
    else:
        return {
            "task_id": task_id,
            "status": result.status,
            "result": None
        }
```