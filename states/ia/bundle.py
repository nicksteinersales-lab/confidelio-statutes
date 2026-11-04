# Iowa Code (4 Nov 2026), from the Iowa Legislature, legis.iowa.gov: the
# current edition's title pages list every chapter, and each chapter is
# published as one official XML file, split here into sections.
# Usage: bundle.py <out dir> [max chapters]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://www.legis.iowa.gov"
HOME = get(SITE + "/law/iowaCode")
YEAR = max(re.findall(r"chapters\?title=[IVX]+&(?:amp;)?year=(\d{4})", HOME))
def units():
    chs = []
    for t in dict.fromkeys(re.findall(r"chapters\?title=([IVX]+)&(?:amp;)?year=" + YEAR, HOME)):
        chs += re.findall(r"/docs/code/" + YEAR + r"/([0-9A-Z]+)\.pdf", get(f"{SITE}/law/iowaCode/chapters?title={t}&year={YEAR}"))
    return list(dict.fromkeys(chs))
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
print(f"Iowa Code {YEAR}: {len(chapters)} chapters", flush=True)
TOK = re.compile(r'(?s)<slim:Level class="(\w+)"[^>]*>\s*<slim:Heading[^>]*>(.*?)</slim:Heading>|</slim:Level>|<slim:Section class="codeSection"[^>]*>(.*?)</slim:Section>')
MARK = re.compile(r'<xhtml:div class="(\w+)"><xhtml:div class="heading"><xhtml:span class="identifier">([^<]*)</xhtml:span></xhtml:div>')
def head(h):
    m = re.search(r'(?s)class="identifier">(.*?)</xhtml:span>.*?class="headnote">(.*)', h)
    return (oneline(m.group(1)), oneline(m.group(2))) if m else ("", oneline(h))
def one(ch):
    x = get(f"{SITE}/docs/publications/ICC/{YEAR}/attachments/{ch}_slim.xml", allow404=True)
    if not x: return None
    x = re.sub(r"<xhtml:span class=\"blank-line\"/>", " ", x)
    rows, stack = [], []
    for m in TOK.finditer(x):
        if m.group(1):
            i, n = head(m.group(2))
            lab = {"codeChapter": "Chapter", "codeArticle": "Article", "codeSubchapter": "Subchapter", "codeDivision": "Division", "codePart": "Part", "codeSubpart": "Subpart"}.get(m.group(1), "")
            stack.append(f"{lab} {i} {n.title() if n.isupper() else n}".strip())
        elif m.group(3) is not None:
            s = m.group(3)
            hm = re.match(r'(?s)\s*<xhtml:div class="heading"><xhtml:span class="identifier">(.*?)</xhtml:span>(?:<xhtml:span class="headnote">(.*?)</xhtml:span>)?</xhtml:div>', s)
            if not hm: continue
            body = s[hm.end():].split('<xhtml:div class="history">')[0]
            body = MARK.sub(lambda k: "\n" + (f"({k.group(2)}) " if k.group(1) == "subpara" else f"{k.group(2)}. "), body)
            body = re.sub(r"</?xhtml:(?:span|i|b|em)\b[^>]*>", "", body)
            body = re.sub(r"(?i)</?xhtml:p[^>]*>", lambda k: "\n" if k.group(0).startswith("</") else "", body)
            body = re.sub(r"\n\s*\n", "\n", clean(body).replace(". \n", ". "))
            rows.append(row("IOWA", oneline(hm.group(1)), " > ".join(stack), oneline(hm.group(2) or ""), body))
        elif stack:
            stack.pop()
    return rows
write(pool(one, chapters, 6, 200, "chapters"), out, "IA", f"https://www.legis.iowa.gov/law/iowaCode (Iowa Legislative Services Agency, Iowa Code {YEAR})")
