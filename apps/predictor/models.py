"""
Database models for the predictor app.

These are optional — the API works without them.
Enable them if you want to track prediction history.
"""
from django.db import models


class PredictionRecord(models.Model):
    """Stores each prediction for analytics / history."""

    image = models.ImageField(upload_to="uploads/%Y/%m/%d/")
    result_json = models.JSONField(default=dict)
    floor_count = models.IntegerField(default=0)
    max_confidence = models.FloatField(default=0.0)
    image_width = models.IntegerField(default=0)
    image_height = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Prediction #{self.pk} — {self.floor_count} floors ({self.created_at:%Y-%m-%d %H:%M})"
