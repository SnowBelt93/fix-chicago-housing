"""State bill tracker: downloads Illinois General Assembly bill status from ilga.gov (runs in GitHub Actions).

ilga.gov serves its certificate without the intermediate, so Python can't verify it out of the box. We don't turn
verification off: we read the server's leaf certificate, follow its "CA Issuers" link to download the missing
intermediate, check that a root in certifi's bundle signed it, and only then add it to the trust store.

Steps (python3 tools/bills/fetch.py [steps]):
  probe   save directory listings and one sample bill to tools/raw/bills/probe.json (to learn the formats)
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

if __name__ == "__main__":
    steps = sys.argv[1:] or ["probe"]
    for s in steps: globals()[s]()
