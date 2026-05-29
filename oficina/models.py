"""Modelo de domínio da Full Torque.

Decisões estruturais (custam nada agora, caras depois):
- `local` (FK) em tudo o que é operacional (mesmo com uma só oficina) — visão de cadeia.
- RegistoServico é APPEND-ONLY: não se edita nem apaga. Correções = nova entrada
  ligada via `registo_corrigido`. É o log auditável que protege o dono.
- Próximas revisões e IPO calculam-se a partir dos dados, não se gravam.

Domínio (v2): catálogo Marca/Modelo, Peças + stock, Orçamentos (orçamento → aprovação
→ registo), Inspeções (check-list digital com fotos).
"""
import calendar
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def adicionar_meses(data, meses):
    """Soma `meses` a uma data, ajustando o dia ao último dia do mês quando preciso."""
    indice = data.month - 1 + meses
    ano = data.year + indice // 12
    mes = indice % 12 + 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return data.replace(year=ano, month=mes, day=dia)


class Sincronizavel(models.Model):
    """Base dos modelos sincronizados entre a oficina (local) e a cloud.

    `uuid` é o identificador estável entre instâncias; `atualizado_em` é a marca
    de água usada pela sincronização.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    atualizado_em = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Marca de água para a sincronização: atualiza no save normal; é preservada
        # quando o registo vem do sync (passar sincronizando=True).
        if not kwargs.pop('sincronizando', False):
            self.atualizado_em = timezone.now()
            campos = kwargs.get('update_fields')
            if campos is not None:
                kwargs['update_fields'] = list(set(campos) | {'atualizado_em'})
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Catálogo de viaturas
# ---------------------------------------------------------------------------
class Marca(Sincronizavel):
    """Marca de viatura (VW, Renault, ...). Catálogo partilhado pela cadeia."""

    nome = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'marca'
        verbose_name_plural = 'marcas'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Modelo(Sincronizavel):
    """Modelo de uma marca (Golf, Clio, ...)."""

    marca = models.ForeignKey(Marca, on_delete=models.CASCADE, related_name='modelos')
    nome = models.CharField(max_length=80)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'modelo'
        verbose_name_plural = 'modelos'
        ordering = ['marca__nome', 'nome']
        constraints = [
            models.UniqueConstraint(fields=['marca', 'nome'], name='modelo_unico_por_marca'),
        ]

    def __str__(self):
        return f'{self.marca} {self.nome}'


# ---------------------------------------------------------------------------
# Locais, clientes, serviços
# ---------------------------------------------------------------------------
class Local(Sincronizavel):
    """Uma oficina/sucursal. Tudo o que é operacional aponta para um Local."""

    nome = models.CharField(max_length=120)
    morada = models.CharField(max_length=255, blank=True)
    codigo_postal = models.CharField('código postal', max_length=12, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    slug = models.SlugField(unique=True, help_text='Identificador para URLs por loja (futuro).')
    capacidade_slot = models.PositiveSmallIntegerField(
        'capacidade por horário', default=2,
        help_text='Marcações simultâneas possíveis no mesmo horário.')
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'local'
        verbose_name_plural = 'locais'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Cliente(Sincronizavel):
    """Cliente da marca. Sem `local`: pode ser servido em qualquer oficina da cadeia."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cliente',
    )
    nome = models.CharField(max_length=160)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    nif = models.CharField('NIF', max_length=20, blank=True)
    morada = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class TipoServico(Sincronizavel):
    """Catálogo de serviços. Intervalos definem a recorrência (próximas revisões)."""

    nome = models.CharField(max_length=120)
    descricao = models.TextField('descrição', blank=True)
    preco_base = models.DecimalField('preço base', max_digits=8, decimal_places=2, null=True, blank=True)
    duracao_estimada = models.DurationField(
        'duração estimada', null=True, blank=True, help_text='Para marcações.')
    intervalo_km = models.PositiveIntegerField(
        null=True, blank=True, help_text='Periodicidade em km (vazio = não recorrente).')
    intervalo_meses = models.PositiveIntegerField(
        null=True, blank=True, help_text='Periodicidade em meses (vazio = não recorrente).')
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'tipo de serviço'
        verbose_name_plural = 'tipos de serviço'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def e_recorrente(self):
        return self.intervalo_km is not None or self.intervalo_meses is not None


