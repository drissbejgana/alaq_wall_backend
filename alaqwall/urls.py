"""AlaqWall URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('api/auth/', include('apps.accounts.urls')),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # DTU reference data
    path('api/dtu/', include('apps.dtu.urls')),

    # Quotes, Orders, Invoices
    path('api/', include('apps.quotes.urls')),

    # DRF browsable API login
    path('api-auth/', include('rest_framework.urls')),
]
