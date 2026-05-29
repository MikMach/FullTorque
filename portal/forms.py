"""Formulários do portal do cliente: login (por email) e registo."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from oficina.models import Cliente

User = get_user_model()


class ClienteLoginForm(AuthenticationForm):
    """Login por email (o campo 'username' do AuthenticationForm = email)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'
        self.fields['username'].widget = forms.EmailInput(attrs={'class': 'field', 'autofocus': True})
        self.fields['password'].widget.attrs.update({'class': 'field'})


class RegistoClienteForm(forms.Form):
    nome = forms.CharField(label='Nome', max_length=160, widget=forms.TextInput(attrs={'class': 'field'}))
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'field'}))
    telefone = forms.CharField(label='Telefone', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'field'}))
    password1 = forms.CharField(label='Palavra-passe', widget=forms.PasswordInput(attrs={'class': 'field'}))
    password2 = forms.CharField(label='Confirmar palavra-passe', widget=forms.PasswordInput(attrs={'class': 'field'}))

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Já existe uma conta com este email. Inicia sessão.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'As palavras-passe não coincidem.')
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as exc:
                self.add_error('password1', exc)
        return cleaned

    def save(self):
        cd = self.cleaned_data
        partes = cd['nome'].split()
        user = User.objects.create_user(
            email=cd['email'], password=cd['password1'], papel=User.Papel.CLIENTE,
            first_name=partes[0], last_name=' '.join(partes[1:]))
        # Se já existe um Cliente (criado pelo staff/marcação) sem conta, liga-o.
        cliente = Cliente.objects.filter(email__iexact=cd['email'], user__isnull=True).first()
        if cliente:
            cliente.user = user
            if not cliente.telefone:
                cliente.telefone = cd['telefone']
            cliente.save()
        else:
            Cliente.objects.create(user=user, nome=cd['nome'], email=cd['email'], telefone=cd['telefone'])
        return user
