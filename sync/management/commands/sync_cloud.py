"""Sincroniza a oficina (local) com a cloud.

Corre no servidor LOCAL (periodicamente, ex.: cron). Envia a operação para a
cloud (push) e puxa as marcações/clientes novos (pull). Se a internet estiver
em baixo, falha em silêncio e recupera na próxima ronda (a marca de água garante
que nada se perde).
"""
import base64
import json
import urllib.error
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from oficina.models import FotoOrdem, FotoRegisto
from sync.models import SyncEstado
from sync.nucleo import aplicar_lote, recolher


class Command(BaseCommand):
    help = 'Sincroniza a oficina (local) com a cloud: envia operação e puxa marcações.'

    def add_arguments(self, parser):
        parser.add_argument('--cloud-url', default=settings.SYNC_CLOUD_URL)
        parser.add_argument('--key', default=settings.SYNC_API_KEY)

    def handle(self, *args, **opts):
        base = (opts['cloud_url'] or '').rstrip('/')
        if not base:
            self.stderr.write('Define SYNC_CLOUD_URL (ou --cloud-url).')
            return
        chave = opts['key']
        try:
            self._push(base, chave)
            self._enviar_ficheiros(base, chave)
            self._pull(base, chave)
        except urllib.error.URLError as exc:
            self.stderr.write(f'Cloud inacessível ({exc}). Recupera na próxima ronda.')

    def _pedido(self, url, chave, dados=None):
        corpo = json.dumps(dados).encode() if dados is not None else None
        req = urllib.request.Request(
            url, data=corpo, method='POST' if dados is not None else 'GET',
            headers={'X-Sync-Key': chave, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def _push(self, base, chave):
        marca = SyncEstado.marca('push')
        lote, maximo = recolher(('up', 'both'), marca.ultimo)
        if not lote:
            self.stdout.write('Push: nada novo.')
            return
        resp = self._pedido(f'{base}/sync/push/', chave, {'registos': lote})
        marca.ultimo = maximo
        marca.save()
        self.stdout.write(self.style.SUCCESS(
            f"Push: {len(lote)} enviados → {resp.get('aplicados')} aplicados, {resp.get('ignorados')} ignorados."))

    def _pull(self, base, chave):
        marca = SyncEstado.marca('pull')
        desde = marca.ultimo.isoformat() if marca.ultimo else ''
        resp = self._pedido(f'{base}/sync/pull/?desde={desde}', chave)
        lote = resp.get('registos', [])
        if lote:
            aplicados, ignorados = aplicar_lote(lote)
            self.stdout.write(self.style.SUCCESS(
                f'Pull: {len(lote)} recebidos → {aplicados} aplicados, {ignorados} ignorados.'))
        else:
            self.stdout.write('Pull: nada novo.')
        if resp.get('maximo'):
            marca.ultimo = parse_datetime(resp['maximo'])
            marca.save()

    def _enviar_ficheiros(self, base, chave):
        """Envia para a cloud as fotos cujo ficheiro ainda não foi enviado."""
        enviados = 0
        for Modelo in (FotoRegisto, FotoOrdem):
            for foto in Modelo.objects.filter(ficheiro_enviado=False).exclude(imagem=''):
                try:
                    with foto.imagem.open('rb') as fh:
                        conteudo = base64.b64encode(fh.read()).decode()
                except (FileNotFoundError, ValueError, OSError):
                    continue
                try:
                    resp = self._pedido(f'{base}/sync/ficheiro/', chave, {
                        'modelo': Modelo.__name__, 'uuid': str(foto.uuid),
                        'nome': foto.imagem.name.rsplit('/', 1)[-1], 'conteudo': conteudo})
                except urllib.error.HTTPError:
                    continue  # cloud ainda sem o registo; tenta na próxima ronda
                if resp.get('ok'):
                    Modelo.objects.filter(pk=foto.pk).update(ficheiro_enviado=True)
                    enviados += 1
        self.stdout.write(self.style.SUCCESS(f'Ficheiros: {enviados} foto(s) enviada(s).')
                          if enviados else 'Ficheiros: nada novo.')
