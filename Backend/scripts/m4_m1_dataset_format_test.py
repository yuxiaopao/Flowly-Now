#!/usr/bin/env python
"""
M4.1 — ML dataset format validators + dataset_upload node smoke tests.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "Backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from datasets.ml_format_validators import validate_ml_dataset  # noqa: E402
from workflows.services.langchain_service import LangChainService  # noqa: E402


def _write_png(path: Path) -> None:
    # Minimal valid 1x1 PNG
    path.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        )
    )


def test_classification_folders() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for cls in ("cat", "dog"):
            d = root / "train" / cls
            d.mkdir(parents=True)
            _write_png(d / f"{cls}.png")
        result = validate_ml_dataset(str(root), "classification_folders")
        assert result["valid"], result.get("error")
        assert set(result["class_names"]) == {"cat", "dog"}
        assert result["stats"]["image_count"] == 2


def test_image_text_pairs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        img = root / "a.png"
        _write_png(img)
        pairs = root / "pairs.jsonl"
        pairs.write_text(
            json.dumps({"image": "a.png", "text": "a cat"}) + "\n",
            encoding="utf-8",
        )
        result = validate_ml_dataset(str(root), "image_text_pairs")
        assert result["valid"], result.get("error")
        assert result["stats"]["image_count"] == 1


def test_image_folder() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        images = root / "images"
        images.mkdir()
        _write_png(images / "1.png")
        result = validate_ml_dataset(str(root), "image_folder")
        assert result["valid"], result.get("error")
        assert result["stats"]["image_count"] == 1


def test_yolo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "images").mkdir()
        (root / "labels").mkdir()
        _write_png(root / "images" / "img1.png")
        (root / "labels" / "img1.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        (root / "data.yaml").write_text(
            "path: .\ntrain: images\nnc: 2\nnames: [helmet, no_helmet]\n",
            encoding="utf-8",
        )
        result = validate_ml_dataset(str(root), "yolo")
        assert result["valid"], result.get("error")
        assert result["class_names"] == ["helmet", "no_helmet"]
        assert result["dataset_yaml_path"]


def test_dataset_upload_runner() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "images").mkdir()
        _write_png(root / "images" / "x.png")
        pairs = root / "pairs.jsonl"
        pairs.write_text(
            json.dumps({"image": "images/x.png", "text": "sample"}) + "\n",
            encoding="utf-8",
        )
        svc = LangChainService()
        out = svc.run_dataset_upload_node(
            {
                "source": "upload",
                "path": str(root),
                "format": "image_text_pairs",
                "label": "M4Smoke",
            },
            {},
        )
        assert out.get("success"), out.get("error")
        payload = out["output"]
        assert payload["format"] == "image_text_pairs"
        assert payload["dataset_path"]
        assert payload["stats"]["image_count"] == 1


def main() -> int:
    tests = [
        test_classification_folders,
        test_image_text_pairs,
        test_image_folder,
        test_yolo,
        test_dataset_upload_runner,
    ]
    failed = 0
    for fn in tests:
        name = fn.__name__
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {name}: {exc}")
        except Exception as exc:
            failed += 1
            print(f"ERROR {name}: {exc}")

    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
