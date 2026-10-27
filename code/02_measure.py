"""Step 2. Measure the ground at every candidate.

For each candidate point in data/candidates.csv:
  * elev_m: ground height (AWS Terrain Tiles, zoom 10, about 90 m cells; see dem.py);
  * pct_2km: share of the ground within 2 km that is lower than the point (1 = the highest spot around);
  * hill_1km_pct: the highest ground within 1 km of the point, ranked against all ground within 3 km
    (a village at the foot of a hill still scores high: the hill is there);
  * relief_1km_m, relief_3km_m: highest minus lowest ground within 1 km and 3 km;
  * coast_km: distance to the sea (Natural Earth 1:10m coastline of Great Britain, Ireland and Man);
  * road_km: distance to the nearest Roman road in Itiner-e (datum-corrected; Itiner-e has no roads
    north of about 56 N in Scotland, so this is blank there);
  * river_km: distance to the nearest named river or stream (OS Open Rivers, inland or tidal);
  * water_km: distance to the nearest named lake, loch or pool (OS Open Names, Inland Water);
  * fort_km, fort_name: the nearest hillfort in the Atlas of Hillforts;
  * humber_km, liddel_km: distance to the River Humber and to Liddel Water (OS Open Rivers), named in the texts.
Also writes data/coast_bi.geojson (simplified coastline used for the maps).

NE10 (env) points to Natural Earth ne_10m_admin_0_countries.geojson for the first run only.
Run: python3 code/02_measure.py
"""
import os, json, sqlite3, struct
import numpy as np, pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import shape, mapping, Point, LineString, MultiLineString
import warnings; warnings.filterwarnings("ignore", category=DeprecationWarning)
from shapely.ops import unary_union, transform as stransform
from shapely.strtree import STRtree
from dem import DEM

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, ".."); HIST = os.path.abspath(os.path.join(ROOT, ".."))
NE10 = os.environ.get("NE10", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/sw/ne/geojson/ne_10m_admin_0_countries.geojson")
ITINERE = os.path.join(HIST, "how-roman-is-your-road", "results", "itinere_gb_corrected.geojson")
GPKG = os.path.join(HIST, "osrivers", "Data", "oprvrs_gb.gpkg")
OSN = os.path.join(HIST, "osnames_gb.tsv")
ATLAS = os.path.join(HIST, "within-sight", "data", "forts_visibility.csv")
COAST = os.path.join(ROOT, "data", "coast_bi.geojson")

fwd = Transformer.from_crs(4326, 27700, always_xy=True)
to_bng = lambda lon, lat: fwd.transform(lon, lat)


def coast_geom():
    if not os.path.exists(COAST):
        ne = json.load(open(NE10))
        polys = [shape(f["geometry"]) for f in ne["features"] if f["properties"]["ADMIN"] in ("United Kingdom", "Ireland", "Isle of Man")]
        land = unary_union(polys).simplify(0.002, preserve_topology=True)
        land = land.intersection(shape({"type": "Polygon", "coordinates": [[[-11, 49.7], [2.2, 49.7], [2.2, 61], [-11, 61], [-11, 49.7]]]}))
        json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"source": "Natural Earth 1:10m admin 0 (public domain), simplified"},
                   "geometry": json.loads(json.dumps(mapping(land)))}]}, open(COAST, "w"), separators=(",", ":"))
    g = shape(json.load(open(COAST))["features"][0]["geometry"])
    return g


NAMED = {"humber_km": "River Humber", "liddel_km": "Liddel Water"}  # rivers named in the texts


