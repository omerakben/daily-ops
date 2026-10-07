"""Original, offline-only presentation assets for the report worksheet.

The runtime has no interpolated task data. render.py supplies an escaped JSON data
block and hashes these exact assets into the document's content security policy.
"""

CSS = r"""
:root{color-scheme:light;--paper:#f5f3eb;--card:#fffef9;--ink:#243b39;--muted:#536862;--line:#d5ddd4;--accent:#216355;--soft:#e8f0e8;--amber:#80551d;--warn:#fff4da}
*{box-sizing:border-box}html{scroll-padding-top:24px}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--accent);text-underline-offset:3px}a:hover{text-decoration-thickness:2px}:focus-visible{outline:3px solid #8b551c;outline-offset:4px}button,input,select,textarea{font:inherit}button,select{cursor:pointer}button{border:1px solid var(--accent);border-radius:8px;padding:11px 16px;background:var(--accent);color:white;font-weight:650}button.secondary{background:var(--card);color:var(--accent)}button:disabled{cursor:not-allowed;opacity:.55}input,select,textarea{width:100%;max-width:100%;border:1px solid #81978d;border-radius:6px;background:white;color:var(--ink);padding:10px}textarea{resize:vertical;min-height:100px}label{display:block;font-size:.9rem;font-weight:650;margin:12px 0 5px}[hidden]{display:none!important}
.layout{display:grid;grid-template-columns:225px minmax(0,1fr);max-width:1440px;margin:auto}.sidebar{align-self:start;position:sticky;top:0;padding:34px 24px;min-height:100vh;border-right:1px solid var(--line)}.brand{font-size:1.2rem;font-weight:750;letter-spacing:-.04em}.sidebar p{font-size:.82rem;color:var(--muted)}nav{display:grid;gap:5px;margin-top:34px}nav a{padding:8px 10px;text-decoration:none;border-radius:6px;font-size:.9rem}nav a:hover{background:var(--soft)}main{min-width:0;max-width:1080px;width:100%;padding:40px 44px 70px}.eyebrow{font-size:.72rem;text-transform:uppercase;letter-spacing:.14em;color:var(--accent);font-weight:750}h1{font-size:clamp(2rem,4vw,3.3rem);line-height:1.1;letter-spacing:-.045em;margin:12px 0 18px;overflow-wrap:anywhere}h2{font-size:1.35rem;line-height:1.3;letter-spacing:-.025em;margin:0 0 16px}h3{font-size:1.12rem;line-height:1.4;margin:6px 0 12px}p{margin:8px 0}.intro{max-width:68ch}.muted,.meta{color:var(--muted)}.meta{font-size:.83rem}.section{margin-top:36px;scroll-margin-top:24px}.section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap}.count{font-size:.85rem;color:var(--muted);font-weight:450;margin-left:8px}.hero{background:var(--accent);color:#fffef9;padding:26px;border-radius:14px;margin-top:24px;overflow-wrap:anywhere}.hero .eyebrow{color:#d9edc9}.hero h2{font-size:1.6rem;margin:7px 0 10px}.hero a{color:inherit}.hero .meta{color:#e1ede3}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.stat{border:1px solid var(--line);border-radius:10px;background:var(--card);padding:16px;min-width:0}.stat strong{display:block;font-size:2rem;font-weight:650;letter-spacing:-.04em;overflow-wrap:anywhere}.stat span{font-size:.8rem;color:var(--muted)}.arithmetic{margin:12px 0;font-size:.9rem;color:var(--muted)}.notice{border:1px solid #d7c393;background:var(--warn);padding:22px;border-radius:12px}.notice h2{margin-bottom:10px}.notice ul{margin:8px 0;padding-left:22px}.decisions{display:grid;gap:14px;padding:0;list-style:none}.decisions li{border-top:1px solid #ddcfae;padding-top:14px}.decisions li:first-child{border:0;padding-top:0}.decisions p{margin:4px 0}.question{font-weight:600}.task-list{list-style:none;padding:0;margin:0;display:grid;gap:16px}.task{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px;scroll-margin-top:24px;overflow-wrap:anywhere}.selected .task{border-left:4px solid var(--accent)}.task-top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.tag{display:inline-block;border-radius:4px;padding:3px 8px;background:var(--soft);font-size:.76rem}.tag.warn{background:var(--warn);color:var(--amber)}.facts{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:.85rem;color:var(--muted);margin:0 0 12px}.notes{white-space:pre-wrap}.reason{padding-top:12px;border-top:1px solid var(--line);font-size:.9rem}.concern{padding:12px 14px;border-radius:7px;background:var(--warn);font-size:.9rem;margin-top:14px}.request{font-size:.8rem;color:var(--muted);margin-top:14px}.request code{display:block}.empty{border:1px dashed #aabaae;padding:20px;border-radius:10px;color:var(--muted)}details{border-top:1px solid var(--line);margin-top:16px;padding-top:14px}summary{cursor:pointer;font-weight:650;font-size:.9rem}summary:hover{color:var(--accent)}fieldset{border:0;margin:14px 0 0;padding:0;min-width:0}legend{font-size:.85rem;color:var(--muted)}.response-field{margin-top:8px}.help{font-size:.8rem;color:var(--muted)}.response-message{font-size:.85rem;min-height:1.4em}.response-message.error{color:#a03728}.review-status{font-size:.75rem;color:var(--muted)}.review-status.proposed{color:var(--accent);font-weight:700}.review-status.kept{color:var(--accent)}.export-panel{padding:24px;background:var(--soft);border:1px solid #b9cfc0;border-radius:12px}.actions{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0 8px}.progress{font-weight:650}.footer{font-size:.8rem;color:var(--muted);border-top:1px solid var(--line);margin-top:36px;padding-top:20px}.footer p{max-width:80ch}code,pre{font:.86em ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;white-space:pre-wrap}pre{padding:14px;background:#f0f2ec;border-radius:7px}.skip{position:fixed;left:12px;top:-100px;background:white;z-index:5;padding:12px}.skip:focus{top:12px}.pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px}.pair>section{min-width:0;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px}.diff-list{list-style:none;padding:0;margin:0}.diff-list>li{padding:16px 0;border-top:1px solid var(--line)}.diff-list>li:first-child{border-top:0}.diff-values{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.value{margin-top:5px;padding:12px;border:1px solid var(--line);border-radius:6px;white-space:pre-wrap;overflow-wrap:anywhere;background:white}.value-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.flow-list{list-style:none;padding:0;display:grid;gap:12px}.flow-list li{border-top:1px solid var(--line);padding-top:10px;overflow-wrap:anywhere}.flow-list strong{display:block}.flow-list p{font-size:.85rem}
@media(max-width:960px){.layout{grid-template-columns:180px minmax(0,1fr)}.sidebar{padding:28px 16px}main{padding:32px 24px}.pair{grid-template-columns:1fr}}
@media(max-width:700px){.layout{display:block}.sidebar{position:static;min-height:0;padding:16px 18px;border-right:0;border-bottom:1px solid var(--line)}.sidebar>p{margin:2px 0}.sidebar .sidebar-note{display:none}nav{display:flex;flex-wrap:wrap;margin-top:12px;gap:2px}nav a{padding:5px 9px;font-size:.8rem}main{padding:26px 16px 48px}.stats{gap:7px}.stat{padding:11px}.stat strong{font-size:1.6rem}.stat span{font-size:.72rem}.hero,.task,.notice,.export-panel{padding:18px}.diff-values{grid-template-columns:1fr}.actions{display:grid}.actions button{width:100%}}
@media print{body{background:white;font-size:11pt}.layout{display:block}.sidebar,.skip,.worksheet,.review-tools,.request{display:none!important}main{max-width:none;padding:0}.hero{background:white;color:var(--ink);border:2px solid var(--accent)}.hero .eyebrow,.hero .meta{color:var(--ink)}.stats{display:flex}.stat{flex:1}.task,.notice,.pair>section,.diff-list>li{break-inside:avoid}.section{margin-top:24px}h2,h3{break-after:avoid}a{color:inherit;text-decoration:none}.pair{display:block}.pair>section{margin-bottom:15px}details>*{display:block!important}summary{display:none}.footer{font-size:9pt}}
"""

