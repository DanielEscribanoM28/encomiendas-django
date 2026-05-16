from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from api.auth_views import EncomiendaTokenView, LoginCookieView, LogoutCookieView
from envios import api_views as envios_api_views
from envios.viewsets import EncomiendaViewSet, RutaViewSet
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

router = DefaultRouter()
router.register('encomiendas', EncomiendaViewSet, basename='encomienda')
router.register('rutas-viewset', RutaViewSet, basename='ruta-viewset')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', EncomiendaTokenView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('auth/login-cookie/', LoginCookieView.as_view(), name='login_cookie'),
    path('auth/logout-cookie/', LogoutCookieView.as_view(), name='logout_cookie'),
    path(
        'generics/encomiendas/',
        envios_api_views.EncomiendaListCreateView.as_view(),
        name='api_encomienda_list',
    ),
    path(
        'generics/encomiendas/<int:pk>/',
        envios_api_views.EncomiendaDetailView.as_view(),
        name='api_encomienda_detail',
    ),
    path('clientes/', envios_api_views.ClienteListView.as_view(), name='api_cliente_list'),
    path('rutas/', envios_api_views.RutaListView.as_view(), name='api_ruta_list'),
    path('fbv/encomiendas/', envios_api_views.encomienda_list, name='api_fbv_encomienda_list'),
    path(
        'fbv/encomiendas/<int:pk>/',
        envios_api_views.encomienda_detail,
        name='api_fbv_encomienda_detail',
    ),
    path(
        'apiview/encomiendas/',
        envios_api_views.EncomiendaListAPIView.as_view(),
        name='api_apiview_encomienda_list',
    ),
    path(
        'apiview/encomiendas/<int:pk>/',
        envios_api_views.EncomiendaDetailAPIView.as_view(),
        name='api_apiview_encomienda_detail',
    ),
    path(
        'mixins/encomiendas/',
        envios_api_views.EncomiendaMixinListCreateView.as_view(),
        name='api_mixins_encomienda_list',
    ),
    path(
        'mixins/encomiendas/<int:pk>/',
        envios_api_views.EncomiendaMixinDetailView.as_view(),
        name='api_mixins_encomienda_detail',
    ),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
