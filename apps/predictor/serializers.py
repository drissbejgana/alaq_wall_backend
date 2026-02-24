"""
Serializers for the predictor API.
"""
from rest_framework import serializers


# ── Request serializers ──────────────────────────────────

class ImageUploadSerializer(serializers.Serializer):
    """Validates the uploaded image file."""
    file = serializers.ImageField(
        help_text="Room image (JPG, PNG, WebP). Max 10 MB."
    )


class PointSerializer(serializers.Serializer):
    x = serializers.FloatField()
    y = serializers.FloatField()


class AreaRequestSerializer(serializers.Serializer):
    """Validates area calculation input."""
    points = PointSerializer(many=True, min_length=3)
    image_width = serializers.IntegerField(min_value=1)
    image_height = serializers.IntegerField(min_value=1)
    reference_length_px = serializers.FloatField(min_value=0.01)
    reference_length_cm = serializers.FloatField(min_value=0.01)


# ── Response serializers ─────────────────────────────────

class PredictionSerializer(serializers.Serializer):
    """Single floor prediction."""

    # 'class' is a Python keyword, so we use source mapping
    floor_class = serializers.CharField(source="class")
    class_id = serializers.IntegerField()
    confidence = serializers.FloatField()
    points = PointSerializer(many=True)


class PredictionResponseSerializer(serializers.Serializer):
    """Full prediction response."""
    predictions = PredictionSerializer(many=True)
    image_width = serializers.IntegerField()
    image_height = serializers.IntegerField()


class AreaResponseSerializer(serializers.Serializer):
    """Area calculation response."""
    area_px = serializers.FloatField()
    area_m2 = serializers.FloatField()
    scale_factor = serializers.FloatField()
