#!/usr/bin/env sh
# Sincroniza com a cloud em ciclo. Se a internet falhar, recupera na ronda seguinte.
while true; do
    python manage.py sync_cloud || true
    sleep "${SYNC_INTERVALO:-120}"
done
