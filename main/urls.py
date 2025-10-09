from django.urls import path
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('home/', views.home, name='home'),
    path('paper/<str:paper_osd>/', views.paper, name='paper'),
]