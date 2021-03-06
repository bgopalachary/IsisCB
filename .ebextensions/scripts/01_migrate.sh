#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Migrating...'
  #source /opt/python/run/venv/bin/activate
  source /var/app/venv/staging-LQM1lest/bin/activate
  pip install -r requirements.txt
  cd isiscb
  python manage.py migrate auth --noinput
  python manage.py migrate --noinput
  python manage.py createcachetable
else
  echo 'The script 01_migrate.sh is only executed in non-docker environments.'
fi
