"""Puxa as faturas do software de faturação e associa-as aos clientes.

Corre na CLOUD (onde está o portal), idealmente agendado (ex.: a cada hora):

    python manage.py puxar_faturas

Escolhe o software com a env FATURACAO_PROVIDER (ou --provedor para forçar).
"""
from django.core.management.base import BaseCommand

from faturacao.ingestao import puxar


class Command(BaseCommand):
    help = 'Puxa faturas do software de faturação (API) e associa-as aos clientes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provedor', default=None,
            help="Força o provedor (ex.: 'demo', 'invoicexpress', 'moloni'). "
                 'Por omissão usa a env FATURACAO_PROVIDER.')
        parser.add_argument(
            '--sem-pdf', action='store_true',
            help='Não descarrega os PDFs (só metadados).')

    def handle(self, *args, **options):
        criadas, por_resolver = puxar(
            provedor=options['provedor'],
            com_pdf=not options['sem_pdf'],
            registar=lambda m: self.stdout.write(m))
        msg = f'✓ {criadas} fatura(s) nova(s)'
        if por_resolver:
            msg += f' — {por_resolver} POR RESOLVER (atribuir no admin)'
        self.stdout.write(self.style.SUCCESS(msg + '.'))
