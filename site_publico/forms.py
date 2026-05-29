"""Formulário de marcação online (público) + disponibilidade de horários."""
from django import forms
from django.urls import reverse_lazy
from django.utils import timezone

from oficina.models import Local, Marca, Marcacao, Modelo, TipoServico

HORAS = [(f'{h:02d}:{m:02d}', f'{h:02d}:{m:02d}') for h in range(9, 19) for m in (0, 30)]


def horas_disponiveis(local, data):
    """Horários ainda com vaga nesse local/dia (respeita Local.capacidade_slot)."""
    ocupacao = {}
    qs = Marcacao.objects.filter(
        local=local, data_hora__date=data,
        estado__in=[Marcacao.Estado.PENDENTE, Marcacao.Estado.CONFIRMADA])
    for m in qs:
        chave = timezone.localtime(m.data_hora).strftime('%H:%M')
        ocupacao[chave] = ocupacao.get(chave, 0) + 1
    return [(h, label) for h, label in HORAS if ocupacao.get(h, 0) < local.capacidade_slot]


class MarcacaoPublicaForm(forms.Form):
    # Atributos HTMX para recarregar as horas disponíveis ao mudar oficina/data.
    _HX_HORAS = {
        'class': 'field',
        'hx-get': reverse_lazy('site_publico:horas'),
        'hx-target': '#id_hora',
        'hx-include': 'closest form',
        'hx-trigger': 'change',
    }

    local = forms.ModelChoiceField(
        queryset=Local.objects.filter(ativo=True), label='Oficina',
        widget=forms.Select(attrs=_HX_HORAS))
    tipo_servico = forms.ModelChoiceField(
        queryset=TipoServico.objects.filter(ativo=True), label='Serviço',
        widget=forms.Select(attrs={'class': 'field'}))
    data = forms.DateField(
        label='Data', widget=forms.DateInput(attrs={'type': 'date', **_HX_HORAS}))
    hora = forms.ChoiceField(
        choices=HORAS, label='Hora', widget=forms.Select(attrs={'class': 'field'}))

    matricula = forms.CharField(
        label='Matrícula', max_length=15,
        widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'AA-00-AA'}))
    marca = forms.ModelChoiceField(
        queryset=Marca.objects.filter(ativo=True), required=False, label='Marca',
        widget=forms.Select(attrs={
            'class': 'field',
            'hx-get': reverse_lazy('site_publico:modelos_por_marca'),
            'hx-target': '#id_modelo',
            'hx-trigger': 'change',
        }))
    modelo = forms.ModelChoiceField(
        queryset=Modelo.objects.all(), required=False, label='Modelo',
        widget=forms.Select(attrs={'class': 'field'}))
    ano = forms.IntegerField(
        required=False, label='Ano', min_value=1950, max_value=2030,
        widget=forms.NumberInput(attrs={'class': 'field', 'placeholder': 'opcional'}))

    nome = forms.CharField(label='Nome', max_length=160, widget=forms.TextInput(attrs={'class': 'field'}))
    telefone = forms.CharField(label='Telefone', max_length=20, widget=forms.TextInput(attrs={'class': 'field'}))
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'field'}))
    notas = forms.CharField(
        required=False, label='Notas (opcional)',
        widget=forms.Textarea(attrs={'class': 'field', 'rows': 3, 'placeholder': 'Algo que devamos saber?'}))

    def clean_data(self):
        d = self.cleaned_data['data']
        if d < timezone.localdate():
            raise forms.ValidationError('A data não pode ser no passado.')
        return d

    def clean_matricula(self):
        return self.cleaned_data['matricula'].upper().strip()

    def clean(self):
        cleaned = super().clean()
        local, data, hora = cleaned.get('local'), cleaned.get('data'), cleaned.get('hora')
        if local and data and hora and hora not in dict(horas_disponiveis(local, data)):
            self.add_error('hora', 'Esse horário já está preenchido. Escolhe outro.')
        return cleaned
