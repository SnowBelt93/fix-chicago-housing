"""Read the number of homes from a Chicago building permit's work description.

Chicago's permit data has no 'number of units' field, so the tracker reads it from the free-text description
("ERECT A 4 STORY, 12 D.U. MASONRY BUILDING ..."). Rules, in order:
  1. Not housing (tents, stages, cranes, hotels, garages, schools ...) -> None.
  2. Partial permits (caissons, foundation, excavation only) -> 0, so a project isn't counted twice.
  3. An explicit count ("12 D.U.", "SIX DWELLING UNITS", "(3) 4-UNIT TOWNHOUSE BUILDINGS") -> that number.
  4. Building words ("SINGLE FAMILY", "TWO-FLAT", "DUPLEX", "COACH HOUSE") -> 1, 2 or 3.
  5. Housing words but no count -> None (counted as unknown, reported separately).
Accuracy is measured in tools/tracker/accuracy.py against the Census Building Permits Survey and a hand-checked sample."""
import re

WORDS = {w: i for i, w in enumerate('ZERO ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE THIRTEEN FOURTEEN FIFTEEN SIXTEEN SEVENTEEN EIGHTEEN NINETEEN TWENTY'.split())}
WORDS.update({'THIRTY': 30, 'FORTY': 40, 'FIFTY': 50, 'SIXTY': 60})
_W = '|'.join(sorted(WORDS, key=len, reverse=True))
NUM = r'(\d{1,4}(?:,\d{3})?|(?:(?:' + _W + r')\s+HUNDRED(?:\s+(?:AND\s+)?(?:' + _W + r')(?:[- ](?:' + _W + r'))?)?)|(?:' + _W + r')(?:[- ](?:' + _W + r'))?)'

def num(s):
    s = s.replace(',', '').strip()
    if s.isdigit(): return int(s)
    t, n = 0, 0
    for w in s.replace('-', ' ').split():
        if w == 'AND': continue
        if w == 'HUNDRED': n = (n or 1) * 100; t += n; n = 0; continue
        if w not in WORDS: return None
        n += WORDS[w]
    return t + n

RES = re.compile(r'DWELLING|D\.\s?U\b|\d\s?D\.?U\b|\bDUS?\b|SINGLE[- ]?FAMILY|ONE[- ]FAMILY|\bS\.?F\.?R\b|RESIDEN|\bUNITS?\b|APART|APARMENT|TOWN ?HOME|TOWN ?HOUSE|ROW ?HOUSE|CONDO|\bFLAT\b|[23TWOHRE]+[- ]FLAT|DUPLEX|TWO[- ]FAMILY|2[- ]FAMILY|COACH HOUSE|\bADU\b|HOMES?\b|R-?2 OCCUPANCY|R-?3\b')
NOT_HOUSING = re.compile(r'\bTENTS?\b|\bSTAGES?\b|TRUSS STRUCTURE|BLEACHER|CANOPY|TRAILER|TOWER CRANE|\bCRANE\b|\bHOIST\b|SCAFFOLD|BILLBOARD|\bSIGNS?\b|SOLAR|ANTENNA|MONOPOLE|PLATFORM'
                         r'|HOTEL|MOTEL|SELF[- ]STORAGE|STORAGE UNITS|WAREHOUSE|SCHOOL|CHURCH|HOSPITAL|PARKING (?:LOT|STRUCTURE|GARAGE)\b(?!.*DWELLING)'
                         r'|RESTAURANT|FIELD ?HOUSE|COMFORT STATION|FUEL|CAR WASH|DATA CENT')
GARAGE_ONLY = re.compile(r'^(?:(?!DWELLING|D\.?\s?U\b|FAMILY|RESIDEN|UNIT|FLAT|HOME|HOUSE|APART|CONDO).)*GARAGE', re.S)
PARTIAL = re.compile(r'(?:FOUNDATION|CAISSON|EXCAVATION|PILE|SUPERSTRUCTURE)[^.]{0,90}\bONLY\b(?! (?:A|THE) )|CAISSONS?(?: \([^)]*\))?(?: AND [A-Z ]+)? ONLY|CAISSON PERMIT FOR|FOUNDATION(?:.?S)?(?: PERMIT)? ONLY|FOUNDATION (?:AND|&) (?:UNDERGROUND|BELOW[- ]GRADE)[A-Z ]* ONLY'
                     r'|EXCAVATION(?: AND [A-Z ]+)? ONLY|SHORING|EARTH RETENTION|EARLY START|SUPERSTRUCTURE ONLY|BELOW GRADE ONLY|UNDERGROUND (?:WORK|UTILITIES) ONLY'
                     r'|(?:PHASE|PART) (?:I|1|ONE)\b[^.]{0,40}(?:FOUNDATION|CAISSON|EXCAVATION)|PILES? ONLY|PARTIAL SUPERSTRUCTURE|FOUNDATIONS? PERMIT(?! (?:UNDER|ISSUED|NO|NUMBER|#)| ?\(?#|S? (?:WAS |WERE )?(?:ISSUED|UNDER))'
                     r'|FOUNDATION (?:AND|&) (?:CONCRETE )?(?:SUPER)?STRUCTURE (?:UP TO|THROUGH|TO THE)|FOUNDATION (?:AND|&) [A-Z ()0-9]{0,30}(?:BASEMENT|MEP)[A-Z ]{0,20}ONLY|STRUCTURE UP TO GRADE'
                     r'|FOUNDATIONS?[- ]ONLY|(?:FOUNDATION|STRUCTURE)[A-Z ,&]{0,40} ONLY,? (?:UP )?(?:TO|THROUGH) (?:LEVEL|THE|FLOOR)')
