import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class PredictorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.predictor"
    verbose_name = "Floor Predictor"

    def ready(self):
        """Load the YOLO model once when Django starts."""
        from apps.predictor.services import yolo_service
        yolo_service.load_model()