# ---------------------------------------------------------------------------
# Peças e stock
# ---------------------------------------------------------------------------
class Peca(Sincronizavel):
    """Peça de catálogo (referência + preço de venda)."""

    referencia = models.CharField('referência', max_length=60, unique=True)
    nome = models.CharField(max_length=160)
    preco_venda = models.DecimalField('preço de venda', max_digits=8, decimal_places=2, default=Decimal('0.00'))
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'peça'
        verbose_name_plural = 'peças'
        ordering = ['nome']

    def __str__(self):
        return f'{self.referencia} — {self.nome}'


class StockPeca(Sincronizavel):
    """Stock de uma peça num local."""

    peca = models.ForeignKey(Peca, on_delete=models.CASCADE, related_name='stocks')
    local = models.ForeignKey(Local, on_delete=models.CASCADE, related_name='stocks')
    quantidade = models.IntegerField(default=0)
    stock_minimo = models.PositiveIntegerField('stock mínimo', default=0)

    class Meta:
        verbose_name = 'stock de peça'
        verbose_name_plural = 'stock de peças'
        ordering = ['peca__nome']
        constraints = [
            models.UniqueConstraint(fields=['peca', 'local'], name='stock_unico_peca_local'),
        ]

    def __str__(self):
        return f'{self.peca} @ {self.local}: {self.quantidade}'

    @property
    def abaixo_minimo(self):
        return self.quantidade <= self.stock_minimo


