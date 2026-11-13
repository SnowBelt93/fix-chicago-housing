// Writes budget/data/levers.json: the budget simulator's options in plan-code order, so other pages (the community page)
// can read shared budget plans (#b2.<value per lever>~<dept:pct,...>). Run after changing the L array in budget/index.html:
//   node tools/budget/levers.mjs
import fs from "node:fs";
const root = new URL("../../", import.meta.url).pathname;
const html = fs.readFileSync(root + "budget/index.html", "utf8");
const a = html.indexOf("const L = ["), b = html.indexOf("\n];", a);
if (a < 0 || b < 0) throw new Error("couldn't find the L array");
const L = new Function("return " + html.slice(a + "const L = ".length, b + 2))();
const out = L.map(l => {
  const o = {id: l.id, t: l.t, g: l.g, sub: l.sub || "", kind: l.kind, type: l.type, start: l.type === "income" ? 0 : (l.start || 0)};
  if (l.type === "opts") o.opts = l.opts.map(x => x[0]);
  if (l.type === "range"){ o.min = l.min; o.max = l.max; o.step = l.step; }
  if (l.gone) o.gone = 1;   // kept only so older plan codes still line up
  return o;
});
// department names as the simulator shows them (its short() function), for "<dept id>:<percent>" in plan codes
const sa = html.indexOf("function short(n){"), sb = html.indexOf("\n", sa);
const short = new Function(html.slice(sa, sb) + "\nreturn short;")();
const B = JSON.parse(fs.readFileSync(root + "budget/data/budget.json", "utf8"));
const depts = Object.fromEntries(B.depts.map(d => [d.id, d.id === "99" ? "Citywide costs" : short(d.name)]));
fs.writeFileSync(root + "budget/data/levers.json", JSON.stringify({made: new Date().toISOString().slice(0, 10), levers: out, depts}));
console.log(out.length, "levers;", [...new Set(out.map(o => o.type))].join(", "));
