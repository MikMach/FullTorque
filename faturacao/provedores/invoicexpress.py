"""InvoiceXpress — ESQUELETO (por ligar).

Software certificado pela AT. API REST+JSON, autenticada por `api_key` na query
string; a conta fica no subdomínio: https://<conta>.app.invoicexpress.com/...
Docs: https://invoicexpress.com/api/

Quando o Rui escolher este software, preencher os dois métodos com as chamadas
reais. Credenciais via settings: FATURACAO_API_KEY (api_key) e FATURACAO_CONTA
(subdomínio da conta).
"""
from django.conf import settings

from .base import ProvedorFaturacao


class ProvedorInvoiceXpress(ProvedorFaturacao):
    nome = 'invoicexpress'

    def __init__(self):
        self.api_key = getattr(settings, 'FATURACAO_API_KEY', '')
        self.conta = getattr(settings, 'FATURACAO_CONTA', '')

    def _base_url(self):
        return f'https://{self.conta}.app.invoicexpress.com'

    def listar_faturas(self, desde=None):
        # TODO: GET {base}/invoices.json?api_key={api_key}&... (paginado)
        #       filtrar por data >= `desde`; para cada fatura, mapear -> FaturaExterna,
        #       incluindo NIF/nome/email do cliente e o link do PDF (permalink).
        raise NotImplementedError('InvoiceXpress: listar_faturas() por implementar.')

    def descarregar_pdf(self, fatura):
        # TODO: GET do PDF (endpoint /api/pdf/{id}.json -> devolve um URL temporário;
        #       descarregar esse URL) -> devolver bytes.
        raise NotImplementedError('InvoiceXpress: descarregar_pdf() por implementar.')
