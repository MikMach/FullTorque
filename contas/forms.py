"""Formulários de admin para o custom User (login por email, sem username).

Estendem os forms do django-unfold para herdarem o estilo do tema do admin.
"""
from unfold.forms import UserChangeForm as UnfoldUserChangeForm
from unfold.forms import UserCreationForm as UnfoldUserCreationForm

from .models import User


class UserCreationForm(UnfoldUserCreationForm):
    class Meta(UnfoldUserCreationForm.Meta):
        model = User
        fields = ('email', 'papel')
        # O form base mapeia "username" -> UsernameField; o nosso User não tem username.
        field_classes = {}


class UserChangeForm(UnfoldUserChangeForm):
    class Meta(UnfoldUserChangeForm.Meta):
        model = User
        fields = '__all__'
        field_classes = {}
