from . import views
from django.urls import path

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.home, name='search'),
    path('details/', views.details, name='details'),
    path('about/', views.about, name='about'),
]