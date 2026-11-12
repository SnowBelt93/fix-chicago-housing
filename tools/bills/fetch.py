"""State bill tracker: downloads Illinois General Assembly bill status from ilga.gov (runs in GitHub Actions).

ilga.gov serves its certificate without the intermediate, so Python can't verify it out of the box. We don't turn
verification off: we read the server's leaf certificate, follow its "CA Issuers" link to download the missing
intermediate, check that a root in certifi's bundle signed it, and only then add it to the trust store.

Steps (python3 tools/bills/fetch.py [steps]):
  probe   save directory listings and one sample bill to tools/raw/bills/probe.json (to learn the formats)
  bills   (default) every House and Senate bill of the current General Assembly: downloads only the status files whose
          date changed since the last run (tools/raw/bills/index.json), keeps every bill parsed in
          tools/raw/bills/all.json.gz, and writes tracker/bills.json with the bills on Chicago's housing, transit, budget,
          pensions and property taxes (topic rules in TOPICS below; shell bills left out).
Bill sponsors are legislators (elected officials); nothing else about people is kept.
"""
import json, os, re, ssl, socket, sys, time, urllib.request
import certifi
from cryptography import x509
from cryptography.x509.oid import ExtensionOID, AuthorityInformationAccessOID

OUT = os.path.join(os.path.dirname(__file__), "..", "raw", "bills")
os.makedirs(OUT, exist_ok=True)
HOST = "www.ilga.gov"
UA = {"User-Agent": "ShapeChicago-data/1.0 (civic project; daily bill status)"}

def context():
    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with socket.create_connection((HOST, 443), timeout=30) as s:
            with ctx.wrap_socket(s, server_hostname=HOST):
                return ctx            # already verifies: nothing to add
    except ssl.SSLCertVerificationError:
        pass
    # the leaf, read only to find where its issuer lives; nothing from this connection is trusted
    raw = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); raw.check_hostname = False; raw.verify_mode = ssl.CERT_NONE
    with socket.create_connection((HOST, 443), timeout=30) as s:
        with raw.wrap_socket(s, server_hostname=HOST) as t:
            leaf = x509.load_der_x509_certificate(t.getpeercert(binary_form=True))
    aia = leaf.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
    urls = [d.access_location.value for d in aia if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS]
    roots = x509.load_pem_x509_certificates(open(certifi.where(), "rb").read())
    for u in urls:
        data = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
        try: inter = x509.load_der_x509_certificate(data)
        except ValueError: inter = x509.load_pem_x509_certificate(data)
        ok = False
        for r in roots:
            if r.subject != inter.issuer: continue
            try: inter.verify_directly_issued_by(r); ok = True; break
            except Exception: pass
        if not ok: print("intermediate from", u, "isn't signed by a trusted root; skipping"); continue
        ctx.load_verify_locations(cadata=inter.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM).decode())
        print("added intermediate", inter.subject.rfc4514_string(), "from", u)
        return ctx
    raise SystemExit("couldn't complete ilga.gov's certificate chain")

CTX = None
def get(url, tries=3):
    global CTX
    CTX = CTX or context()
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60, context=CTX).read()
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(3 * (i + 1))

def probe():
    out = {}
    for name, url in [("ftp_root", "https://www.ilga.gov/ftp/legislation/"),
                      ("ftp_104", "https://www.ilga.gov/ftp/legislation/104/"),
                      ("billstatus", "https://www.ilga.gov/ftp/legislation/104/BillStatus/"),
                      ("billstatus_xml", "https://www.ilga.gov/ftp/legislation/104/BillStatus/XML/"),
                      ("hb5626", "https://www.ilga.gov/ftp/legislation/104/BillStatus/XML/10400HB5626.xml"),
                      ("hb5626_html", "https://www.ilga.gov/ftp/legislation/104/BillStatus/HTML/10400HB5626.html"),
                      ("legislation", "https://www.ilga.gov/Legislation")]:
        try:
            b = get(url); t = b.decode("utf-8", "replace")
            out[name] = {"url": url, "ok": True, "bytes": len(b), "head": t[:6000], "tail": t[-2000:],
                         "links": len(re.findall(r'href=', t, re.I))}
        except Exception as e:
            out[name] = {"url": url, "ok": False, "err": str(e)[:300]}
        print(name, out[name].get("ok"), out[name].get("bytes"), out[name].get("err", ""))
    json.dump(out, open(os.path.join(OUT, "probe.json"), "w"), indent=1)

