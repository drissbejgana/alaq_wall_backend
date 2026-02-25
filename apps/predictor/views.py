"""
API views for the FloorViz predictor.

Endpoints:
    POST /api/predict/   — Upload image → floor polygon predictions
    POST /api/area/      — Polygon + reference → real-world area (m²)
    GET  /api/health/    — Health check
"""
import logging
import traceback

from PIL import Image
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from apps.predictor.services import yolo_service
from apps.predictor.serializers import (
    ImageUploadSerializer,
    AreaRequestSerializer,
)
from apps.predictor.models import PredictionRecord

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# POST /api/predict/
# ─────────────────────────────────────────────────────────
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def predict_floor(request):
    """
    Upload a room image and get floor segmentation polygon coordinates.

    Request:  multipart/form-data with field `file` (image)
    Response: {predictions: [...], image_width, image_height}
    """
    serializer = ImageUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = serializer.validated_data["file"]

    try:
        # ✅ Seek to start — file pointer may already be at end from validation
        uploaded_file.seek(0)
        image = Image.open(uploaded_file).convert("RGB")
        image.load()  # ✅ Force full decode NOW while file is still open
    except Exception as e:
        logger.error(f"Failed to open image: {e}\n{traceback.format_exc()}")
        return Response(
            {"error": "Could not read image file."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Run YOLO inference
    try:
        result = yolo_service.predict(image)
    except Exception as e:
        # ✅ Full traceback so you can see the exact line
        logger.error(f"Prediction failed:\n{traceback.format_exc()}")
        return Response(
            {"error": "Model inference failed.", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # try:
    #     # ✅ Rewind file pointer before saving to DB — after Image.open() it's at EOF
    #     uploaded_file.seek(0)
    #     PredictionRecord.objects.create(
    #         image=uploaded_file,
    #         result_json=result,
    #         floor_count=len(result["predictions"]),
    #         max_confidence=(
    #             max(p["confidence"] for p in result["predictions"])
    #             if result["predictions"]
    #             else 0.0
    #         ),
    #         image_width=result["image_width"],
    #         image_height=result["image_height"],
    #     )
    # except Exception as e:
    #     # Don't fail the request if DB write fails
    #     logger.warning(f"Could not save prediction record: {e}\n{traceback.format_exc()}")

    return Response(result, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────
# POST /api/area/
# ─────────────────────────────────────────────────────────
@api_view(["POST"])
@parser_classes([JSONParser])
def calculate_area(request):
    """
    Calculate real-world floor area from polygon + reference measurement.

    Request JSON:
    {
        "points": [{"x": ..., "y": ...}, ...],
        "image_width": 640,
        "image_height": 384,
        "reference_length_px": 100,
        "reference_length_cm": 60
    }
    """
    serializer = AreaRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    points = data["points"]
    ref_px = data["reference_length_px"]
    ref_cm = data["reference_length_cm"]

    # Shoelace formula
    n = len(points)
    area_px = 0.0
    for i in range(n):
        j = (i + 1) % n
        # ✅ DRF returns OrderedDicts from nested serializers — access safely
        xi = points[i].get("x") if hasattr(points[i], "get") else points[i]["x"]
        yi = points[i].get("y") if hasattr(points[i], "get") else points[i]["y"]
        xj = points[j].get("x") if hasattr(points[j], "get") else points[j]["x"]
        yj = points[j].get("y") if hasattr(points[j], "get") else points[j]["y"]

        if xi is None or yi is None or xj is None or yj is None:
            return Response(
                {"error": f"Point at index {i} or {j} has None coordinate."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        area_px += xi * yj
        area_px -= xj * yi

    area_px = abs(area_px) / 2.0

    # Scale: cm per pixel
    scale = ref_cm / ref_px

    # px² → cm² → m²
    area_cm2 = area_px * (scale ** 2)
    area_m2 = area_cm2 / 10_000

    return Response(
        {
            "area_px": round(area_px, 2),
            "area_m2": round(area_m2, 2),
            "scale_factor": round(scale, 4),
        },
        status=status.HTTP_200_OK,
    )


# ─────────────────────────────────────────────────────────
# GET /api/health/
# ─────────────────────────────────────────────────────────
@api_view(["GET"])
def health_check(request):
    """Health check — also reports whether the YOLO model is loaded."""
    return Response(
        {
            "status": "ok",
            "model_loaded": yolo_service.is_loaded,
            "model_path": str(yolo_service._model.model_name) if yolo_service.is_loaded else None,
        },
        status=status.HTTP_200_OK,
    )