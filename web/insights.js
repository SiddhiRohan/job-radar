/* Insight card on Applied: the postings behind open applications. Uses el, api, waitJob, toast and loadApplied from app.js. */
/* watchCard: postings behind open applications that closed or changed since applying. */
function watchCard() {
  const card = el("section", { class: "card wide" }, el("h3", {}, "Postings since you applied"), el("p", { class: "sub" }, "Loading"));
  api("/api/watch").then(r => fillWatch(card, r)).catch(e => card.replaceChildren(el("h3", {}, "Postings since you applied"), el("p", { class: "error" }, e.message)));
  return card;
}

function fillWatch(card, r) {
  const check = el("button", { type: "button", onclick: async () => {
    check.disabled = true; check.textContent = "Checking";
    try { await waitJob((await api("/api/watch/run", {})).job_id); loadApplied(); }
    catch (e) { toast(`Could not check postings: ${e.message}`); check.disabled = false; check.textContent = "Check postings"; }
  } }, "Check postings");
  const head = el("div", { class: "mailhead" }, el("div", {}, el("h3", {}, "Postings since you applied"),
    el("p", { class: "sub" }, r.last_run ? `${r.open} still open, ${r.closed.length} closed, ${r.changed.length} changed. Last checked ${r.last_run}.` : "Not checked yet; runs with the morning radar.")), check);
  const days = d => Math.max(0, Math.round((Date.now() - new Date(d + "T12:00")) / 864e5));
  const item = (p, note) => el("li", {}, el("b", {}, p.company), `, ${p.title}: `, note);
  const closed = r.closed.length ? [el("h4", {}, "Closed with no reply", el("span", { class: "n" }, String(r.closed.length))),
    el("ul", { class: "mailevents" }, ...r.closed.map(p => item(p, `posting gone since ${p.closed_since}, ${days(p.applied)} days after you applied`)))] : [];
  const changed = r.changed.length ? [el("h4", {}, "Changed", el("span", { class: "n" }, String(r.changed.length))),
    el("ul", { class: "mailevents" }, ...r.changed.map(p => item(p, p.changes.map(c => `${c.what} (${c.date})`).join("; "))))] : [];
  card.replaceChildren(head, ...closed, ...changed, (!closed.length && !changed.length && r.last_run) ? el("p", { class: "kempty" }, "Every open application's posting is still up and unchanged.") : null);
}
