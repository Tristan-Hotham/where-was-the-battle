"""Step 3. What the texts say, how each candidate fares against it, and how far apart the theories are.

For every battle I list the clues the early texts actually give (a hill, a siege, ships, a river, a
named place nearby) and turn each into a check I can compute from the measures in work/measured.csv.
Each check gives 1 (fits), 0.5 (fits loosely) or 0 (does not fit), with the thresholds written next
to it. A candidate's 'fit' is the mean over that battle's checks. This is a transparent tally, not a
verdict: it ignores the place-name, archaeological and literary arguments that drive most proposals,
and a clue in a 12th-century chronicle is not worth the same as one in a contemporary poem.

Also: the spread of each battle's candidates (how far apart the theories are), where Wikidata pins
each battle, and how many battles in Britain and Ireland Wikidata gives a coordinate.

Writes data/candidates_scored.csv, data/battles.csv, data/checks.csv, data/results.json, work/site.json.
Run: python3 code/03_analyse.py
"""
import os, json, re
import numpy as np, pandas as pd
from shapely.geometry import shape, Point

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, ".."); HIST = os.path.abspath(os.path.join(ROOT, ".."))
WD = os.path.join(HIST, "_data2", "wikidata", "battles_world.json")
OSN = os.path.join(HIST, "osnames_gb.tsv")
PLEI = "/mnt/user-data/uploads/Downloads/pleiades-places-latest.csv.gz"


def hav(la1, lo1, la2, lo2):
    p1, p2 = np.radians(la1), np.radians(la2); dl = np.radians(np.asarray(lo2) - np.asarray(lo1))
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


# reference places (OS Open Names exact entries, or Pleiades)
REF_OS = {"Whalley": ("Whalley", "Lancashire"), "York": ("York", "York"), "Edinburgh": ("Edinburgh", "City of Edinburgh"),
          "Leeds": ("Leeds", None), "Hexham": ("Hexham", "Northumberland"), "Penselwood": ("Penselwood", "Somerset"),
          "Tettenhall": ("Tettenhall", None), "Wednesfield": ("Wednesfield", None), "Athelney": ("Athelney", "Somerset"),
          "Ribchester": ("Ribchester", "Lancashire")}
REF_PLEI = {"Verulamium": 79739}

