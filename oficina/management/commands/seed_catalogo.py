"""Popula o catálogo de marcas e modelos de viaturas (dados de referência)."""
import re
import unicodedata

from django.core.management.base import BaseCommand

from oficina.catalogo import CATALOGO
from oficina.models import Marca, Modelo


def slugify(texto):
    t = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-zA-Z0-9]+', '-', t).strip('-').lower()


class Command(BaseCommand):
    help = 'Popula o catálogo de marcas e modelos de viaturas.'

    def handle(self, *args, **options):
        novos = 0
        for nome_marca, modelos in CATALOGO.items():
            marca, _ = Marca.objects.get_or_create(
                nome=nome_marca, defaults={'slug': slugify(nome_marca)})
            for nome_modelo in modelos:
                _, criado = Modelo.objects.get_or_create(marca=marca, nome=nome_modelo)
                novos += int(criado)
        self.stdout.write(self.style.SUCCESS(
            f'  Catálogo: {Marca.objects.count()} marcas, {Modelo.objects.count()} modelos '
            f'({novos} novos).'))
