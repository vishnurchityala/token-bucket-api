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
    sender.add_periodic_task(TIME_GAP, refill_tokens.s(), name="refill tokens every 1s")

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
        logging.info(f"[Process] No tokens for {x}, retrying in 1s...")
        raise self.retry(countdown=2 ** self.request.retries)