# ---------------------------------------------------------------- the battles, their texts and their checks
# check: (id, short label, the clue and where it comes from, kind, parameters, weight note)
B = [
 dict(id="whalley", name="Whalley", full="Battle of Whalley (Billingahoh)", date="798", year=798,
      who="Eardwulf, king of Northumbria, against the rebel leader Wada",
      texts=[("Anglo-Saxon Chronicle, year 798", "A great battle 'at Whalley in Northumbria' in Lent, on 2 April; Alric son of Heardberht was killed, and many with him."),
             ("Symeon of Durham, Historia Regum (12th century, from earlier northern annals)", "Wada, a leader of the plot that killed King Aethelred, fought Eardwulf 'in a place called by the English Billingahoh, near Walalege'. Wada was put to flight.")],
      checks=[("near_whalley", "Near Whalley", "Both texts tie the fight to Whalley (Hwaelleage, Walalege)", "near", ("Whalley", 2, 5)),
              ("hoh", "A hill-spur", "Billingahoh ends in Old English hoh, a heel or spur of land; the Victoria County History reads it as the hill now called Whalley Nab", "hill", (0.9, 0.75))]),
 dict(id="badon", name="Mount Badon", full="Battle of Mount Badon", date="about 500", year=500,
      who="Britons against Saxons",
      texts=[("Gildas, De Excidio Britanniae (about 540s)", "'The siege of Badon Hill' (obsessio Badonici montis), 'almost the last great slaughter' of the invaders, in the year of Gildas's birth."),
             ("Bede, Ecclesiastical History (731)", "The siege of Mount Badon, 44 years after the Saxons came."),
             ("Historia Brittonum (about 830)", "Arthur's twelfth battle, 'on Mount Badon', where 960 fell in one charge."),
             ("Annales Cambriae (10th century)", "The battle of Badon, in which Arthur carried the cross for three days and nights."),
             ("Geoffrey of Monmouth (about 1136)", "Places it at Bath. Geoffrey invents freely.")],
      checks=[("mons", "A hill", "Every early text calls Badon a hill (mons)", "hill", (0.9, 0.75)),
              ("siege", "A place to besiege", "Gildas and Bede call it a siege (obsessio): I test for a hillfort within reach", "fort", (0.5, 2))]),
 dict(id="brunanburh", name="Brunanburh", full="Battle of Brunanburh", date="937", year=937,
      who="Aethelstan of England against Olaf of Dublin, Constantine of Alba and Owain of Strathclyde",
      texts=[("Anglo-Saxon Chronicle poem (within two decades)", "Fought 'around Brunanburh'; the Norsemen fled in their ships over deep water, 'Dingesmere', to Dublin."),
             ("Aethelweard (late 10th century); Symeon of Durham", "Brunandun; Weondune ('dun', a hill)."),
             ("John of Worcester, Symeon of Durham, Chronicle of Melrose (12th century)", "Olaf's fleet entered the mouth of the Humber."),
             ("Egil's Saga (13th century)", "Vinheidr: a heath, with Aethelstan's camp between a river and a wooded rise.")],
      checks=[("ships", "Ships within reach", "The defeated fled by sea to Dublin", "coast", (10, 25)),
              ("dun", "A hill", "Brunandun, Weondune: dun is a hill", "hill", (0.9, 0.75)),
              ("humber", "Near the Humber", "Later chroniclers put Olaf's fleet in the Humber (12th century and after)", "humber", (30, 60)),
              ("river", "A river nearby", "Egil's Saga puts a river beside the English camp (a late saga)", "river", (1, 2))]),
 dict(id="graupius", name="Mons Graupius", full="Battle of Mons Graupius", date="AD 83 or 84", year=83,
      who="Agricola's Roman army against the Caledonians under Calgacus",
      texts=[("Tacitus, Agricola (AD 98)", "The Caledonians held the slopes of a hill, Mons Graupius, rising in tiers above level ground; the fleet had been sent ahead along the coast; the beaten army fled to woods.")],
      checks=[("mons", "A big hill", "Tens of thousands ranked in tiers up a hill: I ask for at least 150 m of relief within 3 km (300 m for a full pass)", "relief", (300, 150)),
              ("fleet", "Near the sea", "Agricola's fleet worked along the coast; some argue the field was within sight of the sea", "coast", (10, 30))]),
 dict(id="boudica", name="Boudica's last stand", full="Boudica's final battle ('Watling Street')", date="AD 60 or 61", year=60,
      who="Suetonius Paulinus against the Iceni and Trinovantes under Boudica",
      texts=[("Tacitus, Annals 14 (about 115)", "Paulinus chose a narrow defile with a wood behind him, opening onto a plain; the Britons' wagons were drawn up behind their line."),
             ("Cassius Dio (about 200)", "No place named.")],
      checks=[("defile", "A defile", "A narrow pass with rising ground on the flanks: at least 60 m of relief within 3 km (30 m for a loose fit)", "relief", (60, 30)),
              ("road", "On a Roman road", "Paulinus was marching back from Anglesey with his legions", "road", (2, 5)),
              ("reach", "Within reach of the sacked towns", "The battle followed the burning of Verulamium (St Albans)", "near", ("Verulamium", 100, 200))]),
 dict(id="camlann", name="Camlann", full="Battle of Camlann", date="about 537", year=537,
      who="Arthur and Medraut (Mordred)",
      texts=[("Annales Cambriae (10th century, entry for 537)", "'The strife of Camlann, in which Arthur and Medraut fell.'"),
             ("Geoffrey of Monmouth (about 1136) and later", "On the River Camel in Cornwall; Layamon says Camelford; the French romances and Malory say Salisbury.")],
      checks=[("glann", "A river bank", "The name may come from Brittonic *Cambo-glanna, 'crooked bank'", "river", (1, 2))]),
 dict(id="catraeth", name="Catraeth", full="Battle of Catraeth", date="about 600", year=600,
      who="The Gododdin war band against the Angles of Bernicia and Deira",
      texts=[("Y Gododdin, attributed to Aneirin", "A war band feasted at Din Eidyn (Edinburgh) for a year and rode to Catraeth, where nearly all were killed.")],
      checks=[]),
 dict(id="arfderydd", name="Arfderydd", full="Battle of Arfderydd", date="573", year=573,
      who="Gwenddoleu against Rhydderch Hael, or Peredur and Gwrgi",
      texts=[("Annales Cambriae (entry for 573)", "The battle of Armterid."),
             ("John of Fordun (14th century)", "On the plain between Liddel and Carwannok.")],
      checks=[("liddel", "By the Liddel", "Fordun names the Liddel", "liddel", (3, 6)),
              ("plain", "Open ground", "Fordun calls it a plain: at most 40 m of relief within 1 km (80 m loosely)", "flat", (40, 80))]),
 dict(id="degsastan", name="Degsastan", full="Battle of Degsastan", date="about 603", year=603,
      who="Aethelfrith of Bernicia against Aedan mac Gabrain of Dal Riata",
      texts=[("Bede, Ecclesiastical History (731)", "Aedan came against Aethelfrith with 'an immense and mighty army' and was beaten 'at a famous place called Degsastan'.")],
      checks=[]),
 dict(id="maserfield", name="Maserfield", full="Battle of Maserfield", date="642", year=642,
      who="Penda of Mercia against Oswald of Northumbria",
      texts=[("Bede, Ecclesiastical History (731)", "Oswald fell at Maserfelth."),
             ("Annales Cambriae; Canu Heledd", "Cocboy; Cogwy.")],
      checks=[("feld", "Open ground", "Maserfelth ends in Old English feld, open country: at most 40 m of relief within 1 km (80 m loosely)", "flat", (40, 80))]),
 dict(id="winwaed", name="Winwaed", full="Battle of the Winwaed", date="655", year=655,
      who="Oswiu of Northumbria against Penda of Mercia",
      texts=[("Bede, Ecclesiastical History (731)", "Fought by the river Winwaed, swollen by heavy rain, so that 'many more were drowned in the flight than destroyed by the sword'; Oswiu ended the campaign in the district of Loidis.")],
      checks=[("river", "A river", "The battle is named after a river that drowned the fleeing army", "river", (1, 2)),
              ("loidis", "Near Leeds (Loidis)", "Bede ends the campaign in the district of Loidis", "near", ("Leeds", 25, 50))]),
 dict(id="nechtansmere", name="Nechtansmere", full="Battle of Dun Nechtain (Nechtansmere)", date="685", year=685,
      who="Bridei of the Picts against Ecgfrith of Northumbria",
      texts=[("Bede, Ecclesiastical History (731)", "Ecgfrith was lured 'into the straits of inaccessible mountains' and killed."),
             ("Irish annals; Historia Brittonum", "Dun Nechtain, 'Nechtan's fort'; Gueith Linn Garan, by a lake.")],
      checks=[("mountains", "Mountains", "'Straits of inaccessible mountains': at least 300 m of relief within 3 km (150 m loosely)", "relief", (300, 150)),
              ("lake", "A lake", "Linn Garan and the English name Nechtansmere both point to a lake (many have since been drained)", "water", (1.5, 3))]),
 dict(id="assandun", name="Assandun", full="Battle of Assandun", date="1016", year=1016,
      who="Cnut against Edmund Ironside",
      texts=[("Anglo-Saxon Chronicle, 1016", "Edmund caught the Danes at Assandun as they were going back to their ships.")],
      checks=[("dun", "A hill", "Assandun ends in dun, a hill", "hill", (0.9, 0.75)),
              ("ships", "Near the ships", "The Danes were heading back to their ships", "coast", (10, 25))]),
 dict(id="edington", name="Ethandun", full="Battle of Edington (Ethandun)", date="878", year=878,
      who="Alfred of Wessex against Guthrum",
      texts=[("Anglo-Saxon Chronicle, 878", "Alfred rode from Athelney to Ecgbryht's stone 'east of Selwood', on to Iley the next day, and then to Ethandun, where he won."),
             ("Asser, Life of King Alfred (893)", "Ethandun.")],
      checks=[("dun", "A hill", "Ethandun ends in dun, a hill", "hill", (0.9, 0.75)),
              ("selwood", "East of Selwood", "The muster was 'east of Selwood' and the army marched on from there: I test for a point east of Penselwood", "east", ("Penselwood",))]),
 dict(id="ellendun", name="Ellendun", full="Battle of Ellendun", date="825", year=825,
      who="Ecgberht of Wessex against Beornwulf of Mercia",
      texts=[("Anglo-Saxon Chronicle, 825", "Ecgberht fought Beornwulf at Ellendun.")],
      checks=[("dun", "A hill", "Ellendun ends in dun, a hill", "hill", (0.9, 0.75))]),
 dict(id="tettenhall", name="Tettenhall", full="Battle of Tettenhall (Wednesfield)", date="910", year=910,
      who="The armies of Mercia and Wessex against the Northumbrian Danes",
      texts=[("Aethelweard (late 10th century)", "Near Tettenhall (Teotanheale)."),
             ("Anglo-Saxon Chronicle", "Wodnesfeld (Wednesfield).")],
      checks=[("tett", "Near Tettenhall", "Aethelweard", "near", ("Tettenhall", 3, 6)),
              ("wodn", "Near Wednesfield", "The Chronicle", "near", ("Wednesfield", 3, 6))]),
 dict(id="hatfield", name="Hatfield Chase", full="Battle of Hatfield Chase", date="633", year=633,
      who="Cadwallon and Penda against Edwin of Northumbria",
      texts=[("Bede, Ecclesiastical History (731)", "Edwin was killed 'on the plain called Haethfelth'.")],
      checks=[("feld", "Open heath", "Haethfelth: open heathland, a field: at most 40 m of relief within 1 km (80 m loosely)", "flat", (40, 80))]),
 dict(id="heavenfield", name="Heavenfield", full="Battle of Heavenfield", date="634", year=634, control=True,
      who="Oswald of Northumbria against Cadwallon of Gwynedd",
      texts=[("Bede, Ecclesiastical History (731)", "Oswald set up a cross at Hefenfelth, near the wall the Romans built, and the monks of Hexham went there every year; Cadwallon was killed at Denisesburna.")],
      checks=[("wall", "By the Roman Wall", "Near the wall the Romans built across Britain", "road", (2, 5)),
              ("hexham", "Near Hexham", "The brethren of Hexham kept the site", "near", ("Hexham", 10, 20))]),
]
BY = {b["id"]: b for b in B}


