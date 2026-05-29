"""
Django settings for fulltorque project.

Full Torque — app de gestão de oficina automóvel.
Gerado com Django 5.2 LTS. SQLite em local; visão de longo prazo é uma cadeia de oficinas.
"""

from pathlib import Path

from django.templatetags.static import static
from django.urls import reverse_lazy

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-mac=cm42lopa^*o78+9+=%_(-5b!*1qufro^20idw(o5brdtyu'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    # Tema moderno do admin (django-unfold) — TEM de vir antes de django.contrib.admin
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps do projeto
    'contas',        # autenticação + custom User (papel: cliente/funcionario/dono)
    'oficina',       # domínio: Local, Cliente, Viatura, TipoServico, Funcionario, RegistoServico, Marcacao
    'site_publico',  # site público anónimo
    'portal',        # área de cliente autenticada
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fulltorque.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fulltorque.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Custom User model — decidido desde o início (mudar depois é caríssimo).
# Login por email; o papel distingue cliente / funcionário / dono.
AUTH_USER_MODEL = 'contas.User'

# Portal do cliente (autenticação)
LOGIN_URL = 'portal:login'
LOGIN_REDIRECT_URL = 'portal:dashboard'
LOGOUT_REDIRECT_URL = 'site_publico:home'

# Email — em dev imprime na consola; em produção trocar por SMTP.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Full Torque <geral@fulltorque.pt>'


# Tema do admin (django-unfold) — branding e cores alinhadas com o site público.
UNFOLD = {
    'SITE_TITLE': 'Full Torque',
    'SITE_HEADER': 'Full Torque',
    'SITE_SUBHEADER': 'Gestão da oficina',
    'SITE_ICON': lambda request: static('img/favicon-32.png'),
    'SITE_LOGO': {
        'light': lambda request: static('img/logo.png'),
        'dark': lambda request: static('img/logo-dark.png'),
    },
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': True,
    'COLORS': {
        # Vermelho da marca Full Torque
        'primary': {
            '50': '254 242 242',
            '100': '254 226 226',
            '200': '254 202 202',
            '300': '252 165 165',
            '400': '248 113 113',
            '500': '239 68 68',
            '600': '220 38 38',
            '700': '185 28 28',
            '800': '153 27 27',
            '900': '127 29 29',
            '950': '69 10 10',
        },
    },
    'DASHBOARD_CALLBACK': 'oficina.dashboard.dashboard_callback',
    'SIDEBAR': {
        'show_search': True,
        'navigation': [
            {
                'title': 'Operação',
                'items': [
                    {'title': 'Painel', 'icon': 'dashboard', 'link': reverse_lazy('admin:index')},
                    {'title': 'Marcações', 'icon': 'event', 'link': reverse_lazy('admin:oficina_marcacao_changelist')},
                    {'title': 'Viaturas', 'icon': 'directions_car', 'link': reverse_lazy('admin:oficina_viatura_changelist')},
                    {'title': 'Registos de serviço', 'icon': 'build', 'link': reverse_lazy('admin:oficina_registoservico_changelist')},
                    {'title': 'Inspeções', 'icon': 'checklist', 'link': reverse_lazy('admin:oficina_inspecao_changelist')},
                    {'title': 'Orçamentos', 'icon': 'request_quote', 'link': reverse_lazy('admin:oficina_orcamento_changelist')},
                    {'title': 'Clientes', 'icon': 'group', 'link': reverse_lazy('admin:oficina_cliente_changelist')},
                ],
            },
            {
                'title': 'Catálogo',
                'collapsible': True,
                'permission': lambda request: request.user.is_superuser,
                'items': [
                    {'title': 'Marcas', 'icon': 'sell', 'link': reverse_lazy('admin:oficina_marca_changelist')},
                    {'title': 'Modelos', 'icon': 'category', 'link': reverse_lazy('admin:oficina_modelo_changelist')},
                    {'title': 'Tipos de serviço', 'icon': 'home_repair_service', 'link': reverse_lazy('admin:oficina_tiposervico_changelist')},
                    {'title': 'Peças', 'icon': 'inventory_2', 'link': reverse_lazy('admin:oficina_peca_changelist')},
                    {'title': 'Stock', 'icon': 'warehouse', 'link': reverse_lazy('admin:oficina_stockpeca_changelist')},
                ],
            },
            {
                'title': 'Gestão',
                'collapsible': True,
                'permission': lambda request: request.user.is_superuser,
                'items': [
                    {'title': 'Locais', 'icon': 'store', 'link': reverse_lazy('admin:oficina_local_changelist')},
                    {'title': 'Funcionários', 'icon': 'badge', 'link': reverse_lazy('admin:oficina_funcionario_changelist')},
                    {'title': 'Utilizadores', 'icon': 'manage_accounts', 'link': reverse_lazy('admin:contas_user_changelist')},
                ],
            },
        ],
    },
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-pt'

TIME_ZONE = 'Europe/Lisbon'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media (fotos dos registos de serviço)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
