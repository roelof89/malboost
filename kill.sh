#!/bin/bash

pkill celer
pkill -9 -f 'celery'
pkill gunicorn
pkill redis-server
cat pidfile | xargs kill -9