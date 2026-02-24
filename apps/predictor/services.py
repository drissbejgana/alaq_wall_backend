"""
YOLOv8 segmentation model service.
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
from django.conf import settings

logger = logging.getLogger(__name__)


class YOLOService:
    """Singleton wrapper around the Ultralytics YOLO segmentation model."""

    _instance: Optional["YOLOService"] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── Model loading ────────────────────────────────────────

    def load_model(self):
        """Load the YOLO model from disk. Called once at startup via AppConfig.ready()."""
        model_path = Path(settings.YOLO_MODEL_PATH)

        try:
            from ultralytics import YOLO

            if not model_path.exists():
                logger.warning(
                    f"Model file not found at {model_path}. "
                    "Running in DEMO mode (empty predictions)."
                )
                self._model = None
                return

            self._model = YOLO(str(model_path))
            logger.info(f"✓ YOLO model loaded from {model_path}")
            logger.info(f"  Model class names: {self._model.names}")

        except ImportError:
            logger.warning("ultralytics not installed — running in DEMO mode.")
            self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    # ── Inference ────────────────────────────────────────────

    def predict(self, image: Image.Image) -> dict:
        """
        Run YOLOv8 segmentation on a PIL Image.
        """
        width, height = image.size
        logger.debug(f"predict() called — image size: {width}x{height}, mode: {image.mode}")

        if not self.is_loaded:
            logger.warning("Model not loaded — returning empty predictions.")
            return {
                "predictions": [],
                "image_width": width,
                "image_height": height,
            }

        try:
            # ✅ Pass PIL Image directly — Ultralytics handles scaling correctly
            # This fixes coordinate mismatches that occur when passing numpy arrays
            results = self._model.predict(
                source=image,
                classes=[1],
            )
        except Exception as e:
            logger.error(f"self._model.predict() threw: {e}", exc_info=True)
            raise

        logger.debug(f"YOLO returned {len(results)} result(s)")

        predictions = []

        for result_idx, r in enumerate(results):
            logger.debug(f"Result[{result_idx}]: masks={r.masks}, boxes={r.boxes}")

            # ── Guard: no detections at all ──
            if r.masks is None:
                logger.debug(f"Result[{result_idx}]: masks is None — skipping")
                continue

            if r.boxes is None:
                logger.debug(f"Result[{result_idx}]: boxes is None — skipping")
                continue

            masks_xy = r.masks.xy
            boxes = r.boxes

            logger.debug(f"Result[{result_idx}]: {len(masks_xy)} mask(s), {len(boxes)} box(es)")

            for i, (mask, box) in enumerate(zip(masks_xy, boxes)):

                # ── Guard: empty mask ──
                if mask is None or len(mask) == 0:
                    logger.debug(f"  mask[{i}] is empty — skipping")
                    continue

                # ── Guard: empty box tensors ──
                if box is None:
                    logger.debug(f"  box[{i}] is None — skipping")
                    continue

                cls_tensor = box.cls
                conf_tensor = box.conf

                if cls_tensor is None or len(cls_tensor) == 0:
                    logger.debug(f"  box[{i}].cls is empty — skipping")
                    continue

                if conf_tensor is None or len(conf_tensor) == 0:
                    logger.debug(f"  box[{i}].conf is empty — skipping")
                    continue

                class_id = int(cls_tensor[0])
                confidence = round(float(conf_tensor[0]), 4)

                # ── Guard: class_id not in model names ──
                class_name = self._model.names.get(class_id, f"class_{class_id}")

                points = [
                    {
                        "x": round(float(pt[0]), 2),
                        "y": round(float(pt[1]), 2),
                    }
                    for pt in mask
                ]

                logger.debug(
                    f"  Detection[{i}]: class={class_name}({class_id}), "
                    f"conf={confidence}, points={len(points)}"
                )

                predictions.append({
                    "class": class_name,
                    "class_id": class_id,
                    "confidence": confidence,
                    "points": points,
                })

        predictions.sort(key=lambda p: p["confidence"], reverse=True)

        logger.debug(f"Returning {len(predictions)} prediction(s)")

        return {
            "predictions": predictions,
            "image_width": width,
            "image_height": height,
        }


# Module-level singleton
yolo_service = YOLOService()