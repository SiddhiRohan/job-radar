/* Interview debrief card on the Agents view: say how a screen or interview went, and an agent writes what was asked
   and how each answer could be stronger, what the interviewer seemed unsure about, what you said you would send, what
   to prepare next, and a thank-you note. The next prep for that role reads it. Text only, never innerHTML.
   Uses el, api, waitJob and toast from app.js, and AG and loadAgents from agents.js. */
function debriefCard(r) {
  const card = el("section", { class: "card wide" }, el("h3", {}, "Interview debrief"),
    el("p", { class: "sub" }, "Right after a screen or an interview, say how it went: what they asked, how you answered, what they seemed unsure about, names. Numbers stay to what you said and your resume."));
  const staged = AG.apps.filter(a => a.status === "screen" || a.status === "interview");
  const rest = AG.apps.filter(a => !staged.includes(a)).sort((a, b) => b.date.localeCompare(a.date));
  const pick = el("select", { "aria-label": "The application the interview was for" },
    ...[...staged, ...rest].map(a => el("option", { value: `${a.company}|${a.req_id}` }, `${a.company}, ${a.title} (${a.status})`)));
  const account = el("textarea", { rows: "5", "aria-label": "How it went", placeholder: "They asked ... I answered ... They seemed unsure about ... I said I would send ..." });
  const go = el("button", { type: "button", class: "primary", onclick: async () => {
    const [company, req_id] = pick.value.split("|");
    if (!account.value.trim()) { toast("Say how it went first"); return; }
    go.disabled = true; go.textContent = "Writing";
    try {
      const res = await api("/api/agents/debrief", { company, req_id, account: account.value });
      if (res.job_id) {
        const out = await waitJob(res.job_id), err = out.debrief?.errors?.[0];
        toast(err ? `Debrief: ${err}` : "Debrief written");
      } else toast(`Kept your account. ${res.note}`);
      loadAgents();
    } catch (e) { toast(`Debrief: ${e.message}`); go.disabled = false; go.textContent = "Write debrief"; }
  } }, "Write debrief");
  if (!AG.apps.length) go.disabled = true;
  const waiting = r.debriefs.waiting;
  card.append(el("div", { class: "debform" }, pick, account,
    el("div", { class: "mailacts" }, go, waiting ? el("span", { class: "sub" }, `${waiting} account${waiting === 1 ? "" : "s"} waiting for a debrief`) : null)));
  r.debriefs.items.forEach((d, i) => card.append(debriefItem(d, i === 0)));
  return card;
}

function debriefItem(rec, open) {
  const d = rec.debrief, sec = (title, ...kids) => [el("h4", {}, title), ...kids];
  const note = `${d.thank_you_subject}\n\n${d.thank_you_body}`;
  const copy = el("button", { type: "button", class: "quiet", onclick: async () => {
    try { await navigator.clipboard.writeText(note); toast("Thank-you note copied"); } catch (e) { toast("Copy is blocked here: select the text instead"); }
  } }, "Copy the thank-you note");
  return el("details", { class: "prep", ...(open ? { open: "" } : {}) },
    el("summary", {}, el("b", {}, rec.company), ` ${rec.title}`, el("span", { class: "stage" }, `round ${rec.round}, ${rec.stage}`), el("span", { class: "sub" }, rec.added.slice(0, 10))),
    el("div", { class: "pbody" },
      el("p", {}, d.summary),
      ...sec("What they asked", el("ol", {}, ...d.asked.map(a => el("li", {}, a.question, el("span", { class: `went ${a.went}` }, a.went),
        a.better ? el("span", { class: "from" }, `Try saying: ${a.better}`) : null)))),
      ...(d.concerns.length ? sec("They seemed unsure about", el("ul", {}, ...d.concerns.map(c => el("li", {}, el("b", {}, c.concern.replace(/\.$/, "")), `: ${c.address}`)))) : []),
      ...(d.owed.length ? sec("You said you would send", el("ul", {}, ...d.owed.map(x => el("li", {}, x)))) : []),
      ...sec("Keep doing", el("ul", {}, ...d.went_well.map(x => el("li", {}, x)))),
      ...sec("For the next round", el("ul", {}, ...d.next_round.map(x => el("li", {}, x)))),
      ...sec("Thank-you note", el("div", { class: "draft" }, el("b", {}, d.thank_you_subject), "\n\n", d.thank_you_body), el("div", { class: "mailacts" }, copy)),
      rec.notes.length ? el("ul", { class: "pnotes" }, ...rec.notes.map(n => el("li", {}, n))) : null));
}
