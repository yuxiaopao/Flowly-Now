from __future__ import annotations

import re
from pathlib import Path

NODES_DIR = Path(__file__).resolve().parents[1] / "src" / "components" / "workflow" / "nodes"
BADGE_IMPORT = "import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'\n"

HEADER_BADGE = re.compile(
    r"<div class=\"node-header\">\s*<div\s+class=\"node-type-badge\"[\s\S]*?</div>\s*</div>",
    re.M,
)


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "NODE_TYPE" not in text:
        return False
    original = text

    if HEADER_BADGE.search(text) and "NodeTypeBadge" not in text.split("<template>")[1].split("</template>")[0]:
        text = HEADER_BADGE.sub(
            '<div class="node-header">\n      <NodeTypeBadge :node-type="NODE_TYPE" compact />\n    </div>',
            text,
            count=1,
        )

    if BADGE_IMPORT.strip() not in text and "NodeTypeBadge" in text:
        m = re.search(r"import \{ useNodePresentation \}", text)
        if m:
            text = text[: m.start()] + BADGE_IMPORT + text[m.start() :]

    text = re.sub(
        r"\{\{ data\.label \|\| '[^']+' \}\}",
        "{{ data.label || nodeLabel }}",
        text,
    )

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = 0
    for path in sorted(NODES_DIR.glob("*.vue")):
        if patch(path):
            print(path.name)
            n += 1
    print(f"fixed {n}")


if __name__ == "__main__":
    main()
