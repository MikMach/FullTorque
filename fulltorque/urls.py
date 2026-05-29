"""URL configuration for fulltorque project.

As URLs activas dependem de FT_ROLE:
- 'completo' (dev): tudo.
- 'oficina'  (servidor local): admin + tablet + sync.
- 'cloud'    (internet): admin + site público + portal + marcações + sync.
"""
import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

ROLE = settings.FT_ROLE

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sync/', include('sync.urls')),
]

if ROLE in ('completo', 'oficina'):
    urlpatterns += [path('tablet/', include('tablet.urls'))]

if ROLE in ('completo', 'cloud'):
    urlpatterns += [
        path('cliente/', include('portal.urls')),
        path('', include('site_publico.urls')),
    ]
elif ROLE == 'oficina':
    # No servidor local, a raiz abre o tablet.
    urlpatterns += [path('', RedirectView.as_view(pattern_name='tablet:inicio', permanent=False))]

# Servir media: em DEBUG via static(); em produção só se NÃO houver object storage (R2/S3).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif not os.environ.get('AWS_STORAGE_BUCKET_NAME'):
    from django.urls import re_path
    from django.views.static import serve
    urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})]
