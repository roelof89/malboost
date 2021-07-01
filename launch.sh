#!/bin/bash

redis-server --port 6380 &
celery -A app.celery worker --loglevel=debug -f celery.log --without-gossip --without-mingle --without-heartbeat -Ofair --pool=solo &
gunicorn -w 4 -p pidfile --access-logfile gcorn.log -D app:app &
