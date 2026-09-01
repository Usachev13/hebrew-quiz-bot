import re, sys, cairosvg, io
from pathlib import Path
from PIL import Image, ImageDraw
frag = Path(sys.argv[1]).read_text(encoding="utf-8")
dm = re.search(r'<clipPath.*?</clipPath>', frag, re.S)
defs = dm.group(0) if dm else ""
gs = {}
for m in re.finditer(r'(<g id="sk-([\w-]+)".*?)(?=<g id="sk-|$)', frag, re.S):
    gs[m.group(2)] = m.group(1).strip()
cols, cell = 5, int(sys.argv[3]) if len(sys.argv) > 3 else 140
imgs=[]
for n,g in sorted(gs.items()):
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
         f'fill="none" stroke="#B0703C"><defs>{defs}</defs>{g}</svg>')
    imgs.append((n, Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(),
        output_width=cell, output_height=cell, background_color="#F7F1E6")))))
rows=(len(imgs)+cols-1)//cols; pad=14
sh=Image.new("RGB",(cols*(cell+pad)+pad, rows*(cell+pad+16)+pad),"#EDE3CE")
d=ImageDraw.Draw(sh)
for i,(n,im) in enumerate(imgs):
    x=pad+(i%cols)*(cell+pad); y=pad+(i//cols)*(cell+pad+16)
    sh.paste(im,(x,y)); d.text((x,y+cell+3),n,fill="#4a4436")
sh.save(sys.argv[2]); print(sys.argv[2], sh.size, len(imgs))
