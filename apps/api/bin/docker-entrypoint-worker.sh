#!/bin/bash
set -e

python manage.py wait_for_db
# Wait for migrations
python manage.py wait_for_migrations
# Run the processes
# Celery defaults to one prefork process per host CPU, which on Railway means
# dozens of processes and several GB of RAM. Cap it; override via env vars.
# CELERY_MAX_MEMORY_PER_CHILD is in KiB; a child is recycled once it exceeds it.
celery -A plane worker -l info \
  --concurrency="${CELERY_WORKER_CONCURRENCY:-2}" \
  --max-memory-per-child="${CELERY_MAX_MEMORY_PER_CHILD:-300000}"