REVISION = re.compile(r'REVISION PERMIT|REVISIONS? (?:TO|OF) (?:THE )?(?:ISSUED )?(?:FULL BUILDING |PARTIAL |FOUNDATION |SUPERSTRUCTURE )?(?:PERMIT|PERMIT APPLICATION)|REVISED PERMIT|\bREVISION #|AMENDMENT TO PERMIT')
# "(3) 4-UNIT TOWNHOUSE BUILDINGS"
MULTI = re.compile(r'\(?' + NUM + r'\)?\s+(?:NEW\s+)?(?:\w+\s+){0,2}?\(?' + NUM + r'\)?[- ](?:D\.?\s?U\.?|DWELLING[- ]UNIT|UNIT|FLAT)S?\b[^.]{0,40}?BUILDINGS\b')
COUNT = re.compile(r'(?:TOTAL OF\s+)?\(?' + NUM + r'\)?(?:\s*\(\d+\))?\s*[-\s/]?\s*(?:NEW\s+|TOTAL\s+)?(?:(?:RES\.?|RESIDENTIAL|DWELLING|APARTMENT|EFFICIENCY|STUDIO|RENTAL|CONDO(?:MINIUM)?|AFFORDABLE|SENIOR|MARKET[- ]RATE|ATTACHED|SINGLE[- ]FAMILY|FAMILY)\s+)*'
                   r"(?:D\.?\s?U\.?(?:'?S)?\b|" r'DWELL?ING[- ]UNITS?\b|DWELLINGS?\b|UNITS?\b|UNTS?\b|APARTMENTS?\b|TOWN ?HOMES?\b|TOWN ?HOUSES?\b|ROW ?HOUSES?\b|RESIDENCES\b)')
NOT_UNIT_AFTER = re.compile(r'^\s*(?:OF\s+)?(?:HOTEL|ROOMS?|KEYS|STORAGE|ROOFTOP|RTU|A/?C|HVAC|CONDENS|RETAIL|COMMERCIAL|OFFICE|PARKING|CAR\b|BEDS?)')
NOT_UNIT_BEFORE = re.compile(r'(?:ROOFTOP|RETAIL|COMMERCIAL|OFFICE|STORAGE|HOTEL|PARKING|MECHANICAL|A/C|HVAC)\s*$')
SFR = re.compile(r'SINGLE[- ]?FAMILY|ONE[- ]FAMILY|\bS\.?F\.?R\.?\b|SINGLE[- ]FAMIL|\bSFD\b|SINGLE DWELLING|ONE DWELLING')
TWO = re.compile(r'\bTWO[- ]FLAT|\b2[- ]FLAT|DUPLEX|TWO[- ]FAMILY|\b2[- ]FAMILY|TWO DWELLING')
THREE = re.compile(r'\bTHREE[- ]FLAT|\b3[- ]FLAT|THREE[- ]FAMILY|\b3[- ]FAMILY')
COACH = re.compile(r'COACH HOUSE|\bADU\b|ACCESSORY DWELLING')
LABEL = re.compile(r"\bB(?:UI)?LD(?:IN)?G\.?(?:\s+(?:#|NO\.?)?\s*|\s*#\s*)['\"]?([A-Z]|\d{1,2})['\"]?(?=[\s,.:;'\"-]|$)")

EXISTING = re.compile(r'(?:(?:FOR|TO SERVE|SERVING|ON|IN|OF|AT|TO|REPLAC(?:E|ING)|BEHIND)\s+)?(?:AN?\s+|THE\s+)?EXISTING\b[^.;,]*|\bCURRENT(?: USE)?\s*:[^;.]*')
SMALL_JOB = re.compile(r'\b(?:GREENHOUSE|SHED|DECK|POOL|STOOP|PORCH|PERGOLA|FENCE|ADDITION|RENOVATION|REMODEL|GARAGES?|SIDING|DORMER|BALCON(?:Y|IES)|STAIRS?)\b')
GROUP = re.compile(r'RESIDENCE HALL|DORMITOR|\bDORM\b|STUDENT HOUSING|GROUP LIVING|NURSING HOME|SHELTER')