GA = "104"
BASE = f"https://www.ilga.gov/ftp/legislation/{GA}/BillStatus/"
def tag(x, t):
    m = re.search(rf"<{t}>(.*?)</{t}>", x, re.S); return unesc(m.group(1).strip()) if m else ""
def unesc(t):
    import html; return html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ").strip()

def parse(fn, x):
    m = re.match(r"\d{5}(HB|SB)(\d+)\.xml", fn); kind, num = m.group(1), int(m.group(2))
    am = re.search(r"<actions>(.*?)</actions>", x, re.S)
    acts = [(unesc(d), unesc(c), unesc(a)) for d, c, a in re.findall(r"<statusdate>(.*?)</statusdate>\s*<chamber>(.*?)</chamber>\s*<action>(.*?)</action>", am.group(1) if am else "", re.S)]
    syn = re.search(r"<SynopsisText>(.*?)</SynopsisText>", x, re.S)
    return {"id": f"{kind}{num}", "short": tag(x, "shortdesc"), "spon": tag(x, "sponsors"),
            "refs": [unesc(r) for r in re.findall(r"<reference>(.*?)</reference>", x, re.S)][:60],
            "syn": unesc(syn.group(1)) if syn else "", "acts": acts}

def iso(d):
    m = re.match(r"(\d+)/(\d+)/(\d{4})", d or ""); return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""

# Where a bill stands, from its actions (latest that applies wins)
def stage(acts):
    st, label = 0, "Filed"
    text = [a[2] for a in acts]
    for a in text:
        if re.search(r"Public Act", a): return 6, "Law"
    for a in text:
        if re.search(r"Total Veto|Veto Stands", a): return 5, "Vetoed"
    for a in text:
        if re.search(r"Sent to the Governor", a): st, label = 5, "Sent to the Governor"
    if st: return st, label
    for a in text:
        if re.search(r"Passed Both Houses", a): return 4, "Passed both chambers"
    for a in text:
        if re.search(r"Third Reading - (Short Debate - )?Passed", a): st, label = 3, "Passed one chamber"
    if st: return st, label
    for a in text:
        if re.search(r"Do Pass|Recommends Be Adopted|Placed on Calendar Order of 2nd Reading|Second Reading", a): st, label = 2, "Out of committee"
    if st: return st, label
    for a in text:
        if re.search(r"Assigned to|Referred to", a): st, label = 1, "In committee"
    return st, label

# Topics: ILCS references first (what the bill amends), then words in its short title and synopsis
TOPICS = {
  "housing": (r"65 ILCS 5/11-13|65 ILCS 5/11-12\.2|65 ILCS 5/11-13\.1|55 ILCS 5/5-12|55 ILCS 5/5-1063|310 ILCS|20 ILCS 3805|765 ILCS 705|765 ILCS 710|765 ILCS 750|35 ILCS 200/18-173|35 ILCS 200/10-245",
              r"\bzoning\b|dwelling unit|accessory dwelling|affordable housing|housing development|middle housing|single stairway|residential building|\bhousing\b|landlord|tenant|starter home|manufactured home"),
  "transit": (r"70 ILCS 3605|70 ILCS 3615|70 ILCS 3610|70 ILCS 3620",
              r"transit|\bMetra\b|\bPace\b|Regional Transportation Authority|Chicago Transit Authority|Northern Illinois Transit"),
  "pensions": (r"40 ILCS 5/5-|40 ILCS 5/6-|40 ILCS 5/8-|40 ILCS 5/11-",
               r"Policemen's Annuity|Firemen's Annuity|Municipal Employees' Annuity|Laborers' Annuity"),
  "budget": (r"65 ILCS 5/8-11|65 ILCS 5/8-3-19|30 ILCS 115|35 ILCS 5/901|65 ILCS 5/11-74\.4",
             r"municipality with a population of (more than|over) 1,000,000|City of Chicago|home rule municipal|Local Government Distributive Fund|tax increment"),
  "property": (r"35 ILCS 200",
               r"property tax|assessment|homestead exemption"),
}
CHI = r"Chicago|population of (more than|over) (1,000,000|500,000)|Cook County|Northern Illinois Transit|Regional Transportation Authority"
def topics(b):
    refs = " ".join(b["refs"]); words = b["short"] + " " + b["syn"]
    out = []
    for k, (r, w) in TOPICS.items():
        if re.search(r, refs) or re.search(w, words, re.I): out.append(k)
    if "pensions" in out and not re.search(r"40 ILCS 5/(5|6|8|11)-", refs) and not re.search(CHI, words): out.remove("pensions")
    if "budget" in out and not re.search(CHI, words): out.remove("budget")
    if "property" in out and not re.search(CHI, words): out.remove("property")
    return out
