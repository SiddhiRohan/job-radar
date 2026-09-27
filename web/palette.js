/* Command palette: Ctrl+K (Cmd+K) opens a search over views, days, actions and today's postings. Anything that
   matches nothing is sent to the assistant. Loads after app.js and uses its helpers (T, api, waitJob, toast,
   setChat, sendChat, runRadar, loadToday, loadApplied, setCur). */
const P = { items: [], hits: [], sel: 0 };
const cmdk = () => $("#cmdk");

/* Score a query against a label: exact substring first, then in-order characters. 0 means no match. */
function match(q, label) {
  const l = label.toLowerCase(), i = l.indexOf(q);
  if (i >= 0) return 100 - i - (l.length - q.length) / 40;
  let j = 0;
  for (const ch of q) { j = l.indexOf(ch, j); if (j < 0) return 0; j++; }
  return 20 - l.length / 40;
}

function goToday(date, then) {
  if (date && date !== T.date) { T.date = date; loadToday().then(then); } else if (then) then();
  if ((location.hash || "#today") !== "#today") location.hash = "today";
}
const jobRun = async (path, label) => {
  toast(`${label} started`);
  try { await waitJob((await api(path, {})).job_id); toast(`${label} finished`); loadApplied(); }
  catch (e) { toast(`${label} failed: ${e.message}`); }
};

/* Built when the palette opens, so days and postings are always the ones on the page. */
function buildItems() {
  const items = [
    { g: "Go", label: "Today", run: () => (location.hash = "today") },
    { g: "Go", label: "Tailor", run: () => (location.hash = "tailor") },
    { g: "Go", label: "Applied", run: () => (location.hash = "applied") },
    { g: "Do", label: "Run the radar", hint: "poll, score, digest", run: () => runRadar(1, false) },
    { g: "Do", label: "Check mail", hint: "statuses from hiring emails", run: () => jobRun("/api/mail/sync", "Mail check") },
    { g: "Do", label: "Check postings", hint: "closed or changed since you applied", run: () => jobRun("/api/watch/run", "Posting check") },
    { g: "Do", label: "New chat thread", run: () => $("#chatnew").click() },
    { g: "Do", label: "Keyboard shortcuts", run: () => $("#keys").showModal() },
    { g: "Look", label: "Accent: Teal", run: () => setAccent("") },
    { g: "Look", label: "Accent: Indigo", run: () => setAccent("indigo") },
    { g: "Look", label: "Accent: Rust", run: () => setAccent("rust") },
  ];
  for (const d of T.dates || []) items.push({ g: "Day", label: d, run: () => goToday(d) });
  const rows = Object.values(T.last?.sections || {}).flat();
  for (const r of rows) {
    items.push({ g: "Posting", label: `${r.company}, ${r.title}`, hint: r.location, run: () => goToday(null, () => {
      const row = [...document.querySelectorAll("#today-body article.row")].find(x => x.dataset.company === r.company && x.querySelector(".title")?.textContent === r.title);
      if (row) { row.closest("details")?.setAttribute("open", ""); setCur(row); openDrawer(r, row); }
    }) });
  }
  return items;
}

function renderHits(q) {
  const list = $("#cmdk-list");
  q = q.trim().toLowerCase();
  P.hits = q
    ? P.items.map(it => ({ it, s: match(q, it.label) })).filter(x => x.s > 0).sort((a, b) => b.s - a.s).slice(0, 12).map(x => x.it)
    : P.items.filter(it => it.g !== "Posting").slice(0, 12);
  if (q) P.hits.push({ g: "Ask", label: `Ask the assistant: ${q}`, run: () => { setChat(true); sendChat(q).then(loadThreads); } });
  P.sel = 0;
  list.replaceChildren(...P.hits.map((it, i) => el("li", { role: "option", "aria-selected": String(i === 0), "data-i": String(i),
    onclick: () => choose(i), onmousemove: () => select(i) },
    el("span", { class: "cg" }, it.g), el("span", { class: "cl" }, it.label), it.hint ? el("span", { class: "ch" }, it.hint) : null)));
}
function select(i) {
  P.sel = i;
  $("#cmdk-list").querySelectorAll("li").forEach((li, j) => li.setAttribute("aria-selected", String(j === i)));
  $("#cmdk-list").children[i]?.scrollIntoView({ block: "nearest" });
}
function choose(i) { const it = P.hits[i]; cmdk().close(); if (it) it.run(); }
function openPalette() {
  P.items = buildItems();
  const inp = $("#cmdk-in"); inp.value = ""; renderHits("");
  cmdk().showModal(); inp.focus();
}

document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); cmdk().open ? cmdk().close() : openPalette(); }
});
$("#cmdk-in").addEventListener("input", e => renderHits(e.target.value));
$("#cmdk-in").addEventListener("keydown", e => {
  if (e.key === "ArrowDown") { e.preventDefault(); select(Math.min(P.hits.length - 1, P.sel + 1)); }
  else if (e.key === "ArrowUp") { e.preventDefault(); select(Math.max(0, P.sel - 1)); }
  else if (e.key === "Enter") { e.preventDefault(); choose(P.sel); }
});
cmdk().addEventListener("click", e => { if (e.target === cmdk()) cmdk().close(); });  /* backdrop click closes */
$("#cmdkbtn").addEventListener("click", openPalette);
