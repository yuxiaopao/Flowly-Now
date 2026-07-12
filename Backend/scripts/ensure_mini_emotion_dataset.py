#!/usr/bin/env python
"""Ensure minimal YOLO emotion-detection dataset fixture exists."""
from __future__ import annotations

from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FIXTURE = BACKEND / "scripts" / "fixtures" / "t2_mini_emotion"

EMOTION_CLASSES = ["happy", "sad", "angry", "neutral", "surprise"]

# class_id cx cy w h — tiny boxes for smoke training
SAMPLE_LABELS = [
    "0 0.45 0.40 0.25 0.30\n",  # happy
    "1 0.55 0.45 0.22 0.28\n",  # sad
    "2 0.50 0.50 0.24 0.26\n",  # angry
]


def ensure_mini_emotion_dataset() -> Path:
    """Create minimal facial-emotion YOLO dataset fixture if missing."""
    root = FIXTURE
    images = root / "images" / "train"
    labels = root / "labels" / "train"
    images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        Image = None
        ImageDraw = None

    colors = [(255, 220, 100), (100, 140, 255), (255, 100, 100)]

    for i in range(3):
        img_path = images / f"face_{i}.jpg"
        lbl_path = labels / f"face_{i}.txt"
        if not lbl_path.exists():
            lbl_path.write_text(SAMPLE_LABELS[i % len(SAMPLE_LABELS)], encoding="utf-8")
        if not img_path.exists():
            if Image:
                color = colors[i % len(colors)]
                img = Image.new("RGB", (128, 128), color=color)
                if ImageDraw:
                    draw = ImageDraw.Draw(img)
                    draw.ellipse((40, 30, 88, 90), fill=(255, 220, 180))
                    draw.arc((48, 50, 80, 70), 0, 180, fill=(60, 40, 30), width=2)
                img.save(img_path)
            else:
                img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    yaml_path = root / "dataset.yaml"
    if not yaml_path.exists():
        names_block = "\n".join(f"  {idx}: {name}" for idx, name in enumerate(EMOTION_CLASSES))
        yaml_path.write_text(
            f"path: {root.as_posix()}\n"
            "train: images/train\n"
            "val: images/train\n"
            f"names:\n{names_block}\n",
            encoding="utf-8",
        )
    return root


if __name__ == "__main__":
    path = ensure_mini_emotion_dataset()
    print(path)