# ---------------------------------------------------------------------------
# Funcionários e viaturas
# ---------------------------------------------------------------------------
class Funcionario(Sincronizavel):
    """Funcionário de um Local. `user` opcional até existir o login do staff."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='funcionario',
    )
    local = models.ForeignKey(Local, on_delete=models.PROTECT, related_name='funcionarios')
    nome = models.CharField(max_length=160)
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=80, blank=True, help_text='Ex.: mecânico, rececionista.')
    ativo = models.BooleanField(default=True)
    data_admissao = models.DateField('data de admissão', null=True, blank=True)
    pin = models.CharField(
        'PIN', max_length=128, blank=True,
        help_text='PIN de acesso ao tablet (guardado cifrado).')

    class Meta:
        verbose_name = 'funcionário'
        verbose_name_plural = 'funcionários'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def set_pin(self, raw):
        self.pin = make_password(raw) if raw else ''

    def check_pin(self, raw):
        return bool(self.pin) and bool(raw) and check_password(raw, self.pin)

    @property
    def tem_pin(self):
        return bool(self.pin)


class Viatura(Sincronizavel):
    """Viatura de um cliente. Marca/Modelo do catálogo; `local` = oficina de registo.

    A quilometragem atual deriva-se do último RegistoServico (append-only).
    """

    class Combustivel(models.TextChoices):
        GASOLINA = 'gasolina', 'Gasolina'
        DIESEL = 'diesel', 'Diesel'
        ELETRICO = 'eletrico', 'Elétrico'
        HIBRIDO = 'hibrido', 'Híbrido'
        GPL = 'gpl', 'GPL'
        OUTRO = 'outro', 'Outro'

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='viaturas')
    local = models.ForeignKey(
        Local, on_delete=models.PROTECT, related_name='viaturas',
        help_text='Oficina de registo da viatura.')
    matricula = models.CharField('matrícula', max_length=15, unique=True)
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, related_name='viaturas', null=True, blank=True)
    modelo = models.ForeignKey(Modelo, on_delete=models.PROTECT, related_name='viaturas', null=True, blank=True)
    ano = models.PositiveIntegerField(null=True, blank=True)
    combustivel = models.CharField('combustível', max_length=15, choices=Combustivel.choices, blank=True)
    cor = models.CharField(max_length=40, blank=True)
    vin = models.CharField('VIN / nº de chassis', max_length=40, blank=True)
    inspecao_valida_ate = models.DateField(
        'IPO válida até', null=True, blank=True,
        help_text='Validade da Inspeção Periódica Obrigatória.')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'viatura'
        verbose_name_plural = 'viaturas'
        ordering = ['matricula']

    def __str__(self):
        marca_modelo = ' '.join(p for p in [str(self.marca or ''), str(self.modelo.nome if self.modelo else '')] if p)
        return f'{self.matricula} — {marca_modelo}'.strip(' —')

    @property
    def quilometragem_atual(self):
        ultimo = self.registos.exclude(quilometragem__isnull=True).first()
        return ultimo.quilometragem if ultimo else None

    @property
    def ipo_dias_restantes(self):
        if not self.inspecao_valida_ate:
            return None
        return (self.inspecao_valida_ate - timezone.localdate()).days

    def proximas_revisoes(self):
        """Previsão da próxima revisão por cada tipo de serviço recorrente já efetuado."""
        previsoes = []
        recorrentes = TipoServico.objects.filter(
            models.Q(intervalo_km__isnull=False) | models.Q(intervalo_meses__isnull=False),
            ativo=True,
        )
        for tipo in recorrentes:
            ultimo = self.registos.filter(tipo_servico=tipo).first()
            if ultimo is None:
                continue
            proxima_data = (
                adicionar_meses(ultimo.data_servico, tipo.intervalo_meses)
                if tipo.intervalo_meses else None
            )
            proximo_km = (
                ultimo.quilometragem + tipo.intervalo_km
                if tipo.intervalo_km and ultimo.quilometragem is not None else None
            )
            previsoes.append({
                'tipo_servico': tipo,
                'ultimo_registo': ultimo,
                'proxima_data': proxima_data,
                'proximo_km': proximo_km,
            })
        return previsoes


# ---------------------------------------------------------------------------
# Registos de serviço (append-only) + peças usadas + fotos
# ---------------------------------------------------------------------------
class RegistoServico(Sincronizavel):
    """Registo APPEND-ONLY de um serviço executado. Não se edita nem se apaga.

    Correção = NOVA entrada ligada à original via `registo_corrigido`.
    Histórico imutável que protege o dono numa reclamação.
    """

    class Estado(models.TextChoices):
        EM_EXECUCAO = 'em_execucao', 'Em execução'
        CONCLUIDO = 'concluido', 'Concluído'
        CANCELADO = 'cancelado', 'Cancelado'

    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='registos')
    local = models.ForeignKey(Local, on_delete=models.PROTECT, related_name='registos')
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.PROTECT, null=True, blank=True,
        related_name='registos', help_text='Quem executou o serviço.')
    tipo_servico = models.ForeignKey(TipoServico, on_delete=models.PROTECT, related_name='registos')

    data_servico = models.DateField('data do serviço', default=timezone.localdate)
    quilometragem = models.PositiveIntegerField(null=True, blank=True)
    trabalho_feito = models.TextField('trabalho feito')
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.CONCLUIDO)

    registo_corrigido = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True, related_name='correcoes',
        help_text='Se preenchido, esta entrada corrige/anula a original (o log é append-only).')

    registado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registos_criados')
    criado_em = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'registo de serviço'
        verbose_name_plural = 'registos de serviço'
        ordering = ['-data_servico', '-criado_em']

    def __str__(self):
        return f'{self.viatura.matricula} — {self.tipo_servico} ({self.data_servico})'

    def save(self, *args, **kwargs):
        # APPEND-ONLY: só permitimos inserir. Para corrigir, cria-se nova entrada.
        if self.pk is not None:
            raise ValidationError(
                'RegistoServico é append-only: não pode ser editado. '
                "Cria uma nova entrada ligada via 'registo_corrigido'."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('RegistoServico é append-only: não pode ser apagado.')

    @property
    def total_pecas(self):
        return sum((p.subtotal for p in self.pecas.all()), Decimal('0.00'))


class PecaServico(Sincronizavel):
    """Peça usada num registo de serviço (linha de detalhe)."""

    registo = models.ForeignKey(RegistoServico, on_delete=models.PROTECT, related_name='pecas')
    peca = models.ForeignKey(Peca, on_delete=models.PROTECT, null=True, blank=True, related_name='usos')
    descricao = models.CharField('descrição', max_length=200)
    quantidade = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('1.00'))
    preco_unitario = models.DecimalField('preço unitário', max_digits=8, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'peça do serviço'
        verbose_name_plural = 'peças do serviço'

    def __str__(self):
        return f'{self.descricao} ×{self.quantidade}'

    @property
    def subtotal(self):
        return (self.quantidade or 0) * (self.preco_unitario or 0)


class FotoRegisto(Sincronizavel):
    """Foto associada a um registo de serviço (antes/depois, peças, etc.)."""

    registo = models.ForeignKey(RegistoServico, on_delete=models.PROTECT, related_name='fotos')
    imagem = models.ImageField(upload_to='registos/%Y/%m/')
    legenda = models.CharField(max_length=160, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    ficheiro_enviado = models.BooleanField('ficheiro enviado p/ cloud', default=False, editable=False)

    class Meta:
        verbose_name = 'foto de registo'
        verbose_name_plural = 'fotos de registo'

    def __str__(self):
        return self.legenda or f'Foto #{self.pk}'


# ---------------------------------------------------------------------------
# Inspeções (check-list digital — DVI)
# ---------------------------------------------------------------------------
class Inspecao(Sincronizavel):
    """Inspeção/check-list digital de uma viatura (pontos verificados + fotos)."""

    class Resultado(models.TextChoices):
        OK = 'ok', 'Tudo OK'
        ATENCAO = 'atencao', 'Requer atenção'
        URGENTE = 'urgente', 'Intervenção urgente'

    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='inspecoes')
    local = models.ForeignKey(Local, on_delete=models.PROTECT, related_name='inspecoes')
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.PROTECT, null=True, blank=True, related_name='inspecoes')
    data = models.DateField(default=timezone.localdate)
    quilometragem = models.PositiveIntegerField(null=True, blank=True)
    resultado = models.CharField(max_length=10, choices=Resultado.choices, default=Resultado.OK)
    notas = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'inspeção'
        verbose_name_plural = 'inspeções'
        ordering = ['-data', '-criado_em']

    def __str__(self):
        return f'Inspeção {self.viatura.matricula} ({self.data})'


class ItemInspecao(Sincronizavel):
    """Ponto verificado numa inspeção (ex.: travões, pneus, óleo)."""

    class Estado(models.TextChoices):
        OK = 'ok', 'OK'
        ATENCAO = 'atencao', 'Atenção'
        URGENTE = 'urgente', 'Urgente'

    inspecao = models.ForeignKey(Inspecao, on_delete=models.CASCADE, related_name='itens')
    ponto = models.CharField(max_length=120)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.OK)
    nota = models.CharField(max_length=255, blank=True)
    foto = models.ImageField(upload_to='inspecoes/%Y/%m/', null=True, blank=True)

    class Meta:
        verbose_name = 'ponto de inspeção'
        verbose_name_plural = 'pontos de inspeção'

    def __str__(self):
        return f'{self.ponto}: {self.get_estado_display()}'


# ---------------------------------------------------------------------------
# Orçamentos (orçamento → aprovação → registo de serviço)
# ---------------------------------------------------------------------------
class Orcamento(Sincronizavel):
    """Orçamento. Ao ser aprovado, gera um RegistoServico (ordem de trabalho)."""

    class Estado(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        ENVIADO = 'enviado', 'Enviado'
        APROVADO = 'aprovado', 'Aprovado'
        REJEITADO = 'rejeitado', 'Rejeitado'
        EXPIRADO = 'expirado', 'Expirado'

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='orcamentos')
    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='orcamentos')
    local = models.ForeignKey(Local, on_delete=models.PROTECT, related_name='orcamentos')
    tipo_servico = models.ForeignKey(
        TipoServico, on_delete=models.PROTECT, null=True, blank=True, related_name='orcamentos')
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='orcamentos')
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.RASCUNHO)
    validade = models.DateField(null=True, blank=True)
    notas = models.TextField(blank=True)
    registo_gerado = models.ForeignKey(
        RegistoServico, on_delete=models.SET_NULL, null=True, blank=True, related_name='orcamento_origem')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'orçamento'
        verbose_name_plural = 'orçamentos'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Orçamento #{self.pk} — {self.viatura.matricula}'

    @property
    def total(self):
        return sum((i.subtotal for i in self.itens.all()), Decimal('0.00'))

    def resumo_mao_obra(self):
        linhas = [i.descricao for i in self.itens.filter(tipo=ItemOrcamento.Tipo.MAO_OBRA)]
        return '; '.join(linhas)

    def aprovar(self, user=None):
        """Aprova o orçamento e gera o RegistoServico correspondente."""
        if self.estado == self.Estado.APROVADO and self.registo_gerado_id:
            return self.registo_gerado
        tipo = self.tipo_servico or TipoServico.objects.filter(ativo=True).first()
        if tipo is None:
            raise ValidationError('Não há TipoServico definido para gerar o registo.')
        registo = RegistoServico.objects.create(
            viatura=self.viatura,
            local=self.local,
            funcionario=self.funcionario,
            tipo_servico=tipo,
            data_servico=timezone.localdate(),
            quilometragem=self.viatura.quilometragem_atual,
            trabalho_feito=self.resumo_mao_obra() or f'Serviço do orçamento #{self.pk}',
            estado=RegistoServico.Estado.CONCLUIDO,
            registado_por=user,
        )
        for item in self.itens.filter(tipo=ItemOrcamento.Tipo.PECA):
            PecaServico.objects.create(
                registo=registo, peca=item.peca, descricao=item.descricao,
                quantidade=item.quantidade, preco_unitario=item.preco_unitario)
        self.estado = self.Estado.APROVADO
        self.registo_gerado = registo
        self.save(update_fields=['estado', 'registo_gerado'])
        return registo


class ItemOrcamento(Sincronizavel):
    """Linha de um orçamento (mão de obra ou peça)."""

    class Tipo(models.TextChoices):
        MAO_OBRA = 'mao_obra', 'Mão de obra'
        PECA = 'peca', 'Peça'

    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name='itens')
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.MAO_OBRA)
    peca = models.ForeignKey(Peca, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    descricao = models.CharField('descrição', max_length=200)
    quantidade = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('1.00'))
    preco_unitario = models.DecimalField('preço unitário', max_digits=8, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'item de orçamento'
        verbose_name_plural = 'itens de orçamento'

    def __str__(self):
        return f'{self.descricao} ×{self.quantidade}'

    @property
    def subtotal(self):
        return (self.quantidade or 0) * (self.preco_unitario or 0)


# ---------------------------------------------------------------------------
# Marcações
# ---------------------------------------------------------------------------
class Marcacao(Sincronizavel):
    """Marcação/agendamento. Sem fluxo público ainda — gerida no admin pelo staff."""

    class Estado(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        CONFIRMADA = 'confirmada', 'Confirmada'
        CONCLUIDA = 'concluida', 'Concluída'
        CANCELADA = 'cancelada', 'Cancelada'

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='marcacoes')
    viatura = models.ForeignKey(
        Viatura, on_delete=models.PROTECT, null=True, blank=True, related_name='marcacoes')
    local = models.ForeignKey(Local, on_delete=models.PROTECT, related_name='marcacoes')
    tipo_servico = models.ForeignKey(TipoServico, on_delete=models.PROTECT, related_name='marcacoes')
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='marcacoes')
    data_hora = models.DateTimeField('data e hora')
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDENTE)
    notas = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'marcação'
        verbose_name_plural = 'marcações'
        ordering = ['data_hora']

    def __str__(self):
        return f'{self.cliente} — {self.data_hora:%Y-%m-%d %H:%M}'


# ---------------------------------------------------------------------------
# Ordens de trabalho (tablet do funcionário): trabalho ao vivo + tempo + extras + fotos
# ---------------------------------------------------------------------------
class OrdemTrabalho(Sincronizavel):
    """Trabalho ao vivo numa viatura (gerido pelo funcionário no tablet).

    Editável enquanto decorre; ao concluir gera um RegistoServico APPEND-ONLY
    (a prova permanente que protege a garantia).
    """

    class Estado(models.TextChoices):
        ABERTA = 'aberta', 'Aberta'
        EM_EXECUCAO = 'em_execucao', 'Em execução'
        PAUSADA = 'pausada', 'Pausada'
        CONCLUIDA = 'concluida', 'Concluída'
        CANCELADA = 'cancelada', 'Cancelada'

    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='ordens')
    local = models.ForeignKey(Local, on_delete=models.PROTECT, related_name='ordens')
    tipo_servico = models.ForeignKey(
        TipoServico, on_delete=models.PROTECT, null=True, blank=True, related_name='ordens')
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordens')
    orcamento = models.ForeignKey(
        Orcamento, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordens',
        help_text='Orçamento de referência (para comparar com os extras).')
    marcacao = models.ForeignKey(
        Marcacao, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordens')

    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ABERTA)
    quilometragem = models.PositiveIntegerField('quilometragem à entrada', null=True, blank=True)
    notas = models.TextField(blank=True)

    registo_gerado = models.ForeignKey(
        RegistoServico, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordem_origem')
    criado_em = models.DateTimeField(auto_now_add=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'ordem de trabalho'
        verbose_name_plural = 'ordens de trabalho'
        ordering = ['-criado_em']

    def __str__(self):
        return f'OT#{self.pk} — {self.viatura.matricula}'

    @property
    def segundos_trabalhados(self):
        return sum((s.segundos for s in self.sessoes.all()), 0)

    @property
    def horas_formatadas(self):
        horas, minutos = divmod(self.segundos_trabalhados // 60, 60)
        return f'{horas}h{minutos:02d}'

    @property
    def sessao_ativa(self):
        return self.sessoes.filter(fim__isnull=True).first()

    @property
    def total_extras(self):
        return sum((i.subtotal for i in self.itens.filter(fora_orcamento=True)), Decimal('0.00'))

    def iniciar(self, funcionario):
        if not self.sessoes.filter(fim__isnull=True, funcionario=funcionario).exists():
            SessaoTrabalho.objects.create(ordem=self, funcionario=funcionario)
        if self.estado in (self.Estado.ABERTA, self.Estado.PAUSADA):
            self.estado = self.Estado.EM_EXECUCAO
            self.save(update_fields=['estado'])

    def parar(self, funcionario=None):
        sessoes = self.sessoes.filter(fim__isnull=True)
        if funcionario:
            sessoes = sessoes.filter(funcionario=funcionario)
        for sessao in sessoes:
            sessao.fim = timezone.now()
            sessao.save(update_fields=['fim'])
        if self.estado == self.Estado.EM_EXECUCAO and not self.sessoes.filter(fim__isnull=True).exists():
            self.estado = self.Estado.PAUSADA
            self.save(update_fields=['estado'])

    def concluir(self, user=None):
        """Fecha a ordem e gera o RegistoServico append-only (com peças e extras)."""
        if self.estado == self.Estado.CONCLUIDA and self.registo_gerado_id:
            return self.registo_gerado
        self.parar()
        tipo = self.tipo_servico or TipoServico.objects.filter(ativo=True).first()
        if tipo is None:
            raise ValidationError('Sem TipoServico definido para gerar o registo.')
        primeira = self.sessoes.first()
        func = self.funcionario or (primeira.funcionario if primeira else None)
        registo = RegistoServico.objects.create(
            viatura=self.viatura, local=self.local, funcionario=func, tipo_servico=tipo,
            data_servico=timezone.localdate(), quilometragem=self.quilometragem,
            trabalho_feito=(self.notas or f'Trabalho concluído ({self.horas_formatadas}).'),
            estado=RegistoServico.Estado.CONCLUIDO, registado_por=user)
        for item in self.itens.filter(tipo=ItemOrdem.Tipo.PECA):
            PecaServico.objects.create(
                registo=registo, peca=item.peca, descricao=item.descricao,
                quantidade=item.quantidade, preco_unitario=item.preco_unitario)
        self.estado = self.Estado.CONCLUIDA
        self.concluida_em = timezone.now()
        self.registo_gerado = registo
        self.save(update_fields=['estado', 'concluida_em', 'registo_gerado'])
        return registo


class SessaoTrabalho(Sincronizavel):
    """Sessão de tempo de um funcionário numa ordem (o sistema soma as horas)."""

    ordem = models.ForeignKey(OrdemTrabalho, on_delete=models.CASCADE, related_name='sessoes')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name='sessoes')
    inicio = models.DateTimeField(default=timezone.now)
    fim = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'sessão de trabalho'
        verbose_name_plural = 'sessões de trabalho'
        ordering = ['inicio']

    def __str__(self):
        return f'{self.funcionario} · {self.inicio:%d/%m %H:%M}'

    @property
    def segundos(self):
        return max(0, int(((self.fim or timezone.now()) - self.inicio).total_seconds()))


class ItemOrdem(Sincronizavel):
    """Peça/mão de obra acrescentada numa ordem; `fora_orcamento` marca os imprevistos."""

    class Tipo(models.TextChoices):
        MAO_OBRA = 'mao_obra', 'Mão de obra'
        PECA = 'peca', 'Peça'

    ordem = models.ForeignKey(OrdemTrabalho, on_delete=models.CASCADE, related_name='itens')
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.PECA)
    peca = models.ForeignKey(Peca, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    descricao = models.CharField('descrição', max_length=200)
    quantidade = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('1.00'))
    preco_unitario = models.DecimalField('preço unitário', max_digits=8, decimal_places=2, default=Decimal('0.00'))
    fora_orcamento = models.BooleanField('fora do orçamento (extra)', default=True)
    nota = models.CharField(max_length=255, blank=True, help_text='Justificação do imprevisto.')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'item da ordem'
        verbose_name_plural = 'itens da ordem'
        ordering = ['criado_em']

    def __str__(self):
        return f'{self.descricao} ×{self.quantidade}'

    @property
    def subtotal(self):
        return (self.quantidade or 0) * (self.preco_unitario or 0)


class FotoOrdem(Sincronizavel):
    """Foto tirada no tablet durante a ordem (danos à entrada, imprevistos, etc.)."""

    class Categoria(models.TextChoices):
        ENTRADA = 'entrada', 'Estado à entrada'
        IMPREVISTO = 'imprevisto', 'Imprevisto'
        DURANTE = 'durante', 'Durante o trabalho'
        FIM = 'fim', 'Trabalho concluído'

    ordem = models.ForeignKey(OrdemTrabalho, on_delete=models.PROTECT, related_name='fotos')
    item = models.ForeignKey(ItemOrdem, on_delete=models.SET_NULL, null=True, blank=True, related_name='fotos')
    imagem = models.ImageField(upload_to='ordens/%Y/%m/')
    categoria = models.CharField(max_length=12, choices=Categoria.choices, default=Categoria.DURANTE)
    legenda = models.CharField(max_length=200, blank=True)
    funcionario = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    criado_em = models.DateTimeField(auto_now_add=True)
    ficheiro_enviado = models.BooleanField('ficheiro enviado p/ cloud', default=False, editable=False)

    class Meta:
        verbose_name = 'foto da ordem'
        verbose_name_plural = 'fotos da ordem'
        ordering = ['criado_em']

    def __str__(self):
        return f'{self.get_categoria_display()} — OT#{self.ordem_id}'
