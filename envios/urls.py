from django.urls import path

from . import views
from . import views_async

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('dashboard/stats/async/', views_async.dashboard_stats_async, name='dashboard_stats_async'),
    path('encomiendas/', views.encomienda_lista, name='encomienda_lista'),
    path('encomiendas/nueva/', views.encomienda_crear, name='encomienda_crear'),
    path('encomiendas/<int:pk>/', views.encomienda_detalle, name='encomienda_detalle'),
    path(
        'encomiendas/<int:pk>/estado/',
        views.encomienda_cambiar_estado,
        name='encomienda_cambiar_estado',
    ),
]
