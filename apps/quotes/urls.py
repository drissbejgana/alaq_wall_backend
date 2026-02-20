from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuoteViewSet, OrderViewSet, InvoiceViewSet, DashboardView, CalculatePreviewView

router = DefaultRouter()
router.register('quotes', QuoteViewSet, basename='quote')
router.register('orders', OrderViewSet, basename='order')
router.register('invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('calculate/', CalculatePreviewView.as_view(), name='calculate-preview'),
    path('', include(router.urls)),
]