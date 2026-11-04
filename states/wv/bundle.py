# West Virginia Code (4 Nov 2026), from the Legislature's code site,
# code.wvlegislature.gov: every section listed in its sitemap, one page per
# section. Usage: bundle.py <out dir> [max sections]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://code.wvlegislature.gov/"
def units():
    return list(dict.fromkeys(re.findall(r"<loc>https://code\.wvlegislature\.gov/([0-9A-Z]+-[0-9A-Z]+-[0-9A-Z.\-]+)/</loc>", get(SITE + "sitemap.xml"))))
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
print(f"West Virginia: {len(chapters)} sections", flush=True)
def one(s):
    page = get(f"{SITE}{s}/", allow404=True)
    if not page: return None
    m = re.search(r"(?s)class='sectiontext[^']*'>\s*<h4>\s*(?:§|&sect;)\s*([0-9A-Z.\-]+?)\.\s*(.*?)</h4>(.*?)</div>", page)
    if not m: return None
    c, a = m.group(1).split("-")[:2]
    return row("WVC", m.group(1), f"Chapter {c} > Article {a}", oneline(m.group(2)), clean(re.sub(r"\s+", " ", m.group(3))))
write(pool(one, chapters, 6, 2000, "sections"), out, "WV", "https://code.wvlegislature.gov/ (West Virginia Legislature)")
