"""Puxar faturas de um provedor, cruzar com o cliente e gravar (com PDF)."""
from django.core.files.base import ContentFile
from django.utils import timezone

from .correspondencia import casar_cliente
from .models import EstadoFaturacao, Fatura
from .provedores import obter_provedor


def puxar(provedor=None, com_pdf=True, registar=None):
    """Puxa faturas novas. Devolve (criadas, por_resolver).

    `provedor`: força um provedor pelo nome; se None usa FATURACAO_PROVIDER.
    `registar`: função opcional de log (recebe strings).
    """
    def log(msg):
        if registar:
            registar(msg)

    prov = obter_provedor(provedor)
    if prov is None:
        log('Sem software de faturação configurado (FATURACAO_PROVIDER vazio) — nada a fazer.')
        return 0, 0

    estado, _ = EstadoFaturacao.objects.get_or_create(provedor=prov.nome)
    criadas = por_resolver = 0

    for fx in prov.listar_faturas(desde=estado.ultimo):
        if Fatura.objects.filter(provedor=prov.nome, id_externo=fx.id_externo).exists():
            continue  # já a temos — não duplica

        cliente, estado_corr = casar_cliente(fx.nif, fx.email, fx.nome)
        fatura = Fatura(
            provedor=prov.nome, id_externo=fx.id_externo, numero=fx.numero or '',
            data=fx.data, total=fx.total, moeda=fx.moeda or 'EUR',
            nif=fx.nif or '', nome=fx.nome or '', email=fx.email or '',
            pdf_url=fx.pdf_url or '', cliente=cliente, estado=estado_corr)

        if com_pdf:
            try:
                dados = prov.descarregar_pdf(fx)
                if dados:
                    nome_ficheiro = f'{prov.nome}-{fx.id_externo}.pdf'.replace('/', '-')
                    fatura.pdf.save(nome_ficheiro, ContentFile(dados), save=False)
            except NotImplementedError:
                pass  # provedor ainda sem download — guarda só os metadados/URL

        fatura.save()
        criadas += 1
        if cliente is None:
            por_resolver += 1
        log(f'  + {fatura} → {cliente.nome if cliente else "POR RESOLVER"}')

    estado.ultimo = timezone.now()
    estado.save(update_fields=['ultimo'])
    return criadas, por_resolver
