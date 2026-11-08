// The link-preview image for a shared plan (1200x630), drawn as SVG and rasterized in the Worker with resvg.
// Only numbers from the stored plan go in, so nothing anyone typed can appear in it.
const STAR = "M12 1 L14.4 7.84 L21.53 6.5 L16.8 12 L21.53 17.5 L14.4 16.16 L12 23 L9.6 16.16 L2.47 17.5 L7.2 12 L2.47 6.5 L9.6 7.84 Z";
const fmt = n => Math.round(n).toLocaleString("en-US");
export function cardSvg(c, artB64){
  const neg = c.homes < 0, big = (neg ? "−" : "") + fmt(Math.abs(c.homes));
  const goalWord = c.mode === 1 ? "Hard mode goal" : c.mode === 2 ? "Every ward goal" : "Goal";
  const rentLine = c.rent < c.rentno ? "Rent in 2041: $" + fmt(c.rent) + " instead of $" + fmt(c.rentno)
    : c.rent > c.rentno ? "Rent in 2041: $" + fmt(c.rent) + ", up from $" + fmt(c.rentno) + " with no change" : "Rent in 2041: $" + fmt(c.rent);
  const gradeFill = c.grade === "F" || c.grade === "–" ? "none" : "#e4002b";
  const gradeInk = gradeFill === "none" ? "#e4002b" : "#ffffff";
  const size = big.length > 7 ? 116 : 132;
  return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="630" viewBox="0 0 1200 630">
<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f8faf7"/><stop offset="1" stop-color="#e5ebe4"/></linearGradient></defs>
<rect width="1200" height="630" fill="url(#bg)"/>
<rect y="0" width="1200" height="3" fill="#41b6e6"/><rect y="8" width="1200" height="1.5" fill="#41b6e6"/>
${artB64 ? `<image x="600" y="210" width="640" height="404" preserveAspectRatio="xMidYMax meet" xlink:href="data:image/png;base64,${artB64}"/>` : ""}
<path d="${STAR}" transform="translate(64 48) scale(1.6)" fill="#e4002b"/>
<text x="112" y="80" font-family="Instrument Sans" font-weight="700" font-size="30" fill="#1a1d21">Shape Chicago</text>
<text x="64" y="168" font-family="Instrument Sans" font-weight="600" font-size="30" fill="#3d434b">A plan from Fix Chicago Housing</text>
<text x="60" y="${168 + size + 6}" font-family="Instrument Sans" font-weight="600" font-size="${size}" letter-spacing="-2" fill="${neg ? "#b3001e" : "#1a1d21"}">${big}</text>
<text x="64" y="${168 + size + 60}" font-family="Instrument Sans" font-weight="400" font-size="34" fill="#1a1d21">new homes by 2041</text>
<g transform="translate(64 ${168 + size + 104})">
  <path d="${STAR}" transform="scale(3.1)" fill="${gradeFill}" stroke="#e4002b" stroke-width="${gradeFill === "none" ? 0.9 : 0}"/>
  <text x="37" y="47" text-anchor="middle" font-family="Instrument Sans" font-weight="700" font-size="${c.grade.length > 1 ? 24 : 28}" fill="${gradeInk}">${c.grade}</text>
  <text x="92" y="32" font-family="Instrument Sans" font-weight="600" font-size="27" fill="#1a1d21">${goalWord}: ${fmt(c.goal)}</text>
  <text x="92" y="66" font-family="Instrument Sans" font-weight="400" font-size="25" fill="#3d434b">${rentLine}</text>
</g>
<text x="64" y="598" font-family="Instrument Sans" font-weight="400" font-size="19" fill="#5a6069">Not affiliated with the City of Chicago.</text>
</svg>`;
}
