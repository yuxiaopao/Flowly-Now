"""Generate Desktop/icons from Frontend/public/logo.png"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def main() -> int:
    source = Path(sys.argv[1])
    png_out = Path(sys.argv[2])
    ico_out = Path(sys.argv[3])

    img = Image.open(source).convert('RGBA')
    img512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    png_out.parent.mkdir(parents=True, exist_ok=True)
    img512.save(png_out, format='PNG', optimize=True)

    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img512.save(ico_out, format='ICO', sizes=sizes)
    print(f'Generated {png_out.name} and {ico_out.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
