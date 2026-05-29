"""Contrato que todo o software de faturação tem de cumprir."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class FaturaExterna:
    """Uma fatura tal como vem do software, antes de a cruzarmos com o cliente."""
    id_externo: str
    numero: str = ''
    data: date = None
    total: Decimal = None
    moeda: str = 'EUR'
    nif: str = ''
    nome: str = ''
    email: str = ''
    pdf_url: str = ''


class ProvedorFaturacao:
    """Interface. Cada software concreto implementa estes dois métodos."""
    nome = ''

    def listar_faturas(self, desde=None):
        """Devolve um iterável de FaturaExterna emitidas/atualizadas desde `desde`."""
        raise NotImplementedError

    def descarregar_pdf(self, fatura):
        """Devolve os bytes do PDF de uma FaturaExterna (ou levanta NotImplementedError)."""
        raise NotImplementedError
