#!/usr/bin/env python3
"""Replace hardcoded node badges/icons with NodeTypeBadge + nodeIcon."""
from __future__ import annotations

import re
from pathlib import Path

NODES_DIR = Path(__file__).resolve().parents[1] / "src" / "components" / "workflow" / "nodes"
BADGE_IMPORT = "import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'\n"

BADGE_BLOCK = re.compile(
    r"<div\s+class=\"node-type-badge\"[\s\S]*?</div>\s*\n",
    re.M,
)

DOMAIN_BADGE_WITH_BTN = re.compile(
    r"<div class=\"node-header\">\s*<div\s+class=\"node-type-badge\"[\s\S]*?</div>\s*<button",
    re.M,
)


def patch_templates(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "NODE_TYPE" not in text:
        return False
    original = text

    if BADGE_IMPORT.strip() not in text:
        m = re.search(r"import \{ useNodePresentation \}", text)
        if m:
            text = text[: m.start()] + BADGE_IMPORT + text[m.start() :]

    # domain-node header with expand button
    text = DOMAIN_BADGE_WITH_BTN.sub(
        '<div class="node-header">\n      <NodeTypeBadge :node-type="NODE_TYPE" />\n      <button',
        text,
    )

    # simple header-only badge (triggers, core)
    if "NodeTypeBadge" not in text:
        text = BADGE_BLOCK.sub('      <NodeTypeBadge :node-type="NODE_TYPE" compact />\n', text, count=1)

    # icon wrapper in body: replace first lucide component with dynamic
    text = re.sub(
        r"(class=\"node-icon-wrapper\"[\s\S]*?)\n\s*<[A-Z][a-zA-Z0-9]*\n\s*:size=\"18\"\n\s*:style=\"\{ color: nodeColor \}\"\n\s*/>",
        r"\1\n        <component\n          :is=\"nodeIcon\"\n          :size=\"18\"\n          :style=\"{ color: nodeColor }\"\n        />",
        text,
        count=1,
    )

    # fix leftover borderColor: color
    text = text.replace("borderColor: color", "borderColor: nodeColor")

    # domain badge label -> nodeLabel in default name
    text = re.sub(
        r"props\.data\.label \|\| props\.data\.name \|\| '[^']+'",
        "props.data.label || props.data.name || nodeLabel",
        text,
    )
    text = re.sub(
        r"localName\.value = v \|\| '[^']+'",
        "localName.value = v || nodeLabel",
        text,
    )

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = 0
    for path in sorted(NODES_DIR.glob("*.vue")):
        if path.name in ("NodeTypeBadge.vue", "WorkflowNodeHost.vue", "SiteFactoryNodeShell.vue", "ComfyMultimodalNodeShell.vue"):
            continue
        if patch_templates(path):
            print(path.name)
            n += 1
    print(f"template patches: {n}")


if __name__ == "__main__":
    main()