def decode(blob):
    flags = blob[3]; off = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]; wkb = blob[off:]
    bo = "<" if wkb[0] == 1 else ">"; typ = struct.unpack(bo + "I", wkb[1:5])[0]
    dim = 3 if (typ // 1000 in (1, 2) or typ & 0x80000000) else 2
    n = struct.unpack(bo + "I", wkb[5:9])[0]
    return np.frombuffer(wkb[9:9 + 8 * dim * n], dtype=bo + "f8").reshape(n, dim)[:, :2]


def river_dist(con, x, y, r=8000, name=None):
    q = """select w.watercourse_name, w.geometry from watercourse_link w join rtree_watercourse_link_geometry t on w.fid=t.id
           where t.minx<=? and t.maxx>=? and t.miny<=? and t.maxy>=? and w.watercourse_name is not null and w.form in ('inlandRiver','tidalRiver')"""
    best = (None, None)
    for nm, g in con.execute(q, (x + r, x - r, y + r, y - r)):
        if name and nm != name: continue
        d = LineString(decode(g)).distance(Point(x, y)) if len(decode(g)) > 1 else Point(*decode(g)[0]).distance(Point(x, y))
        if best[0] is None or d < best[0]: best = (d, nm)
    return best


def disc(lat, lon, r_m, step=90.0):
    """Points on a square grid inside a circle of radius r_m around (lat, lon)."""
    k = np.arange(-r_m, r_m + 1, step); X, Y = np.meshgrid(k, k); m = X ** 2 + Y ** 2 <= r_m ** 2
    dx, dy = X[m], Y[m]
    return lat + dy / 111320.0, lon + dx / (111320.0 * np.cos(np.radians(lat))), np.hypot(dx, dy)


def main():
    c = pd.read_csv(os.path.join(ROOT, "data", "candidates.csv"))
    dem = DEM()
    land = coast_geom(); coast_line = stransform(lambda x, y, z=None: fwd.transform(x, y), land.boundary)
    roads = json.load(open(ITINERE))["features"]
    rl, rn = [], []
    for f in roads:
        g = shape(f["geometry"]); rl.append(stransform(lambda x, y, z=None: fwd.transform(x, y), g))
        rn.append(f["properties"].get("itin") or f["properties"].get("name") or "")
    rtree = STRtree(rl)
    con = sqlite3.connect(GPKG)
    osn = pd.read_csv(OSN, sep="\t", usecols=["name1", "local_type", "x", "y"])
    lakes = osn[osn.local_type == "Inland Water"].reset_index(drop=True); ltree = cKDTree(lakes[["x", "y"]].values)
    atlas = pd.read_csv(ATLAS, usecols=["name", "lat", "lon"])
    ax, ay = to_bng(atlas.lon.values, atlas.lat.values); ftree = cKDTree(np.c_[ax, ay])
    named = {nm: [decode(g) for (g,) in con.execute("select geometry from watercourse_link where watercourse_name=?", (nm,))] for nm in NAMED.values()}
    rows = []
    for _, r in c.iterrows():
        x, y = to_bng(r.lon, r.lat)
        e = float(dem.elev(np.array([r.lat]), np.array([r.lon]))[0])
        la, lo, d = disc(r.lat, r.lon, 3000); z = dem.elev(la, lo)
        z2 = z[d <= 2000]; z1 = z[d <= 1000]
        top1 = z1.max()
        row = dict(elev_m=round(e, 1), pct_2km=round(float((z2 < e).mean()), 3),
                   hill_1km_pct=round(float((z < top1).mean()), 3), top_1km_m=round(float(top1), 1),
                   relief_1km_m=round(float(z1.max() - z1.min()), 1), relief_3km_m=round(float(z.max() - z.min()), 1))
        row["coast_km"] = round(coast_line.distance(Point(x, y)) / 1000, 2)
        if r.lat < 56.05:
            i = rtree.nearest(Point(x, y)); row["road_km"] = round(rl[i].distance(Point(x, y)) / 1000, 2); row["road_name"] = rn[i]
        else:
            row["road_km"] = None; row["road_name"] = None
        dr, nm = river_dist(con, x, y)
        row["river_km"] = round(dr / 1000, 2) if dr is not None else None; row["river_name"] = nm
        dw, iw = ltree.query([x, y]); row["water_km"] = round(dw / 1000, 2); row["water_name"] = lakes.name1[iw]
        df, jf = ftree.query([x, y]); row["fort_km"] = round(df / 1000, 2); row["fort_name"] = atlas.name[jf]
        for key, nm in NAMED.items():
            row[key] = round(min(LineString(g).distance(Point(x, y)) for g in named[nm]) / 1000, 2)
        rows.append(row)
    m = pd.concat([c, pd.DataFrame(rows)], axis=1)
    m.to_csv(os.path.join(ROOT, "work", "measured.csv"), index=False)
    print(m[["battle", "candidate", "elev_m", "pct_2km", "hill_1km_pct", "relief_3km_m", "coast_km", "road_km", "river_km", "water_km", "fort_km"]].to_string())


if __name__ == "__main__":
    main()
