"""Step 6. Render ../header.png (1200x630 social card) with Playwright Chromium.

Fonts: FONT_DIR (env) may hold Fraunces, Source Serif 4 and IBM Plex Mono TTFs; otherwise system serif.
Run: python3 code/06_header.py
"""
import os, json, math
from playwright.sync_api import sync_playwright
from shapely.geometry import shape

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
S = json.load(open(os.path.join(ROOT, "work", "site.json"))); R = S["R"]; FD = os.environ.get("FONT_DIR", "")
land = shape(json.load(open(os.path.join(ROOT, "data", "coast_bi.geojson")))["features"][0]["geometry"])
K = math.cos(math.radians(54.5)); LON0, LON1, LAT0, LAT1 = -8.4, 2.0, 49.85, 58.7
H = 610; W = H * (LON1 - LON0) * K / (LAT1 - LAT0)
P = lambda lon, lat: ((lon - LON0) * K / ((LON1 - LON0) * K) * W, (LAT1 - lat) / (LAT1 - LAT0) * H)
paths = []
for poly in (land.geoms if land.geom_type == "MultiPolygon" else [land]):
    if poly.area < 0.02: continue
    pts = [P(x, y) for x, y in poly.simplify(0.01).exterior.coords]
    paths.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z")
by = {}
for c in S["c"]: by.setdefault(c["battle"], []).append(c)
spokes, dots = [], []
for b, cs in by.items():
    cen = R["battles"][b]["centroid"]; cx, cy = P(cen[1], cen[0])
    for c in cs:
        x, y = P(c["lon"], c["lat"])
        spokes.append(f"M{cx:.1f} {cy:.1f}L{x:.1f} {y:.1f}")
        f = c["fit"]; col = "#A8231C" if f == 1 else "#B07A12" if (f or 0) > 0 else "#8F8676"
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{col}" stroke="#F2ECDD" stroke-width="1.2"/>')
ff = ""
if FD:
    ff = "".join(f"@font-face{{font-family:'{n}';src:url('file://{FD}/{f}');font-weight:{w};}}" for n, f, w in [
        ("Fraunces", "Fraunces[SOFT,WONK,opsz,wght].ttf", "100 900"), ("Source Serif 4", "SourceSerif4[opsz,wght].ttf", "200 900"),
        ("IBM Plex Mono", "IBMPlexMono-Regular.ttf", "400"), ("IBM Plex Mono", "IBMPlexMono-Medium.ttf", "500")])
hd = R["headline"]
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{ff}
body{{margin:0;width:1200px;height:630px;background:#F2ECDD;color:#211B14;overflow:hidden;position:relative;font-family:'Source Serif 4',Georgia,serif}}
.k{{position:absolute;left:66px;top:70px;font:500 15px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#6E6455;display:flex;gap:12px;align-items:center}}
.k b{{background:#A8231C;color:#fff;padding:7px 9px;font-weight:500}}
h1{{position:absolute;left:62px;top:112px;margin:0;font:900 116px/.86 Fraunces,Georgia,serif;letter-spacing:-.02em;font-variation-settings:"SOFT" 50}}
h1 em{{font-style:normal;color:#A8231C;display:block}}
p{{position:absolute;left:66px;top:400px;width:560px;margin:0;font-size:26px;line-height:1.36;color:#3A3128}}
.f{{position:absolute;left:66px;bottom:40px;font:400 14px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#857B6B}}
svg{{position:absolute;right:30px;top:10px}}
</style></head><body>
<div class="k"><b>Data study</b><span>Lost battlefields of early Britain</span></div>
<h1>Where was<em>the battle?</em></h1>
<p>{R['n_candidates']} proposed sites for {R['n_battles']} battles. Camlann's theories are {round(hd['widest']['km'])} km apart; Whalley's fit inside {hd['narrowest']['km']:.1f}&nbsp;km.</p>
<div class="f">Dr Tristan Hotham · Independent researcher</div>
<svg width="{W:.0f}" height="{H}" viewBox="0 0 {W:.0f} {H}"><path d="{' '.join(paths)}" fill="#E4DAC3" stroke="#B9AB8C" stroke-width="1"/>
<path d="{' '.join(spokes)}" stroke="#211B14" stroke-width="1" stroke-opacity=".45" fill="none"/>{''.join(dots)}</svg>
</body></html>"""
os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
tmp = os.path.join(ROOT, "work", "header.html"); open(tmp, "w").write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.goto("file://" + os.path.abspath(tmp)); pg.wait_for_timeout(500)
    pg.screenshot(path=os.path.join(ROOT, "header.png")); b.close()
print("header.png written")
