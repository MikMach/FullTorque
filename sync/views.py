"""Endpoints do servidor de sync (lado CLOUD)."""
import json

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from .nucleo import aplicar_lote, recolher


def _autorizado(request):
    return request.headers.get('X-Sync-Key') == settings.SYNC_API_KEY


@csrf_exempt
def push(request):
    """A oficina envia a operação; a cloud aplica."""
    if not _autorizado(request):
        return HttpResponseForbidden('chave de sync inválida')
    if request.method != 'POST':
        return JsonResponse({'erro': 'usa POST'}, status=405)
    lote = json.loads(request.body or b'{}').get('registos', [])
    aplicados, ignorados = aplicar_lote(lote)
    return JsonResponse({'recebidos': len(lote), 'aplicados': aplicados, 'ignorados': ignorados})


@csrf_exempt
def pull(request):
    """A oficina puxa o que pertence à cloud (marcações + clientes/viaturas novos)."""
    if not _autorizado(request):
        return HttpResponseForbidden('chave de sync inválida')
    desde_raw = request.GET.get('desde', '')
    desde = parse_datetime(desde_raw) if desde_raw else None
    lote, maximo = recolher(('down', 'both'), desde)
    return JsonResponse({'registos': lote, 'maximo': maximo.isoformat() if maximo else None})
