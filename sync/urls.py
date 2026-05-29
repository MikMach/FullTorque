from django.urls import path

from . import views

app_name = 'sync'

urlpatterns = [
    path('push/', views.push, name='push'),
    path('pull/', views.pull, name='pull'),
    path('ficheiro/', views.ficheiro, name='ficheiro'),
]
