import re, sys, cairosvg, io
from pathlib import Path
from PIL import Image, ImageDraw
frag = Path(sys.argv[1]).read_text(encoding="utf-8")
gs = {m.group(1): m.group(0) for m in
      re.finditer(r'<g id="sk-([\w-]+)".*?</g>\s*$|<g id="sk-([\w-]+)".*?</g>(?=\n<g|\Z)',
                  frag, re.S | re.M)}
gs = {}
for line in frag.split("\n"):
    m = re.match(r'<g id="sk-([\w-]+)"', line)
    if m: gs[m.group(1)] = line
cw, ch = 210, 146
cols = 4
imgs = []
for n, g in sorted(gs.items()):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 104" '
           f'width="{cw}" height="{ch}">{g}</svg>')
    imgs.append((n, Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=svg.encode(), output_width=cw, output_height=ch)))))
rows = (len(imgs) + cols - 1) // cols
pad = 12
sh = Image.new("RGB", (cols*(cw+pad)+pad, rows*(ch+pad+16)+pad), "#EDE3CE")
d = ImageDraw.Draw(sh)
for i, (n, im) in enumerate(imgs):
    x = pad+(i % cols)*(cw+pad); y = pad+(i//cols)*(ch+pad+16)
    sh.paste(im, (x, y), im if im.mode == "RGBA" else None)
    d.text((x, y+ch+3), n, fill="#4a4436")
sh.save(sys.argv[2]); print(sys.argv[2], sh.size, len(imgs))
