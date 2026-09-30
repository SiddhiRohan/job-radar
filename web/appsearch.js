/* Search on Applied: find applications by company, role or status as you type. Every word typed must appear in the
   company, the title or the status. A result keeps its status select, so a found application can be moved on the
   spot. Text only, never innerHTML: company names and titles come from job postings.
   Uses el from app.js, and A, svg, dayOf, shortDay and statusSelect from applied.js. */
function searchCard(rows) {
  const input = el("input", { type: "search", id: "appsearch", autocomplete: "off", spellcheck: "false",
    placeholder: "Find an application: company, role or status", "aria-label": "Find an application by company, role or status" });
  input.value = A.query || "";
  const results = el("div", { class: "sresults", "aria-live": "polite" });
  const show = () => { A.query = input.value; fillResults(results, rows, input.value); };
  input.addEventListener("input", show);
  input.addEventListener("keydown", e => { if (e.key === "Escape" && input.value) { e.stopPropagation(); input.value = ""; show(); } });
  const glass = svg("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" });
  glass.append(svg("circle", { cx: 10.5, cy: 10.5, r: 6.5 }), svg("path", { d: "M15.5 15.5 21 21" }));
  show();
  return el("section", { class: "card wide search" },
    el("div", { class: "sbar" }, glass, input, el("kbd", { class: "shint", title: "Press f to search from anywhere on Applied" }, "f")), results);
}

const matchesAll = (r, words) => { const hay = `${r.company} ${r.title} ${r.status}`.toLowerCase(); return words.every(w => hay.includes(w)); };

/* The text with every typed word wrapped in <mark>, built from text nodes. Overlapping hits keep the first. */
function withMarks(text, words) {
  const low = text.toLowerCase(), hits = [];
  for (const w of words) for (let i = low.indexOf(w); i >= 0; i = low.indexOf(w, i + w.length)) hits.push([i, i + w.length]);
  hits.sort((a, b) => a[0] - b[0]);
  const out = []; let at = 0;
  for (const [s, e] of hits) { if (s < at) continue; if (s > at) out.push(text.slice(at, s)); out.push(el("mark", {}, text.slice(s, e))); at = e; }
  if (at < text.length) out.push(text.slice(at));
  return out;
}

function fillResults(box, rows, query) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) { box.replaceChildren(); return; }
  const found = rows.filter(r => matchesAll(r, words)).sort((a, b) => b.date.localeCompare(a.date));
  if (!found.length) {
    box.replaceChildren(el("p", { class: "kempty" }, `No application matches “${query.trim()}”. Try part of a company name, or a role such as “engineer”.`));
    return;
  }
  const title = r => r.url ? el("a", { href: r.url, target: "_blank", rel: "noopener" }, ...withMarks(r.title, words)) : el("span", {}, ...withMarks(r.title, words));
  box.replaceChildren(
    el("p", { class: "sub" }, `${found.length} application${found.length === 1 ? "" : "s"} found` + (found.length > 50 ? ", showing the newest 50" : "")),
    el("ul", { class: "slist" }, ...found.slice(0, 50).map(r => el("li", {},
      el("span", { class: "sc" }, ...withMarks(r.company, words)), el("span", { class: "stt" }, title(r)),
      el("span", { class: "sd" }, `applied ${shortDay(dayOf(r))}`), statusSelect(r)))));
}
