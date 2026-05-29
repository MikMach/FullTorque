"""Seleção do provedor de faturação a partir das settings.

Adicionar um software novo = criar um ficheiro aqui com uma classe que herda
`ProvedorFaturacao` e registá-lo no `obter_provedor()`.
"""
from django.conf import settings

from .base import FaturaExterna, ProvedorFaturacao  # noqa: F401 (reexport)


def obter_provedor(nome=None):
    """Devolve uma instância do provedor, ou None se nenhum estiver configurado."""
    nome = (nome or getattr(settings, 'FATURACAO_PROVIDER', '') or '').strip().lower()
    if not nome:
        return None
    if nome == 'demo':
        from .demo import ProvedorDemo
        return ProvedorDemo()
    if nome == 'invoicexpress':
        from .invoicexpress import ProvedorInvoiceXpress
        return ProvedorInvoiceXpress()
    if nome == 'moloni':
        from .moloni import ProvedorMoloni
        return ProvedorMoloni()
    raise ValueError(f'Software de faturação desconhecido: {nome!r}')
