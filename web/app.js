"use strict";
const $ = (s, r = document) => r.querySelector(s);
const el = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) e.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined) e.append(k.nodeType ? k : document.createTextNode(k));
  return e;
};
const api = async (path, body) => {
  const r = await fetch(path, body ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) } : {});
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `${r.status} from ${path}`);
  return r.json();
};
const waitJob = async (id, onTick) => {
  for (;;) {
    const s = await api(`/jobs/${id}`);
    if (s.status === "done") return s.result;
    if (s.status === "error") throw new Error(s.error);
    onTick && onTick();
    await new Promise(res => setTimeout(res, 1500));
  }
};
let toastTimer;
const toast = msg => { const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 4000); };
const fail = (where, e, retry) => {
  const offline = /Failed to fetch|NetworkError|Load failed/.test(e.message);
  const msg = offline ? "The server is not answering. Start it with: python server.py (in the job-radar folder), then retry."
    : `${e.message}. Check the server terminal, then retry.`;
  where.replaceChildren(el("p", { class: "error" }, msg, " ", retry ? el("button", { type: "button", onclick: retry }, "Retry") : null));
  if (offline && retry) setTimeout(() => { if (where.querySelector(".error")) retry(); }, 5000);
};

/* ---------- Today ---------- */
const T = { date: "", dates: [], open: new Set() };
const best = r => Math.max(r.score_entry || 0, r.score_experienced || 0);
const scorePair = r => {
  const rec = r.recommended_resume;
  const E = el(rec === "entry" ? "b" : "span", {}, `E${r.score_entry ?? "-"}`), X = el(rec === "experienced" ? "b" : "span", {}, `X${r.score_experienced ?? "-"}`);
  return el("span", { class: "pair-score" }, E, " / ", X);
};
const variant = r => r.recommended_resume ? `${r.recommended_resume}${r.recommended_variant ? ", " + r.recommended_variant.split("/").pop() : ""}` : "";
const tag = r => el("span", { class: `tag ${r.sponsorship || "unknown"}`, title: r.evidence || "no phrase found in the posting" }, r.sponsorship || "unknown");
function rowEl(r) {
  const done = r.applied;
  /* Update this row in place: reloading the list closed the collapsed sections and lost the scroll position. */
  const applyBtn = el("button", { type: "button", onclick: async () => {
    applyBtn.disabled = true;
    try {
      await api("/api/applied", { company: r.company, req_id: r.req_id, title: r.title });
      r.applied = true; row.classList.add("done"); applyBtn.textContent = "Applied";
      toast(`Marked applied: ${r.company}, ${r.title}`);
    } catch (e) { applyBtn.disabled = false; toast(`Could not mark applied: ${e.message}`); }
  } }, done ? "Applied" : "Mark applied");
  if (done) applyBtn.disabled = true;
  const row = el("article", { class: "row" + (done ? " done" : "") },
    el("div", { class: "score", "data-s": String(best(r)), "aria-label": `best score ${best(r) || "none"}` }, String(best(r) || "–")),
    el("div", {},
      el("div", { class: "head" }, el("span", { class: "company" }, r.company), el("span", { class: "title" }, r.title),
        el("span", { class: "meta" }, r.location), el("span", { class: "meta" }, r.posted_on)),
      el("div", { class: "sub" }, scorePair(r), el("span", {}, variant(r)), tag(r),
        el("a", { href: r.url, target: "_blank", rel: "noopener" }, "Open posting"),
        el("div", { class: "acts" }, applyBtn)),
      r.why ? el("p", { class: "why" }, r.why) : null));
  return row;
}
function sectionEl(name, cls, rows, collapsed) {
  const h = el("h2", { class: cls }, name, el("span", { class: "n" }, String(rows.length)));
  const body = rows.length ? rows.map(rowEl) : [el("p", { class: "empty" }, "Nothing here today.")];
  if (!collapsed) return [h, ...body];
  /* Remember which collapsed sections are open so a refresh, a date change or the end of a run keeps them open. */
  const d = el("details", { open: T.open.has(name) ? "" : null }, el("summary", {}, h), ...body);
  d.addEventListener("toggle", () => { if (d.open) T.open.add(name); else T.open.delete(name); });
  return [d];
}
async function loadToday() {
  const body = $("#today-body");
  try {
    const d = await api(`/api/today?date=${T.date}`);
    T.date = d.date; T.dates = d.dates; T.last = d;
    const sel = $("#date"); sel.replaceChildren(...d.dates.map(x => el("option", { value: x, selected: x === d.date ? "" : null }, x)));
    $("#datectl").hidden = false;
    $("#stats").textContent = d.stats || (d.date ? "No run stats for this date; the header only covers the latest run." : "");
    if (!d.date) { body.replaceChildren(el("p", { class: "empty" }, "No digest yet. Run the radar (python run.py) and reload.")); return; }
    const s = d.sections;
    if (!Object.values(s).some(v => v.length)) { body.replaceChildren(el("p", { class: "empty" }, "No digest for this date. Run the radar or pick another day.")); return; }
    body.replaceChildren(...sectionEl("Apply", "apply", s.apply),
      ...sectionEl("Entry level", "entry", s.entry || []), ...sectionEl("Maybe", "maybe", s.maybe),
      ...sectionEl("Contract or backup", "contract", s.contract), ...sectionEl("Everything else", "lower", s.lower, true),
      ...sectionEl("Skipped for sponsorship", "lower", s.skipped || [], true));
  } catch (e) { fail(body, e, loadToday); }
}
$("#date").addEventListener("change", e => { T.date = e.target.value; loadToday(); });
$("#prev").addEventListener("click", () => { const i = T.dates.indexOf(T.date); if (i < T.dates.length - 1) { T.date = T.dates[i + 1]; loadToday(); } });
$("#next").addEventListener("click", () => { const i = T.dates.indexOf(T.date); if (i > 0) { T.date = T.dates[i - 1]; loadToday(); } });

