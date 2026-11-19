/* Popisky bublín na mobile: obdĺžniky nad a pod autom, spojené čiarou s bublinou, bez prekrývania.
   items: [{ el: .bubble, x, y, op, half }] – x/y = stred bubliny v px vzhľadom na kontajner bublín. */
const NS = "http://www.w3.org/2000/svg";
export const calloutQuery = matchMedia("(max-width: 760px)");

const PAD = 8, LH = 26, GAP = 5;
let bounds = null, boundsAt = 0;

function limits(box) {
  const now = performance.now();
  if (bounds && now - boundsAt < 400) return bounds;
  const br = box.getBoundingClientRect(), H = box.clientHeight;
  let top = 80, bottom = H - 12;
  const season = document.querySelector(".season");
  if (season && !season.hidden) {
    const r = season.getBoundingClientRect();
    if (r.height) top = Math.max(top, r.bottom - br.top + 10);
  }
  for (const sel of [".hint.on", ".static .go3d"]) {
    const el = document.querySelector(sel);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (r.height && getComputedStyle(el).display !== "none") bottom = Math.min(bottom, r.top - br.top - 10);
  }
  bounds = { top, bottom };
  boundsAt = now;
  return bounds;
}
export const resetCalloutBounds = () => (bounds = null);

export function clearCallouts(box) {
  box.classList.remove("callouts");
  box.querySelector("svg.leaders")?.remove();
  box.querySelectorAll(".bubble .lab").forEach((l) => { l.style.left = l.style.top = ""; });
}

export function layoutCallouts(box, items, carY) {
  box.classList.add("callouts");
  let svg = box.querySelector("svg.leaders");
  if (!svg) {
    svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "leaders");
    svg.setAttribute("aria-hidden", "true");
    box.prepend(svg);
  }
  while (svg.childElementCount < items.length) svg.appendChild(document.createElementNS(NS, "line"));
  const W = box.clientWidth, { top, bottom } = limits(box);

  const vis = items.filter((i) => i.op > 0.3);
  vis.forEach((i) => { i.inline = i.el.classList.contains("big"); i.w = i.el.querySelector(".lab").offsetWidth; });
  const up = vis.filter((i) => !i.inline && i.y < carY), down = vis.filter((i) => !i.inline && i.y >= carY);

  // pás nad autom / pod autom: popisky zoradené podľa x (čiary sa nekrížia), ak sa nezmestia → viac radov
  const band = (list, isUp) => {
    if (!list.length) return;
    list.sort((a, b) => a.x - b.x);
    const total = list.reduce((s, i) => s + i.w + GAP, 0);
    const rows = Math.max(1, Math.ceil(total / (W - 2 * PAD)));
    let step = LH + GAP;
    let y0 = isUp ? Math.min(...list.map((i) => i.y - i.half)) - 16 - LH : Math.max(...list.map((i) => i.y + i.half)) + 16;
    if (isUp) { if (y0 - (rows - 1) * step < top) step = Math.max(LH + 2, (y0 - top) / Math.max(1, rows - 1)); y0 = Math.max(y0, top + (rows - 1) * step); }
    else { if (y0 + (rows - 1) * step + LH > bottom) step = Math.max(LH + 2, (bottom - LH - y0) / Math.max(1, rows - 1)); y0 = Math.min(y0, bottom - LH - (rows - 1) * step); }
    for (let r = 0; r < rows; r++) {
      const row = list.filter((_, k) => k % rows === r);
      row.forEach((i) => { i.lx = Math.min(Math.max(i.x - i.w / 2, PAD), W - PAD - i.w); i.ly = isUp ? y0 - r * step : y0 + r * step; });
      for (let k = 1; k < row.length; k++) row[k].lx = Math.max(row[k].lx, row[k - 1].lx + row[k - 1].w + GAP);
      const last = row[row.length - 1];
      if (last.lx + last.w > W - PAD) {
        last.lx = W - PAD - last.w;
        for (let k = row.length - 2; k >= 0; k--) row[k].lx = Math.min(row[k].lx, row[k + 1].lx - GAP - row[k].w);
      }
    }
  };
  band(up, true); band(down, false);

  items.forEach((i, idx) => {
    const lab = i.el.querySelector(".lab"), line = svg.children[idx];
    if (i.op > 0.3 && i.inline) {                      // veľká bublina (Odťah): popisok hneď vedľa, smerom do stredu
      lab.style.left = lab.style.top = "";
      i.el.classList.toggle("left", i.x > W / 2);
      line.style.opacity = "0";
      return;
    }
    if (i.op <= 0.3 || i.ly == null) { line.style.opacity = "0"; i.ly = null; return; }
    const w = i.w, lx = i.lx;
    lab.style.left = (lx - (i.x - i.half)).toFixed(1) + "px";
    lab.style.top = (i.ly - (i.y - i.half)).toFixed(1) + "px";
    // čiara: od okraja bubliny k najbližšiemu bodu obdĺžnika
    const ax = Math.min(Math.max(i.x, lx + 8), lx + w - 8), ay = i.ly + (i.y < i.ly ? 0 : LH);
    const dx = ax - i.x, dy = ay - i.y, d = Math.hypot(dx, dy) || 1;
    line.setAttribute("x1", (i.x + (dx / d) * i.half).toFixed(1));
    line.setAttribute("y1", (i.y + (dy / d) * i.half).toFixed(1));
    line.setAttribute("x2", ax.toFixed(1));
    line.setAttribute("y2", ay.toFixed(1));
    line.style.opacity = String(Math.min(1, i.op));
    line.classList.toggle("hot", i.el.classList.contains("hot"));
    i.ly = null;
  });
}
