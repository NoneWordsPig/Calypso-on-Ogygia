"""Offline conversion of the legacy Godot sheets into production PNG frames.

The conversion deliberately happens at build time: transparent checkerboard
pixels are made fully transparent (including their RGB channels), and no
resampling is performed.
"""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "残稿" / "pictures"

def source(rel: str) -> Image.Image:
    p = LEGACY / rel
    if p.exists(): return Image.open(p).convert("RGBA")
    # Keep the tool usable from a clean checkout where the reference folder is absent.
    for rev in ("HEAD", "HEAD~1", "00316a9^"):
        try:
            b = subprocess.check_output(["git", "show", f"{rev}:{rel}"], cwd=ROOT)
            import io
            return Image.open(io.BytesIO(b)).convert("RGBA")
        except (subprocess.SubprocessError, FileNotFoundError): pass
    raise FileNotFoundError(rel)

def clean(im: Image.Image) -> Image.Image:
    px = list(im.getdata())
    # Legacy exports contain checkerboard RGB under alpha=0.
    im.putdata([(0, 0, 0, 0) if a == 0 else (r, g, b, a) for r,g,b,a in px])
    return im

def frames(im: Image.Image, count: int, split_equal=False) -> tuple[list[Image.Image], list[list[int]]]:
    a = im.getchannel("A"); w, h = im.size
    if split_equal:
        runs = [(i*w//count, (i+1)*w//count) for i in range(count)]
    else:
        active = [any(a.getpixel((x,y)) for y in range(h)) for x in range(w)]
        runs=[]; x=0
        while x<w:
            while x<w and not active[x]: x+=1
            s=x
            while x<w and active[x]: x+=1
            if x-s >= 4: runs.append((s,x))
    result=[]; rects=[]
    for s,e in runs[:count]:
        bbox = a.crop((s,0,e,h)).getbbox()
        if not bbox: continue
        bx,by,ex,ey=bbox; rects.append([s+bx,by,s+ex,ey]); result.append(im.crop((s+bx,by,s+ex,ey)))
    return result, rects

def process(out: Path) -> dict:
    specs = {"walk_down":"Calypso/front_walk.png", "walk_up":"Calypso/back_walk.png",
             "walk_left":"Calypso/left_walk.png", "walk_right":"Calypso/right_walk.png",
             "idle_down":"Calypso/front_rest.png", "idle_up":"Calypso/back_rest .png",
             "work":"Calypso/typing.png", "sleep":"Calypso/sleep.png"}
    manifest = {"cell_size": [164,408], "animations": {}}
    for name, rel in specs.items():
        im = clean(source(rel)); n = 4
        d = out / name; d.mkdir(parents=True, exist_ok=True)
        fs, rects = frames(im, n, name == "sleep")
        cw=max(f.width for f in fs); ch=max(f.height for f in fs)
        for i, f in enumerate(fs):
            canvas=Image.new("RGBA", (cw,ch)); canvas.alpha_composite(f, ((cw-f.width)//2, ch-f.height)); canvas.save(d / f"{i:02d}.png", optimize=True)
        manifest["animations"][name] = {"frames": [str((d/f'{i:02d}.png').relative_to(out)).replace('\\','/') for i in range(n)],
          "count": len(fs), "source_size": list(im.size), "source_rects": rects,
          "canvas_size": [cw,ch], "anchor": [cw//2, ch], "anchor_type":"feet-center"}
    manifest["animations"]["idle_left"] = {"alias":"walk_left","count":4,"anchor":[82,408],"anchor_type":"feet-center"}
    manifest["animations"]["idle_right"] = {"alias":"walk_right","count":4,"anchor":[82,408],"anchor_type":"feet-center"}
    for name, rel in (("computer_off","object/computer.png"),("computer_on","object/computer.png")):
        im=clean(source(rel)); a=im.getchannel("A"); active=[any(a.getpixel((x,y)) for y in range(im.height)) for x in range(im.width)]
        runs=[]; x=0
        while x<im.width:
            while x<im.width and not active[x]: x+=1
            s=x
            while x<im.width and active[x]: x+=1
            if x-s>=4: runs.append((s,x))
        idx=0 if name.endswith('off') else 1; s,e=runs[idx]; box=a.crop((s,0,e,im.height)).getbbox(); bx,by,ex,ey=box
        (out.parent/"objects").mkdir(parents=True,exist_ok=True); im.crop((s+bx,by,s+ex,ey)).save(out.parent/"objects"/f"{name}.png", optimize=True)
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path,default=ROOT/"assets"/"calypso"); args=ap.parse_args(); process(args.output)
