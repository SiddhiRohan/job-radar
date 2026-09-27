/* Email card on Applied: Check mail, the needs-review list, and the latest automatic updates.
   Statuses move on their own only for emails that carry a matching req id; everything else waits here for a person.
   Uses el, api, waitJob and toast from app.js, and STAGES and postingTitle defined alongside it. */
function mailCard(apps) {
  const card = el("section", { class: "card wide mailcard" }, el("h3", {}, "Email"), el("p", { class: "sub" }, "Loading"));
  api("/api/mail").then(s => fillMail(card, s, apps)).catch(e => card.replaceChildren(el("h3", {}, "Email"), el("p", { class: "error" }, e.message)));
  return card;
}

function fillMail(card, s, apps) {
  if (!s.configured) {
    card.replaceChildren(el("h3", {}, "Email"), el("p", { class: "sub" },
      "Connect Gmail and hiring emails will move statuses here: add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to .env. docs/CONFIG.md has the steps."));
    return;
  }
  const check = el("button", { type: "button", onclick: () => checkMail(check) }, "Check mail");
  const head = el("div", { class: "mailhead" }, el("div", {}, el("h3", {}, "Email"),
    el("p", { class: "sub" }, s.last_sync ? `Last checked ${s.last_sync}` : "Not checked yet")), check);
  const review = s.review.length
    ? [el("h4", {}, "Needs review", el("span", { class: "n" }, String(s.review.length))), ...s.review.map(r => reviewItem(r, apps))]
    : [el("p", { class: "kempty" }, "Nothing needs review.")];
  const updates = s.events.length
    ? [el("h4", {}, "Recent updates"), el("ul", { class: "mailevents" }, ...s.events.map(e => el("li", {},
        el("b", {}, e.company), ` moved from ${e.from_status} to ${e.status}`, e.reason === "reviewed" ? " by you" : "", ", from ",
        el("a", { href: e.link, target: "_blank", rel: "noopener" }, e.subject || "an email"))))]
    : [];
  card.replaceChildren(head, ...review, ...updates);
}

function reviewItem(r, apps) {
  const key = a => `${a.company}|${a.req_id}`;
  const opt = a => el("option", { value: key(a), selected: a.company === r.company && a.req_id === r.req_id ? "" : null }, `${a.company}, ${a.title}`);
  const likely = new Set((r.candidates || []).map(key));  /* applications the email may be about go first */
  const first = apps.filter(a => likely.has(key(a))), rest = apps.filter(a => !likely.has(key(a)));
  const pick = el("select", { class: "mailpick", "aria-label": "Which application this email is about" },
    el("option", { value: "" }, "Choose the application"),
    first.length ? el("optgroup", { label: "Likely" }, ...first.map(opt)) : null,
    el("optgroup", { label: first.length ? "All applications" : "Applications" }, ...rest.map(opt)));
  const status = el("select", { "aria-label": "Status this email means" },
    ...STAGES.map(s => el("option", { value: s, selected: s === (r.status || "applied") ? "" : null }, s)));
  /* Settling an email can be taken back from the toast: it returns to Needs review and any status change reverts. */
  const settle = async body => {
    try {
      await api("/api/mail/resolve", { message_id: r.message_id, ...body }); loadApplied();
      toast(body.status ? `Set ${body.company} to ${body.status} from this email` : "Email dismissed",
        { label: "Undo", run: () => api("/api/mail/unresolve", { message_id: r.message_id }).then(loadApplied).catch(e => toast(e.message)) });
    } catch (e) { toast(e.message); }
  };
  const apply = el("button", { type: "button", class: "primary", onclick: () => {
    if (!pick.value) return toast("Choose the application first");
    const [company, req_id] = pick.value.split("|");
    settle({ company, req_id, status: status.value });
  } }, "Apply");
  const dismiss = el("button", { type: "button", class: "quiet", onclick: () => settle({}) }, "Dismiss");
  return el("article", { class: "mailitem" },
    el("div", { class: "mailmeta" }, el("span", {}, r.sender.replace(/<[^>]*>/, "").trim() || r.sender), el("span", {}, r.date), el("span", { class: "tag unknown" }, r.reason)),
    el("a", { class: "mailsubj", href: r.link, target: "_blank", rel: "noopener" }, r.subject || "(no subject)"),
    el("p", { class: "mailsnip" }, r.snippet),
    el("div", { class: "mailacts" }, pick, status, apply, dismiss));
}

async function checkMail(btn) {
  btn.disabled = true; btn.textContent = "Checking";
  try {
    const r = await waitJob((await api("/api/mail/sync", {})).job_id);
    toast(`Email checked: ${r.updated} status update${r.updated === 1 ? "" : "s"}, ${r.review} to review`);
    loadApplied();
  } catch (e) { toast(`Could not check email: ${e.message}`); btn.disabled = false; btn.textContent = "Check mail"; }
}
