# D.C. Code (4 Nov 2026), from the D.C. Council's official codified XML
# (github.com/DCCouncil/law-xml-codified, the source of code.dccouncil.gov):
# one XML file per section. Usage: bundle.py <out dir> [max sections]
import glob, os, re, subprocess, sys, tempfile, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SRC = os.environ.get("DC_XML_DIR") or os.path.join(tempfile.gettempdir(), "dc-law-xml")
if not os.path.isdir(SRC):
    subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/DCCouncil/law-xml-codified", SRC], check=True)
NS = "{https://code.dccouncil.us/schemas/dc-library}"
SKIP = {NS + "annotations", NS + "history"}
def text_of(el, depth=0):
    parts = []
    for ch in el:
        if ch.tag in SKIP: continue
        tag = ch.tag.replace(NS, "")
        if tag in ("num", "heading") and depth == 0: continue
        if tag == "para":
            parts.append(text_of(ch, depth + 1))
        elif tag in ("num",):
            parts.append((ch.text or "").strip() + " ")
        elif tag in ("heading",):
            parts.append(" ".join(ch.itertext()).strip() + " ")
        else:
            parts.append(" ".join(" ".join(ch.itertext()).split()) + "\n")
    return "".join(parts)
files = sorted(glob.glob(os.path.join(SRC, "us/dc/council/code/titles/*/sections/*.xml")))
if LIMIT: files = files[:LIMIT]
rows = []
for f in files:
    try:
        root = ET.parse(f).getroot()
    except Exception:
        continue
    num = (root.findtext(NS + "num") or "").strip()
    head = " ".join((root.findtext(NS + "heading") or "").split())
    if not num: continue
    title = num.split("-")[0]
    body = re.sub(r"\n\s*\n+", "\n", text_of(root)).strip()
    rows.append(row("DC", num, f"Title {title}", head, body))
write(rows, out, "DC", "https://github.com/DCCouncil/law-xml-codified (Council of the District of Columbia)")
