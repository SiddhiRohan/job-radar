/* Filter audit card on the Agents view: what the title, seniority, domain and location rules dropped this week, the
   dropped postings worth a look, and the config.json changes that would have kept them. A change is made only when
   the person presses Apply. Text only, never innerHTML. Uses el, api, waitJob and toast from app.js and loadAgents
   from agents.js. */
const DROPPED = {
  off_target: "titles naming no target role", seniority: "senior titles", domain: "domain words", non_us: "outside the US",
  sponsorship_no: "skipped for sponsorship wording", years_gate: "skipped for six or more years",
};

function auditCard(r) {
  const a = r.audit;
  const week = Object.entries(a.dropped || {}).sort((x, y) => y[1] - x[1]).map(([k, n]) => `${n} ${DROPPED[k] || k}`).join(", ");
  const card = el("section", { class: "card wide" }, el("h3", {}, "Filter audit"),
    el("p", { class: "sub" }, `Once a week a sample of what your rules dropped goes to the model, which names the postings you would have wanted and the change that would have kept them. Dropped in the last week: ${week || "nothing logged yet; the log starts with the next run"}.`));
  const run = el("button", { type: "button", onclick: async () => {
    run.disabled = true; run.textContent = "Auditing";
    try {
      const out = await waitJob((await api("/api/agents/audit/run", {})).job_id), err = out.audit?.errors?.[0];
      toast(err ? `Audit: ${err}` : "Audit written"); loadAgents();
    } catch (e) { toast(`Audit: ${e.message}`); run.disabled = false; run.textContent = "Audit now"; }
  } }, "Audit now");
  if (!r.key) run.disabled = true;
  card.append(el("div", { class: "mailacts" }, run, el("span", { class: "sub" }, a.made ? `Last audit ${a.made}, of what was dropped since ${a.since}` : "No audit yet")));
  if (!a.made) return card;
  card.append(el("p", {}, a.summary));
  if (a.wanted.length) card.append(el("h4", { class: "minor" }, "Dropped, but probably worth seeing"),
    el("ul", { class: "mailevents" }, ...a.wanted.map(w => el("li", {}, el("b", {}, w.company), " ",
      w.url ? el("a", { href: w.url, target: "_blank", rel: "noopener" }, w.title) : w.title,
      el("span", { class: "sub" }, ` (${DROPPED[w.reason] || w.reason}${w.count > 1 ? `, ${w.count} postings` : ""}) `), w.why))));
  if (a.changes.length) card.append(el("h4", { class: "minor" }, "Changes that would have kept them"),
    el("ul", { class: "fixes" }, ...a.changes.map((c, i) => {
      const done = (a.applied || []).includes(i);
      const btn = el("button", { type: "button", onclick: async () => {
        btn.disabled = true;
        try { toast((await api("/api/agents/audit/apply", { n: i })).result); loadAgents(); }
        catch (e) { toast(`Could not apply: ${e.message}`); btn.disabled = false; }
      } }, done ? "Applied" : "Apply");
      if (done) btn.disabled = true;
      return el("li", {}, el("code", {}, `${c.setting}: ${c.action} "${c.value}"`), el("span", {}, c.why), btn);
    })));
  if ((a.notes || []).length) card.append(el("ul", { class: "pnotes" }, ...a.notes.map(n => el("li", {}, n))));
  return card;
}
