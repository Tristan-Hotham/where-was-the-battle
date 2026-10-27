"""Step 1. The candidate sites, where each idea comes from, and where each point comes from.

Every candidate below is a place that a named source proposes (or reports as proposed) for an
unlocated or disputed early battle in Britain. For each I record:
  * who proposed it, as the source states it, and the kind of case made (basis);
  * the source page (URL) that names it;
  * how the point was placed (geo): never guessed, always one of
      os:NAME|COUNTY       OS Open Names entry with that exact name (and county, if needed;
                           @LAT,LON picks the nearest of several same-named entries)
      atlas:NAME           Atlas of Hillforts record (via ../within-sight/data/forts_visibility.csv)
      pleiades:ID          Pleiades place, representative point
      grid:REF             OS grid reference stated in the source
      coord:LAT,LON        coordinates stated in the source page
      river:NAME@LAT,LON   OS Open Rivers: the named watercourse run nearest the hint point;
                           the point is the vertex nearest the run's length-weighted centre
  * precision: 'site' (a named hill, fort, camp or field), 'village' (a settlement point standing for
    a place), or 'area' (a valley, river or district standing for a vaguer proposal).

Output: data/candidates.csv (one row per candidate with lat/lon and provenance).
Run: python3 code/01_candidates.py
"""
import os, re, sqlite3, struct
import numpy as np, pandas as pd
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
HIST = os.path.abspath(os.path.join(ROOT, ".."))
OSN = os.path.join(HIST, "osnames_gb.tsv")
ATLAS = os.path.join(HIST, "within-sight", "data", "forts_visibility.csv")
PLEI = "/mnt/user-data/uploads/Downloads/pleiades-places-latest.csv.gz"
GPKG = os.path.join(HIST, "osrivers", "Data", "oprvrs_gb.gpkg")
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True); os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)

W = "https://en.wikipedia.org/wiki/"
VCH_WHALLEY = "https://www.british-history.ac.uk/vch/lancs/vol6/pp349-360"
VCH_BILLINGTON = "https://www.british-history.ac.uk/node/44977"
TMA_LOE = "https://www.themodernantiquarian.com/site/3015/loe-hill"
COLLECTOR = "https://www.thecollector.com/where-was-battle-camlann-king-athur/"
RCAHMW = "https://historicplacenames.rcahmw.gov.uk/placenames/headname/d93ab688-ddcf-4dd1-a557-515c10bd4e3c"
SCARF = "https://scarf.scot/regional/sesarf/8-early-medieval/8-6-conflict/8-6-2-textual-sources-relating-to-battles/"
LYDIARD = "https://www.britishlistedbuildings.co.uk/101198420-lydiard-park-west-swindon"

