"""Per-ward inputs for ward mode (meta.json "wardFloor"): {ward: [homes today, lot area within 1/2 mile of the L or Metra
in sq ft]} from the building files (b/<area>.wasm) and the ward byte in b/extra.wasm; buildings that are gone are skipped.
Run from the repo root: python3 tools/prep_wards.py"""
import json, struct, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
meta = json.load(open(os.path.join(ROOT, 'meta.json')))
ex = open(os.path.join(ROOT, 'b', 'extra.wasm'), 'rb').read()
na = struct.unpack_from('<I', ex, 0)[0]; o = 4; EXTRA = {}
for _ in range(na):
    num, N = struct.unpack_from('<II', ex, o); o += 8; EXTRA[num] = ex[o:o + N]; o += N
homes = collections.Counter(); near = collections.Counter()
for a in meta['areas']:
    num = a['num']; b = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N, V = struct.unpack_from('<II', b, 0); off = 24 + 4 * V
    nv = b[off:off + N]; st = b[off + N:off + 2 * N]; fl = b[off + 2 * N:off + 3 * N]; off += 3 * N
    if (3 * N) % 2: off += 1
    un = struct.unpack_from(f'<{N}H', b, off); off += 2 * N
    fp = struct.unpack_from(f'<{N}H', b, off)
    E = EXTRA.get(num, bytes(N))
    for i in range(N):
        if i < len(E) and (E[i] & 64): continue
        w = E[i] & 63 if i < len(E) else 0
        if not w: continue
        homes[w] += un[i]
        if (fl[i] & 3) or (fl[i] & 4): near[w] += max(2 * fp[i] * 2, 3125)
meta['wardFloor'] = {str(w): [homes[w], near[w]] for w in range(1, 51)}
json.dump(meta, open(os.path.join(ROOT, 'meta.json'), 'w'), separators=(',', ':'))
H, T = sum(homes.values()), sum(near.values())
print('homes', H, 'near-transit lot sq ft', T)
for w in (1, 2, 19, 27, 42, 43, 46, 48):
    print(w, homes[w], near[w], 'equal', round(97078 / 50), 'homes', round(97078 * homes[w] / H), 'blend', round(97078 * (homes[w] / H + near[w] / T) / 2))
