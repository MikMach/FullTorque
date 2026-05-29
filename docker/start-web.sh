#!/usr/bin/env sh
# Arranque do serviço web (servidor local da oficina).
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_catalogo            # catálogo de marcas/modelos (idempotente)

if [ "$SEED_DEMO" = "1" ]; then
    python manage.py seed_demo            # dados de demonstração (só se pedido)
fi

exec gunicorn fulltorque.wsgi --bind 0.0.0.0:8000 --workers 3
