from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import ClienteLoginForm

app_name = 'portal'

urlpatterns = [
    path('entrar/', auth_views.LoginView.as_view(
        template_name='portal/login.html',
        authentication_form=ClienteLoginForm,
        redirect_authenticated_user=True), name='login'),
    path('sair/', auth_views.LogoutView.as_view(), name='logout'),
    path('registar/', views.register, name='register'),
    path('', views.dashboard, name='dashboard'),
    path('viatura/<int:pk>/', views.viatura_detail, name='viatura'),
]
