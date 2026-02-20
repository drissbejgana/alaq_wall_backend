from django.urls import path
from .views import DTUReferenceView, SystemPreviewView

urlpatterns = [
    path('reference/', DTUReferenceView.as_view(), name='dtu-reference'),
    path('system/', SystemPreviewView.as_view(), name='system-preview'),
]