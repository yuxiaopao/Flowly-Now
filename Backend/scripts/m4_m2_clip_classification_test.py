#!/usr/bin/env python
"""M4.2 — CLIP classification node smoke tests."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "Backend"
FRONTEND = REPO / "Frontend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from training.clip_service import run_zero_shot_classification, run_finetune_classification  # noqa: E402
from workflows.services.langchain_service import LangChainService  # noqa: E402


def _write_png(path: Path) -> None:
    path.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        )
    )


def test_zero_shot_service() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_zero_shot_classification(tmp, ["cat", "dog"], tmp, base_model="ViT-B/32")
        assert result["success"], result.get("error")
        assert Path(result["model_path"]).is_file()
        assert result["class_names"] == ["cat", "dog"]


def test_finetune_service() -> None:
    try:
        import torch  # noqa: F401
    except ImportError:
        print("SKIP  test_finetune_service (torch not installed)")
        return

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "data"
        for cls in ("cat", "dog"):
            d = root / "train" / cls
            d.mkdir(parents=True)
            _write_png(d / f"{cls}.png")
            _write_png(d / f"{cls}_2.png")

        out = Path(tmp) / "out"
        result = run_finetune_classification(
            str(root),
            ["cat", "dog"],
            str(out),
            epochs=2,
            batch_size=2,
        )
        assert result["success"], result.get("error")
        assert result["metrics"]["accuracy"] >= 0


def test_runner_zero_shot() -> None:
    svc = LangChainService()
    out = svc.run_clip_classification_node(
        {
            "mode": "zero_shot",
            "classNames": ["apple", "orange"],
            "baseModel": "ViT-B/32",
            "outputDir": tempfile.mkdtemp(),
            "label": "M4ZeroShot",
        },
        {},
    )
    assert out.get("success"), out.get("error")
    payload = out["output"]
    assert payload["training_run_id"]
    assert payload["model_path"]
    assert payload["class_names"] == ["apple", "orange"]


def test_static_frontend() -> None:
    files = [
        FRONTEND / "src/components/workflow/nodes/ClipClassificationNode.vue",
        FRONTEND / "src/components/workflow/nodes/ClipRetrievalNode.vue",
        FRONTEND / "src/components/workflow/configs/ClipClassificationConfig.vue",
        FRONTEND / "src/components/workflow/configs/ClipRetrievalConfig.vue",
    ]
    for f in files:
        assert f.is_file(), f"missing {f}"

    registry = (FRONTEND / "src/config/nodeRegistry.js").read_text(encoding="utf-8")
    assert "clip_classification" in registry
    assert "clip_retrieval" in registry

    lc = (BACKEND / "workflows/services/langchain_service.py").read_text(encoding="utf-8")
    assert "def run_clip_classification_node" in lc
    assert "def run_clip_retrieval_node" in lc


def main() -> int:
    tests = [
        test_zero_shot_service,
        test_finetune_service,
        test_runner_zero_shot,
        test_static_frontend,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc}")
        except Exception as exc:
            failed += 1
            print(f"ERROR {fn.__name__}: {exc}")

    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
