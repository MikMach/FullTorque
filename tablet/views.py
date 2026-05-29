"""Tablet do funcionário: gerir ordens de trabalho (tempo, fotos, extras)."""
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from oficina.models import (
    Funcionario, FotoOrdem, ItemOrdem, Marcacao, OrdemTrabalho, Peca, Viatura,
)


def funcionario_required(view):
    @wraps(view)
    @login_required(login_url='tablet:login')
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_superuser or hasattr(request.user, 'funcionario')):
            return redirect('tablet:login')
        return view(request, *args, **kwargs)
    return wrapper


def _funcionario(request):
    return getattr(request.user, 'funcionario', None)


def _func_sessao(request, ordem):
    """Funcionário a atribuir à sessão (fallback para o dono/superuser sem perfil)."""
    return _funcionario(request) or ordem.funcionario or Funcionario.objects.first()


def _ctx(request, ordem):
    return {
        'ordem': ordem,
        'func': _funcionario(request),
        'fotos': ordem.fotos.select_related('item').all(),
        'extras': ordem.itens.all(),
        'pecas': Peca.objects.filter(ativo=True),
        'categorias': FotoOrdem.Categoria.choices,
    }


def _dec(valor, omissao='0'):
    try:
        return Decimal((valor or omissao).replace(',', '.'))
    except (InvalidOperation, AttributeError):
        return Decimal(omissao)


@funcionario_required
def inicio(request):
    ordens = (OrdemTrabalho.objects
              .exclude(estado__in=[OrdemTrabalho.Estado.CONCLUIDA, OrdemTrabalho.Estado.CANCELADA])
              .select_related('viatura', 'viatura__marca', 'viatura__modelo', 'funcionario')
              .order_by('-criado_em'))
    hoje = timezone.localdate()
    marcacoes = (Marcacao.objects
                 .filter(data_hora__date=hoje,
                         estado__in=[Marcacao.Estado.PENDENTE, Marcacao.Estado.CONFIRMADA],
                         ordens__isnull=True)
                 .select_related('viatura', 'cliente', 'tipo_servico')
                 .order_by('data_hora'))
    return render(request, 'tablet/inicio.html', {
        'func': _funcionario(request), 'ordens': ordens, 'marcacoes': marcacoes})


@funcionario_required
def ordem(request, pk):
    o = get_object_or_404(OrdemTrabalho, pk=pk)
    return render(request, 'tablet/ordem.html', _ctx(request, o))


@funcionario_required
def iniciar(request, pk):
    o = get_object_or_404(OrdemTrabalho, pk=pk)
    if request.method == 'POST':
        o.iniciar(_func_sessao(request, o))
    return render(request, 'tablet/_painel.html', _ctx(request, o))


@funcionario_required
def parar(request, pk):
    o = get_object_or_404(OrdemTrabalho, pk=pk)
    if request.method == 'POST':
        o.parar()
    return render(request, 'tablet/_painel.html', _ctx(request, o))


@funcionario_required
def foto(request, pk):
    o = get_object_or_404(OrdemTrabalho, pk=pk)
    if request.method == 'POST' and request.FILES.get('imagem'):
        FotoOrdem.objects.create(
            ordem=o, imagem=request.FILES['imagem'],
            categoria=request.POST.get('categoria', FotoOrdem.Categoria.DURANTE),
            legenda=request.POST.get('legenda', ''),
            funcionario=_funcionario(request))
    return render(request, 'tablet/_fotos.html', _ctx(request, o))


@funcionario_required
def extra(request, pk):
    o = get_object_or_404(OrdemTrabalho, pk=pk)
    if request.method == 'POST' and request.POST.get('descricao'):
        peca = Peca.objects.filter(pk=request.POST.get('peca')).first() if request.POST.get('peca') else None
        ItemOrdem.objects.create(
            ordem=o, tipo=request.POST.get('tipo', ItemOrdem.Tipo.PECA), peca=peca,
            descricao=request.POST['descricao'],
            quantidade=_dec(request.POST.get('quantidade'), '1'),
            preco_unitario=_dec(request.POST.get('preco_unitario'), '0'),
            fora_orcamento=True, nota=request.POST.get('nota', ''))
    return render(request, 'tablet/_extras.html', _ctx(request, o))


@funcionario_required
def concluir(request, pk):
    o = get_object_or_404(OrdemTrabalho, pk=pk)
    if request.method == 'POST':
        o.concluir(user=request.user)
        return redirect('tablet:inicio')
    return redirect('tablet:ordem', pk=pk)


@funcionario_required
def nova_ordem(request):
    if request.method == 'POST':
        viatura = get_object_or_404(Viatura, pk=request.POST.get('viatura'))
        marcacao = Marcacao.objects.filter(pk=request.POST.get('marcacao')).first() if request.POST.get('marcacao') else None
        o = OrdemTrabalho.objects.create(
            viatura=viatura, local=viatura.local,
            tipo_servico=(marcacao.tipo_servico if marcacao else None),
            funcionario=_funcionario(request), marcacao=marcacao,
            quilometragem=viatura.quilometragem_atual)
        return redirect('tablet:ordem', pk=o.pk)
    return render(request, 'tablet/nova.html', {
        'func': _funcionario(request),
        'viaturas': Viatura.objects.select_related('marca', 'modelo', 'cliente').order_by('matricula')})
