from django.contrib import admin
from unfold.admin import ModelAdmin

from .correspondencia import casar_cliente
from .models import EstadoFaturacao, Fatura


@admin.register(Fatura)
class FaturaAdmin(ModelAdmin):
    list_display = ('numero', 'data', 'total', 'nome', 'nif', 'cliente', 'estado')
    list_filter = ('estado', 'provedor', 'data')
    search_fields = ('numero', 'nif', 'nome', 'email', 'id_externo')
    autocomplete_fields = ('cliente',)
    date_hierarchy = 'data'
    readonly_fields = ('provedor', 'id_externo', 'numero', 'data', 'total', 'moeda',
                       'nif', 'nome', 'email', 'pdf', 'pdf_url', 'puxado_em')
    fields = ('cliente', 'estado',
              'numero', 'data', 'total', 'moeda',
              'nome', 'nif', 'email',
              'pdf', 'pdf_url', 'provedor', 'id_externo', 'puxado_em')
    actions = ['recasar']

    def has_add_permission(self, request):
        return False  # faturas entram só pela API (puxar_faturas), nunca à mão

    def save_model(self, request, obj, form, change):
        # Atribuição manual feita no admin -> marca como 'manual'.
        if obj.cliente_id and 'cliente' in form.changed_data:
            obj.estado = Fatura.Estado.MANUAL
        super().save_model(request, obj, form, change)

    @admin.action(description='Tentar casar de novo (NIF/email)')
    def recasar(self, request, queryset):
        n = 0
        for f in queryset:
            cliente, estado = casar_cliente(f.nif, f.email, f.nome)
            if cliente is not None and cliente != f.cliente:
                f.cliente = cliente
                f.estado = estado
                f.save(update_fields=['cliente', 'estado'])
                n += 1
        self.message_user(request, f'{n} fatura(s) casada(s).')


@admin.register(EstadoFaturacao)
class EstadoFaturacaoAdmin(ModelAdmin):
    list_display = ('provedor', 'ultimo')
    readonly_fields = ('provedor', 'ultimo')