def shell(b):
    s = b["syn"]
    return bool(re.search(r"Makes a technical change|Contains only a short title|Makes technical changes", s)) and len(s) < 400

def bills():
    idx_p = os.path.join(OUT, "index.json"); all_p = os.path.join(OUT, "all.json.gz")
    import gzip
    idx = json.load(open(idx_p)) if os.path.exists(idx_p) else {}
    allb = json.load(gzip.open(all_p, "rt")) if os.path.exists(all_p) else {}
    listing = get(BASE + "XML/").decode("utf-8", "replace")
    files = {fn: f"{d} {sz}" for d, sz, fn in re.findall(r"(\d+/\d+/\d{4}\s+\d+:\d+ [AP]M)\s+(\d+) <A HREF=\"[^\"]+/(\d{5}(?:HB|SB)\d+\.xml)\">", listing)}
    todo = [fn for fn, v in files.items() if idx.get(fn) != v]
    print(len(files), "bills listed;", len(todo), "new or changed")
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time(); done = 0
    def one(fn):
        try: return fn, parse(fn, get(BASE + "XML/" + fn).decode("utf-8", "replace"))
        except Exception as e: return fn, None
    with ThreadPoolExecutor(8) as ex:
        for fn, b in ex.map(one, todo):
            if b: allb[b["id"]] = b; idx[fn] = files[fn]; done += 1
            if time.time() - t0 > 40 * 60: break
    print("downloaded", done, "in", round(time.time() - t0), "s")
    json.dump(idx, open(idx_p, "w"))
    with gzip.open(all_p, "wt") as f: json.dump(allb, f, separators=(",", ":"))
    out = []
    for b in allb.values():
        tp = topics(b)
        if not tp or shell(b): continue
        st, lab = stage(b["acts"])
        k, n = re.match(r"([A-Z]+)(\d+)", b["id"]).groups()
        last = b["acts"][-1] if b["acts"] else ("", "", "")
        spon = re.split(r"-|,| and ", re.sub(r"^(Rep\.|Sen\.)\s*", "", b["spon"]))[0].strip()
        out.append({"id": b["id"], "t": b["short"], "tp": tp, "st": st, "lab": lab, "by": spon, "bych": "Rep." if k == "HB" else "Sen.",
                    "in": iso(b["acts"][0][0]) if b["acts"] else "", "last": [iso(last[0]), last[1], last[2]],
                    "syn": b["syn"][:900], "url": f"https://www.ilga.gov/ftp/legislation/{GA}/BillStatus/HTML/{GA}00{k}{int(n):04d}.html",
                    "hist": [[iso(d), c, a] for d, c, a in b["acts"] if re.search(r"Passed|Public Act|Governor|Veto|Do Pass|Filed with|Referred to Rules|Re-referred", a)][-12:]})
    out.sort(key=lambda x: (-x["st"], x["last"][0]), reverse=False)
    os.makedirs("tracker", exist_ok=True)
    json.dump({"ga": GA, "made": time.strftime("%Y-%m-%d"), "n_all": len(allb), "bills": out}, open("tracker/bills.json", "w"), separators=(",", ":"))
    from collections import Counter
    print(len(out), "on our topics;", Counter(t for b in out for t in b["tp"]), Counter(b["lab"] for b in out))

if __name__ == "__main__":
    steps = sys.argv[1:] or ["bills"]
    for s in steps: globals()[s]()