# battle, candidate, proposer (as the source reports it), basis, source url, geo, precision
C = [
 # ---------------- Whalley, 798 ----------------
 ("whalley", "Whalley village", "Anglo-Saxon Chronicle, 798: a great battle 'at Whalley in Northumbria'", "chronicle", VCH_WHALLEY, "os:Whalley|Lancashire", "village"),
 ("whalley", "Billington", "Symeon of Durham, Historia Regum: 'Billingahoh, near Walalege'", "chronicle", VCH_BILLINGTON, "os:Billington|Lancashire", "village"),
 ("whalley", "Billington Moor", "Wikipedia: Eardwulf 'fought a battle at Billington Moor'", "chronicle", W + "Billington,_Lancashire", "os:Billington Moor|Lancashire", "site"),
 ("whalley", "Whalley Nab (Billingahoth hill)", "Victoria County History: the hill 'Billingahoth' of 798 is the summit 'now contracted simply to Whalley Nab'", "place-name", VCH_BILLINGTON, "os:Nab Wood|Lancashire@53.8235,-2.4061", "site"),
 ("whalley", "Loe Hill, Winckley lowes", "Local folklore reported by Rev. J. R. Luck (1896): Wada's followers buried in the mound", "local tradition", TMA_LOE, "grid:SD708373", "site"),
 # ---------------- Badon ----------------
 ("badon", "Bath", "Geoffrey of Monmouth; Tim and Annette Burkitt", "legend and place-name", W + "Battle_of_Badon", "os:Bath|Bath and North East Somerset", "village"),
 ("badon", "Bathampton Down", "Traditional, 'the hills around Bath'", "tradition", W + "Battle_of_Badon", "os:Bathampton Down|Bath and North East Somerset|Spot Height", "site"),
 ("badon", "Little Solsbury Hill", "Listed as a possible location (Mick Baker, the case for Bath)", "tradition", W + "Solsbury_Hill", "atlas:Little Solsbury Hill Camp", "site"),
 ("badon", "Liddington Castle", "Susan Hirst, Geoffrey Ashe, Michael Wood (Badbury, OE Baddan byrig)", "place-name and strategy", W + "Battle_of_Badon", "atlas:Liddington Castle, Wiltshire", "site"),
 ("badon", "Badbury Rings", "Edwin Guest (via Hutchins); David Cooper", "place-name", W + "Badbury_Rings", "atlas:Badbury Rings, Dorset", "site"),
 ("badon", "Ringsbury Camp, Braydon", "Andrew Breeze (2020), reading Bradonici for Badonici", "place-name", W + "Battle_of_Badon", "atlas:Ringsbury Camp", "site"),
 ("badon", "Bowden Hill, Linlithgow", "William Forbes Skene", "place-name", W + "Battle_of_Badon", "atlas:Bowden Hill, West Lothian", "site"),
 ("badon", "Baumber, Lincolnshire", "Thomas Green (Domesday Badeburg)", "place-name and archaeology", W + "Battle_of_Badon", "os:Baumber|Lincolnshire", "village"),
 ("badon", "Arbury Hill, Northamptonshire", "Bernard Mees", "place-name", W + "Battle_of_Badon", "atlas:Arbury Hill, Badby", "site"),
 ("badon", "Mynydd Baedan, Maesteg", "Local lore", "local tradition", W + "Battle_of_Badon", "os:Mynydd Baedan", "site"),
 ("badon", "Bowden Hill, Wiltshire", "Local lore", "local tradition", W + "Battle_of_Badon", "os:Bowden Hill|Wiltshire", "village"),
 # ---------------- Brunanburh, 937 ----------------
 ("brunanburh", "Bromborough", "Charters; Paul Cavill; Michael Livingston; Wirral Archaeology", "place-name and archaeology", W + "Battle_of_Brunanburh", "os:Bromborough", "village"),
 ("brunanburh", "Brackenwood, Bebington", "Proposed as a site 'around' Bromborough", "place-name", W + "Battle_of_Brunanburh", "os:Brackenwood Park", "site"),
 ("brunanburh", "Brimstage", "Landscape survey placing Bruna's burh", "landscape survey", W + "Battle_of_Brunanburh", "os:Brimstage", "village"),
 ("brunanburh", "Barnsdale", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Barnsdale|", "area"),
 ("brunanburh", "Brinsworth", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Brinsworth", "village"),
 ("brunanburh", "Leighton Bromswold", "Listed proposal (Bromswold)", "listed", W + "Battle_of_Brunanburh", "os:Leighton Bromswold", "village"),
 ("brunanburh", "Burnley", "Local historians, later Thomas Newbigging", "place-name", W + "Battle_of_Brunanburh", "os:Burnley|Lancashire", "village"),
 ("brunanburh", "Burnswark", "George Neilson (1899); Charles Oman; Kevin Halloran", "place-name and topography", W + "Battle_of_Brunanburh", "os:Burnswark Hill", "site"),
 ("brunanburh", "Lanchester", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Lanchester|County Durham", "village"),
 ("brunanburh", "Hunwick", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Hunwick", "village"),
 ("brunanburh", "Londesborough", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Londesborough", "village"),
 ("brunanburh", "Nunburnholme", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Nunburnholme", "village"),
 ("brunanburh", "Heysham", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Heysham", "village"),
 ("brunanburh", "Barton-upon-Humber", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Barton-upon-Humber", "village"),
 ("brunanburh", "Little Weighton", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Little Weighton", "village"),
 ("brunanburh", "Bourn", "Listed proposal", "listed", W + "Battle_of_Brunanburh", "os:Bourn|Cambridgeshire", "village"),
 # ---------------- Mons Graupius, AD 83 or 84 ----------------
 ("graupius", "Bennachie", "Modern focus on the north-east: 'at the foot of Bennachie'", "archaeology (marching camps)", W + "Battle_of_Mons_Graupius", "os:Bennachie", "site"),
 ("graupius", "Durno marching camp", "The large marching camp at Logie Durno, north of Bennachie", "archaeology (marching camps)", W + "Battle_of_Mons_Graupius", "os:Durno", "village"),
 ("graupius", "Kempstone Hill", "Roy, Watt, Hogan and others", "topography and Elsick Mounth", W + "Battle_of_Mons_Graupius", "os:Kempstone Hill", "site"),
 ("graupius", "Hill of Megray", "Roy, Watt, Hogan and others", "topography and Elsick Mounth", W + "Battle_of_Mons_Graupius", "os:Hill of Megray", "site"),
 ("graupius", "Raedykes camp", "Gabriel Jacques Surenne and other scholars", "archaeology (marching camp)", W + "Raedykes", "grid:NO842902", "site"),
 ("graupius", "Dalginross", "19th-century Perthshire identifications", "antiquarian", W + "Battle_of_Mons_Graupius", "os:Dalginross", "village"),
 ("graupius", "Blairgowrie", "19th-century Perthshire identifications", "antiquarian", W + "Battle_of_Mons_Graupius", "os:Blairgowrie", "village"),
 # ---------------- Boudica's last battle, AD 60 or 61 ----------------
 ("boudica", "Mancetter", "Graham Webster", "Roman road and military reasoning", W + "Boudican_revolt", "os:Mancetter", "village"),
 ("boudica", "High Cross", "Kevin K. Carroll (Watling Street meets the Fosse Way)", "Roman road and military reasoning", W + "Boudican_revolt", "os:High Cross|Leicestershire", "village"),
 ("boudica", "Virginia Water", "Fuentes (between Callow Hill and Knowle Hill, off the Devil's Highway)", "Roman road and military reasoning", W + "Boudican_revolt", "os:Virginia Water|Surrey|Village", "village"),
 ("boudica", "The Rampart, Messing", "Local legend", "local tradition", W + "Boudican_revolt", "os:Messing", "village"),
 ("boudica", "Ambresbury Banks", "Local legend", "local tradition", W + "Boudican_revolt", "atlas:Ambresbury Banks", "site"),
 ("boudica", "Kings Norton", "Roman artefacts near Metchley Camp", "archaeology", W + "Boudican_revolt", "os:King's Norton||Suburban Area", "village"),
 ("boudica", "Cuttle Mill, Paulerspury", "Akeman Street as a route from the south-west", "Roman road", W + "Boudican_revolt", "os:Paulerspury", "village"),
 ("boudica", "Church Stowe", "Akeman Street as a route from the south-west", "Roman road", W + "Boudican_revolt", "os:Church Stowe", "village"),
 ("boudica", "Arbury Banks, Hertfordshire", "2009 suggestion: Iceni returning along the Icknield Way", "route reasoning", W + "Boudican_revolt", "atlas:Arbury Banks, Hertfordshire", "site"),
 ("boudica", "King's Cross (Battle Bridge)", "Old tradition, rejected by modern historians", "local tradition", W + "Boudican_revolt", "os:King's Cross", "village"),
 ("boudica", "St Asaph (Bryn Paulin)", "Thomas Pennant; Richard Williams Morgan", "place-name and legend", W + "Boudican_revolt", "os:St Asaph", "village"),
 ("boudica", "Trelawnyd", "Morien", "legend", W + "Boudican_revolt", "os:Trelawnyd", "village"),
 # ---------------- Camlann ----------------
 ("camlann", "Castlesteads (Camboglanna)", "Andrew Breeze (2020), after R. G. Collingwood", "place-name", W + "Battle_of_Camlann", "pleiades:89133", "site"),
 ("camlann", "Camelford, River Camel", "Geoffrey of Monmouth, Wace, Layamon", "legend", W + "Battle_of_Camlann", "os:Camelford", "village"),
 ("camlann", "Slaughterbridge", "Legendary and folk associations", "local tradition", W + "Slaughterbridge", "os:Slaughterbridge", "village"),
 ("camlann", "Salisbury", "French romances and Malory ('Battle of Salisbury')", "legend", W + "Battle_of_Camlann", "os:Salisbury|Wiltshire", "village"),
 ("camlann", "Camlan, near Mallwyd", "Patrick Sims-Williams, on Llywelyn Fardd's Camlan", "place-name", COLLECTOR, "grid:SH8511512041", "site", RCAHMW),
 ("camlann", "Afon Gamlan", "Patrick Sims-Williams (also named)", "place-name", COLLECTOR, "river:Afon Gamlan@52.80,-3.90", "area"),
 ("camlann", "Dunnichen, Angus", "Earlier local tradition (Headrick, Second Statistical Account)", "local tradition", W + "Battle_of_Dun_Nechtain", "os:Dunnichen", "village"),
 # ---------------- Catraeth, about 600 ----------------
 ("catraeth", "Catterick", "Thomas Stephens; Ifor Williams; most modern scholars", "place-name", W + "Battle_of_Catraeth", "coord:54.377222,-1.63", "village"),
 # ---------------- Arfderydd, 573 ----------------
 ("arfderydd", "Arthuret, near Longtown", "W. F. Skene, from John of Fordun", "place-name", W + "Battle_of_Arfderydd", "coord:55.016667,-2.916667", "village"),
 # ---------------- Degsastan, about 603 ----------------
 ("degsastan", "Dawston, Liddesdale", "Possible site (Dawstane); 'a likely possibility' (ScARF)", "place-name", SCARF, "os:Liddesdale", "area"),
 ("degsastan", "Western Dawyck, Tweeddale", "Andrew Breeze (2020)", "place-name", SCARF, "os:Dawyck Mill Pool", "area"),
 # ---------------- Maserfield, 642 ----------------
 ("maserfield", "Oswestry", "Traditional ('Oswald's Tree')", "place-name", W + "Battle_of_Maserfield", "os:Oswestry", "village"),
 ("maserfield", "Forden", "Andrew Breeze (2020), from Canu Heledd", "place-name", W + "Battle_of_Maserfield", "os:Forden", "village"),
 # ---------------- Winwaed, 655 ----------------
 ("winwaed", "Cock Beck, Leeds", "Common identification", "river name", W + "Battle_of_the_Winwaed", "river:Cock Beck@53.84,-1.42", "area"),
 ("winwaed", "River Went", "Andrew Breeze (2004)", "river name", W + "Battle_of_the_Winwaed", "river:River Went@53.63,-1.20", "area"),
 ("winwaed", "Winwick, Cheshire", "'Wilder speculation'", "place-name", W + "Battle_of_the_Winwaed", "os:Winwick|Warrington", "village"),
 ("winwaed", "Oswestry", "'Wilder speculation'", "place-name", W + "Battle_of_the_Winwaed", "os:Oswestry", "village"),
 # ---------------- Nechtansmere / Dun Nechtain, 685 ----------------
 ("nechtansmere", "Dunnichen", "George Chalmers (early 19th century)", "place-name", W + "Battle_of_Dun_Nechtain", "coord:56.628437,-2.805156", "village"),
 ("nechtansmere", "Dunnichen Moss", "George Chalmers: a drained lake east of the village", "place-name and topography", W + "Battle_of_Dun_Nechtain", "grid:NO516489", "site"),
 ("nechtansmere", "Rescobie Loch", "More recent suggestions: the valley north of Dunnichen Hill", "topography", W + "Battle_of_Dun_Nechtain", "grid:NO512518", "site"),
 ("nechtansmere", "Restenneth Loch", "More recent suggestions: the valley north of Dunnichen Hill", "topography", W + "Battle_of_Dun_Nechtain", "grid:NO483518", "site"),
 ("nechtansmere", "Dunachton, Loch Insh", "Alex Woolf (2006); James Fraser", "place-name and topography", W + "Battle_of_Dun_Nechtain", "grid:NH820047", "site"),
 # ---------------- Assandun, 1016 ----------------
 ("assandun", "Ashingdon", "Long supposed", "place-name", W + "Battle_of_Assandun", "os:Ashingdon", "village"),
 ("assandun", "Ashdon", "Alternative identification", "place-name", W + "Battle_of_Assandun", "os:Ashdon", "village"),
 ("assandun", "Hadstock", "Skeletons found in the 'Red Field'; early 11th-century church", "archaeology", W + "Battle_of_Assandun", "os:Hadstock", "village"),
 # ---------------- Edington / Ethandun, 878 ----------------
 ("edington", "Edington, Wiltshire", "Accepted by most present-day historians", "place-name", W + "Battle_of_Edington", "coord:51.263889,-2.142778", "site"),
 ("edington", "Edington, Polden Hills, Somerset", "Charles Whistler and Albany Major (1913); Illtyd Trethowan (1939)", "place-name and military reasoning", W + "Battle_of_Edington", "os:Edington|Somerset", "village"),
 ("edington", "Abingdon", "Polydore Vergil (a misreading)", "misreading", W + "Battle_of_Edington", "os:Abingdon-on-Thames", "village"),
 # ---------------- Ellendun, 825 ----------------
 ("ellendun", "Wroughton", "Charles Oman", "boundaries and geography", W + "Battle_of_Ellendun", "os:Wroughton", "village"),
 ("ellendun", "Lydiard Park", "T. Spicer", "unstated", W + "Battle_of_Ellendun", "coord:51.561413,-1.851614", "site", LYDIARD),
 ("ellendun", "Wilton", "William Camden (1610)", "antiquarian", W + "Battle_of_Ellendun", "os:Wilton|Wiltshire|Town", "village"),
 # ---------------- Tettenhall / Wednesfield, 910 ----------------
 ("tettenhall", "Tettenhall", "Aethelweard", "chronicle", W + "Battle_of_Tettenhall", "os:Tettenhall", "village"),
 ("tettenhall", "Wednesfield", "Alternative name of the battle (Wodnesfeld)", "chronicle", W + "Battle_of_Tettenhall", "os:Wednesfield", "village"),
 # ---------------- Hatfield Chase, 633 ----------------
 ("hatfield", "Hatfield Chase", "Traditional: marshy ground north-east of Doncaster", "place-name", W + "Battle_of_Hatfield_Chase", "os:Hatfield Chase", "area"),
 ("hatfield", "Cuckney ('High Hatfield')", "Battle of Hatfield Investigation Society", "place-name and burials", W + "Battle_of_Hatfield_Chase", "os:Cuckney", "village"),
 # ---------------- Heavenfield, 634 (control) ----------------
 ("heavenfield", "Heavenfield, St Oswald's", "Bede; the cross and church by the Roman Wall", "chronicle and continuous tradition", W + "Battle_of_Heavenfield", "coord:55.0203,-2.1005", "site"),
 ("heavenfield", "Devil's Water", "Max Adams", "charter evidence for Denisesburn", W + "Battle_of_Heavenfield", "river:Devil's Water@54.93,-2.07", "area"),
]

# proposals the sources name but that are regions or places I could not pin to a point from a source
UNPLACED = [
    ("brunanburh", "Broadclough, Rossendale", "Thomas Newbigging", "no point in the sources I used"),
    ("graupius", "Gask Ridge", "suggested", "a ridge about 20 km long, not a point"),
    ("graupius", "Sutherland", "suggested", "a county, not a site"),
]

tr = Transformer.from_crs(27700, 4326, always_xy=True)


def grid_to_ll(ref):
    letters = ref[:2].upper(); digits = ref[2:]
    a = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    l1, l2 = a.index(letters[0]), a.index(letters[1])
    e100 = ((l1 - 2) % 5) * 5 + (l2 % 5); n100 = (19 - (l1 // 5) * 5) - (l2 // 5)
    h = len(digits) // 2; e, n = digits[:h], digits[h:]
    scale = 10 ** (5 - h)
    E = e100 * 100000 + int(e) * scale + scale / 2; N = n100 * 100000 + int(n) * scale + scale / 2
    lon, lat = tr.transform(E, N)
    return lat, lon


def decode(blob):
    flags = blob[3]; off = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]; wkb = blob[off:]
    bo = "<" if wkb[0] == 1 else ">"; typ = struct.unpack(bo + "I", wkb[1:5])[0]
    dim = 3 if (typ // 1000 in (1, 2) or typ & 0x80000000) else 2
    n = struct.unpack(bo + "I", wkb[5:9])[0]
    return np.frombuffer(wkb[9:9 + 8 * dim * n], dtype=bo + "f8").reshape(n, dim)[:, :2]


def river_point(name, hlat, hlon):
    """Vertex nearest the length-weighted centre of the connected run of NAME nearest the hint."""
    con = sqlite3.connect(GPKG)
    rows = con.execute("select length,start_node,end_node,geometry from watercourse_link where watercourse_name=?", (name,)).fetchall()
    fwd = Transformer.from_crs(4326, 27700, always_xy=True); hx, hy = fwd.transform(hlon, hlat)
    geoms = [decode(r[3]) for r in rows]
    parent = list(range(len(rows)))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    first = {}
    for i, r in enumerate(rows):
        for nd in r[1:3]:
            if nd in first: parent[find(i)] = find(first[nd])
            else: first[nd] = i
    mids0 = np.array([g[len(g) // 2] for g in geoms])
    for i in range(len(rows)):  # also join pieces broken by an unnamed link, a lake or a culvert (within 2 km)
        for j in range(i + 1, len(rows)):
            if np.hypot(*(mids0[i] - mids0[j])) < 2000: parent[find(i)] = find(j)
    comps = {}
    for i in range(len(rows)): comps.setdefault(find(i), []).append(i)
    best = min(comps.values(), key=lambda idx: min(np.hypot(*(geoms[i] - [hx, hy]).T).min() for i in idx))
    L = np.array([rows[i][0] for i in best]); mids = np.array([geoms[i][len(geoms[i]) // 2] for i in best])
    cen = (mids * L[:, None]).sum(0) / L.sum(); V = np.vstack([geoms[i] for i in best])
    v = V[np.argmin(((V - cen) ** 2).sum(1))]
    lon, lat = tr.transform(v[0], v[1])
    return lat, lon, float(L.sum())


def main():
    osn = pd.read_csv(OSN, sep="\t", dtype=str)
    atlas = pd.read_csv(ATLAS, usecols=["atlas_id", "name", "lat", "lon"])
    plei = pd.read_csv(PLEI, usecols=["id", "title", "reprLat", "reprLong"])
    out = []
    for b, cand, prop, basis, url, geo, prec, *gurl in C:
        kind, arg = geo.split(":", 1); gurl = gurl[0] if gurl else ""
        note = ""
        if kind == "os":
            hint = None
            if "@" in arg: arg, h = arg.split("@"); hint = list(map(float, h.split(",")))
            parts = arg.split("|"); m = osn[osn.name1 == parts[0]]
            if len(parts) > 1 and parts[1]: m = m[m.county == parts[1]]
            if len(parts) > 2: m = m[m.local_type == parts[2]]
            if len(parts) > 1 and parts[1] == "": m = m[m.county.isna()]
            if hint:  # several entries of the same name: take the one nearest the place the source is about
                d = (m.lat.astype(float) - hint[0]) ** 2 + ((m.lon.astype(float) - hint[1]) * 0.6) ** 2
                m = m.loc[[d.idxmin()]]
            assert len(m) == 1, (cand, len(m), m[["name1", "county", "local_type"]].values.tolist())
            lat, lon = float(m.lat.iloc[0]), float(m.lon.iloc[0])
            gsrc = f"OS Open Names: {m.name1.iloc[0]} ({m.local_type.iloc[0]})"
        elif kind == "atlas":
            m = atlas[atlas.name.str.startswith(arg)]
            assert len(m) == 1, (cand, m.name.tolist())
            lat, lon = float(m.lat.iloc[0]), float(m.lon.iloc[0])
            gsrc = f"Atlas of Hillforts {int(m.atlas_id.iloc[0])}: {m.name.iloc[0]}"
        elif kind == "pleiades":
            m = plei[plei.id == int(arg)]; lat, lon = float(m.reprLat.iloc[0]), float(m.reprLong.iloc[0])
            gsrc = f"Pleiades {arg}: {m.title.iloc[0].lstrip('*')}"
        elif kind == "grid":
            lat, lon = grid_to_ll(arg); h = (len(arg) - 2) // 2
            gsrc = f"Grid reference {arg[:2]} {arg[2:2 + h]} {arg[2 + h:]} " + ("from " + gurl if gurl else "stated in the source")
        elif kind == "coord":
            lat, lon = map(float, arg.split(",")); gsrc = "Coordinates " + ("from " + gurl if gurl else "stated in the source page")
        elif kind == "river":
            name, h = arg.split("@"); hl = list(map(float, h.split(",")))
            lat, lon, L = river_point(name, *hl)
            gsrc = f"OS Open Rivers: {name}, midpoint of a {L / 1000:.1f} km run"
        out.append(dict(battle=b, candidate=cand, proposer=prop, basis=basis, source_url=url,
                        lat=round(lat, 5), lon=round(lon, 5), precision=prec, geocode=gsrc))
    df = pd.DataFrame(out)
    df.to_csv(os.path.join(ROOT, "data", "candidates.csv"), index=False)
    pd.DataFrame(UNPLACED, columns=["battle", "candidate", "proposer", "why_unplaced"]).to_csv(os.path.join(ROOT, "data", "unplaced.csv"), index=False)
    print(len(df), "candidates for", df.battle.nunique(), "battles")
    print(df.groupby("battle").size().to_string())


if __name__ == "__main__":
    main()
