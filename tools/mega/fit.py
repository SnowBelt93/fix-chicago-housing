"""Pixel → lon/lat by a least-squares affine fit to street-crossing control points."""
import numpy as np, math
def fit(ctrl):   # ctrl: [((px, py), (lon, lat)), ...]
    A = np.array([[px, py, 1] for (px, py), _ in ctrl]); L = np.array([ll for _, ll in ctrl])
    M, res, *_ = np.linalg.lstsq(A, L, rcond=None)
    err = A @ M - L; lat0 = L[:, 1].mean()
    print('control misfit (m):', [round(math.hypot(e[0] * 111319.49 * math.cos(math.radians(lat0)), e[1] * 111319.49), 1) for e in err])
    return lambda pts: [[round(v, 7) for v in (np.array([x, y, 1]) @ M)] for x, y in pts]
def rect(x0, y0, x1, y1): return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
