"""Moloni — ESQUELETO (por ligar).

Software certificado pela AT. API REST com OAuth2 (access_token + refresh_token).
Docs: https://www.moloni.pt/dev/

Quando o Rui escolher este software, preencher os dois métodos. Credenciais via
settings: FATURACAO_API_KEY (pode guardar o refresh_token/credenciais) e
FATURACAO_CONTA (company_id). Convém guardar/renovar o access_token.
"""
from django.conf import settings

from .base import ProvedorFaturacao


class ProvedorMoloni(ProvedorFaturacao):
    nome = 'moloni'

    def __init__(self):
        self.credenciais = getattr(settings, 'FATURACAO_API_KEY', '')
        self.company_id = getattr(settings, 'FATURACAO_CONTA', '')

    def listar_faturas(self, desde=None):
        # TODO: obter access_token (OAuth2) -> POST {api}/invoices/getAll/ com company_id
        #       e filtro de data >= `desde`; mapear cada documento -> FaturaExterna
        #       (NIF/nome/email do cliente + link/identificador do PDF).
        raise NotImplementedError('Moloni: listar_faturas() por implementar.')

    def descarregar_pdf(self, fatura):
        # TODO: POST {api}/documents/getPDF/ (ou getLink) -> descarregar -> bytes.
        raise NotImplementedError('Moloni: descarregar_pdf() por implementar.')