def grade(kind, p, r, refs):
    """Return (score, measured value, unit) for one check on one candidate row r."""
    if kind == "hill":
        v = max(r.pct_2km, r.hill_1km_pct); return (1 if v >= p[0] else .5 if v >= p[1] else 0), v, "rank"
    if kind == "fort":
        v = r.fort_km; return (1 if v <= p[0] else .5 if v <= p[1] else 0), v, "km"
    if kind == "coast":
        v = r.coast_km; return (1 if v <= p[0] else .5 if v <= p[1] else 0), v, "km"
    if kind == "humber":
        v = r.humber_km; return (1 if v <= p[0] else .5 if v <= p[1] else 0), v, "km"
    if kind == "liddel":
        v = r.liddel_km; return (1 if v <= p[0] else .5 if v <= p[1] else 0), v, "km"
    if kind == "river":
        v = r.river_km; return (1 if v <= p[0] else .5 if v <= p[1] else 0), v, "km"
    if kind == "water":
        v = r.water_km; return (1 if v <= p[0] else .5 if v <= p[1] else 0), v, "km"
    if kind == "road":
        v = r.road_km
        if v is None or (isinstance(v, float) and np.isnan(v)): return None, None, "km"
        return (1 if v <= p[0] else .5 if v <= p[1] else 0), v, "km"
    if kind == "relief":
        v = r.relief_3km_m; return (1 if v >= p[0] else .5 if v >= p[1] else 0), v, "m"
    if kind == "flat":
        v = r.relief_1km_m; return (1 if v <= p[0] else .5 if v <= p[1] else 0), v, "m"
    if kind == "near":
        la, lo = refs[p[0]]; v = float(hav(r.lat, r.lon, la, lo)); return (1 if v <= p[1] else .5 if v <= p[2] else 0), v, "km"
    if kind == "east":
        la, lo = refs[p[0]]; v = r.lon - lo; return (1 if v > 0 else 0), float(v), "deg"
    raise ValueError(kind)


