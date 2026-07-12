#!/usr/bin/env python
"""M4.4 — CLIP retrieval workflow chain smoke (nodes only, no full site gen wait)."""
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

from workflows.services.langchain_service import LangChainService  # noqa: E402


def _write_jpeg(path: Path, color=(200, 100, 50)) -> None:
    from PIL import Image

    Image.new("RGB", (32, 32), color=color).save(path, format="JPEG")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="flowly_m4_chain_"))
    ds = tmp / "dataset"
    img_dir = ds / "images"
    img_dir.mkdir(parents=True)

    samples = [
        ("cat.jpg", "一只橘猫", (220, 120, 40)),
        ("dog.jpg", "金毛犬", (180, 160, 60)),
        ("shoe.jpg", "红色运动鞋", (200, 40, 40)),
    ]
    for name, text, color in samples:
        _write_jpeg(img_dir / name, color)
        with open(ds / "pairs.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"image": f"images/{name}", "text": text}, ensure_ascii=False) + "\n")

    svc = LangChainService()
    ctx: dict = {}

    upload = svc.run_dataset_upload_node(
        {
            "source": "upload",
            "path": str(ds),
            "format": "image_text_pairs",
            "label": "ChainDataset",
        },
        {},
    )
    assert upload.get("success"), upload.get("error")
    ctx.update(upload["output"])

    retrieval = svc.run_clip_retrieval_node(
        {
            "label": "ChainIndex",
            "outputDir": str(tmp / "index"),
            "baseModel": "simple-bow",
            "config": {"trainingMode": "sync"},
        },
        ctx,
    )
    assert retrieval.get("success"), retrieval.get("error")
    ctx.update(retrieval["output"])

    profiler = svc.run_project_profiler_node(
        {"websiteType": "clip_retrieval", "useLlmEnrich": False},
        ctx,
    )
    assert profiler.get("success"), profiler.get("error")
    assert profiler["output"]["recommended_template"] == "clip_retrieval"
    ctx.update(profiler["output"])

    site_out = tmp / "site_out"
    site_out.mkdir()
    wg = svc.run_website_generator_node(
        {
            "websiteType": "clip_retrieval",
            "outputDir": str(site_out),
            "indexDir": ctx.get("index_dir", ""),
            "trainingRunId": ctx.get("training_run_id", ""),
            "wizard": {
                "siteName": "链式检索演示",
                "usageDescription": "文本搜图",
                "wizardCompleted": True,
            },
            "profile": ctx.get("profile", {}),
        },
        ctx,
    )
    assert wg.get("success"), wg.get("error")
    assert wg["output"]["website_type"] == "clip_retrieval"
    assert "/search/text" in wg["output"]["inference_endpoint"]

    tpl = (REPO / "Frontend/src/config/clipRetrievalWorkflowTemplate.js").read_text(encoding="utf-8")
    seed = (BACKEND / "workflows/management/commands/seed_domain_templates.py").read_text(encoding="utf-8")
    checks = {
        "dataset_upload": bool(ctx.get("dataset_path")),
        "index_built": Path(ctx["index_dir"]).joinpath("metadata.json").is_file(),
        "profiler_retrieval": profiler["output"]["domain"] == "多模态检索",
        "website_queued": wg["output"]["status"] == "generating",
        "frontend_template": "clip_retrieval_1" in tpl,
        "seed_template": 'slug="clip-retrieval-project"' in seed,
    }
    passed = all(checks.values())
    report = {"passed": passed, "checks": checks}
    out_path = REPO / "test-reports" / "m4-chain-smoke-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
