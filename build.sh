#!/usr/bin/env bash
# Build de deploy (Render / Railway). Definir como "Build Command".
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_demo   # idempotente: só semeia se a BD estiver vazia
