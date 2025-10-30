from celery import shared_task
import random
from datetime import datetime

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def sample_task(self):
    """
    Runs periodically (every 10s per project/celery.py).
    Retries up to 3 times on failure, with 5s delay between retries.
    Logs successful runs to task_log.txt
    """
    try:
        print("🔁 Running periodic task...")

        # simulate an intermittent failure
        if random.choice([True, False]):
            raise ValueError("Simulated random failure")

        # on success, append to a local log file
        with open("task_log.txt", "a") as f:
            f.write(f"{datetime.now()} - Task succeeded ✅\n")

        print("✅ Task completed successfully!")
        return "Success"

    except Exception as exc:
        print(f"❌ Task failed: {exc}. Will retry in 5s (if retries left).")
        # re-raise to trigger Celery retry
        raise self.retry(exc=exc)
