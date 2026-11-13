"""Regex pieces shared by every language's tables (month and day names as they appear on the English pages)."""
MF = '(January|February|March|April|May|June|July|August|September|October|November|December)'
MS = '(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\\.?'
MA = '(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\\.?'
DF = '(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'
DS = '(Mon|Tue|Wed|Thu|Fri|Sat|Sun)'

# P(english, spanish, chinese, polish): a pattern row from a sentence with numbers and dates in it. Every number in the English
# ($1,234 / 12.5% / 3.2B) and every date (Nov. 9 / Nov. 9, 2026) becomes a captured piece; in the translations write #1, #2…
# for the pieces in order (copied as they are) and @1, @2… for dates (translated, "9 nov.").
import re as _re
_MANC = MA.replace('(', '(?:', 1)
_DATE = _MANC + r' \d{1,2}(?:, \d{4})?'
_NUM = r'[−-]?\$?\d(?:[\d,]*\d)?(?:\.\d+)?%?[MBK]?'
def P(en, *tr):
    pat, i, n = '', 0, 0
    for m in _re.finditer('(' + _DATE + ')|(' + _NUM + ')', en):
        pat += _re.escape(en[i:m.start()]); pat += '(' + (_DATE if m.group(1) else _NUM) + ')'; i = m.end(); n += 1
    pat = '^' + pat + _re.escape(en[i:]) + '$'
    out = []
    for t in tr:
        t = t.replace('$', '$$')
        for k in range(n, 0, -1): t = t.replace('#' + str(k), '$' + str(k)).replace('@' + str(k), '[[$' + str(k) + ']]')
        out.append(t)
    return [pat] + out

# Q(english, spanish, chinese, polish): a pattern row from a script template, with {} where the page fills something in.
# In the translations write {1}, {2}… for those pieces in order; each piece is translated too when it can be.
# {#} in the English stands for a number or money amount only ($1,234 / 12.5% / $3.2M), which keeps short rows like
# '{#} a home' from swallowing whole sentences.
def Q(en, *tr):
    bits = _re.split(r'(\{#?\})', en); n = 0; pat = '^'
    for b in bits:
        if b == '{}': pat += '(.+?)'; n += 1
        elif b == '{#}': pat += '(' + _NUM + ')'; n += 1
        else: pat += _re.escape(b)
    pat += '$'
    out = []
    for t in tr:
        t = t.replace('$', '$$')
        for k in range(n, 0, -1): t = t.replace('{' + str(k) + '}', '[[$' + str(k) + ']]')
        out.append(t)
    return [pat] + out
