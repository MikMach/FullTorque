from django.urls import path

from . import views

app_name = 'site_publico'

urlpatterns = [
    path('', views.home, name='home'),
    path('marcar/', views.marcar, name='marcar'),
    path('marcar/horas/', views.horas, name='horas'),
    path('marcar/modelos/', views.modelos_por_marca, name='modelos_por_marca'),
    path('marcacao/<int:pk>/confirmada/', views.marcacao_confirmada, name='marcacao_confirmada'),
]
