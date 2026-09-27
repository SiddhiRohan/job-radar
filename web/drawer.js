/* Posting drawer: click a row on Today (or press Enter on the keyboard cursor) and the stored description opens in a
   sheet on the right, with the pay sentence and the sponsorship phrase highlighted. Loads after app.js and uses its
   helpers (api, el, toast, startTailor, setCur, K). Nothing here calls Workday: the text is what the poll stored. */
const D = { key: null, row: null };
const drawer = () => $("#drawer");

/* Split plain text into paragraphs, wrapping every occurrence of the given phrases in <mark>. */
function paragraphs(text, marks) {
  const out = [];
  for (const para of (text || "").split(/\n{2,}/)) {
    const lines = para.split("\n").filter(l => l.trim());
    if (!lines.length) continue;
    const isList = lines.every(l => l.trim().startsWith("- "));
    const node = isList ? el("ul", {}, ...lines.map(l => el("li", {}, ...marked(l.trim().slice(2), marks)))) : el("p", {}, ...marked(lines.join(" "), marks));
    out.push(node);
  }
  return out;
}
function marked(s, marks) {
  const hits = marks.filter(m => m.text && s.includes(m.text)).map(m => ({ i: s.indexOf(m.text), ...m })).sort((a, b) => a.i - b.i);
  const parts = []; let pos = 0;
  for (const h of hits) {
    if (h.i < pos) continue;
    parts.push(s.slice(pos, h.i), el("mark", { class: h.cls, title: h.title }, h.text)); pos = h.i + h.text.length;
  }
  parts.push(s.slice(pos));
  return parts;
}

async function openDrawer(r, row) {
  D.key = r.key || `${r.company}|${r.req_id}`; D.row = row || null;
  document.querySelectorAll("#today-body article.row.sel").forEach(x => x.classList.remove("sel"));
  row?.classList.add("sel");
  const d = drawer();
  d.hidden = false; document.body.classList.add("has-drawer");
  $("#d-title").textContent = r.title;
  $("#d-facts").replaceChildren(el("b", {}, r.company), el("span", {}, r.location || ""), el("span", {}, r.req_id), el("span", {}, r.posted_on || ""));
  $("#d-body").replaceChildren(el("p", { class: "dim" }, "Loading the posting"));
  $("#d-open").href = r.url || "#";
  try {
    const p = await api(`/api/posting?company=${encodeURIComponent(r.company)}&req_id=${encodeURIComponent(r.req_id)}`);
    if (D.key !== (p.key || `${p.company}|${p.req_id}`)) return;  /* another row was clicked meanwhile */
    const marks = [
      { text: p.pay_sentence, cls: "pay", title: p.salary ? `Pay: ${p.salary.text}` : "Pay" },
      { text: p.evidence, cls: "spon", title: `Sponsorship: ${p.sponsorship || "unknown"}` },
    ];
    const facts = [el("b", {}, p.company), el("span", {}, p.location || ""), el("span", {}, p.req_id), el("span", {}, p.posted_on || "")];
    if (p.years_required != null) facts.push(el("span", {}, `${p.years_required}+ years asked`));
    if (p.salary) facts.push(el("span", { class: "pay" }, p.salary.text));
    facts.push(el("span", { class: `tag ${p.sponsorship || "unknown"}` }, p.sponsorship || "unknown"));
    $("#d-facts").replaceChildren(...facts);
    $("#d-body").replaceChildren(p.why ? el("p", { class: "dwhy" }, p.why) : null, ...paragraphs(p.description, marks));
    $("#d-body").scrollTop = 0;
  } catch (e) { $("#d-body").replaceChildren(el("p", { class: "error" }, e.message)); }
}
function closeDrawer() {
  drawer().hidden = true; document.body.classList.remove("has-drawer");
  D.row?.classList.remove("sel"); D.key = D.row = null;
}
const drawerOpen = () => !drawer().hidden;

$("#d-close").addEventListener("click", closeDrawer);
$("#d-apply").addEventListener("click", () => D.row?.querySelector("button.apply")?.click());
$("#d-tailor").addEventListener("click", () => { const [company, req_id] = D.key.split("|"); location.hash = "tailor"; startTailor({ company, req_id }); });
/* Rows: a click anywhere but a link, button or select opens the drawer; Enter on the keyboard cursor does the same. */
$("#today-body").addEventListener("click", e => {
  const row = e.target.closest("article.row"); if (!row || e.target.closest("a, button, select")) return;
  const r = row.__row; if (r) openDrawer(r, row);
});
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && K.cur && !e.target.matches("input, textarea, select, button, a, [contenteditable]") && (location.hash || "#today") === "#today") { e.preventDefault(); openDrawer(K.cur.__row, K.cur); }
});
addEventListener("hashchange", () => { if ((location.hash || "#today") !== "#today" && drawerOpen()) closeDrawer(); });
