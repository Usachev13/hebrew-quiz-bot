import re, sys, cairosvg, io
from pathlib import Path
from PIL import Image, ImageDraw
frag = Path(sys.argv[1]).read_text(encoding="utf-8")
raw = {m.group(1): m.group(0) for m in re.finditer(r'<g id="i-([\w-]+)">(.*?)</g>', frag, re.S)}
def sheet(px, cell, out, cols=6, sw=1.5):
    imgs=[]
    for n,g in sorted(raw.items()):
        svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
             f' stroke="#B0703C" stroke-width="{sw}" stroke-linecap="round"'
             f' stroke-linejoin="round">{g}</svg>')
        imgs.append((n, Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(),
            output_width=px, output_height=px, background_color="#F7F1E6")))))
    rows=(len(imgs)+cols-1)//cols; pad=14
    sh=Image.new("RGB",(cols*(cell+pad)+pad, rows*(cell+pad+16)+pad),"#EDE3CE")
    d=ImageDraw.Draw(sh)
    for i,(n,im) in enumerate(imgs):
        x=pad+(i%cols)*(cell+pad); y=pad+(i//cols)*(cell+pad+16)
        sh.paste(im,(x+(cell-px)//2,y+(cell-px)//2)); d.text((x,y+cell+3),n,fill="#4a4436")
    sh.save(out); print(out)
sheet(88,88,"ic2_big.png"); sheet(22,60,"ic2_real.png")
