"""Site público: homepage e marcação online (com disponibilidade + notificações)."""
from datetime import date, datetime

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from oficina.models import Cliente, Local, Marcacao, Modelo, Viatura

from .forms import MarcacaoPublicaForm, horas_disponiveis


def home(request):
    """Homepage pública."""
    return render(request, 'site_publico/home.html')


def _notificar_marcacao(marcacao):
    """Envia email de confirmação ao cliente e alerta à oficina (consola em dev)."""
    detalhe = (
        f'Serviço: {marcacao.tipo_servico}\n'
        f'Oficina: {marcacao.local}\n'
        f'Data: {marcacao.data_hora:%d/%m/%Y às %H:%M}\n'
        f'Viatura: {marcacao.viatura.matricula}\n'
        f'Referência: #{marcacao.pk}'
    )
    if marcacao.cliente.email:
        send_mail(
            'Marcação recebida — Full Torque',
            f'Olá {marcacao.cliente.nome},\n\nRecebemos o teu pedido de marcação:\n\n{detalhe}\n\n'
            'Entraremos em contacto para confirmar.\n\n— Full Torque',
            None, [marcacao.cliente.email], fail_silently=True)
    destino = marcacao.local.email or settings.DEFAULT_FROM_EMAIL
    send_mail(
        f'Nova marcação #{marcacao.pk} — {marcacao.local}',
        f'Novo pedido de marcação:\n\n{detalhe}\n\n'
        f'Cliente: {marcacao.cliente.nome} ({marcacao.cliente.telefone})',
        None, [destino], fail_silently=True)


def marcar(request):
    """Marcação online (sem login; pré-preenche se for cliente autenticado)."""
    cliente_user = None
    initial = {}
    if request.user.is_authenticated and hasattr(request.user, 'cliente'):
        cliente_user = request.user.cliente
        initial = {'nome': cliente_user.nome, 'telefone': cliente_user.telefone, 'email': cliente_user.email}

    if request.method == 'POST':
        form = MarcacaoPublicaForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            cliente = cliente_user or Cliente.objects.filter(email=cd['email']).first()
            if cliente is None:
                cliente = Cliente.objects.create(
                    nome=cd['nome'], telefone=cd['telefone'], email=cd['email'])

            viatura, _ = Viatura.objects.get_or_create(
                matricula=cd['matricula'],
                defaults={'cliente': cliente, 'local': cd['local'],
                          'marca': cd['marca'], 'modelo': cd['modelo'], 'ano': cd['ano']})

            hora_h, hora_m = (int(x) for x in cd['hora'].split(':'))
            quando = timezone.make_aware(
                datetime.combine(cd['data'], datetime.min.time()).replace(hour=hora_h, minute=hora_m),
                timezone.get_current_timezone())

            marcacao = Marcacao.objects.create(
                cliente=cliente, viatura=viatura, local=cd['local'],
                tipo_servico=cd['tipo_servico'], data_hora=quando,
                estado=Marcacao.Estado.PENDENTE, notas=cd['notas'])
            _notificar_marcacao(marcacao)
            return redirect('site_publico:marcacao_confirmada', pk=marcacao.pk)
        messages.error(request, 'Há erros no formulário. Revê os campos assinalados.')
    else:
        form = MarcacaoPublicaForm(initial=initial)

    return render(request, 'site_publico/marcar.html', {'form': form})


def horas(request):
    """Endpoint HTMX: opções de hora disponíveis para a oficina + data escolhidas."""
    opcoes = []
    local_id, data_str = request.GET.get('local'), request.GET.get('data')
    if local_id and data_str:
        try:
            local = Local.objects.get(pk=local_id, ativo=True)
            opcoes = horas_disponiveis(local, date.fromisoformat(data_str))
        except (Local.DoesNotExist, ValueError):
            opcoes = []
    return render(request, 'site_publico/_hora_options.html', {'opcoes': opcoes})


def modelos_por_marca(request):
    """Endpoint HTMX: devolve os <option> de modelos da marca escolhida."""
    marca_id = request.GET.get('marca')
    modelos = Modelo.objects.filter(marca_id=marca_id, ativo=True) if marca_id else Modelo.objects.none()
    return render(request, 'site_publico/_modelo_options.html', {'modelos': modelos})


def marcacao_confirmada(request, pk):
    marcacao = get_object_or_404(Marcacao, pk=pk)
    return render(request, 'site_publico/marcacao_confirmada.html', {'marcacao': marcacao})
