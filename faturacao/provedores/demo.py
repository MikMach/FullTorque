"""Provedor de DEMONSTRAÇÃO — NÃO é faturação real, não usar em produção.

Gera 1-2 faturas de exemplo para o cliente demo (o que entra com
cliente@fulltorque.pt), com PDF gerado na hora, só para a página "As minhas
faturas" ter conteúdo no demo. Usa o NIF real do cliente para a fatura casar
mesmo pelo caminho normal (CASADA_NIF).
"""
import io
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .base import FaturaExterna, ProvedorFaturacao


class ProvedorDemo(ProvedorFaturacao):
    nome = 'demo'

    def _cliente_demo(self):
        from oficina.models import Cliente
        return (Cliente.objects.filter(user__email='cliente@fulltorque.pt').first()
                or Cliente.objects.first())

    def listar_faturas(self, desde=None):
        cliente = self._cliente_demo()
        if cliente is None:
            return []
        hoje = timezone.localdate()
        amostras = [
            ('FT 2026/104', hoje - timedelta(days=8), Decimal('189.90')),
            ('FT 2026/072', hoje - timedelta(days=95), Decimal('420.50')),
        ]
        return [
            FaturaExterna(
                id_externo=f'DEMO-{cliente.id}-{i}', numero=numero, data=data,
                total=total, nif=cliente.nif, nome=cliente.nome, email=cliente.email)
            for i, (numero, data, total) in enumerate(amostras, start=1)
        ]

    def descarregar_pdf(self, fatura):
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (1240, 1754), (255, 255, 255))  # ~A4 a 150 dpi
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, 1240, 130), fill=(23, 23, 23))
        d.rectangle((0, 130, 1240, 138), fill=(220, 38, 38))
        d.text((60, 52), 'FULL TORQUE  —  Fatura (demonstração)', fill=(255, 255, 255))
        linhas = [
            f'Número:  {fatura.numero}',
            f'Data:    {fatura.data}',
            '',
            f'Cliente: {fatura.nome}',
            f'NIF:     {fatura.nif}',
            f'Email:   {fatura.email}',
            '',
            f'TOTAL:   {fatura.total} {fatura.moeda}',
            '',
            'Documento de demonstração — sem valor fiscal.',
            'Em produção, o PDF vem do software de faturação certificado.',
        ]
        y = 210
        for ln in linhas:
            d.text((60, y), ln, fill=(20, 20, 20))
            y += 52
        buf = io.BytesIO()
        img.save(buf, 'PDF', resolution=150.0)
        return buf.getvalue()