def classify(desc):
    """Return (homes or None, reason). homes=None means not housing or no count found."""
    d = ' '.join((desc or '').upper().split())
    if not d: return None, 'empty'
    if NOT_HOUSING.search(d) and not re.search(r'DWELLING|D\.\s?U\b|\d\s?DU\b|RESIDENTIAL UNITS?|APARTMENTS?\b', d):
        return None, 'not housing'
    if GROUP.search(d) and not re.search(r'DWELLING UNITS?|APARTMENTS?\b', d): return None, 'not housing'
    # drop phrases about buildings that are already there ("... FOR AN EXISTING 4 STORY 5 UNIT BUILDING")
    d2 = EXISTING.sub(' ', d)
    m = RES.search(d2)
    if not m: return None, 'not housing'
    pre = d2[:m.start()]
    if SMALL_JOB.search(pre) and not re.search(r'ERECT|NEW CONSTRUCTION|CONSTRUCT(?:ION)? OF|COACH', pre):
        return None, 'not housing'
    if re.search(r'(?:ERECT|BUILD|CONSTRUCT)\w*\s+(?:AN?\s+)?(?:NEW\s+)?(?:PREFAB\w*\s+)?(?:\d+(?:\.\d)?[- ]CAR\s+)?(?:[A-Z]+\s+){0,2}(?:GARAGE|GREENHOUSE|DECK|POOL|SHED|PERGOLA)\b', pre) and 'COACH' not in d2:
        return None, 'not housing'
    if GARAGE_ONLY.search(d2) and not re.search(r'DWELLING|D\.?\s?U\b|FAMILY|RESIDEN|\bUNITS?\b|FLAT|HOMES?\b|HOUSE\b|APART|CONDO|COACH', d2):
        return None, 'garage only'
    kind = 'revision' if REVISION.search(d) else 'partial permit' if PARTIAL.search(d) and 'FULL BUILDING' not in d else ''
    n, why = count(d2)
    return n, (kind or why)

def count(d):
    m = MULTI.search(d)
    if m and num(m.group(1)) and num(m.group(2)) and num(m.group(1)) <= 30:
        return num(m.group(1)) * num(m.group(2)), 'count x buildings'
    counts = []
    for m in COUNT.finditer(d):
        n = num(m.group(1))
        if n is None or n == 0 or n > 2000: continue
        if NOT_UNIT_AFTER.match(d[m.end():]) or NOT_UNIT_BEFORE.search(d[:m.start()]): continue
        # "4 STORY 6 UNIT" fine; skip years and code years (2019 CBC)
        if 1900 <= n <= 2100: continue
        counts.append((n, 'TOTAL OF' in m.group(0), 'EFFICIENC' in m.group(0)))
    if counts:
        tot = [n for n, t, _ in counts if t]
        if tot: return tot[0], 'count'
        eff = [n for n, _, e in counts if e]; du = [n for n, _, e in counts if not e]
        if eff and du and max(du) - max(eff) not in du and max(du) not in eff: return max(du) + max(eff), 'count'
        return max(n for n, _, _ in counts), 'count'
    if THREE.search(d): return 3, 'three-flat'
    if TWO.search(d): return 2, 'two-flat'
    if SFR.search(d): return 1, 'single family'
    if COACH.search(d): return 1, 'coach house'
    if re.search(r'TOWN ?HOME|TOWN ?HOUSE|ROW ?HOUSE', d): return 1, 'townhouse'
    return None, 'housing, no count'

def label(desc):
    m = LABEL.search((desc or '').upper())
    return m.group(1) if m else ''

if __name__ == '__main__':
    for t in ['ERECT A 4 STORY, 12 D.U. MASONRY BUILDING', 'NEW CONSTRUCTION (4) RESIDENTIAL UNIT TOWNHOUSE BUILDING \'A\', 3 STORIES',
              'ERECT NEW 3 STORY, III-B, 3DU APARTMENT BUILDING', 'NEW CONSTRUCTION, (4) FOUR STORY + BASEMENT, (6) SIX DWELLING UNIT BUILDING',
              'DDS 2019 CBC: CAISSONS ONLY PERMIT FOR NEW CONSTRUCTION OF A 6 STORY MIXED USE BUILDING TO CONTAIN A TOTAL OF 45 DWELLING UNITS',
              'CONSTRUCTION OF NEW 2 STORY HOTEL WITH 92 UNITS AS PER PLANS', 'ERECT A 2 STORY FRAME SINGLE FAMILY RESIDENCE WITH DETACHED 2 CAR GARAGE',
              'NEW 2 CAR GARAGE WITH ROOF DECK', 'NEW CONSTRUCTION, 18 STORIES, 240 DWELLING UNITS. REVISION TO PERMIT#100547950',
              'ERECT (3) 4-UNIT TOWNHOUSE BUILDINGS PER PLANS', 'SC 2019 CBC ERECT TWO-FLAT WITH BASEMENT', 'NEW 3 UNIT MASONRY BUILDING WITH 3 CAR GARAGE']:
        print(classify(t), label(t), '|', t[:70])
