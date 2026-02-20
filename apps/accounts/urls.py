from django.urls import path
from .views import RegisterView, ProfileView, GoogleAuthURLView, GoogleCallbackView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('google/url/', GoogleAuthURLView.as_view(), name='google-auth-url'),
    path('google/callback/', GoogleCallbackView.as_view(), name='google-callback'),
]