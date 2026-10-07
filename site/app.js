"use strict";

// Fictional examples only. No network calls, storage, or AI inference.
const EXAMPLE_DATE = "2026-10-07";
const SCENARIOS = {
  student: {
    title: "Between classes",
    description: "A lab deadline, some reading, and more good intentions than minutes.",
    available: 100, reserve: 20,
    tasks: [
      { id: "T001", title: "Finish lab write-up", minutes: 45, priority: "high", due: EXAMPLE_DATE },
      { id: "T002", title: "Read the next chapter", minutes: 30, priority: "normal" },
      { id: "T003", title: "Design the club poster", minutes: 30, priority: "low" },
      { id: "T004", title: "Prepare for next week's exam", minutes: 120, priority: "high", due: "2026-10-14" },
    ],
  },
  freelancer: {
    title: "A few moving pieces",
    description: "An invoice to send, a proposal to finish, and one task waiting on someone else.",
    available: 150, reserve: 30,
    tasks: [
      { id: "T001", title: "Send the project invoice", minutes: 20, priority: "high", due: "2026-10-06" },
      { id: "T002", title: "Finish the client proposal", minutes: 60, priority: "high", due: EXAMPLE_DATE },
      { id: "T003", title: "Categorize this month's receipts", minutes: 25, priority: "low" },
      { id: "T004", title: "Refresh portfolio case study", minutes: 90, priority: "normal" },
      { id: "T005", title: "Prepare the final handover", minutes: 45, priority: "normal", blocked_by: "Waiting for client approval" },
    ],
  },
  caregiver: {
    title: "In the spaces between",
    description: "A few practical things to do, with room for the day to change. Try reducing the available time to 35.",
    available: 60, reserve: 20,
    tasks: [
      { id: "T001", title: "Complete the school form", minutes: 15, priority: "high", due: EXAMPLE_DATE },
      { id: "T002", title: "Pick up groceries", minutes: 25, priority: "normal" },
      { id: "T003", title: "Sort the hallway closet", minutes: 60, priority: "low" },
    ],
  },
  contributor: {
    title: "Between the meetings",
    description: "One review, a useful documentation task, and an analysis that needs input first.",
    available: 120, reserve: 20,
    tasks: [
      { id: "T001", title: "Review the project brief", minutes: 45, priority: "high", due: EXAMPLE_DATE },
      { id: "T002", title: "Update the setup guide", minutes: 45, priority: "high" },
      { id: "T003", title: "File the weekly expenses", minutes: 15, priority: "low" },
      { id: "T004", title: "Analyze the research results", minutes: 120, priority: "normal", blocked_by: "Waiting for the source dataset" },
    ],
  },
};

function urgency(task, date) {
  if (!task.due) return 3;
  if (task.due < date) return 0;
  if (task.due === date) return 1;
  return 2;
}

