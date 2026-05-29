from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Gestor de utilizadores que usa o email como identificador de login."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('papel', self.model.Papel.DONO)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser tem de ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser tem de ter is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Utilizador da plataforma.

    Login por email (sem username). O campo `papel` distingue os três públicos:
    cliente, funcionário e dono.
    """

    class Papel(models.TextChoices):
        CLIENTE = 'cliente', _('Cliente')
        FUNCIONARIO = 'funcionario', _('Funcionário')
        DONO = 'dono', _('Dono')

    # Removemos o username: o identificador de login passa a ser o email.
    username = None
    email = models.EmailField(_('email'), unique=True)
    papel = models.CharField(
        _('papel'), max_length=20, choices=Papel.choices, default=Papel.CLIENTE
    )
    telefone = models.CharField(_('telefone'), max_length=20, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _('utilizador')
        verbose_name_plural = _('utilizadores')

    def __str__(self):
        nome = self.get_full_name()
        return f'{nome or self.email} ({self.get_papel_display()})'
