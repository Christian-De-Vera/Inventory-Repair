import logging
import os
import threading
import time

from django.db import connection

logger = logging.getLogger(__name__)


def _keepalive_loop(interval):
    while True:
        time.sleep(interval)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            logger.warning("DB keep-alive ping failed", exc_info=True)


def start_keepalive_thread(interval=None):
    """Keep the database compute awake by pinging it on a fixed interval.

    Neon (and other serverless Postgres) autosuspend idle compute, which makes
    the first request after inactivity take many seconds (cold start). A short,
    regular ping prevents the compute from ever idling. Runs as a daemon thread
    inside each gunicorn worker, so it ships with a normal git pull + restart.
    """
    if interval is None:
        interval = int(os.environ.get("DB_KEEPALIVE_SECONDS", "60"))
    if interval <= 0:
        return
    thread = threading.Thread(target=_keepalive_loop, args=(interval,), daemon=True)
    thread.name = "db-keepalive"
    thread.start()
    logger.info("Started DB keep-alive thread (interval=%ss)", interval)
