import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


GOOGLE_CLIENT_ID = settings.GOOGLE_OAUTH2_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_OAUTH2_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_OAUTH2_REDIRECT_URI 

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _build_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    return flow


def _get_or_create_user(google_user_info: dict) -> tuple:

    email = google_user_info["email"]
    try:
        user = User.objects.get(email=email)
        return user, False
    except User.DoesNotExist:
        base_username = email.split("@")[0]
        username = base_username

        if User.objects.filter(username=username).exists():
            username = f"{base_username}_{uuid.uuid4().hex[:6]}"

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=google_user_info.get("given_name", ""),
            last_name=google_user_info.get("family_name", ""),
        )
        user.set_unusable_password()
        user.save()
        return user, True


def _jwt_for_user(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }



class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET/PUT /api/auth/profile/ — Current user profile."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ---------------------------------------------------------------------------
# Google OAuth2 views
# ---------------------------------------------------------------------------
class GoogleAuthURLView(APIView):
    """
    GET /api/auth/google/url/
    Returns the Google consent-screen URL the frontend should redirect to.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        flow = _build_flow()
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="select_account",
        )
        # Store state in session so we can verify on callback
        request.session["google_oauth_state"] = state
        return Response({"authorization_url": authorization_url, "state": state})

@method_decorator(csrf_exempt, name='dispatch')
class GoogleCallbackView(APIView):
    """
    POST /api/auth/google/callback/
    Body: { "code": "<authorization_code>", "state": "<state>" }
    Exchanges the code for tokens, verifies identity, returns JWT.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response(
                {"error": "Le paramètre 'code' est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Exchange authorization code for credentials -----------------
        try:
            flow = _build_flow()
            flow.fetch_token(code=code)
            credentials = flow.credentials
        except Exception as e:
            return Response(
                {"error": f"Échec de l'échange du code Google : {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Verify the ID token ----------------------------------------
        try:
            user_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                GOOGLE_CLIENT_ID,
            )
        except ValueError as e:
            return Response(
                {"error": f"Token Google invalide : {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user_info.get("email_verified", False):
            return Response(
                {"error": "L'adresse email Google n'est pas vérifiée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Get or create local user -----------------------------------
        user, created = _get_or_create_user(user_info)

        # --- Issue JWT tokens -------------------------------------------
        tokens = _jwt_for_user(user)
        return Response(
            {
                **tokens,
                "user": UserSerializer(user).data,
                "created": created,
            },
            status=status.HTTP_200_OK,
        )