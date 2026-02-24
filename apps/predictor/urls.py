"""
Predictor API URL patterns.

    POST /api/predict/   → predict_floor
    POST /api/area/      → calculate_area
    GET  /api/health/    → health_check
"""
from django.urls import path
from apps.predictor import views

urlpatterns = [
    path("predict/", views.predict_floor, name="predict-floor"),
    path("area/", views.calculate_area, name="calculate-area"),
    path("health/", views.health_check, name="health-check"),
]