function buildPlan(tasks, date, budget) {
  const priorities = { high: 0, normal: 1, low: 2 };
  const ranked = tasks.filter(task => !task.status || task.status === "open").slice().sort((a, b) =>
    urgency(a, date) - urgency(b, date) ||
    (a.due || "9999-12-31").localeCompare(b.due || "9999-12-31") ||
    priorities[a.priority] - priorities[b.priority] ||
    Number(a.id.replace(/\D/g, "")) - Number(b.id.replace(/\D/g, ""))
  );
  const result = { selected: [], deferred: [], blocked: [], conflicts: [], planned: 0, remaining: budget };
  for (const task of ranked) {
    let reason;
    let group;
    if (task.blocked_by) {
      group = "blocked";
      reason = task.blocked_by;
    } else if (task.not_before && task.not_before > date) {
      group = "deferred";
      reason = `Available from ${task.not_before}.`;
    } else if (task.minutes > result.remaining) {
      group = "deferred";
      reason = `Needs ${task.minutes} min; ${result.remaining} min left when considered.`;
    } else {
      group = "selected";
      reason = task.due && task.due <= date ? "A due task that fits the budget." : "Fits after earlier-ranked tasks.";
      result.remaining -= task.minutes;
      result.planned += task.minutes;
    }
    result[group].push({ task, reason });
    if (group !== "selected" && task.due && task.due <= date) {
      result.conflicts.push(`${task.id}: ${task.title} is due ${task.due < date ? "before today" : "today"} and is not in the plan.`);
    }
  }
  return result;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderTasks(target, entries, emptyMessage) {
  target.replaceChildren();
  if (!entries.length) {
    target.append(element("li", "empty-state", emptyMessage));
    return;
  }
  for (const { task, reason } of entries) {
    const item = element("li", "demo-task");
    const top = element("div", "task-topline");
    top.append(element("span", "task-id", task.id), element("span", "task-estimate", `${task.minutes} min`));
    item.append(top, element("h5", "", task.title));
    const due = task.due ? task.due < EXAMPLE_DATE ? "Overdue" : task.due === EXAMPLE_DATE ? "Due today" : `Due ${task.due}` : "No deadline";
    item.append(element("p", `task-detail${task.due && task.due <= EXAMPLE_DATE ? " task-due" : ""}`, `${due} · ${task.priority} priority`));
    item.append(element("p", "task-reason", reason));
    target.append(item);
  }
}

let activeScenario = "student";
const availableInput = document.getElementById("available");
const reserveInput = document.getElementById("reserve");
const error = document.getElementById("budget-error");

function updatePlan() {
  const available = Number(availableInput.value);
  const reserve = Number(reserveInput.value);
  const invalidAvailable = availableInput.value === "" || !Number.isInteger(available) || available < 0 || available > 1440;
  const invalidReserve = reserveInput.value === "" || !Number.isInteger(reserve) || reserve < 0 || reserve > available;
  availableInput.setAttribute("aria-invalid", String(invalidAvailable));
  reserveInput.setAttribute("aria-invalid", String(invalidReserve));
  error.hidden = !invalidAvailable && !invalidReserve;
  error.textContent = invalidAvailable ? "Enter a whole number from 0 to 1,440 for available minutes." : invalidReserve ? "Reserve must be a whole number from 0 to your available minutes." : "";
  if (!error.hidden) {
    document.getElementById("capacity").textContent = "Check inputs";
    document.getElementById("demo-results").hidden = true;
    document.getElementById("plan-announcement").textContent = "The plan is unavailable until the time inputs are valid.";
    return;
  }
  document.getElementById("demo-results").hidden = false;
  const capacity = available - reserve;
  const plan = buildPlan(SCENARIOS[activeScenario].tasks, EXAMPLE_DATE, capacity);
  document.getElementById("capacity").textContent = `${capacity} min`;
  document.getElementById("planned-total").textContent = String(plan.planned);
  document.getElementById("remaining-summary").textContent = `${plan.remaining} min unallocated`;
  for (const group of ["selected", "deferred", "blocked"]) {
    document.getElementById(`${group}-count`).textContent = String(plan[group].length);
  }
  renderTasks(document.getElementById("selected-list"), plan.selected, "Nothing fits this budget. You can choose a smaller next action or leave space today.");
  renderTasks(document.getElementById("deferred-list"), plan.deferred, "Everything eligible fits. No tasks set aside.");
  renderTasks(document.getElementById("blocked-list"), plan.blocked, "No tasks waiting for input.");
  for (const [id, minutes] of [["bar-selected", plan.planned], ["bar-open", plan.remaining], ["bar-reserve", reserve]]) {
    document.getElementById(id).style.width = `${available ? minutes / available * 100 : 0}%`;
  }
  document.getElementById("budget-bar").setAttribute("aria-label", `${plan.planned} minutes planned, ${plan.remaining} unallocated, ${reserve} reserved`);
  document.getElementById("conflicts").hidden = !plan.conflicts.length;
  const conflictList = document.getElementById("conflict-list");
  conflictList.replaceChildren(...plan.conflicts.map(message => element("li", "", message)));
  document.getElementById("plan-announcement").textContent = `${plan.selected.length} tasks selected, ${plan.planned} of ${capacity} task minutes planned. ${plan.deferred.length} for later. ${plan.blocked.length} waiting. ${plan.conflicts.length} due tasks need a decision.`;
}

function selectScenario(name) {
  activeScenario = name;
  const scenario = SCENARIOS[name];
  availableInput.value = String(scenario.available);
  reserveInput.value = String(scenario.reserve);
  document.getElementById("scenario-title").textContent = scenario.title;
  document.getElementById("scenario-description").textContent = scenario.description;
  document.querySelectorAll("[data-scenario]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.scenario === name));
  });
  updatePlan();
}

document.querySelectorAll("[data-scenario]").forEach(button => {
  button.disabled = false;
  button.addEventListener("click", () => selectScenario(button.dataset.scenario));
});
document.getElementById("time-inputs").disabled = false;
document.getElementById("reset-demo").disabled = false;
document.getElementById("reset-demo").addEventListener("click", () => selectScenario(activeScenario));
document.getElementById("plan-controls").addEventListener("submit", event => event.preventDefault());
availableInput.addEventListener("input", updatePlan);
reserveInput.addEventListener("input", updatePlan);
updatePlan();

// Inspectable demo contract for lightweight browser checks; no persisted state.
window.DailyOpsDemo = Object.freeze({ plan: buildPlan, scenarios: SCENARIOS, date: EXAMPLE_DATE });
