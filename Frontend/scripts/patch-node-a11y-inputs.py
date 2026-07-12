from __future__ import annotations

import re
from pathlib import Path

NODES_DIR = Path(__file__).resolve().parents[1] / "src" / "components" / "workflow" / "nodes"
SKIP = {"NodeTypeBadge.vue", "ComfyMultimodalNodeShell.vue", "StartNode.vue", "EndNode.vue", "InputNode.vue", "OutputNode.vue"}


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "node-name-input" not in text or 'name="node-label"' in text:
        return False
    if "id:" not in text and "props.id" not in text:
        return False

    pattern = re.compile(
        r"(<input\s+)(?!.*\bname=\"node-label\")(?=[\s\S]*?class=\"node-name-input\")",
        re.M,
    )
    new_text, n = pattern.subn(
        r'\1:id="id ? `node-label-${id}` : undefined"\n        name="node-label"\n        ',
        text,
        count=1,
    )
    if n == 0:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    count = 0
    for path in sorted(NODES_DIR.glob("*.vue")):
        if path.name in SKIP:
            continue
        if patch(path):
            print(path.name)
            count += 1
    print(f"patched {count}")


if __name__ == "__main__":
    main()
