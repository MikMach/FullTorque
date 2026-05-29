"""Portal do cliente: registo, dashboard e ficha de viatura (login obrigatório)."""
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from oficina.models import Viatura

from .forms import RegistoClienteForm


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
        'marcacoes': marcacoes, 'lembretes': lembretes[:6]})


@login_required
def viatura_detail(request, pk):
    viatura = get_object_or_404(Viatura, pk=pk, cliente=_cliente(request))
    return render(request, 'portal/viatura.html', {
        'viatura': viatura,
        'registos': viatura.registos.select_related('tipo_servico', 'funcionario').all(),
        'inspecoes': viatura.inspecoes.all(),
        'proximas': viatura.proximas_revisoes(),
    })
