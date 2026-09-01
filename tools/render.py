# -*- coding: utf-8 -*-
"""Рендерит спрайт в контактный лист PNG, чтобы рисунки можно было увидеть."""
import re, sys, cairosvg, io
from pathlib import Path
from PIL import Image

def groups(html, prefix):
    out = {}
    for m in re.finditer(r'<g id="%s([\w-]+)"(.*?)</g>' % prefix, html, re.S):
        out[m.group(1)] = m.group(0)
    return out

def sheet(items, vb, cols, cell, out, stroke_w, px=None):
    px = px or cell
    imgs = []
    for name, g in items:
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
               f'width="{px}" height="{px}" fill="none" stroke="#1a2740" '
               f'stroke-width="{stroke_w}" stroke-linecap="round" '
               f'stroke-linejoin="round">{g}</svg>')
        png = cairosvg.svg2png(bytestring=svg.encode(), output_width=px,
                               output_height=px, background_color="#FAF5EA")
        imgs.append((name, Image.open(io.BytesIO(png))))
    rows = (len(imgs) + cols - 1) // cols
    pad = 14
    W, H = cols * (cell + pad) + pad, rows * (cell + pad + 16) + pad
    sh = Image.new("RGB", (W, H), "#EDE3CE")
    from PIL import ImageDraw
    d = ImageDraw.Draw(sh)
    for i, (name, im) in enumerate(imgs):
        x = pad + (i % cols) * (cell + pad)
        y = pad + (i // cols) * (cell + pad + 16)
        sh.paste(im, (x, y), im if im.mode == "RGBA" else None)
        d.text((x, y + cell + 3), name, fill="#4a4436")
    sh.save(out)
    print(out, sh.size, len(imgs), "шт")

html = Path(sys.argv[1]).read_text(encoding="utf-8")
sk = groups(html, "sk-")
sheet(sorted(sk.items()), "0 0 100 100", 5, 130, "/tmp/rt/sketches.png", 2.6)
ic = groups(html, "i-")
sheet(sorted(ic.items()), "0 0 24 24", 6, 96, "/tmp/rt/icons.png", 2)
sheet(sorted(ic.items()), "0 0 24 24", 6, 44, "/tmp/rt/icons_small.png", 2)
