"""Dados do painel inicial do admin (Unfold DASHBOARD_CALLBACK)."""
from datetime import timedelta

from django.utils import timezone

from .models import Marcacao, Orcamento, RegistoServico, Viatura


def dashboard_callback(request, context):
    hoje = timezone.localdate()
    em_30_dias = hoje + timedelta(days=30)
    inicio_mes = hoje.replace(day=1)

    ipo_vencer = (
        Viatura.objects
        .filter(inspecao_valida_ate__gte=hoje, inspecao_valida_ate__lte=em_30_dias)
        .select_related('marca', 'modelo', 'cliente')
        .order_by('inspecao_valida_ate')
    )
    orc_pendentes = (
        Orcamento.objects
        .filter(estado__in=[Orcamento.Estado.RASCUNHO, Orcamento.Estado.ENVIADO])
        .select_related('viatura', 'cliente')
        .order_by('-criado_em')
    )

    context.update({
        'kpis': [
            {'icon': 'directions_car', 'value': Viatura.objects.count(), 'label': 'Viaturas'},
            {'icon': 'build', 'value': RegistoServico.objects.filter(data_servico__gte=inicio_mes).count(), 'label': 'Serviços este mês'},
            {'icon': 'event', 'value': Marcacao.objects.filter(estado__in=[Marcacao.Estado.PENDENTE, Marcacao.Estado.CONFIRMADA]).count(), 'label': 'Marcações ativas'},
            {'icon': 'request_quote', 'value': orc_pendentes.count(), 'label': 'Orçamentos pendentes'},
        ],
        'ipo_vencer': list(ipo_vencer[:8]),
        'ipo_vencer_total': ipo_vencer.count(),
        'ipo_expirada_total': Viatura.objects.filter(inspecao_valida_ate__lt=hoje).count(),
        'orc_pendentes': list(orc_pendentes[:8]),
    })
    return context
