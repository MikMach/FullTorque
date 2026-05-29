from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import (
    Cliente,
    Funcionario,
    FotoRegisto,
    Inspecao,
    ItemInspecao,
    ItemOrcamento,
    Local,
    Marca,
    Marcacao,
    Modelo,
    Orcamento,
    Peca,
    PecaServico,
    RegistoServico,
    StockPeca,
    TipoServico,
    Viatura,
)

admin.site.site_header = 'Full Torque — Gestão'
admin.site.site_title = 'Full Torque'
admin.site.index_title = 'Painel de gestão'


# ---------------------------------------------------------------------------
# Catálogo de viaturas
# ---------------------------------------------------------------------------
class ModeloInline(TabularInline):
    model = Modelo
    extra = 0


@admin.register(Marca)
class MarcaAdmin(ModelAdmin):
    list_display = ('nome', 'n_modelos', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    prepopulated_fields = {'slug': ('nome',)}
    inlines = [ModeloInline]

    @admin.display(description='Modelos')
    def n_modelos(self, obj):
        return obj.modelos.count()


@admin.register(Modelo)
class ModeloAdmin(ModelAdmin):
    list_display = ('nome', 'marca', 'ativo')
    list_filter = ('marca', 'ativo')
    search_fields = ('nome', 'marca__nome')
    autocomplete_fields = ('marca',)


# ---------------------------------------------------------------------------
# Locais, clientes, serviços
# ---------------------------------------------------------------------------
@admin.register(Local)
class LocalAdmin(ModelAdmin):
    list_display = ('nome', 'cidade', 'telefone', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'cidade', 'morada')
    prepopulated_fields = {'slug': ('nome',)}


class ViaturaInline(TabularInline):
    model = Viatura
    extra = 0
    fields = ('matricula', 'marca', 'modelo', 'ano', 'local')
    autocomplete_fields = ('marca', 'modelo', 'local')
    show_change_link = True


@admin.register(Cliente)
class ClienteAdmin(ModelAdmin):
    list_display = ('nome', 'telefone', 'email', 'nif')
    search_fields = ('nome', 'telefone', 'email', 'nif')
    autocomplete_fields = ('user',)
    inlines = [ViaturaInline]


@admin.register(TipoServico)
class TipoServicoAdmin(ModelAdmin):
    list_display = ('nome', 'preco_base', 'intervalo_km', 'intervalo_meses', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'descricao')


# ---------------------------------------------------------------------------
# Peças e stock
# ---------------------------------------------------------------------------
class StockPecaInline(TabularInline):
    model = StockPeca
    extra = 0
    autocomplete_fields = ('local',)


@admin.register(Peca)
class PecaAdmin(ModelAdmin):
    list_display = ('referencia', 'nome', 'preco_venda', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('referencia', 'nome')
    inlines = [StockPecaInline]


@admin.register(StockPeca)
class StockPecaAdmin(ModelAdmin):
    list_display = ('peca', 'local', 'quantidade', 'stock_minimo', 'em_falta')
    list_filter = ('local',)
    search_fields = ('peca__referencia', 'peca__nome')
    autocomplete_fields = ('peca', 'local')

    @display(description='Stock', label={'OK': 'success', 'Em falta': 'danger'})
    def em_falta(self, obj):
        return 'Em falta' if obj.abaixo_minimo else 'OK'


# ---------------------------------------------------------------------------
# Funcionários e viaturas
# ---------------------------------------------------------------------------
@admin.register(Funcionario)
class FuncionarioAdmin(ModelAdmin):
    list_display = ('nome', 'cargo', 'local', 'telefone', 'ativo')
    list_filter = ('local', 'ativo', 'cargo')
    search_fields = ('nome', 'telefone', 'cargo')
    autocomplete_fields = ('user', 'local')


class IPOFilter(admin.SimpleListFilter):
    title = 'IPO'
    parameter_name = 'ipo'

    def lookups(self, request, model_admin):
        return (('expirada', 'Expirada'), ('vencer', 'A vencer (30 dias)'), ('valida', 'Válida'), ('sem', 'Sem data'))

    def queryset(self, request, qs):
        from django.utils import timezone
        hoje = timezone.localdate()
        from datetime import timedelta
        if self.value() == 'expirada':
            return qs.filter(inspecao_valida_ate__lt=hoje)
        if self.value() == 'vencer':
            return qs.filter(inspecao_valida_ate__gte=hoje, inspecao_valida_ate__lte=hoje + timedelta(days=30))
        if self.value() == 'valida':
            return qs.filter(inspecao_valida_ate__gt=hoje + timedelta(days=30))
        if self.value() == 'sem':
            return qs.filter(inspecao_valida_ate__isnull=True)
        return qs


class RegistoHistoricoInline(TabularInline):
    """Histórico de serviços na ficha da viatura — só leitura (append-only)."""

    model = RegistoServico
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ('data_servico', 'tipo_servico', 'estado', 'quilometragem', 'funcionario')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Viatura)
class ViaturaAdmin(ModelAdmin):
    list_display = ('matricula', 'marca', 'modelo', 'cliente', 'local', 'km_atual', 'ipo_estado')
    list_filter = ('local', 'combustivel', 'marca', IPOFilter)
    search_fields = ('matricula', 'marca__nome', 'modelo__nome', 'vin', 'cliente__nome')
    autocomplete_fields = ('cliente', 'local', 'marca', 'modelo')
    inlines = [RegistoHistoricoInline]

    @admin.display(description='Km atual')
    def km_atual(self, obj):
        return obj.quilometragem_atual

    @display(description='IPO', label={'Válida': 'success', 'A vencer': 'warning', 'Expirada': 'danger', '—': 'info'})
    def ipo_estado(self, obj):
        d = obj.ipo_dias_restantes
        if d is None:
            return '—'
        if d < 0:
            return 'Expirada'
        if d <= 30:
            return 'A vencer'
        return 'Válida'


# ---------------------------------------------------------------------------
# Registos de serviço (append-only)
# ---------------------------------------------------------------------------
class PecaServicoInline(TabularInline):
    model = PecaServico
    extra = 1
    autocomplete_fields = ('peca',)


class FotoRegistoInline(TabularInline):
    model = FotoRegisto
    extra = 1


@admin.register(RegistoServico)
class RegistoServicoAdmin(ModelAdmin):
    """APPEND-ONLY: pode-se criar e ver, nunca editar ou apagar.

    Para corrigir, cria-se um novo registo ligado em `registo_corrigido`.
    """

    list_display = (
        'data_servico', 'viatura', 'tipo_servico', 'estado_badge',
        'funcionario', 'local', 'quilometragem', 'tem_correcao',
    )
    list_filter = ('estado', 'local', 'tipo_servico', 'data_servico')
    search_fields = ('viatura__matricula', 'trabalho_feito')
    date_hierarchy = 'data_servico'
    autocomplete_fields = ('viatura', 'tipo_servico', 'funcionario', 'local', 'registo_corrigido')
    readonly_fields = ('registado_por', 'criado_em')
    inlines = [PecaServicoInline, FotoRegistoInline]
    fieldsets = (
        ('Identificação', {'fields': ('viatura', 'local', 'tipo_servico', 'funcionario')}),
        ('Serviço', {'fields': ('data_servico', 'quilometragem', 'estado', 'trabalho_feito')}),
        ('Correção / Auditoria', {'fields': ('registo_corrigido', 'registado_por', 'criado_em')}),
    )

    @display(description='Estado', label={'Concluído': 'success', 'Em execução': 'warning', 'Cancelado': 'danger'})
    def estado_badge(self, obj):
        return obj.get_estado_display()

    @admin.display(boolean=True, description='Corrigido?')
    def tem_correcao(self, obj):
        return obj.correcoes.exists()

    def has_change_permission(self, request, obj=None):
        return False  # Append-only: só ver e criar.

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not change and not obj.registado_por_id:
            obj.registado_por = request.user
        super().save_model(request, obj, form, change)


# ---------------------------------------------------------------------------
# Inspeções (check-list digital)
# ---------------------------------------------------------------------------
class ItemInspecaoInline(TabularInline):
    model = ItemInspecao
    extra = 3


@admin.register(Inspecao)
class InspecaoAdmin(ModelAdmin):
    list_display = ('data', 'viatura', 'resultado_badge', 'funcionario', 'local', 'n_itens')
    list_filter = ('resultado', 'local', 'data')
    search_fields = ('viatura__matricula',)
    date_hierarchy = 'data'
    autocomplete_fields = ('viatura', 'local', 'funcionario')
    inlines = [ItemInspecaoInline]

    @display(description='Resultado', label={'Tudo OK': 'success', 'Requer atenção': 'warning', 'Intervenção urgente': 'danger'})
    def resultado_badge(self, obj):
        return obj.get_resultado_display()

    @admin.display(description='Pontos')
    def n_itens(self, obj):
        return obj.itens.count()


# ---------------------------------------------------------------------------
# Orçamentos
# ---------------------------------------------------------------------------
class ItemOrcamentoInline(TabularInline):
    model = ItemOrcamento
    extra = 1
    autocomplete_fields = ('peca',)


@admin.action(description='Aprovar e gerar registo de serviço')
def aprovar_orcamentos(modeladmin, request, queryset):
    aprovados = 0
    for orc in queryset:
        try:
            orc.aprovar(user=request.user)
            aprovados += 1
        except Exception as exc:  # noqa: BLE001
            modeladmin.message_user(request, f'Orçamento #{orc.pk}: {exc}', level=messages.ERROR)
    if aprovados:
        modeladmin.message_user(
            request, f'{aprovados} orçamento(s) aprovado(s) e registo(s) de serviço gerado(s).',
            level=messages.SUCCESS)


@admin.register(Orcamento)
class OrcamentoAdmin(ModelAdmin):
    list_display = ('id', 'viatura', 'cliente', 'estado_badge', 'total_display', 'criado_em')
    list_filter = ('estado', 'local')
    search_fields = ('viatura__matricula', 'cliente__nome')
    date_hierarchy = 'criado_em'
    autocomplete_fields = ('cliente', 'viatura', 'local', 'tipo_servico', 'funcionario')
    readonly_fields = ('total_display', 'registo_gerado', 'criado_em')
    inlines = [ItemOrcamentoInline]
    actions = [aprovar_orcamentos]
    fieldsets = (
        ('Orçamento', {'fields': ('cliente', 'viatura', 'local', 'tipo_servico', 'funcionario')}),
        ('Estado', {'fields': ('estado', 'validade', 'notas')}),
        ('Resultado', {'fields': ('total_display', 'registo_gerado', 'criado_em')}),
    )

    @display(description='Estado', label={
        'Rascunho': 'info', 'Enviado': 'warning', 'Aprovado': 'success',
        'Rejeitado': 'danger', 'Expirado': 'danger'})
    def estado_badge(self, obj):
        return obj.get_estado_display()

    @admin.display(description='Total (€)')
    def total_display(self, obj):
        return f'{obj.total:.2f} €'


# ---------------------------------------------------------------------------
# Marcações
# ---------------------------------------------------------------------------
@admin.register(Marcacao)
class MarcacaoAdmin(ModelAdmin):
    list_display = ('data_hora', 'cliente', 'viatura', 'tipo_servico', 'local', 'estado_badge')
    list_filter = ('estado', 'local', 'tipo_servico')
    search_fields = ('cliente__nome', 'viatura__matricula')
    date_hierarchy = 'data_hora'
    autocomplete_fields = ('cliente', 'viatura', 'local', 'tipo_servico', 'funcionario')

    @display(description='Estado', label={
        'Pendente': 'info', 'Confirmada': 'warning', 'Concluída': 'success', 'Cancelada': 'danger'})
    def estado_badge(self, obj):
        return obj.get_estado_display()
