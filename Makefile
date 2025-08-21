.PHONY: run stop worker beat api redis clean

redis:
	@echo "Starting Redis Server..."
	brew services start redis
	@echo "Redis Server Started"

worker:
	@echo "Starting Celery Worker..."
	celery -A api.celery_workers.app worker -l info

beat:
	@echo "Starting Celery Beat..."
	celery -A api.celery_workers.app beat -l info

api:
	@echo "Starting FastAPI..."
	uvicorn main:app --reload --port 8080

run:
	@echo "Starting All Services..."
	brew services start redis
	celery -A api.celery_workers.app worker -l info & \
	celery -A api.celery_workers.app beat -l info & \
	uvicorn main:app --reload --port 8080 &
	@echo "All services started"

stop:
	@echo "Stopping Services..."
	-pkill -f "celery -A api.celery_workers.app worker"
	-pkill -f "celery -A api.celery_workers.app beat"
	-pkill -f "uvicorn main:app"
	brew services stop redis
	@echo "All services stopped"

clean:
	@echo "Removing Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Cleanup complete"
