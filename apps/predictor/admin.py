from django.contrib import admin
from apps.predictor.models import PredictionRecord


@admin.register(PredictionRecord)
class PredictionRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "floor_count", "max_confidence", "image_width", "image_height", "created_at"]
    list_filter = ["floor_count", "created_at"]
    readonly_fields = ["result_json", "created_at"]
