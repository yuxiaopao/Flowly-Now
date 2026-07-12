from pathlib import Path

d = Path(__file__).resolve().parents[1] / "src" / "components" / "workflow" / "nodes"
for p in d.glob("*.vue"):
    t = p.read_text(encoding="utf-8")
    n = (
        t.replace(':is=\\"nodeIcon\\"', ':is="nodeIcon"')
        .replace(':size=\\"18\\"', ':size="18"')
        .replace(':style=\\"{ color: nodeColor }\\"', ':style="{ color: nodeColor }"')
    )
    if n != t:
        p.write_text(n, encoding="utf-8")
        print(p.name)
