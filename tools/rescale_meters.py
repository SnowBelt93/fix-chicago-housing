"""One-time fix (Oct 2026): the building and street binaries were written with 110,574 m per degree of latitude,
but deck.gl's METER_OFFSETS reads offsets on its Web Mercator sphere (111,319.49 m per degree; lon scaled by cos(lat)).
That pulled everything toward each file's origin by 0.67% north-south (up to ~15 m inside a community area), so
buildings drifted off the basemap and off lon/lat layers like the vacant-lot dots. This rescales the stored offsets.
Safe to run once: meta.json records "meterScale": "deck" and the script refuses to run twice."""
import json, os, struct, math, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mp = os.path.join(ROOT, 'meta.json'); meta = json.load(open(mp))
if meta.get('meterScale') == 'deck': raise SystemExit('already rescaled')
R = 111319.49
def fix(path, unit, header_off, verts_off_fn):
    buf = bytearray(open(path, 'rb').read())
    N, V = struct.unpack_from('<II', buf, 0); lon0, lat0 = struct.unpack_from('<dd', buf, 8)
    sx = R / 111320.0; sy = R / 110574.0
    o = verts_off_fn(buf, N, V)
    q = np.frombuffer(bytes(buf[o:o + 4 * V]), dtype='<i2').astype(np.float64).reshape(-1, 2)
    q[:, 0] *= sx; q[:, 1] *= sy
    q = np.round(q)
    assert q.min() >= -32767 and q.max() <= 32767, (path, q.min(), q.max())
    buf[o:o + 4 * V] = q.astype('<i2').tobytes()
    open(path, 'wb').write(buf)
    return V
n = 0
for a in meta['areas']:
    n += fix(os.path.join(ROOT, 'b', f"{a['num']}.wasm"), 0.5, 24, lambda b, N, V: 24)
def streets_off(buf, P, V):
    o = 24 + P; o += (-o) % 4; o += 4 * (P + 1); return o
n += fix(os.path.join(ROOT, 'b', 'streets.wasm'), 2, 24, streets_off)
meta['meterScale'] = 'deck'
json.dump(meta, open(mp, 'w'), separators=(',', ':'))
print('rescaled', n, 'vertices')
