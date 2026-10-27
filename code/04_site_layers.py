"""Step 4. Map layers for the page: Roman roads (Itiner-e, simplified) and the rivers around Whalley.

Writes work/layers.json: {"roads": [[[lat,lon],...],...], "wh_roads": [...], "wh_rivers": {name: [[[lat,lon],...]]}}.
Run: python3 code/04_site_layers.py
"""
import os, json, sqlite3, struct
import numpy as np
from pyproj import Transformer
from shapely.geometry import shape, LineString

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, ".."); HIST = os.path.abspath(os.path.join(ROOT, ".."))
ITINERE = os.path.join(HIST, "how-roman-is-your-road", "results", "itinere_gb_corrected.geojson")
GPKG = os.path.join(HIST, "osrivers", "Data", "oprvrs_gb.gpkg")
BOX = (53.76, 53.88, -2.56, -2.30)  # Whalley close-up: lat0, lat1, lon0, lon1
inv = Transformer.from_crs(27700, 4326, always_xy=True); fwd = Transformer.from_crs(4326, 27700, always_xy=True)


def decode(blob):
    flags = blob[3]; off = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]; wkb = blob[off:]
    bo = "<" if wkb[0] == 1 else ">"; typ = struct.unpack(bo + "I", wkb[1:5])[0]
    dim = 3 if (typ // 1000 in (1, 2) or typ & 0x80000000) else 2
    n = struct.unpack(bo + "I", wkb[5:9])[0]
    return np.frombuffer(wkb[9:9 + 8 * dim * n], dtype=bo + "f8").reshape(n, dim)[:, :2]


def lines(g):
    return [list(l.coords) for l in (g.geoms if g.geom_type.startswith("Multi") else [g])]


def main():
    roads, wh_roads = [], []
    for f in json.load(open(ITINERE))["features"]:
        g = shape(f["geometry"])
        for l in lines(g.simplify(0.003)):
            roads.append([[round(y, 3), round(x, 3)] for x, y in l])
        for l in lines(g):
            pts = [[round(y, 5), round(x, 5)] for x, y in l]
            if any(BOX[0] <= p[0] <= BOX[1] and BOX[2] <= p[1] <= BOX[3] for p in pts):
                wh_roads.append(pts)
    con = sqlite3.connect(GPKG)
    x0, y0 = fwd.transform(BOX[2], BOX[0]); x1, y1 = fwd.transform(BOX[3], BOX[1])
    q = """select w.watercourse_name, w.geometry from watercourse_link w join rtree_watercourse_link_geometry t on w.fid=t.id
           where t.minx<=? and t.maxx>=? and t.miny<=? and t.maxy>=? and w.watercourse_name in ('River Ribble','River Calder')"""
    riv = {}
    for nm, g in con.execute(q, (x1, x0, y1, y0)):
        xy = decode(g); lon, lat = inv.transform(xy[:, 0], xy[:, 1])
        ls = LineString(np.c_[lon, lat]).simplify(0.0002)
        riv.setdefault(nm, []).append([[round(b, 5), round(a, 5)] for a, b in ls.coords])
    out = dict(roads=roads, wh_roads=wh_roads, wh_rivers=riv, wh_box=BOX)
    json.dump(out, open(os.path.join(ROOT, "work", "layers.json"), "w"), separators=(",", ":"))
    print(len(roads), "road lines;", len(wh_roads), "near Whalley;", {k: len(v) for k, v in riv.items()}, "river pieces;",
          os.path.getsize(os.path.join(ROOT, "work", "layers.json")) // 1024, "KB")


if __name__ == "__main__":
    main()
