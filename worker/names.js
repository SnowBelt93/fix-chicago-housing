// Names people type for shared plans: a plan name and an optional "by" name.
// Checked here on the server (the page checks too, only to answer sooner). Rules:
//   - plan name 3–60 characters, "by" name 2–24; letters (any language), digits, spaces and a little punctuation
//   - no swearing, slurs or sexual words (the `obscenity` English list, which also catches l33t spellings and
//     spaced-out letters like "f u c k" once we close the gaps)
//   - no links, emails, @handles or phone numbers (keeps personal details and spam off the site)
//   - nothing that makes a plan look official ("City of Chicago", "official", "Mayor's plan")
// Anything that fails is refused with a plain message; nothing is stored.
import { RegExpMatcher, englishDataset, englishRecommendedTransformers } from "obscenity";

const matcher = new RegExpMatcher({ ...englishDataset.build(), ...englishRecommendedTransformers });
const ALLOWED = /^[\p{L}\p{M}0-9 '’.,&!?()\-:#/+]+$/u;
const LINKS = /https?:|www\.|\.(com|net|org|io|co|us|ly|gg|xyz|info|biz|me|tv)\b|@|\b\d{3}[\s.\-)]*\d{3}[\s.\-]*\d{4}\b|\d{7,}/i;
const OFFICIAL = /\b(official|city of chicago|mayor'?s plan|cdot|chicago department|alderman'?s plan|alderperson'?s plan|cta official)\b/i;

const clean = s => String(s == null ? "" : s).normalize("NFC").replace(/\s+/g, " ").trim();
// "f u c k" / "f.u.c.k" → "fuck", so spaced-out words are seen too
const closeGaps = s => s.replace(/\b(?:\p{L}[\s._*\-]+){2,}\p{L}\b/gu, m => m.replace(/[\s._*\-]+/g, ""));

export function checkName(raw, kind){
  const s = clean(raw);
  if (!s) return { ok: true, value: "" };
  const [lo, hi] = kind === "author" ? [2, 24] : [3, 60];
  if (s.length < lo || s.length > hi) return { ok: false, why: kind === "author" ? "Keep your name between 2 and 24 characters." : "Keep the plan's name between 3 and 60 characters." };
  if (!ALLOWED.test(s)) return { ok: false, why: "Use letters, numbers, spaces and simple punctuation only." };
  if (LINKS.test(s)) return { ok: false, why: "Names can't include links, emails, handles or phone numbers." };
  if (OFFICIAL.test(s)) return { ok: false, why: "Names can't make a plan look like it comes from the city." };
  if (matcher.hasMatch(s) || matcher.hasMatch(closeGaps(s))) return { ok: false, why: "That name isn't allowed here. Try another." };
  if (/(.)\1{5,}/.test(s)) return { ok: false, why: "Try a name without long runs of the same character." };
  return { ok: true, value: s };
}
