"""Step 5. Build ../index.html and ../README.md from the templates.

Every number in the text is a placeholder like {{headline.widest.km|int}} filled from data/results.json;
work/site.json and work/layers.json are embedded as `const D = ...`.
Formats: int (thousands commas), f1, f2, pct0, words (one to twelve), Words (capitalised), raw.
Run: python3 code/05_build_site.py
"""
import os, re, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
S = json.load(open(os.path.join(ROOT, "work", "site.json"))); S["L"] = json.load(open(os.path.join(ROOT, "work", "layers.json")))


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "f1": return f"{v:.1f}"
    if f == "f2": return f"{v:.2f}"
    if f == "pct0": return f"{v * 100:.0f}%"
    if f in ("words", "Words"):
        w = "zero one two three four five six seven eight nine ten eleven twelve".split()
        s = w[int(v)] if int(v) < len(w) else f"{int(v):,}"
        return s.capitalize() if f == "Words" else s
    return str(v)


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(get(path.strip()), f.strip() or "raw")


t = open(os.path.join(HERE, "page_template.html")).read()
t = re.sub(r"\{\{(.+?)\}\}", sub, t)
t = t.replace("/*DATA*/", "const D = " + json.dumps(S, separators=(",", ":"), ensure_ascii=False) + ";")
open(os.path.join(ROOT, "index.html"), "w").write(t)
print("index.html", len(t.encode()) // 1024, "KB")
md = re.sub(r"\{\{(.+?)\}\}", sub, open(os.path.join(HERE, "README_template.md")).read())
open(os.path.join(ROOT, "README.md"), "w").write(md)
print("README.md written")
