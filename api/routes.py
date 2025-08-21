from fastapi import APIRouter
from celery.result import AsyncResult
from api.celery_workers import process_request, app as celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/process/{x}")
def enqueue_task(x: int):
    task = process_request.delay(x)
    return {"task_id": task.id, "status": "queued"}

@router.get("/status/{task_id}")
def get_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None
    }