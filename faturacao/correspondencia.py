"""Cruzar uma fatura com o cliente certo — sem nunca cair no cliente errado.

Regra (por ordem):
  1. NIF exato e ÚNICO        -> casa (estado CASADA_NIF)
  2. senão email exato e ÚNICO -> casa (estado CASADA_EMAIL)
  3. senão (0 ou vários)       -> fica POR_RESOLVER (o dono resolve no admin)

O nome NUNCA casa sozinho (é ambíguo); serve só para ajudar a decidir no admin.
"""
from oficina.models import Cliente

from .models import Fatura


def casar_cliente(nif='', email='', nome=''):
    """Devolve (cliente_ou_None, estado)."""
    nif = (nif or '').strip()
    if nif:
        qs = Cliente.objects.filter(nif=nif)
        if qs.count() == 1:
            return qs.first(), Fatura.Estado.CASADA_NIF

    email = (email or '').strip()
    if email:
        qs = Cliente.objects.filter(email__iexact=email)
        if qs.count() == 1:
            return qs.first(), Fatura.Estado.CASADA_EMAIL

    return None, Fatura.Estado.POR_RESOLVER
