"""URL configuration for fulltorque project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cliente/', include('portal.urls')),
    path('tablet/', include('tablet.urls')),
    path('', include('site_publico.urls')),
]

# Servir ficheiros de media (fotos) em desenvolvimento.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
