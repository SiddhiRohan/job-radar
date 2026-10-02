/* Agents view: what the agents wrote and found. Interview prep and follow-up drafts are written for you, by Claude
   with your API key or by a coding assistant without one; skill gaps and the sponsor map (agentfacts.js) are counted
   from your own records with no model. Text only, never innerHTML: all of it comes from postings and the model.
   Uses el, api, waitJob, toast and fail from app.js, which are defined before any of these functions run. */
const AG = { apps: [] };

async function loadAgents() {
  const body = $("#agents-body");
  try {
    const [r, apps] = await Promise.all([api("/api/agents"), api("/api/applied")]);
    AG.apps = apps;
    body.replaceChildren(agentsLead(r), el("div", { class: "vgrid" }, prepCard(r), followCard(r), gapsCard(r.gaps), sponsorCard(r.sponsors)));
  } catch (e) { fail(body, e, loadAgents); }
}

/* Run the writing agents, or one of them for one application, then show what they wrote. */
async function runAgents(btn, body, label) {
  btn.disabled = true; const was = btn.textContent; btn.textContent = "Writing";
  try {
    const r = await waitJob((await api("/api/agents/run", body)).job_id);
    const errors = Object.values(r).flatMap(x => x.errors);
    toast(errors.length ? `${label}: ${errors[0]}` : `${label}: done`); loadAgents();
  } catch (e) { toast(`${label} failed: ${e.message}`); btn.disabled = false; btn.textContent = was; }
}

function agentsLead(r) {
  const run = el("button", { type: "button", class: "primary", onclick: () => runAgents(run, {}, "Agents") }, "Run the agents now");
  if (!r.key) run.disabled = true;
  const waiting = r.prep.due + r.followups.due;
  const say = r.key
    ? `They run every morning after the radar. ${waiting ? `${waiting} waiting to be written.` : "Nothing is waiting."}`
    : "No API key, so prep and follow-ups wait: add one on Setup, or run /radar-agents in Claude Code or another coding assistant.";
  return el("div", { class: "agents-lead" }, el("p", {}, "Four agents work from your own records. ", say), run);
}

/* ---------- interview prep ---------- */
function prepCard(r) {
  const card = el("section", { class: "card wide" }, el("h3", {}, "Interview prep"),
    el("p", { class: "sub" }, "Written when an email moves an application to a screen or an interview. Stories use only your resume; a number it cannot find there shows as [?]."));
  const pick = el("select", { "aria-label": "Application to prepare for" },
    ...AG.apps.slice().sort((a, b) => b.date.localeCompare(a.date)).map(a => el("option", { value: `${a.company}|${a.req_id}` }, `${a.company}, ${a.title} (${a.status})`)));
  const write = el("button", { type: "button", onclick: () => {
    const [company, req_id] = pick.value.split("|");
    runAgents(write, { name: "prep", company, req_id }, `Prep for ${company}`);
  } }, "Write prep");
  if (!r.key || !AG.apps.length) write.disabled = true;
  card.append(el("div", { class: "prepform" }, el("span", { class: "sub" }, "Prepare for any application:"), pick, write));
  if (!r.prep.items.length) card.append(el("p", { class: "kempty" }, "No screens or interviews yet. When an email brings one, its prep is here the next morning."));
  r.prep.items.forEach((p, i) => card.append(prepItem(p, i === 0)));
  return card;
}

function prepItem(rec, open) {
  const p = rec.prep, sec = (title, ...kids) => [el("h4", {}, title), ...kids];
  const stage = { screen: "recruiter screen", interview: "interview" }[rec.stage] || "first screen";
  return el("details", { class: "prep", ...(open ? { open: "" } : {}) },
    el("summary", {}, el("b", {}, rec.company), ` ${rec.title}`, el("span", { class: "stage" }, stage), el("span", { class: "sub" }, `made ${rec.made}`)),
    el("div", { class: "pbody" },
      el("p", {}, p.role),
      ...sec("What they will probe", el("ul", {}, ...p.focus.map(f => el("li", {}, el("b", {}, f.topic), ` ${f.why}`, el("span", { class: "from" }, f.evidence ? `Your evidence: ${f.evidence}` : "Nothing on your resume shows this yet."))))),
      ...sec("Likely questions", el("ol", {}, ...p.questions.map(q => el("li", {}, q.question, el("span", { class: "from" }, `${q.kind}: ${q.answer_from}`))))),
      ...sec("Stories from your resume", ...p.stories.map(s => el("div", { class: "story" }, el("b", {}, s.title),
        ...["situation", "task", "action", "result"].map(k => el("span", { class: "from" }, `${k[0].toUpperCase() + k.slice(1)}: ${s[k]}`))))),
      ...(p.gaps.length ? sec("Gaps, and how to answer them", el("ul", {}, ...p.gaps.map(g => el("li", {}, el("b", {}, g.gap.replace(/\.$/, "")), `: ${g.answer}`)))) : []),
      ...sec("Ask them", el("ul", {}, ...p.ask_them.map(q => el("li", {}, q)))),
      ...sec("Work authorization", el("p", { class: "auth" }, p.work_authorization)),
      rec.notes.length ? el("ul", { class: "pnotes" }, ...rec.notes.map(n => el("li", {}, n))) : null));
}

/* ---------- follow-ups ---------- */
function followCard(r) {
  const card = el("section", { class: "card wide" }, el("h3", {}, "Follow-ups"),
    el("p", { class: "sub" }, "Drafts for applications quiet for ten days whose posting is still up. Nothing is sent: copy one, send it yourself, then mark it sent."));
  if (!r.followups.items.length) card.append(el("p", { class: "kempty" }, r.followups.due ? `${r.followups.due} quiet applications wait for a draft.` : "No follow-ups waiting."));
  for (const f of r.followups.items) card.append(followItem(f));
  return card;
}

function followItem(f) {
  const d = f.draft;
  const copy = (text, what) => el("button", { type: "button", class: "quiet", onclick: async () => {
    try { await navigator.clipboard.writeText(text); toast(`${what} copied`); } catch (e) { toast("Copy is blocked here: select the text instead"); }
  } }, `Copy ${what.toLowerCase()}`);
  const done = how => el("button", { type: "button", onclick: async () => {
    try { await api("/api/agents/followups/done", { key: f.key, how }); toast(how === "sent" ? "Marked sent" : "Dismissed"); loadAgents(); }
    catch (e) { toast(`Could not save: ${e.message}`); }
  } }, how === "sent" ? "Mark sent" : "Dismiss");
  const find = el("a", { href: `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(d.search_hint)}`, target: "_blank", rel: "noopener" }, `Search LinkedIn: ${d.search_hint}`);
  return el("div", { class: "mailitem" },
    el("div", { class: "mailmeta" }, el("b", {}, f.company), el("span", {}, f.title), el("span", {}, `applied ${f.applied}`), find),
    el("div", { class: "draft" }, d.linkedin_note), el("div", { class: "mailacts" }, copy(d.linkedin_note, "Note"), el("span", { class: "sub" }, `${d.linkedin_note.length} of 300 characters`)),
    el("div", { class: "draft" }, el("b", {}, d.email_subject), "\n\n", d.email_body),
    el("div", { class: "mailacts" }, copy(`${d.email_subject}\n\n${d.email_body}`, "Email"), done("sent"), done("dismissed")),
    f.notes.length ? el("ul", { class: "pnotes" }, ...f.notes.map(n => el("li", {}, n))) : null);
}
