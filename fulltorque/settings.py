"""
Django settings for fulltorque project.

Full Torque — app de gestão de oficina automóvel.
Gerado com Django 5.2 LTS. SQLite em local; visão de longo prazo é uma cadeia de oficinas.
"""

import os
from pathlib import Path

import dj_database_url
from django.templatetags.static import static
from django.urls import reverse_lazy

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-mac=cm42lopa^*o78+9+=%_(-5b!*1qufro^20idw(o5brdtyu')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]


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
    'tablet',        # tablet do funcionário (ordens de trabalho)
    'sync',          # sincronização oficina (local) <-> cloud
    'faturacao',     # faturas puxadas do software certificado (API) -> portal
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise serve os ficheiros estáticos em produção.
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

# SQLite em local; em produção usa DATABASE_URL (Postgres no Render/Railway/Neon).
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
        conn_health_checks=True,
    )
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

# Papel do deployment: 'completo' (tudo, dev) | 'oficina' (local: tablet+admin) | 'cloud' (site+portal).
FT_ROLE = os.environ.get('FT_ROLE', 'completo')

# Sincronização oficina (local) <-> cloud
SYNC_API_KEY = os.environ.get('SYNC_API_KEY', 'dev-sync-key')
SYNC_CLOUD_URL = os.environ.get('SYNC_CLOUD_URL', '').rstrip('/')  # base URL da cloud (usado no servidor local)

# Faturação: software certificado (API) de onde PUXAMOS as faturas para o portal.
# Vazio = desligado (o portal mostra "sem faturas"). Valores: 'demo'|'invoicexpress'|'moloni'.
FATURACAO_PROVIDER = os.environ.get('FATURACAO_PROVIDER', '')
FATURACAO_API_KEY = os.environ.get('FATURACAO_API_KEY', '')
FATURACAO_CONTA = os.environ.get('FATURACAO_CONTA', '')        # conta/empresa no software
FATURACAO_API_URL = os.environ.get('FATURACAO_API_URL', '')   # base URL, se aplicável


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
                    {'title': 'Faturas', 'icon': 'receipt_long', 'link': reverse_lazy('admin:faturacao_fatura_changelist')},
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

# WhiteNoise: comprime e serve os estáticos em produção (collectstatic -> staticfiles/).
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# Fotos (media) em produção: object storage S3-compatível (Cloudflare R2 / AWS S3).
# Ativa-se quando AWS_STORAGE_BUCKET_NAME está definido; senão fica em disco local.
if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': os.environ['AWS_STORAGE_BUCKET_NAME'],
            'access_key': os.environ.get('AWS_ACCESS_KEY_ID'),
            'secret_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
            'endpoint_url': os.environ.get('AWS_S3_ENDPOINT_URL'),   # R2: https://<account_id>.r2.cloudflarestorage.com
            'region_name': os.environ.get('AWS_S3_REGION_NAME', 'auto'),
            'custom_domain': os.environ.get('AWS_S3_CUSTOM_DOMAIN') or None,
            'querystring_auth': os.environ.get('AWS_S3_QUERYSTRING_AUTH', 'False') == 'True',
            'file_overwrite': False,
            'default_acl': None,  # o R2 não usa ACLs
        },
    }

# Media (fotos dos registos de serviço)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Segurança em produção (atrás do proxy HTTPS do host de alojamento)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SSL_REDIRECT', 'True') == 'True'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
