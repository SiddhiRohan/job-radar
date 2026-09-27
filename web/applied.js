/* Applied view: headline tiles, applications per day, where they stand, by company, a status board, and the
   full table in a collapsed section so no value depends on hovering. Plain SVG and CSS, no chart library.
   Uses el, api and toast from app.js, which are defined before any of these functions run. */
const STAGES = ["applied", "screen", "interview", "offer", "rejected"];
const SVGNS = "http://www.w3.org/2000/svg";
const svg = (tag, attrs = {}) => { const e = document.createElementNS(SVGNS, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); return e; };
const dayOf = r => r.date.slice(0, 10);  /* applications.md stores local time */
const localDay = t => { const d = new Date(t); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const shortDay = d => new Date(d + "T12:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
const A = { rows: [], showAll: false, shown: {} };  /* shown: last tile value per label, so only a change counts up */

/* One floating tooltip for every chart. Text only, never innerHTML: company names come from job postings. */
let tipEl;  /* made on first use: el() is defined in app.js, which loads after this file */
const tipNode = () => tipEl || (tipEl = document.body.appendChild(Object.assign(el("div", { class: "vtip", role: "status" }), { hidden: true })));
function showTip(e, value, label) {
  const tip = tipNode();
  tip.replaceChildren(el("b", {}, value), el("span", {}, label)); tip.hidden = false;
  const r = (e.target.getBoundingClientRect && e.clientX == null) ? e.target.getBoundingClientRect() : null;
  const x = r ? r.left + r.width / 2 : e.clientX, y = r ? r.top : e.clientY;
  tip.style.left = Math.min(x + 12, innerWidth - 200) + "px"; tip.style.top = y + scrollY - 44 + "px";
}
const hoverable = (node, value, label) => {
  node.setAttribute("tabindex", "0"); node.setAttribute("aria-label", `${label}: ${value}`);
  for (const ev of ["pointermove", "focus"]) node.addEventListener(ev, e => showTip(e, value, label));
  for (const ev of ["pointerleave", "blur"]) node.addEventListener(ev, () => (tipNode().hidden = true));
  return node;
};

/* A tile number ticks up from the value last shown (0 on first paint) when it scrolls into view. Re-renders that
   do not change the number stay still. Off under prefers-reduced-motion. */
function countUp(label, value) {
  const tv = el("span", { class: "tv" }, String(value));
  const from = A.shown[label] ?? 0, still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  A.shown[label] = value;
  if (still || from === value || typeof value !== "number") return tv;
  tv.textContent = String(from);
  const io = new IntersectionObserver(es => es.forEach(en => {
    if (!en.isIntersecting) return; io.disconnect();
    const t0 = performance.now(), ms = 700;
    const tick = now => { const p = Math.min(1, (now - t0) / ms), k = 1 - Math.pow(1 - p, 3); tv.textContent = String(Math.round(from + (value - from) * k)); if (p < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }), { threshold: .5 });
  io.observe(tv);
  return tv;
}

function tiles(rows) {
  const weekAgo = localDay(Date.now() - 6 * 864e5);
  const heard = rows.filter(r => r.status !== "applied").length;
  const tile = (label, value, note) => el("div", { class: "tile reveal" }, el("span", { class: "tl" }, label), countUp(label, value), note ? el("span", { class: "tn" }, note) : null);
  return el("div", { class: "tiles" },
    tile("Applications", rows.length),
    tile("Last 7 days", rows.filter(r => dayOf(r) >= weekAgo).length),
    tile("Companies", new Set(rows.map(r => r.company)).size),
    tile("Heard back", heard, heard ? `${Math.round(100 * heard / rows.length)}% of applications` : "No replies recorded yet"));
}

/* Columns, one per day for the last 14 days. Single series, so no legend; the title names it. */
function perDay(rows) {
  const counts = {}; rows.forEach(r => (counts[dayOf(r)] = (counts[dayOf(r)] || 0) + 1));
  const days = Array.from({ length: 14 }, (_, i) => localDay(Date.now() - (13 - i) * 864e5));
  const vals = days.map(d => counts[d] || 0), max = Math.max(4, ...vals), top = Math.ceil(max / 4) * 4;
  const W = 700, H = 200, L = 28, B = 24, T = 14, plotH = H - B - T, slot = (W - L) / days.length, bw = Math.min(24, slot - 6);
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img", "aria-label": "Applications per day, last 14 days" });
  for (let i = 0; i <= 4; i++) {
    const v = (top / 4) * i, y = T + plotH - (v / top) * plotH;
    s.append(svg("line", { x1: L, x2: W, y1: y, y2: y, class: "grid" }));
    const t = svg("text", { x: L - 6, y: y + 4, class: "tick", "text-anchor": "end" }); t.textContent = v; s.append(t);
  }
  const peak = vals.indexOf(Math.max(...vals));
  days.forEach((d, i) => {
    const v = vals[i], h = (v / top) * plotH, x = L + i * slot + (slot - bw) / 2, y = T + plotH - h, r = Math.min(4, h);
    const g = svg("g", { class: "col" });
    g.append(svg("rect", { x: L + i * slot, y: T, width: slot, height: plotH, class: "hit" }));
    if (v) g.append(svg("path", { d: `M${x},${T + plotH} V${y + r} q0,-${r} ${r},-${r} h${bw - 2 * r} q${r},0 ${r},${r} V${T + plotH} Z`, class: "bar" }));
    if (i === peak && v) { const t = svg("text", { x: x + bw / 2, y: y - 4, class: "val", "text-anchor": "middle" }); t.textContent = v; g.append(t); }
    if (i % 2 === 1 || i === days.length - 1) { const t = svg("text", { x: x + bw / 2, y: H - 6, class: "tick", "text-anchor": "middle" }); t.textContent = shortDay(d); g.append(t); }
    s.append(hoverable(g, `${v} application${v === 1 ? "" : "s"}`, shortDay(d)));
  });
  return el("section", { class: "card wide" }, el("h3", {}, "Applications per day"), el("p", { class: "sub" }, "Last 14 days"), s);
}

/* Horizontal bars with the value at the tip; used for stages (fixed order) and companies (by count). */
function barList(title, sub, items, total) {
  const max = Math.max(1, ...items.map(i => i.n));
  return el("section", { class: "card" }, el("h3", {}, title), sub ? el("p", { class: "sub" }, sub) : null,
    el("div", { class: "hbars" }, ...items.map(it => {
      const row = el("div", { class: "hrow" }, el("span", { class: "hl" }, it.label),
        el("span", { class: "track" }, el("span", { class: "fill" + (it.rest ? " rest" : ""), style: `width:${(100 * it.n) / max}%` })), el("span", { class: "hv" }, String(it.n)));
      return hoverable(row, `${it.n} (${Math.round((100 * it.n) / total)}%)`, it.label);
    })));
}
function stages(rows) {
  const items = STAGES.map(s => ({ label: s[0].toUpperCase() + s.slice(1), n: rows.filter(r => r.status === s).length }));
  return barList("Where they stand", "Current status of every application", items, rows.length);
}
function companies(rows) {
  const counts = {}; rows.forEach(r => (counts[r.company] = (counts[r.company] || 0) + 1));
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const items = sorted.slice(0, 7).map(([label, n]) => ({ label, n }));
  const rest = sorted.slice(7);
  /* The aggregate is context, not a company: gray, so the named companies carry the color. */
  if (rest.length) items.push({ label: `Other ${rest.length} companies`, n: rest.reduce((s, [, n]) => s + n, 0), rest: true });
  return barList("By company", `${sorted.length} companies`, items, rows.length);
}

/* A status change can be taken back from the toast; the undo is the same call with the old status. */
async function setStatus(r, status, undoing) {
  const was = r.status;
  await api("/api/applied/status", { req_id: r.req_id, company: r.company, status });
  r.status = status; renderApplied();
  toast(undoing ? `Back to ${status}: ${r.company}` : `Set ${r.company} to ${status}`,
    undoing ? null : { label: "Undo", run: () => setStatus(r, was, true).catch(err => toast(err.message)) });
}
const statusSelect = r => el("select", { "aria-label": `Status for ${r.company}, ${r.title}`, onchange: e => setStatus(r, e.target.value).catch(err => toast(err.message)) },
  ...STAGES.map(s => el("option", { value: s, selected: s === r.status ? "" : null }, s)));

/* The board: one column per stage. Cards drag between columns (the drop calls setStatus, so Undo works); the select
   stays for keyboard and touch. The Applied column shows the newest 6 until asked for the rest. */
const DRAG = { r: null };
function board(rows) {
  const cols = STAGES.map(s => {
    const all = rows.filter(r => r.status === s), cap = s === "applied" && !A.showAll ? 6 : all.length;
    const cards = all.slice(0, cap).map(r => {
      const card = el("article", { class: "kcard", title: r.title, draggable: "true" },
        el("span", { class: "kh" }, el("span", { class: "kc" }, r.company), el("span", { class: "kd" }, shortDay(dayOf(r)))),
        postingTitle(r.title, r.url), statusSelect(r));
      card.addEventListener("dragstart", e => { DRAG.r = r; card.classList.add("ghost"); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", `${r.company}|${r.req_id}`); });
      card.addEventListener("dragend", () => { card.classList.remove("ghost"); DRAG.r = null; document.querySelectorAll(".kcol.over").forEach(c => c.classList.remove("over")); });
      return card;
    });
    const more = all.length > cap ? el("button", { type: "button", class: "quiet", onclick: () => { A.showAll = true; renderApplied(); } }, `Show all ${all.length}`) : null;
    const col = el("div", { class: "kcol", "data-stage": s }, el("h4", {}, s[0].toUpperCase() + s.slice(1), el("span", { class: "n" }, String(all.length))),
      ...(cards.length ? cards : [el("p", { class: "kempty" }, "None yet")]), more);
    col.addEventListener("dragover", e => { if (!DRAG.r || DRAG.r.status === s) return; e.preventDefault(); e.dataTransfer.dropEffect = "move"; col.classList.add("over"); });
    col.addEventListener("dragleave", e => { if (!col.contains(e.relatedTarget)) col.classList.remove("over"); });
    col.addEventListener("drop", e => { e.preventDefault(); col.classList.remove("over"); const r = DRAG.r; DRAG.r = null; if (r && r.status !== s) setStatus(r, s).catch(err => toast(err.message)); });
    return col;
  });
  return el("section", { class: "card wide" }, el("h3", {}, "Board"), el("p", { class: "sub" }, "Drag a card to another column, or change its status"), el("div", { class: "kboard" }, ...cols));
}
function table(rows) {
  const tr = r => el("tr", {}, el("td", {}, r.date), el("td", {}, r.company), el("td", {}, postingTitle(r.title, r.url)), el("td", {}, statusSelect(r)),
    el("td", {}, r.folder ? el("button", { type: "button", class: "quiet", onclick: () => api("/api/open", { path: r.folder }).catch(e => toast(e.message)) }, r.folder) : ""));
  return el("details", { class: "tableview" }, el("summary", {}, "All applications as a table"),
    el("table", {}, el("thead", {}, el("tr", {}, ...["Date", "Company", "Title", "Status", "Folder"].map(h => el("th", {}, h)))), el("tbody", {}, ...rows.map(tr))));
}

function renderApplied(rows = A.rows) {
  A.rows = rows;
  const body = $("#applied-body"), open = body.querySelector("details.tableview")?.open;
  const t = table(rows); if (open) t.open = true;
  body.replaceChildren(tiles(rows), mailCard(rows), el("div", { class: "vgrid" }, perDay(rows), stages(rows), companies(rows), patternsCard(), watchCard(), board(rows)), t);  /* mailCard: web/mail.js, patternsCard and watchCard: web/insights.js */
}
