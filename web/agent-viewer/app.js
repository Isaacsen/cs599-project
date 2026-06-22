const REPORT_URL = "/docs/runs/software_engineer.json";
const EVENTS_URL = "/docs/runs/software_engineer_events.jsonl";

const nodes = [
  ["scan", "Repo Scan", "扫描源码、测试、依赖与入口"],
  ["llm_review", "LLM Review", "生成代码审查 findings"],
  ["llm_fix_plan", "Fix Planner", "选择本轮修复目标"],
  ["llm_fix", "Code Fix", "生成修复建议或写回"],
  ["llm_tests", "Test Writer", "生成 pytest 测试"],
  ["sandbox_validate", "Sandbox", "Local / Docker 验证"],
  ["repair_loop", "Repair Loop", "失败后决定回跳"],
  ["coverage_feedback", "Coverage", "覆盖反馈"],
  ["finish", "Finish", "输出最终报告"],
];

document.getElementById("reload").addEventListener("click", () => loadRun());

loadRun();

async function loadRun() {
  try {
    const [report, events] = await Promise.all([loadJson(REPORT_URL), loadJsonl(EVENTS_URL)]);
    renderSummary(report);
    renderGraph(report, events);
    renderTimeline(events, report);
    renderRounds(report);
  } catch (error) {
    renderError(error);
  }
}

async function loadJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response.json();
}

async function loadJsonl(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    return [];
  }
  const text = await response.text();
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function renderSummary(report) {
  const summary = report.summary || {};
  document.getElementById("run-summary").textContent = [
    `Project: ${report.project_path || "unknown"}`,
    `Status: ${report.status || "unknown"}`,
    `Runtime: ${report.graph_runtime || "unknown"}`,
    `Findings: ${(report.llm_review?.findings || []).length}`,
    `Rounds: ${summary.finding_rounds || 0}`,
  ].join(" | ");
}

function renderGraph(report, events) {
  const graph = document.getElementById("agent-graph");
  const trace = new Set(report.node_trace || []);
  const active = events.length ? events[events.length - 1].node : "";
  document.getElementById("active-node").textContent = active || "Idle";

  graph.innerHTML = "";
  for (const [id, title, subtitle] of nodes) {
    const item = document.createElement("article");
    item.className = "node";
    if (trace.has(id)) item.classList.add("done");
    if (active === id) item.classList.add("active");
    if (id === "sandbox_validate" && report.sandbox_validation?.status === "failed") {
      item.classList.add("failed");
    }
    item.innerHTML = `<small>${id}</small><strong>${title}</strong><small>${subtitle}</small>`;
    graph.appendChild(item);
  }
}

function renderTimeline(events, report) {
  const timeline = document.getElementById("timeline");
  document.getElementById("event-count").textContent = `${events.length} events`;
  timeline.innerHTML = "";

  if (!events.length) {
    timeline.innerHTML = `<li class="empty">没有找到事件日志。请先运行 python -m src.engineer ... 生成 ${EVENTS_URL}。</li>`;
    return;
  }

  for (const event of events) {
    const li = document.createElement("li");
    const time = new Date(event.timestamp).toLocaleTimeString();
    li.innerHTML = `
      <span class="badge ${event.event_type}">${event.event_type}</span>
      <strong>${event.node}</strong>
      <span>${escapeHtml(event.message || "")}<br><small>${time}</small></span>
    `;
    timeline.appendChild(li);
  }

  if (report.status) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="badge node_end">report</span><strong>final</strong><span>${escapeHtml(report.status)}</span>`;
    timeline.appendChild(li);
  }
}

function renderRounds(report) {
  const rounds = buildRounds(report);
  const target = document.getElementById("rounds");
  document.getElementById("round-count").textContent = `${rounds.length} rounds`;
  target.innerHTML = "";

  if (!rounds.length) {
    target.innerHTML = `<div class="empty">当前报告中没有 repair / fix 轮次历史。</div>`;
    return;
  }

  for (const round of rounds) {
    const card = document.createElement("article");
    card.className = "round-card";
    card.innerHTML = `
      <h3>Round ${round.index}</h3>
      <dl class="kv">
        <dt>Fix Plan</dt><dd>${escapeHtml(round.plan)}</dd>
        <dt>Code Fix</dt><dd>${escapeHtml(round.fix)}</dd>
        <dt>Tests</dt><dd>${escapeHtml(round.tests)}</dd>
        <dt>Sandbox</dt><dd>${escapeHtml(round.sandbox)}</dd>
        <dt>Repair</dt><dd>${escapeHtml(round.repair)}</dd>
      </dl>
    `;
    target.appendChild(card);
  }
}

function buildRounds(report) {
  const plans = report.llm_fix_plan_history || [];
  const fixes = report.llm_fix_history || [];
  const tests = report.llm_tests_history || [];
  const sandboxes = report.sandbox_validation_history || [];
  const repairs = report.repair_history || [];
  const count = Math.max(plans.length, fixes.length, tests.length, sandboxes.length, repairs.length);
  const rounds = [];

  for (let index = 0; index < count; index += 1) {
    const plan = plans[index];
    const fix = fixes[index];
    const test = tests[index];
    const sandbox = sandboxes[index];
    const repair = repairs[index];
    rounds.push({
      index: index + 1,
      plan: plan
        ? `${plan.status}; targets=${plan.summary?.target_count ?? 0}; remaining=${plan.summary?.remaining_count ?? 0}`
        : "not_run",
      fix: fix ? `${fix.status}; fixes=${fix.summary?.fix_count ?? 0}; applied=${fix.applied}` : "not_run",
      tests: test ? `${test.status}; generated=${test.generated_test_count ?? test.summary?.generated_test_count ?? 0}` : "not_run",
      sandbox: sandbox
        ? `${sandbox.status}; ${sandbox.analysis?.passed ?? 0}/${sandbox.analysis?.total ?? 0} passed`
        : "not_run",
      repair: repair ? `${repair.status}; next=${repair.next_step}; iteration=${repair.iteration}` : "not_run",
    });
  }
  return rounds;
}

function renderError(error) {
  document.getElementById("run-summary").textContent = "Failed to load run artifacts";
  document.getElementById("agent-graph").innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  document.getElementById("timeline").innerHTML = "";
  document.getElementById("rounds").innerHTML = "";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