def r2(x, d=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


def main():
    m = pd.read_csv(os.path.join(ROOT, "work", "measured.csv"))
    osn = pd.read_csv(OSN, sep="\t", dtype=str)
    refs = {}
    for k, (nm, county) in REF_OS.items():
        q = osn[(osn.name1 == nm) & (osn.type == "populatedPlace")]
        q = q[q.county == county] if county else q[q.county.isna()]
        q = q[q.local_type.isin(["City", "Town", "Village", "Suburban Area", "Hamlet"])]
        assert len(q) == 1, (k, len(q)); refs[k] = (float(q.lat.iloc[0]), float(q.lon.iloc[0]))
    plei = pd.read_csv(PLEI, usecols=["id", "title", "reprLat", "reprLong"])
    for k, pid in REF_PLEI.items():
        q = plei[plei.id == pid]; refs[k] = (float(q.reprLat.iloc[0]), float(q.reprLong.iloc[0]))

    # ---------- checks
    crow, scores = [], []
    for i, r in m.iterrows():
        b = BY[r.battle]; got = []
        for cid, lab, clue, kind, p in b["checks"]:
            s, v, unit = grade(kind, p, r, refs)
            crow.append(dict(battle=r.battle, candidate=r.candidate, check=cid, label=lab, score=s, value=r2(v, 3), unit=unit))
            if s is not None: got.append(s)
        scores.append(dict(n_checks=len(got), fit=round(float(np.mean(got)), 3) if got else None))
    m = pd.concat([m, pd.DataFrame(scores)], axis=1)
    m["rank_in_battle"] = m.groupby("battle")["fit"].rank(ascending=False, method="min")
    m.to_csv(os.path.join(ROOT, "data", "candidates_scored.csv"), index=False)
    ck = pd.DataFrame(crow); ck.to_csv(os.path.join(ROOT, "data", "checks.csv"), index=False)

    # ---------- Wikidata: battles with coordinates in Britain and Ireland
    land = shape(json.load(open(os.path.join(ROOT, "data", "coast_bi.geojson")))["features"][0]["geometry"]).buffer(0.1)
    wd = json.load(open(WD)); seen = {}
    for x in wd:
        mm = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", x["c"])
        if not mm: seen.setdefault(x["b"], dict(label=x["bLabel"], lat=None, lon=None, unknown=True)); continue
        lo, la = float(mm.group(1)), float(mm.group(2))
        if not (49.5 < la < 61.5 and -11 < lo < 2.5) or not land.contains(Point(lo, la)): continue
        d = x.get("d") or x.get("d2") or ""
        yr = (-int(d[1:5]) if d.startswith("-") else int(d[:4])) if d else None
        old = seen.get(x["b"])
        if old is None or (yr is not None and (old.get("year") is None or yr < old["year"])):
            seen[x["b"]] = dict(label=x["bLabel"], lat=la, lon=lo, year=yr)
    wdb = {k: v for k, v in seen.items() if v.get("lat") is not None}
    yrs = np.array([v["year"] for v in wdb.values() if v.get("year") is not None])
    WDMAP = {"brunanburh": "Q2246615", "badon": "Q595320", "graupius": "Q1127337", "catraeth": "Q3403266", "arfderydd": "Q2633662",
             "maserfield": "Q1818410", "assandun": "Q1704268", "edington": "Q2305651", "ellendun": "Q1939977", "tettenhall": "Q2253682",
             "heavenfield": "Q956923", "hatfield": "Q1758473", "degsastan": "Q2712138"}
    nech = [k for k, v in wdb.items() if v["label"] == "Battle of Dun Nechtain"]
    if nech: WDMAP["nechtansmere"] = nech[0]

    # ---------- per battle
    R = dict(n_battles=len(B), n_candidates=int(len(m)), n_unplaced=int(len(pd.read_csv(os.path.join(ROOT, "data", "unplaced.csv")))))
    R["n_candidate_rows_by_precision"] = m.precision.value_counts().to_dict()
    bat, brows = {}, []
    for b in B:
        c = m[m.battle == b["id"]].reset_index(drop=True)
        la, lo = c.lat.values, c.lon.values
        D = hav(la[:, None], lo[:, None], la[None, :], lo[None, :])
        iu = np.triu_indices(len(c), 1)
        far = (int(iu[0][np.argmax(D[iu])]), int(iu[1][np.argmax(D[iu])])) if len(c) > 1 else (0, 0)
        cen = (float(la.mean()), float(lo.mean()))
        info = dict(name=b["name"], full=b["full"], date=b["date"], year=b["year"], who=b["who"], control=bool(b.get("control")),
                    texts=[dict(source=s, says=t) for s, t in b["texts"]],
                    checks=[dict(id=cid, label=lab, clue=clue, kind=kind, params=list(p)) for cid, lab, clue, kind, p in b["checks"]],
                    n=int(len(c)), n_checks=len(b["checks"]),
                    spread_km=r2(D[iu].max() if len(c) > 1 else 0, 1), median_pair_km=r2(np.median(D[iu]) if len(c) > 1 else 0, 1),
                    far_pair=[c.candidate[far[0]], c.candidate[far[1]]] if len(c) > 1 else None,
                    centroid=[round(cen[0], 4), round(cen[1], 4)])
        if len(b["checks"]):
            top = c.fit.max(); lead = c[c.fit == top]
            info.update(top_fit=r2(top, 3), leaders=lead.candidate.tolist(), n_full_fit=int((c.fit == 1).sum()),
                        n_zero_fit=int((c.fit == 0).sum()), mean_fit=r2(c.fit.mean(), 3))
        q = WDMAP.get(b["id"])
        if q and q in wdb:
            w = wdb[q]; dd = hav(w["lat"], w["lon"], la, lo)
            info["wikidata"] = dict(qid=q, lat=w["lat"], lon=w["lon"], nearest=c.candidate[int(np.argmin(dd))], nearest_km=r2(dd.min(), 1),
                                    farthest_km=r2(dd.max(), 1))
        elif q in seen and seen[q].get("unknown"):
            info["wikidata"] = dict(qid=q, unknown=True)
        else:
            info["wikidata"] = None
        bat[b["id"]] = info
        brows.append(dict(battle=b["id"], name=b["full"], date=b["date"], n_candidates=info["n"], n_checks=info["n_checks"],
                          spread_km=info["spread_km"], median_pair_km=info["median_pair_km"], top_fit=info.get("top_fit"),
                          leaders="; ".join(info.get("leaders", [])), wikidata_qid=q or "",
                          wikidata_lat=(info["wikidata"] or {}).get("lat"), wikidata_lon=(info["wikidata"] or {}).get("lon")))
    R["battles"] = bat
    bdf = pd.DataFrame(brows); bdf.to_csv(os.path.join(ROOT, "data", "battles.csv"), index=False)

    # ---------- headline numbers
    unl = bdf[~bdf.battle.isin(["heavenfield"])]
    multi = unl[unl.n_candidates > 1]
    R["headline"] = dict(
        n_unlocated=int(len(unl)), n_multi=int(len(multi)),
        widest=dict(battle=multi.sort_values("spread_km").battle.iloc[-1], km=float(multi.spread_km.max())),
        narrowest=dict(battle=multi.sort_values("spread_km").battle.iloc[0], km=float(multi.spread_km.min())),
        median_spread_km=r2(multi.spread_km.median(), 1),
        n_over_100km=int((multi.spread_km > 100).sum()), n_over_300km=int((multi.spread_km > 300).sum()),
        spread_order=multi.sort_values("spread_km", ascending=False)[["battle", "spread_km"]].values.tolist(),
        n_scored_battles=int((bdf.n_checks > 0).sum()), n_unscored=int((bdf.n_checks == 0).sum()),
        total_checks=int(sum(len(b["checks"]) for b in B)),
        n_battles_with_full_fit=int(sum(1 for k, v in bat.items() if v.get("top_fit") == 1)),
        n_battles_tied_top=int(sum(1 for k, v in bat.items() if v.get("leaders") and len(v["leaders"]) > 1)),
    )
    # how many candidates fit every check, how many none
    sc = m[m.n_checks > 0]
    R["headline"].update(n_cands_scored=int(len(sc)), n_cands_full=int((sc.fit == 1).sum()), n_cands_zero=int((sc.fit == 0).sum()))

    # ---------- Wikidata context
    pins = {k: v["wikidata"] for k, v in bat.items() if v.get("wikidata") and not v["wikidata"].get("unknown")}
    R["wikidata"] = dict(n_battles_bi=int(len(wdb)), n_before_1066=int((yrs < 1066).sum()), n_before_1000=int((yrs < 1000).sum()),
                         n_with_year=int(len(yrs)), n_study_pinned=int(sum(1 for k in pins if k != "heavenfield")),
                         n_study_unknown=int(sum(1 for v in bat.values() if (v.get("wikidata") or {}).get("unknown"))),
                         n_pins_within_2km=int(sum(1 for k, v in pins.items() if k != "heavenfield" and v["nearest_km"] <= 2)),
                         pins_far=sorted([[k, v["nearest_km"], v["nearest"]] for k, v in pins.items()], key=lambda x: -x[1]))
    # ---------- Whalley close-up
    w = m[m.battle == "whalley"].reset_index(drop=True)
    D = hav(w.lat.values[:, None], w.lon.values[:, None], w.lat.values[None, :], w.lon.values[None, :])
    R["whalley"] = dict(
        cands=[dict(name=r.candidate, elev_m=r2(r.elev_m, 0), from_whalley_km=r2(hav(r.lat, r.lon, *refs["Whalley"]), 2), road_km=r2(r.road_km, 1),
                    river_km=r2(r.river_km, 2), river=r.river_name, fit=r2(r.fit, 2), top_1km_m=r2(r.top_1km_m, 0)) for r in w.itertuples()],
        max_pair_km=r2(D.max(), 1), road=w.road_name.iloc[0],
        to_ribchester_km=r2(hav(*refs["Whalley"], *refs["Ribchester"]), 1), to_york_km=r2(hav(*refs["Whalley"], *refs["York"]), 0),
        nab_vs_village_km=r2(D[0, 3], 2), relief_3km_m=r2(w.relief_3km_m.max(), 0))
    R["refs"] = {k: [round(a, 4), round(b, 4)] for k, (a, b) in refs.items()}
    # ---------- extra numbers used in the text
    R["extra"] = dict(
        brun_n_humber_full=int(((ck.battle == "brunanburh") & (ck.check == "humber") & (ck.score == 1)).sum()),
        brun_n_ships_full=int(((ck.battle == "brunanburh") & (ck.check == "ships") & (ck.score == 1)).sum()),
        brun_n_both=int(len(set(ck[(ck.battle == "brunanburh") & (ck.check == "humber") & (ck.score >= .5)].candidate) &
                            set(ck[(ck.battle == "brunanburh") & (ck.check == "ships") & (ck.score >= .5)].candidate))),
        brun_both_full=sorted(set(ck[(ck.battle == "brunanburh") & (ck.check == "humber") & (ck.score == 1)].candidate) &
                              set(ck[(ck.battle == "brunanburh") & (ck.check == "ships") & (ck.score == 1)].candidate)),
        catraeth_from_edinburgh_km=r2(hav(*refs["Edinburgh"], *m[m.battle == "catraeth"][["lat", "lon"]].values[0]), 0),
        n_points_coord=int(m.geocode.str.startswith("Coordinates").sum()),
        bath_fort_km=r2(m[(m.battle == "badon") & (m.candidate == "Bath")].fort_km.iloc[0], 1),
        bromborough_humber_km=r2(m[(m.battle == "brunanburh") & (m.candidate == "Bromborough")].humber_km.iloc[0], 0),
        bennachie_coast_km=r2(m[(m.battle == "graupius") & (m.candidate == "Bennachie")].coast_km.iloc[0], 0),
        graupius_relief_pass=BY["graupius"]["checks"][0][4][0],
        n_checks_by_kind=pd.Series([k[3] for b in B for k in b["checks"]]).value_counts().to_dict(),
        n_points_os=int(m.geocode.str.startswith("OS Open Names").sum()), n_points_atlas=int(m.geocode.str.startswith("Atlas").sum()),
        n_points_grid=int(m.geocode.str.startswith("Grid").sum()),
        n_points_rivers=int(m.geocode.str.startswith("OS Open Rivers").sum()), n_points_pleiades=int(m.geocode.str.startswith("Pleiades").sum()),
        n_sources=int(m.source_url.nunique()), n_wikipedia_sources=int(m.source_url.str.contains("wikipedia").sum()))
    R["extra"]["brun_both_full_n"] = len(R["extra"]["brun_both_full"])
    json.dump(R, open(os.path.join(ROOT, "data", "results.json"), "w"), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))

    # ---------- compact site data
    cols = ["battle", "candidate", "proposer", "basis", "source_url", "lat", "lon", "precision", "geocode", "elev_m", "relief_3km_m", "coast_km", "road_km", "river_km", "river_name", "fort_km", "fort_name", "fit", "rank_in_battle"]
    S = dict(R=R, c=[{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in rec.items()} for rec in m[cols].to_dict("records")],
             ck=[[r.battle, r.candidate, r.check, r.score, r.value] for r in ck.itertuples()],
             order=[b["id"] for b in sorted(B, key=lambda b: b["year"])],
             wd=[[round(v["lat"], 3), round(v["lon"], 3), v["label"], v.get("year")] for v in wdb.values()])
    json.dump(S, open(os.path.join(ROOT, "work", "site.json"), "w"), separators=(",", ":"), ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(R["headline"], indent=1)); print(json.dumps(R["wikidata"], indent=1)); print(json.dumps(R["whalley"], indent=1))
    print(bdf.to_string())


if __name__ == "__main__":
    main()
