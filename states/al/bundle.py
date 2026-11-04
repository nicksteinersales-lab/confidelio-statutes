# Code of Alabama 1975 (4 Nov 2026), from the Legislature's ALISON site,
# alison.legislature.state.al.us, through the public GraphQL API its own
# pages use (plain GET requests): the outline of every title, chapter and
# section, then one request per chapter for its sections' text and history.
# Usage: bundle.py <out dir> [max chapters]
import json, os, re, sys, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
API = "https://alison.legislature.state.al.us/graphql?query="
LEVEL = {"Chapter": 2, "Article": 3, "Part": 4, "Subpart": 5, "Division": 6}
def q(query):
    d = json.loads(get(API + urllib.parse.quote(query)))
    if d.get("errors"): raise RuntimeError(d["errors"])
    return d["data"]
def outline():
    # [(codeId, kind, label, heading path above it)], in code order
    recs, stack = [], []
    for r in q("{ titles: codeOfAlabamaTitles }")["titles"].split("∫"):
        f = r.split("†")
        if len(f) < 2 or not f[0].isdigit(): continue
        kind = f[1].split()[0]
        lvl = 7 if kind == "Section" else (0 if len(f) < 3 else 1) if kind == "Title" else LEVEL.get(kind, 6)
        while stack and stack[-1][0] >= lvl: stack.pop()
        recs.append((f[0], kind, f[1].strip(), " > ".join(x for _, x in stack)))
        if kind != "Section": stack.append((lvl, f[1].strip().rstrip(".")))
    return recs
OUTLINE = outline()
def units():
    return [(cid, (head + " > " if head else "") + label.rstrip(".")) for cid, kind, label, head in OUTLINE if kind == "Chapter"]
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
HEAD = {label.split()[1]: head for cid, kind, label, head in OUTLINE if kind == "Section" and len(label.split()) > 1}
print(f"Alabama: {len(chapters)} chapters", flush=True)
def one(ch):
    cid, chead = ch
    try:
        data = q('{ s: codesOfAlabama(where: { type: { eq: Section } }, include: ["%s"]) { data { displayId catchLine content history } } }' % cid)
    except Exception as e:
        print(f"{chead}: skipped ({e})", flush=True)
        return []
    res = []
    for s in data["s"]["data"]:
        sec = (s.get("displayId") or "").strip()
        if not sec: continue
        body = clean(s.get("content") or "")
        if s.get("history"): body += "\n" + oneline(s["history"])
        res.append(row("ALA", sec, HEAD.get(sec, chead), oneline(s.get("catchLine") or ""), body))
    return res
write(pool(one, chapters, 6, 200, "chapters"), out, "AL", "https://alison.legislature.state.al.us/code-of-alabama (Alabama Legislature, ALISON)")