WORKSHEET_JS = r"""(() => {
  'use strict';
  const report = JSON.parse(document.getElementById('report-data').textContent);
  const cards = Array.from(document.querySelectorAll('[data-review-task]'));
  const tasks = new Map(report.tasks.map(task => [task.id, task]));
  const downloadButton = document.getElementById('download-changes');
  const progress = document.getElementById('review-progress');
  const exportStatus = document.getElementById('export-status');
  const trim = value => value.replace(/^[\s\u0085\u001c-\u001f]+|[\s\u0085\u001c-\u001f]+$/g, '');
  function validDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const [year, month, day] = value.split('-').map(Number);
    if (year < 1 || month < 1 || month > 12) return false;
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    return day >= 1 && day <= [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
  }
  function response(card) {
    const task = tasks.get(card.dataset.reviewTask);
    const choice = card.querySelector('[data-choice]').value;
    const value = field => card.querySelector('[data-field="' + field + '"]').value;
    if (choice === 'unreviewed') return {state: 'pending', label: 'Unreviewed', message: ''};
    if (choice === 'keep') return {state: 'kept', label: 'Kept current', message: 'Reviewed; no change proposed. This does not approve the plan.'};
    let action;
    let error = '';
    let same = false;
    if (choice === 'estimate') {
      const raw = value('minutes');
      const minutes = Number(raw);
      if (!/^\d+$/.test(raw) || !Number.isInteger(minutes) || minutes < 1 || minutes > 1440) error = 'Enter a whole number from 1 to 1440 minutes.';
      else { action = {action: 'update', id: task.id, minutes}; same = minutes === task.minutes; }
    } else if (choice === 'due' || choice === 'defer') {
      const date = value(choice === 'due' ? 'due' : 'until');
      if (!validDate(date)) error = 'Enter a valid calendar date in YYYY-MM-DD form.';
      else if (choice === 'due') { action = {action: 'update', id: task.id, due: date}; same = date === task.due; }
      else { action = {action: 'defer', id: task.id, until: date}; same = date === task.not_before; }
    } else if (choice === 'remove_due') {
      action = {action: 'update', id: task.id, due: null}; same = task.due == null;
    } else if (choice === 'block') {
      const reason = trim(value('reason'));
      const characters = Array.from(reason);
      const invalidUnicode = characters.some(char => char.length === 1 && char.charCodeAt(0) >= 0xd800 && char.charCodeAt(0) <= 0xdfff);
      if (!reason || characters.length > 20000 || reason.includes('\u0000') || invalidUnicode) error = 'Enter a waiting reason of 1 to 20000 valid characters.';
      else { action = {action: 'block', id: task.id, reason}; same = reason === task.blocked_by; }
    } else if (choice === 'unblock' && task.blocked_by) action = {action: 'unblock', id: task.id};
    else error = 'Choose one of the available responses.';
    if (error) return {state: 'invalid', label: 'Needs a value', message: error};
    if (same) return {state: 'unchanged', label: 'Unchanged entry', message: 'This matches the snapshot. No action will be exported; choose Keep current to record your review.'};
    return {state: 'proposed', label: 'Change proposed', message: 'Proposal only. The workspace has not changed.', action};
  }
  function collect() {
    const counts = {pending: 0, kept: 0, proposed: 0, invalid: 0, unchanged: 0};
    const actions = [];
    const seen = new Set();
    for (const card of cards) {
      const choice = card.querySelector('[data-choice]').value;
      for (const field of card.querySelectorAll('[data-for-choice]')) field.hidden = field.dataset.forChoice !== choice;
      const result = response(card);
      counts[result.state] += 1;
      const badge = card.querySelector('[data-review-status]');
      badge.textContent = result.label;
      badge.className = 'review-status ' + result.state;
      const message = card.querySelector('[data-response-message]');
      message.textContent = result.message;
      message.className = 'response-message' + (result.state === 'invalid' ? ' error' : '');
      if (result.action) {
        if (seen.has(result.action.id)) counts.invalid += 1;
        else { seen.add(result.action.id); actions.push(result.action); }
      }
    }
    progress.textContent = counts.pending + ' unreviewed · ' + counts.kept + ' kept current · ' + counts.proposed + ' changes proposed' + (counts.invalid ? ' · ' + counts.invalid + ' need a value' : '') + (counts.unchanged ? ' · ' + counts.unchanged + ' unchanged entries' : '');
    downloadButton.disabled = !actions.length || counts.invalid > 0 || actions.length > 1000;
    return {actions, counts};
  }
  function download(filename, content, type) {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const md = value => String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/([\\`*_{}\[\]()#+.!|~:\-])/g, '\\$1');
  for (const element of document.querySelectorAll('.worksheet, .review-tools')) element.hidden = false;
  for (const card of cards) {
    card.addEventListener('input', () => { exportStatus.textContent = ''; collect(); });
    card.addEventListener('change', () => { exportStatus.textContent = ''; collect(); });
  }
  downloadButton.addEventListener('click', () => {
    const result = collect();
    if (downloadButton.disabled) return;
    const proposal = {schema_version: 1, base_revision: report.revision, actions: result.actions};
    download('changes.json', JSON.stringify(proposal, null, 2) + '\n', 'application/json');
    exportStatus.textContent = 'Download requested: changes.json. This is a proposal from revision ' + report.revision + '; preview it against your current workspace before applying. No workspace changes were made.';
  });
  document.getElementById('download-review').addEventListener('click', () => {
    collect();
    const lines = ['# Daily Ops review worksheet', '', 'Plan date: ' + md(report.date), 'Snapshot revision: ' + report.revision, 'Task budget: ' + md(report.budget_minutes) + ' minutes', '', 'These are reader responses to a snapshot. Kept means reviewed, not approved. Proposed changes have not been applied.', ''];
    for (const card of cards) {
      const task = tasks.get(card.dataset.reviewTask);
      const result = response(card);
      lines.push('## ' + md(task.id) + ': ' + md(task.title), '', 'Plan placement: ' + md(task.placement), 'Plan reason: ' + md(task.plan_reason), 'Estimate: ' + task.minutes + ' minutes', 'Due: ' + md(task.due || 'None'), 'Available: ' + md(task.not_before || 'No later date set'), 'Waiting reason: ' + md(task.blocked_by || 'None'), 'Task notes: ' + md(task.notes || 'None'), 'Response: ' + md(result.label), '');
      for (const concern of report.concerns.filter(item => item.task_id === task.id)) lines.push('Question: ' + md(concern.question), '');
      if (result.action) lines.push('Proposed action: ' + md(JSON.stringify(result.action)), '');
      else if (result.message) lines.push(md(result.message), '');
    }
    const notes = document.getElementById('reader-notes').value;
    if (trim(notes)) lines.push('## Reader notes', '', ...notes.split(/\r?\n/).map(line => md(line)), '');
    lines.push('Return this review and changes.json to your assistant, or preview the proposal using Daily Ops. Recheck the workspace revision before applying. This review file does not apply changes.', '');
    download('review.md', lines.join('\n'), 'text/markdown');
    exportStatus.textContent = 'Download requested: review.md. Your workspace is unchanged. Download changes.json separately to keep a machine-readable proposal.';
  });
  document.getElementById('reader-notes').addEventListener('input', () => { exportStatus.textContent = ''; });
  collect();
})();"""
