# Delaware Code (4 Nov 2026), from the official site delcode.delaware.gov:
# titles, their chapters (some under parts), one page per chapter with every
# section. Usage: bundle.py <out dir> [max chapters]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://delcode.delaware.gov/"
home = get(SITE).replace("&#xA;", "")
titles = list(dict.fromkeys(re.findall(r'href="\s*(title\d+[A-Z]?/index\.html)\s*"', home)))
chapters = []
def walk(url, depth=0):
    page = get(url).replace("&#xA;", "")
    found = False
    for href in dict.fromkeys(re.findall(r'href="\s*([^"#]*?/index\.html)\s*"', page)):
        full = urllib.parse.urljoin(url, href.strip())
        if full == url or not full.startswith(SITE) or full.count("/") <= url.count("/") - 1:
            continue
        if re.search(r"/c\d+[A-Z]?/index\.html$", full):
            if full not in chapters: chapters.append(full); found = True
        elif depth < 2 and re.search(r"/(part|subpart|sc)[^/]*/index\.html$", full, re.I):
            walk(full, depth + 1)
import urllib.parse
for t in titles:
    walk(SITE + t)
if LIMIT: chapters = chapters[:LIMIT]
print(f"Delaware: {len(titles)} titles, {len(chapters)} chapters", flush=True)
def one(url):
    page = get(url)
    th = re.search(r'(?s)<div id="TitleHead">(.*?)</div>', page)
    head = oneline(th.group(1)) if th else ""
    title = re.search(r"/title(\d+[A-Z]?)/", url).group(1)
    out = []
    for m in re.finditer(r'(?s)<div class="SectionHead" id="([^"]+)">(.*?)</div>(.*?)(?=<div class="Section">|<div class="SectionHead"|</div>\s*</div>\s*<div id="CodeFooter"|\Z)', page):
        h = oneline(m.group(2))
        hm = re.match(r"§+\s*([0-9A-Z.\-]+)\.\s*(.*)", h)
        if not hm: continue
        body = re.split(r'(?s)<div class="SectionHistory"|<a [^>]*href="[^"]*laws', m.group(3))[0]
        out.append(row(title, hm.group(1), head, hm.group(2), clean(body)))
    if not out:
        for href in dict.fromkeys(re.findall(r'href="\s*([^"#]*?(?:sc|subchapter)[^"/]*/index\.html)\s*"', page.replace("&#xA;", ""), re.I)):
            sub = urllib.parse.urljoin(url, href.strip())
            if sub != url and sub.startswith(url.rsplit("/", 1)[0]):
                out += one(sub)
    return out
write(pool(one, chapters, 4, 200, "chapters"), out, "DE", "https://delcode.delaware.gov (Delaware Code Revisors)")
