from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'tablet'

urlpatterns = [
    path('entrar/', auth_views.LoginView.as_view(
        template_name='tablet/login.html', redirect_authenticated_user=True), name='login'),
    path('sair/', auth_views.LogoutView.as_view(next_page='tablet:login'), name='logout'),
    path('', views.inicio, name='inicio'),
    path('nova/', views.nova_ordem, name='nova_ordem'),
    path('ordem/<int:pk>/', views.ordem, name='ordem'),
    path('ordem/<int:pk>/iniciar/', views.iniciar, name='iniciar'),
    path('ordem/<int:pk>/parar/', views.parar, name='parar'),
    path('ordem/<int:pk>/foto/', views.foto, name='foto'),
    path('ordem/<int:pk>/extra/', views.extra, name='extra'),
    path('ordem/<int:pk>/concluir/', views.concluir, name='concluir'),
]
