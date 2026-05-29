"""URL configuration for fulltorque project.

As URLs activas dependem de FT_ROLE:
- 'completo' (dev): tudo.
- 'oficina'  (servidor local): admin + tablet + sync.
- 'cloud'    (internet): admin + site público + portal + marcações + sync.
"""
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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
