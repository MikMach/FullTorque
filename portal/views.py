"""Portal do cliente: registo, dashboard e ficha de viatura (login obrigatório)."""
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from faturacao.models import Fatura
from oficina.models import OrdemTrabalho, Viatura

from .forms import RegistoClienteForm

ESTADOS_FECHADOS = [OrdemTrabalho.Estado.CONCLUIDA, OrdemTrabalho.Estado.CANCELADA]


def register(request):
    if request.user.is_authenticated:
        return redirect('portal:dashboard')
    if request.method == 'POST':
        form = RegistoClienteForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('portal:dashboard')
    else:
        form = RegistoClienteForm()
    return render(request, 'portal/register.html', {'form': form})


def _cliente(request):
    return getattr(request.user, 'cliente', None)


@login_required
def dashboard(request):
    cliente = _cliente(request)
    if cliente is None:
        return render(request, 'portal/sem_perfil.html')

    viaturas = list(cliente.viaturas.select_related('marca', 'modelo').all())
    marcacoes = cliente.marcacoes.select_related('tipo_servico', 'local').order_by('data_hora')
    ordens_ativas = (OrdemTrabalho.objects.filter(viatura__cliente=cliente)
                     .exclude(estado__in=ESTADOS_FECHADOS)
                     .select_related('viatura', 'viatura__marca', 'viatura__modelo'))

    lembretes = []
    for v in viaturas:
        if v.inspecao_valida_ate:
            lembretes.append({'viatura': v, 'tipo': 'Inspeção (IPO)', 'data': v.inspecao_valida_ate})
        for p in v.proximas_revisoes():
            if p['proxima_data']:
                lembretes.append({'viatura': v, 'tipo': p['tipo_servico'].nome, 'data': p['proxima_data']})
    lembretes.sort(key=lambda x: x['data'])

    return render(request, 'portal/dashboard.html', {
        'cliente': cliente, 'viaturas': viaturas,
        'marcacoes': marcacoes, 'lembretes': lembretes[:6], 'ordens_ativas': ordens_ativas})


@login_required
def viatura_detail(request, pk):
    viatura = get_object_or_404(Viatura, pk=pk, cliente=_cliente(request))
    ordem = viatura.ordens.exclude(estado__in=ESTADOS_FECHADOS).order_by('-criado_em').first()
    return render(request, 'portal/viatura.html', {
        'viatura': viatura,
        'registos': viatura.registos.select_related('tipo_servico', 'funcionario').all(),
        'inspecoes': viatura.inspecoes.all(),
        'proximas': viatura.proximas_revisoes(),
        'ordem_ativa': ordem,
        'fotos_ordem': list(ordem.fotos.all()) if ordem else [],
        'extras_ordem': list(ordem.itens.filter(fora_orcamento=True)) if ordem else [],
    })


@login_required
def faturas(request):
    cliente = _cliente(request)
    if cliente is None:
        return render(request, 'portal/sem_perfil.html')
    return render(request, 'portal/faturas.html', {
        'cliente': cliente, 'faturas': cliente.faturas.all()})


@login_required
def fatura_pdf(request, pk):
    """Descarrega o PDF — só o dono da fatura lhe pode aceder."""
    cliente = _cliente(request)
    if cliente is None:
        raise Http404
    fatura = get_object_or_404(Fatura, pk=pk, cliente=cliente)
    if fatura.pdf:
        return FileResponse(
            fatura.pdf.open('rb'), as_attachment=True,
            filename=f'fatura-{fatura.pk}.pdf', content_type='application/pdf')
    if fatura.pdf_url:
        return redirect(fatura.pdf_url)
    raise Http404