/* ---------- Tailor ---------- */
const S = { state: null, build: null, cover: null, revision: 0 };
const words = s => s.split(/(\s+)/);
function diffSpans(base, text) {
  // word-level LCS; words not in the common subsequence are wrapped as changed. ** bold markers become <b>.
  const a = words(base).filter(w => w.trim()), b = words(text);
  const bw = b.filter(w => w.trim());
  const n = a.length, m = bw.length, L = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = a[i] === bw[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const keep = new Set(); let i = 0, j = 0;
  while (i < n && j < m) { if (a[i] === bw[j]) { keep.add(j); i++; j++; } else if (L[i + 1][j] >= L[i][j + 1]) i++; else j++; }
  const frag = document.createDocumentFragment(); let bold = false, k = 0;
  for (const w of b) {
    if (!w.trim()) { frag.append(w); continue; }
    const parts = w.split("**");
    parts.forEach((p, idx) => {
      if (idx) bold = !bold;
      if (!p) return;
      const node = bold ? el("b", {}, p) : document.createTextNode(p);
      frag.append(keep.has(k) ? node : el("span", { class: "chg" }, node));
    });
    k++;
  }
  return frag;
}
const plain = node => { // contenteditable back to ** text
  let out = "";
  node.childNodes.forEach(c => { if (c.nodeType === 3) out += c.textContent; else if (c.tagName === "B") out += `**${c.textContent}**`; else if (c.tagName === "BR") out += "\n"; else out += plain(c); });
  return out;
};
function reply(text) {
  // bold via ** and [label](http...) links; everything else stays literal text
  const frag = document.createDocumentFragment();
  const re = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    frag.append(diffSpans(text.slice(last, m.index), text.slice(last, m.index)));
    frag.append(el("a", { href: m[2], target: "_blank", rel: "noopener" }, m[1]));
    last = m.index + m[0].length;
  }
  frag.append(diffSpans(text.slice(last), text.slice(last)));
  return frag;
}
function editCell(base, text, onchange) {
  const cell = el("div", { class: "edit", contenteditable: "true", spellcheck: "false" });
  cell.append(diffSpans(base, text));
  cell.addEventListener("blur", () => { const t = plain(cell).trim(); onchange(t); cell.replaceChildren(diffSpans(base, t)); });
  return cell;
}
function renderTailor(st) {
  const revision = ++S.revision;
  S.state = st; S.build = null; S.cover = null;
  const body = $("#tailor-body"); const j = st.job;
  const v = el("div", { class: "verdict" },
    el("span", { class: "big" }, scorePair(j)), el("span", {}, `${st.base_label}`),
    el("span", {}, tag(j), " ", el("span", { class: "meta" }, j.evidence ? `"${j.evidence.slice(0, 90)}"` : "no phrase found")),
    el("span", {}, st.years_required != null ? `${st.years_required}+ years` : "years not stated"),
    el("span", {}, st.platform_tools.length ? `Platform tools missing: ${st.platform_tools.join(", ")}` : "No platform-tool gaps"),
    el("span", {}, j.cover ? "Cover letter required" : "Cover letter not required"),
    st.skip ? el("span", { class: "skip" }, `The assessment says skip: ${st.assessment.filter(x => x.startsWith("SKIP")).join("; ")}. You can still continue.`) : null);
  const jd = el("div", { class: "jdskills" }, st.jd_skills.length ? "JD asks for:" : "JD asks for nothing outside your confirmed skills.",
    ...st.jd_skills.map(s => el("label", {}, el("input", { type: "checkbox", onchange: async e => {
      if (e.target.checked) { await api("/api/tailor/confirm", { skill: s, used: true }); toast(`Confirmed ${s}, re-planning`); startTailor({ company: j.company, req_id: j.req_id, fresh: true }); }
    } }), s)));
  const secs = st.sections.map(sec => {
    const wrap = el("div", { class: "sec" }, el("h3", {}, sec.label));
    sec.text.forEach((t, n) => {
      const b = sec.base[sec.order ? sec.order[n] : n];
      const pair = el("div", { class: "pair" }, el("div", { class: "base" }, diffSpans(b, b)),
        el("div", {}, sec.moved && sec.moved[n] ? el("span", { class: "moved" }, "moved") : null, editCell(sec.base[sec.order ? sec.order[n] : n], t, val => { sec.text[n] = val; })));
      (sec.notes && sec.notes[String(n)] || []).forEach(x => pair.append(el("div", { class: "note" }, x)));
      wrap.append(pair);
    });
    return wrap;
  });
  const gen = st.general_notes.length ? el("div", { class: "sec" }, el("h3", {}, "Open questions"), ...st.general_notes.map(x => el("p", { class: "note" }, x))) : null;
  const files = el("div", { class: "files" });
  const coverBox = el("div", { class: "cover" });
  const outreachBox = el("div", { class: "outreach" });
  let outreachEditors = null;
  const outreachBtn = el("button", { type: "button", onclick: async () => {
    if (outreachBtn.disabled || revision !== S.revision) return;
    outreachBtn.disabled = true;
    // Read the visible editors even if the focused cell has not blurred yet.
    const cells = [...body.querySelectorAll(".sec .edit")];
    let index = 0;
    const sections = st.sections.map(sec => ({ ...sec, text: sec.text.map(() => plain(cells[index++]).trim()) }));
    try {
      const result = await waitJob((await api("/api/tailor/outreach", { company: j.company, req_id: j.req_id, sections })).job_id);
      if (revision !== S.revision) return;
      const field = (key, label, isNote) => {
        const id = `outreach-${key}`;
        const count = el("p", { id: `${id}-count`, class: "meta", "aria-live": "polite" });
        const editor = el("textarea", { id, "aria-label": label, "aria-describedby": count.id }, result[key]);
        const update = () => {
          const n = isNote ? Array.from(editor.value).length : (editor.value.match(/\S+/g) || []).length;
          const valid = isNote ? n < 300 : n >= 100 && n <= 120;
          count.textContent = isNote ? `${n} characters · must be under 300` : `${n} words · 100–120 inclusive`;
          editor.setAttribute("aria-invalid", String(!valid));
        };
        editor.addEventListener("input", update); update();
        return { editor, nodes: [el("label", { for: id }, label), editor, count] };
      };
      const note = field("linkedin_note", "LinkedIn note", true);
      const message = field("message", "Outreach message", false);
      outreachEditors = { linkedin_note: note.editor, message: message.editor };
      outreachBox.replaceChildren(el("h3", {}, "Outreach"), ...note.nodes, ...message.nodes);
    } catch (e) {
      if (revision === S.revision) {
        toast(e.message);
      }
    } finally { outreachBtn.disabled = false; }
  } }, "Write outreach");
  const rebuild = el("button", { type: "button", class: "primary", onclick: async () => {
    rebuild.disabled = true; rebuild.textContent = "Rebuilding";
    try {
      const edits = Object.fromEntries(st.sections.map(s => [s.id, { text: s.text, order: s.order }]));
      const cover = S.cover !== null ? $("textarea", coverBox).value : null;
      S.build = await waitJob((await api("/api/tailor/rebuild", { state: st, edits, cover })).job_id);
      const id = S.build.dir.split(/[\\/]/).pop();
      files.replaceChildren(...S.build.files.map(f => el("a", { href: `/api/tailor/files/${id}/${encodeURIComponent(f)}` }, `Download ${f}`)));
      toast(`Rebuilt ${S.build.files.length} file(s)`);
    } catch (e) { toast(e.message); } finally { rebuild.disabled = false; rebuild.textContent = "Rebuild resume"; }
  } }, "Rebuild resume");
  const slug = j.title.replace(/[^A-Za-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);
  const dest = el("input", { class: "dest", value: `Resume/For ${j.company}/${j.req_id}_${slug}`, "aria-label": "Folder to save into", spellcheck: "false" });
  const browse = el("button", { type: "button", onclick: async () => {
    try { const r = await api("/api/pick-folder", { start: dest.value.split("/").slice(0, -1).join("/") }); if (r.path) dest.value = r.path; }
    catch (e) { toast(e.message); }
  } }, "Browse");
  const save = el("button", { type: "button", onclick: async () => {
    if (!S.build) return toast("Rebuild first, then save");
    const notes = [...st.general_notes, ...st.sections.flatMap(s => Object.values(s.notes || {}).flat())];
    try {
      const outreach = outreachEditors ? Object.fromEntries(Object.entries(outreachEditors).map(([key, editor]) => [key, editor.value])) : undefined;
      const r = await api("/api/tailor/save", { dir: S.build.dir, job: j, dest: dest.value.trim() || null, assessment: st.assessment, notes, outreach });
      toast(`Saved to ${r.folder}`);
    } catch (e) { toast(e.message); }
  } }, "Save to folder");
  const applied = el("button", { type: "button", onclick: async () => { await api("/api/applied", { company: j.company, req_id: j.req_id, title: j.title }); toast(`Marked applied: ${j.company}, ${j.title}`); } }, "Mark applied");
  const coverBtn = el("button", { type: "button", onclick: async () => {
    coverBtn.disabled = true;
    try { const r = await waitJob((await api("/api/tailor/cover", { company: j.company, req_id: j.req_id, sections: st.sections })).job_id);
      S.cover = r.text; coverBox.replaceChildren(el("h3", {}, "Cover letter"), el("textarea", {}, r.text)); toast("Wrote cover letter; edit it, then rebuild");
    } catch (e) { toast(e.message); } finally { coverBtn.disabled = false; }
  } }, j.cover ? "Write cover letter (required)" : "Write cover letter");
  body.replaceChildren(el("p", { class: "head" }, el("span", { class: "company" }, j.company), " ", el("span", { class: "title" }, j.title), " ", el("span", { class: "meta" }, j.req_id), " ",
    el("a", { href: j.url, target: "_blank", rel: "noopener" }, "Open posting")), v, jd, ...secs, gen, coverBox, outreachBox,
    el("div", { class: "actions" }, rebuild, save, dest, browse, applied, coverBtn, outreachBtn,
      el("button", { type: "button", class: "quiet", onclick: () => startTailor({ company: j.company, req_id: j.req_id, fresh: true }) }, "Re-plan")), files);
  body.classList.add("fresh"); setTimeout(() => body.classList.remove("fresh"), 600);
}
async function startTailor(req) {
  const revision = ++S.revision;
  S.state = null; S.build = null; S.cover = null;
  const body = $("#tailor-body");
  const what = req.url ? "Fetching the posting, scoring it if it is new, then planning the tailoring" : `Planning the tailoring for ${req.company}, ${req.req_id}`;
  const line = el("p", { class: "progress" }, what, ". Usually 30 to 60 seconds; a posting opened before comes back at once.");
  const clock = el("span", { class: "meta" }, " 0 s");
  const t0 = Date.now(), tick = setInterval(() => (clock.textContent = ` ${Math.round((Date.now() - t0) / 1000)} s`), 1000);
  body.replaceChildren(line, clock, el("p", {}, el("a", { href: "#today" }, "Back to Today")));
  try {
    const st = await waitJob((await api("/api/tailor", req)).job_id);
    if (revision !== S.revision) return;
    renderTailor(st);
    if (st.cached) toast("Loaded the saved plan; use Re-plan for a fresh one");
  } catch (e) { if (revision === S.revision) fail(body, e, () => startTailor(req)); } finally { clearInterval(tick); }
}
$("#urlform").addEventListener("submit", e => { e.preventDefault(); startTailor({ url: $("#url").value.trim() }); });

/* ---------- Applied ---------- */
async function loadApplied() {
  const body = $("#applied-body");
  try {
    const rows = await api("/api/applied");
    if (!rows.length) { body.replaceChildren(el("p", { class: "empty" }, "Nothing marked applied yet. Use Mark applied on Today or Tailor.")); return; }
    const tr = r => el("tr", {}, el("td", {}, r.date), el("td", {}, r.company), el("td", {}, r.title),
      el("td", {}, el("select", { onchange: async e => { await api("/api/applied/status", { req_id: r.req_id, company: r.company, status: e.target.value }); toast(`Set ${r.company} to ${e.target.value}`); } },
        ...["applied", "screen", "interview", "rejected", "offer"].map(s => el("option", { value: s, selected: s === r.status ? "" : null }, s)))),
      el("td", {}, r.folder ? el("button", { type: "button", class: "quiet", onclick: () => api("/api/open", { path: r.folder }).catch(e => toast(e.message)) }, r.folder) : ""));
    body.replaceChildren(el("table", {}, el("thead", {}, el("tr", {}, ...["Date", "Company", "Title", "Status", "Folder"].map(h => el("th", {}, h)))), el("tbody", {}, ...rows.map(tr))));
  } catch (e) { fail(body, e, loadApplied); }
}

/* ---------- run the radar ---------- */
function watchRun() {
  const btn = $("#runbtn"); btn.disabled = true;
  const poll = async () => {
    const s = await api("/api/run");
    btn.textContent = s.running ? `Running: ${s.last_line.slice(0, 40) || "starting"}` : "Run the radar";
    if (s.running) return setTimeout(poll, 8000);
    btn.disabled = false; toast(s.exit_code === 0 ? "Run finished" : `Run ended with exit code ${s.exit_code}`); if (location.hash !== "#tailor") show();
  };
  poll();
}
async function runRadar(days, allTiers) {
  const r = await api("/api/run", { days, all_tiers: allTiers });
  if (!r.started) { toast(r.reason); return watchRun(); }
  toast(`Running the radar for ${days} day(s); Today refreshes when it finishes`);
  watchRun();
}
/* a run outlives the page: pick it up again after a refresh */
api("/api/run").then((s) => { if (s.running) watchRun(); }).catch(() => {});
$("#runbtn").addEventListener("click", () => { const d = parseInt(prompt("How many days back? (1 = today's window)", "1") || "0", 10); if (d > 0) runRadar(d, false); });

/* ---------- chat ---------- */
let stored = {}; try { stored = JSON.parse(localStorage.getItem("radar-chat") || "{}"); } catch (e) {}
const C = { open: !!stored.open, session: stored.session || String(Date.now()) };
const persist = () => { try { localStorage.setItem("radar-chat", JSON.stringify({ open: C.open, session: C.session })); } catch (e) {} };
const EMPTY = 'Ask for anything on this page: "load three more days", "mark the Netflix row applied", "open Workday in Tailor and shorten the summary".';
function setChat(open) {
  C.open = open; $("#chat").hidden = !open; $("#chatpill").hidden = open; $("#chatbtn").setAttribute("aria-expanded", String(open));
  document.body.classList.toggle("with-chat", open); persist(); if (open) { loadThreads(); loadHistory(); $("#chatin").focus(); }
}
async function loadThreads() {
  try {
    const list = await api("/api/chat/sessions");
    const sel = $("#threads");
    const opts = list.map(s => el("option", { value: s.id, selected: s.id === C.session ? "" : null }, s.title));
    if (!list.some(s => s.id === C.session)) opts.unshift(el("option", { value: C.session, selected: "" }, "New chat"));
    sel.replaceChildren(...opts);
  } catch (e) { /* offline */ }
}
async function loadHistory() {
  const log = $("#chatlog");
  try {
    const turns = await api(`/api/chat/history?session=${C.session}`);
    log.replaceChildren(...(turns.length ? turns.map(t => el("p", { class: t.who }, t.who === "bot" ? reply(t.text) : t.text)) : [el("p", { class: "empty" }, EMPTY)]));
    log.scrollTop = log.scrollHeight;
  } catch (e) { /* offline; the empty state stays */ }
}
function context() {
  const v = (location.hash || "#today").slice(1);
  const ctx = { view: v, date: T.date, sections_hint: "Today rows: {section, company, req_id, title, score_entry, score_experienced, sponsorship, applied}" };
  if (T.last) ctx.today = Object.fromEntries(Object.entries(T.last.sections).map(([k, rows]) => [k, rows.slice(0, 25).map(r => ({ company: r.company, req_id: r.req_id, title: r.title, E: r.score_entry, X: r.score_experienced, sponsorship: r.sponsorship, applied: r.applied }))]));
  if (S.state) ctx.tailor = { job: S.state.job, sections: S.state.sections.map(s => ({ id: s.id, label: s.label, text: s.text })), jd_skills: S.state.jd_skills, built: !!S.build };
  return ctx;
}
function act(a) {
  const x = a.args || {};
  if (a.tool === "navigate") location.hash = x.view;
  else if (a.tool === "refresh") show();
  else if (a.tool === "open_tailor") { location.hash = "tailor"; startTailor(x.url ? { url: x.url } : { company: x.company, req_id: x.req_id }); }
  else if (a.tool === "edit_section" && S.state) {
    const sec = S.state.sections.find(s => s.id === x.section);
    if (!sec || x.index >= sec.text.length) return toast(`No ${x.section} item ${x.index} to edit`);
    sec.text[x.index] = x.text; renderTailor(S.state); toast(`Edited ${sec.label} item ${x.index + 1}`);
  } else if (a.tool === "rebuild") { const b = [...document.querySelectorAll(".actions button")].find(b => b.textContent.startsWith("Rebuild")); b && b.click(); }
}
async function sendChat(text) {
  const log = $("#chatlog");
  log.querySelector(".empty")?.remove();
  log.append(el("p", { class: "me" }, text));
  const wait = el("p", { class: "meta" }, "Working"); log.append(wait); log.scrollTop = log.scrollHeight;
  try {
    const r = await waitJob((await api("/api/chat", { session: C.session, text, context: context() })).job_id);
    wait.remove(); log.append(el("p", { class: "bot" }, reply(r.reply || "(done)")));
    for (const a of r.actions) act(a);
  } catch (e) { wait.textContent = e.message; wait.className = "error"; }
  log.scrollTop = log.scrollHeight;
}
$("#chatbtn").addEventListener("click", () => setChat(!C.open));
$("#chatpill").addEventListener("click", () => setChat(true));
$("#chatmin").addEventListener("click", () => setChat(false));
$("#chatform").addEventListener("submit", e => { e.preventDefault(); const t = $("#chatin").value.trim(); if (!t) return; $("#chatin").value = ""; sendChat(t).then(loadThreads); });
$("#threads").addEventListener("change", e => { C.session = e.target.value; persist(); loadHistory(); });
$("#chatnew").addEventListener("click", () => { C.session = String(Date.now()); persist(); loadThreads(); loadHistory(); $("#chatin").focus(); });
$("#chatdel").addEventListener("click", async () => {
  if (!confirm("Delete this thread? Memory notes are kept.")) return;
  await api("/api/chat/reset", { session: C.session }); C.session = String(Date.now()); persist(); loadThreads(); loadHistory();
});
setChat(C.open);

/* ---------- routing ---------- */
function show() {
  const v = (location.hash || "#today").slice(1);
  document.querySelectorAll(".view").forEach(s => (s.hidden = s.id !== v));
  document.querySelectorAll(".nav a").forEach(a => a.classList.toggle("on", a.dataset.view === v));
  $("#datectl").hidden = v !== "today";
  if (v === "today") loadToday(); if (v === "applied") loadApplied();
}
window.addEventListener("hashchange", show);
show();
