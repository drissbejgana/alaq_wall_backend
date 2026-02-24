"""
Django management command to train the YOLOv8 segmentation model.

This wraps the exact training code from your Colab notebook:

    from roboflow import Roboflow
    rf = Roboflow(api_key="YOUR_KEY")
    project = rf.workspace("inset").project("roomvo")
    version = project.version(1)
    dataset = version.download("yolov8")

    from ultralytics import YOLO
    model = YOLO('yolov8n-seg.pt')
    model.train(data=f"{dataset.location}/data.yaml", epochs=50, imgsz=640)

Usage:
    python manage.py train_model
    python manage.py train_model --epochs 100 --imgsz 640
    python manage.py train_model --skip-download   # if dataset already downloaded
"""
import shutil
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Download dataset from Roboflow and train YOLOv8 segmentation model"

    def add_arguments(self, parser):
        parser.add_argument(
            "--api-key",
            type=str,
            default="0BpyGvRP0tXzMO3Mp5BH",
            help="Roboflow API key",
        )
        parser.add_argument(
            "--workspace",
            type=str,
            default="inset",
            help="Roboflow workspace name",
        )
        parser.add_argument(
            "--project",
            type=str,
            default="roomvo",
            help="Roboflow project name",
        )
        parser.add_argument(
            "--version",
            type=int,
            default=1,
            help="Roboflow dataset version",
        )
        parser.add_argument(
            "--epochs",
            type=int,
            default=50,
            help="Training epochs (default: 50)",
        )
        parser.add_argument(
            "--imgsz",
            type=int,
            default=640,
            help="Image size (default: 640)",
        )
        parser.add_argument(
            "--base-model",
            type=str,
            default="yolov8n-seg.pt",
            help="Base YOLO model (default: yolov8n-seg.pt)",
        )
        parser.add_argument(
            "--skip-download",
            action="store_true",
            help="Skip dataset download (use existing)",
        )

    def handle(self, *args, **options):
        try:
            from ultralytics import YOLO
        except ImportError:
            raise CommandError("ultralytics not installed. Run: pip install ultralytics")

        dataset_location = None

        # ── Step 1: Download dataset ──────────────────────
        if not options["skip_download"]:
            self.stdout.write(self.style.WARNING("\n📥 Step 1: Downloading dataset from Roboflow...\n"))

            try:
                from roboflow import Roboflow
            except ImportError:
                raise CommandError("roboflow not installed. Run: pip install roboflow")

            rf = Roboflow(api_key=options["api_key"])
            project = rf.workspace(options["workspace"]).project(options["project"])
            version = project.version(options["version"])
            dataset = version.download("yolov8")
            dataset_location = dataset.location

            self.stdout.write(self.style.SUCCESS(f"✓ Dataset downloaded to: {dataset_location}\n"))
        else:
            # Try to find existing dataset
            possible = list(Path(".").glob("**/data.yaml"))
            if possible:
                dataset_location = str(possible[0].parent)
                self.stdout.write(f"Using existing dataset at: {dataset_location}\n")
            else:
                raise CommandError("No data.yaml found. Run without --skip-download first.")

        # ── Step 2: Train model ───────────────────────────
        self.stdout.write(self.style.WARNING(
            f"\n🏋️ Step 2: Training {options['base_model']} for {options['epochs']} epochs...\n"
        ))

        model = YOLO(options["base_model"])
        model.train(
            data=f"{dataset_location}/data.yaml",
            epochs=options["epochs"],
            imgsz=options["imgsz"],
            plots=True,
        )

        self.stdout.write(self.style.SUCCESS("\n✓ Training complete!\n"))

        # ── Step 3: Copy best weights to ml_models/ ──────
        best_weights = Path("runs/segment/train/weights/best.pt")
        if not best_weights.exists():
            # Check for train2, train3, etc.
            runs = sorted(Path("runs/segment").glob("train*/weights/best.pt"))
            if runs:
                best_weights = runs[-1]

        if best_weights.exists():
            dest = Path(settings.YOLO_MODEL_PATH)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(best_weights, dest)
            self.stdout.write(self.style.SUCCESS(
                f"✓ Best weights copied to: {dest}\n"
            ))
            self.stdout.write(
                "\n🚀 Model is ready! Restart the Django server to load it.\n"
                "   python manage.py runserver\n"
            )
        else:
            self.stdout.write(self.style.ERROR(
                "⚠ Could not find best.pt — check runs/segment/ directory.\n"
            ))
