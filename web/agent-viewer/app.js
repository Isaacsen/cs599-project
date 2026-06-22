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

let currentRunId = "";
let currentEvents = [];
let currentReport = {};
let eventSource = null;
const tokenBuffers = {};

document.getElementById("reload").addEventListener("click", () => loadLatestArtifacts());
document.getElementById("start-run").addEventListener("click", () => startRun());
document.getElementById("stop-run").addEventListener("click", () => stopRun());

renderGraph({}, []);
loadLatestArtifacts();

async function startRun() {
  closeEventSource();
  currentEvents = [];
  currentReport = {};
  clearTokenBuffers();
  setRunButtons(true);
  renderAll();

  const payload = {
    project_path: value("project-path"),
    run_sandbox: checked("run-sandbox"),
    sandbox_executor: value("sandbox-executor"),
    apply_fixes: checked("apply-fixes"),
    apply_tests: checked("apply-tests"),
    timeout_seconds: numberValue("timeout-seconds", 30),
    llm_timeout: numberValue("llm-timeout", 90),
    llm_retries: 0,
    no_llm_token_stream: false,
  };

  setSummary(`Starting run for ${payload.project_path}...`);
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    renderError(new Error(`Start run failed: ${response.status}`));
    setRunButtons(false);
    return;
  }
  const run = await response.json();
  currentRunId = run.run_id;
  setSummary(`Run ${currentRunId} started | Project: ${payload.project_path}`);
  connectEvents(currentRunId);
}

async function stopRun() {
  if (!currentRunId) return;
  document.getElementById("stop-run").disabled = true;
  setSummary(`Cancelling run ${currentRunId}... current Agent node will finish or stop at the next boundary.`);
  const response = await fetch(`/api/runs/${currentRunId}/cancel`, { method: "POST" });
  if (!response.ok) renderError(new Error(`Cancel run failed: ${response.status}`));
}

function connectEvents(runId) {
  eventSource = new EventSource(`/api/runs/${runId}/events`);
  eventSource.onmessage = consumeEvent;
  for (const type of ["run_start", "node_start", "node_end", "llm_token", "report", "error", "cancelled", "run_end"]) {
    eventSource.addEventListener(type, consumeEvent);
  }
  eventSource.onerror = () => {
    if (currentReport.status || currentEvents.some((event) => event.event_type === "run_end")) {
      closeEventSource();
      setRunButtons(false);
    }
  };
}

function consumeEvent(message) {
  if (!message.data || message.data === "{}") return;
  const event = JSON.parse(message.data);
  if (event.event_type === "llm_token") appendToken(event.node, event.payload?.token || event.message || "");
  if (!currentEvents.some((item) => item.sequence === event.sequence)) currentEvents.push(event);

  if (event.event_type === "report") {
    currentReport = event.payload?.report || {};
    updateReportLinks(currentRunId);
  }
  if (event.event_type === "run_end") {
    closeEventSource();
    setRunButtons(false);
    if (currentRunId && !currentReport.status) loadRunReport(currentRunId);
  }
  renderAll();
}

async function loadRunReport(runId) {
  try {
    currentReport = await loadJson(`/api/runs/${runId}/report`);
    renderAll();
  } catch (_error) {
    // The final report may be unavailable when the run fails before graph completion.
  }
}

async function loadLatestArtifacts() {
  closeEventSource();
  try {
    const [report, events] = await Promise.all([loadJson(REPORT_URL), loadJsonl(EVENTS_URL)]);
    currentRunId = "";
    currentReport = report;
    currentEvents = events;
    rebuildTokenBuffers(events);
    updateReportLinks("");
    renderAll();
  } catch (error) {
    renderError(error);
  }
}

async function loadJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url} returned ${response.status}`);
  return response.json();
}

async function loadJsonl(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) return [];
  const text = await response.text();
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function renderAll() {
  renderSummary(currentReport, currentEvents);
  renderGraph(currentReport, currentEvents);
  renderTimeline(currentEvents, currentReport);
  renderRounds(currentReport, currentEvents);
}

function renderSummary(report, events) {
  const summary = report.summary || {};
  const last = events.length ? events[events.length - 1] : null;
  setSummary(
    [
      currentRunId ? `Run: ${currentRunId}` : "Latest artifacts",
      `Project: ${report.project_path || value("project-path") || "unknown"}`,
      `Status: ${report.status || last?.message || "running"}`,
      `Runtime: ${report.graph_runtime || "langgraph"}`,
      `Findings: ${(report.llm_review?.findings || []).length}`,
      `Rounds: ${summary.finding_rounds || countRoundEvents(events)}`,
    ].join(" | "),
  );
}

function renderGraph(report, events) {
  const graph = document.getElementById("agent-graph");
  const trace = new Set(report.node_trace || events.filter((event) => event.event_type === "node_end").map((event) => event.node));
  const active = latestActiveNode(events);
  document.getElementById("active-node").textContent = active || "Idle";
  graph.innerHTML = "";

  for (const [id, title, subtitle] of nodes) {
    const item = document.createElement("article");
    item.className = "node";
    if (trace.has(id)) item.classList.add("done");
    if (active === id) item.classList.add("active");
    if (id === "sandbox_validate" && report.sandbox_validation?.status === "failed") item.classList.add("failed");
    item.innerHTML = `<small>${id}</small><strong>${title}</strong><small>${subtitle}</small>`;
    graph.appendChild(item);
  }
}

function renderTimeline(events, report) {
  const timeline = document.getElementById("timeline");
  document.getElementById("event-count").textContent = `${events.length} events`;
  timeline.innerHTML = "";
  if (!events.length) {
    timeline.innerHTML = `<li class="empty">点击 Start Run 后，这里会实时显示 Agent 事件和 LLM token。</li>`;
    return;
  }

  for (const event of compactTimelineEvents(events)) {
    const li = document.createElement("li");
    const time = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : "";
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

function renderRounds(report, events) {
  const rounds = buildDetailedRounds(report, events);
  const target = document.getElementById("rounds");
  document.getElementById("round-count").textContent = `${rounds.length} rounds`;
  target.innerHTML = "";

  if (!rounds.length) {
    target.innerHTML = `<div class="empty">运行到 review / fix / test / sandbox / repair 节点后，这里会显示结构化输出和 LLM token stream。</div>`;
    return;
  }

  for (const round of rounds) {
    const card = document.createElement("article");
    card.className = "round-card detail-card";
    card.innerHTML = `<h3>${escapeHtml(round.title)}</h3>${round.sections.map(renderSection).join("")}`;
    target.appendChild(card);
  }
}

function renderSection(section) {
  if (!section.content || (Array.isArray(section.content) && section.content.length === 0)) return "";
  return `
    <section class="detail-section">
      <h4>${escapeHtml(section.title)}</h4>
      ${renderContent(section.content, section.title)}
    </section>
  `;
}

function renderContent(content, title = "") {
  if (typeof content === "string") return `<p>${escapeHtml(content)}</p>`;
  if (Array.isArray(content)) return `<ul>${content.map((item) => `<li>${renderInline(item)}</li>`).join("")}</ul>`;
  if (content && typeof content === "object" && !Array.isArray(content) && "llm_token_stream" in content) {
    const { llm_token_stream: stream, ...rest } = content;
    const restHtml = hasUsefulContent(rest) ? renderAgentObject(title, rest) : "";
    const streamHtml = stream
      ? `<details class="stream-details"><summary>LLM Token Stream</summary><pre class="token-stream">${escapeHtml(formatTokenStream(stream))}</pre></details>`
      : `<div class="stream-title muted">LLM Token Stream 等待中...</div>`;
    return `${streamHtml}${restHtml}`;
  }
  if (content && typeof content === "object") return renderAgentObject(title, content);
  return `<pre>${escapeHtml(JSON.stringify(content, null, 2))}</pre>`;
}

function renderInline(value) {
  if (typeof value === "string") return escapeHtml(value);
  return `<pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
}

function renderAgentObject(title, value) {
  const normalizedTitle = title.toLowerCase();
  if (normalizedTitle.includes("repo scan")) return renderScanOutput(value);
  if (normalizedTitle.includes("review")) return renderReviewOutput(value);
  if (normalizedTitle.includes("fix planner")) return renderFixPlanOutput(value);
  if (normalizedTitle.includes("code fix")) return renderFixOutput(value);
  if (normalizedTitle.includes("test writer")) return renderTestOutput(value);
  if (normalizedTitle.includes("sandbox")) return renderSandboxOutput(value);
  if (normalizedTitle.includes("repair")) return renderRepairOutput(value);
  if (normalizedTitle.includes("coverage")) return renderCoverageOutput(value);
  return `<pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
}

function renderScanOutput(scan) {
  return `
    ${renderKv({
      status: scan.status,
      source_files: countOf(scan.source_files),
      test_files: countOf(scan.test_files),
      config_files: countOf(scan.config_files),
      dependency_files: countOf(scan.dependency_files),
      package_roots: countOf(scan.package_roots),
      entry_points: countOf(scan.entry_points),
      issue_count: countOf(scan.issues),
    })}
    ${renderObjectList("Scan Issues", scan.issues, ["severity", "path", "message"])}
  `;
}

function renderReviewOutput(report) {
  return `
    ${renderKv({
      status: report.status,
      provider: report.provider,
      model: report.model,
      finding_count: report.summary?.finding_count ?? countOf(report.findings),
    })}
    ${renderObjectList("Findings", report.findings, ["severity", "rule", "file_path", "line", "message", "suggestion"])}
  `;
}

function renderFixPlanOutput(plan) {
  return `
    ${renderKv({
      status: plan.status,
      planner: plan.planner,
      target_count: plan.summary?.target_count ?? countOf(plan.targets),
      remaining_count: plan.summary?.remaining_count,
      rationale: plan.rationale,
      fallback_reason: plan.fallback_reason,
    })}
    ${renderObjectList("Targets", plan.targets, ["finding_index", "severity", "rule", "file_path", "line", "reason"])}
  `;
}

function renderFixOutput(report) {
  return `
    ${renderKv({
      status: report.status,
      applied: report.applied,
      provider: report.provider,
      model: report.model,
      fix_count: report.summary?.fix_count ?? countOf(report.fixes),
      patch_review: report.patch_review ? (report.patch_review.passed ? "passed" : "failed") : "not_run",
      error_summary: report.error_summary,
    })}
    ${renderObjectList("Fixes", report.fixes, [
      "file_path",
      "applied",
      "summary",
      "replacement_sha256",
      "replacement_char_count",
    ])}
    ${renderObjectList("Patch Violations", report.patch_review?.violations || [], [])}
  `;
}

function renderTestOutput(report) {
  const suite = report.suite || {};
  return `
    ${renderKv({
      status: report.status,
      applied: report.applied,
      test_file_path: report.test_file_path,
      generated_test_count: report.summary?.generated_test_count,
      security_check_passed: report.summary?.security_check_passed,
      provider: report.llm_config?.provider,
      model: report.llm_config?.model,
      content_sha256: suite.content_sha256,
      content_char_count: suite.content_char_count,
      error_summary: report.summary?.error_summary,
    })}
    ${renderObjectList("Test Plan", report.test_plan?.items || [], ["qualified_name", "scenario", "reason"])}
    ${renderObjectList("Security Violations", report.security_check?.violations || [], ["rule", "detail", "line"])}
  `;
}

function renderSandboxOutput(report) {
  return `
    ${renderKv({
      status: report.status,
      executor: report.executor,
      passed: report.analysis?.passed,
      total: report.analysis?.total,
      failed: report.analysis?.failed,
      errors: report.analysis?.errors,
      duration_seconds: report.duration_seconds,
    })}
    ${renderObjectList("Key Findings", report.diagnosis?.key_findings || [], [])}
    ${renderObjectList("Suggestions", report.diagnosis?.suggestions || [], [])}
    ${report.stdout ? `<h5>stdout</h5><pre>${escapeHtml(report.stdout)}</pre>` : ""}
    ${report.stderr ? `<h5>stderr</h5><pre>${escapeHtml(report.stderr)}</pre>` : ""}
  `;
}

function renderRepairOutput(report) {
  return `
    ${renderKv({
      status: report.status,
      iteration: report.iteration,
      next_step: report.next_step,
    })}
    ${renderObjectList("Actions", report.actions || [], [])}
  `;
}

function renderCoverageOutput(report) {
  return `
    ${renderKv({
      coverage_ratio: typeof report.coverage_ratio === "number" ? `${Math.round(report.coverage_ratio * 100)}%` : report.coverage_ratio,
      covered_count: countOf(report.covered_functions),
      missing_count: countOf(report.missing_functions),
    })}
    ${renderObjectList("Covered Functions", report.covered_functions || [], [])}
    ${renderObjectList("Missing Functions", report.missing_functions || [], [])}
  `;
}

function renderKv(values) {
  const rows = Object.entries(values)
    .filter(([_key, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`)
    .join("");
  return rows ? `<dl class="kv agent-kv">${rows}</dl>` : "";
}

function renderObjectList(title, items, columns) {
  if (!items || !items.length) return "";
  const normalized = items.map((item) => (typeof item === "object" && item !== null ? item : { value: item }));
  const activeColumns = columns.length ? columns : Object.keys(normalized[0] || {});
  const head = activeColumns.map((column) => `<th>${escapeHtml(column)}</th>`).join("");
  const body = normalized
    .map((item) => `<tr>${activeColumns.map((column) => `<td>${escapeHtml(formatCell(item[column]))}</td>`).join("")}</tr>`)
    .join("");
  return `<h5>${escapeHtml(title)}</h5><div class="table-scroll"><table class="agent-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function formatTokenStream(stream) {
  const text = stream.trim();
  const parsed = parseJsonLike(text);
  if (parsed) return JSON.stringify(redactLargeFields(parsed), null, 2);
  return truncate(text, 5000);
}

function parseJsonLike(text) {
  try {
    return JSON.parse(text);
  } catch (_error) {
    return null;
  }
}

function redactLargeFields(value) {
  if (Array.isArray(value)) return value.map(redactLargeFields);
  if (!value || typeof value !== "object") return value;
  const result = {};
  for (const [key, item] of Object.entries(value)) {
    if (key === "replacement_content" || key === "content" || key === "user" || key === "system") {
      const text = String(item || "");
      result[`${key}_summary`] = `${text.length} chars, hidden in viewer`;
      continue;
    }
    result[key] = redactLargeFields(item);
  }
  return result;
}

function countOf(value) {
  return Array.isArray(value) ? value.length : Number(value || 0);
}

function formatCell(value) {
  if (value === undefined || value === null) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return value;
}

function buildDetailedRounds(report, events) {
  const rounds = [];
  const reviewSections = buildReviewSections(report, events);
  if (reviewSections.length) rounds.push({ title: "Review Output", sections: reviewSections });

  const roundCount = Math.max(
    report.llm_fix_plan_history?.length || 0,
    report.llm_fix_history?.length || 0,
    report.llm_tests_history?.length || 0,
    report.sandbox_validation_history?.length || 0,
    report.repair_history?.length || 0,
    countRoundEvents(events),
    countRoundStarts(events),
  );

  for (let index = 0; index < roundCount; index += 1) {
    rounds.push({
      title: `Round ${index + 1}`,
      sections: [
        buildFixPlanSection(report, events, index),
        buildFixSection(report, events, index),
        buildTestSection(report, events, index),
        buildSandboxSection(report, events, index),
        buildRepairSection(report, events, index),
      ].filter(Boolean),
    });
  }

  const coverageSections = buildCoverageSections(report, events);
  if (coverageSections.length) rounds.push({ title: "Coverage Output", sections: coverageSections });
  return rounds;
}

function buildReviewSections(report, events) {
  const sections = [];
  const scan = report.scan || latestPayload(events, "scan")?.scan;
  if (scan) sections.push({ title: "Repo Scan Agent", content: scan });

  const review = report.llm_review || latestPayload(events, "llm_review")?.llm_review;
  if (review) {
    sections.push({
      title: "LLM Review Agent",
      content: withTokenStream("llm_review", review),
    });
  } else if (hasNodeStarted(events, "llm_review")) {
    sections.push({ title: "LLM Review Agent", content: runningContent("llm_review") });
  }
  return sections;
}

function buildFixPlanSection(report, events, index) {
  const plan = report.llm_fix_plan_history?.[index];
  if (plan) return { title: "Fix Planner Agent", content: withTokenStream("llm_fix_plan", plan) };
  return eventSection(events, "llm_fix_plan", "llm_fix_plan", index, "Fix Planner Agent");
}

function buildFixSection(report, events, index) {
  const fix = report.llm_fix_history?.[index];
  if (fix) return { title: "Code Fix Agent", content: withTokenStream("llm_fix", fix) };
  return eventSection(events, "llm_fix", "llm_fix", index, "Code Fix Agent");
}

function buildTestSection(report, events, index) {
  const tests = report.llm_tests_history?.[index];
  if (tests) return { title: "Test Writer Agent", content: withTokenStream("llm_tests", tests) };
  return eventSection(events, "llm_tests", "llm_tests", index, "Test Writer Agent");
}

function buildSandboxSection(report, events, index) {
  const sandbox = report.sandbox_validation_history?.[index];
  if (sandbox) {
    return {
      title: "Sandbox Validator Agent",
      content: {
        status: sandbox.status,
        executor: sandbox.executor,
        analysis: sandbox.analysis,
        diagnosis: sandbox.diagnosis,
        stdout: truncate(sandbox.execution?.stdout || "", 3000),
        stderr: truncate(sandbox.execution?.stderr || "", 3000),
        command: sandbox.execution?.command,
        duration_seconds: sandbox.execution?.duration_seconds,
      },
    };
  }
  return eventSection(events, "sandbox_validate", "sandbox_validation", index, "Sandbox Validator Agent");
}

function buildRepairSection(report, events, index) {
  const repair = report.repair_history?.[index];
  if (repair) return { title: "Repair Loop Agent", content: repair };
  return eventSection(events, "repair_loop", "repair_loop", index, "Repair Loop Agent");
}

function buildCoverageSections(report, events) {
  const coverage = report.coverage_feedback || latestPayload(events, "coverage_feedback")?.coverage_feedback;
  return coverage ? [{ title: "Coverage Feedback Agent", content: coverage }] : [];
}

function eventSection(events, node, payloadKey, occurrenceIndex, title) {
  const endEvent = nthNodeEnd(events, node, occurrenceIndex);
  if (endEvent) {
    const structured = endEvent.payload?.[payloadKey];
    if (structured && hasUsefulContent(structured)) return { title, content: withTokenStream(node, structured) };
    return {
      title,
      content: {
        status: endEvent.message || "completed",
        detail: "该 Agent 没有返回专属结构化输出。请查看 Timeline 或最终 JSON 报告中的错误字段。",
        llm_token_stream: tokenBuffers[node] || "",
      },
    };
  }
  const startEvent = nthNodeStart(events, node, occurrenceIndex);
  if (startEvent) return { title, content: runningContent(node) };
  return null;
}

function runningContent(node) {
  return {
    status: "running",
    detail: "该 Agent 正在运行，LLM token 会实时追加在 llm_token_stream 字段中；结构化结果会在 node_end 后出现。",
    llm_token_stream: tokenBuffers[node] || "",
  };
}

function latestPayload(events, node) {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.event_type === "node_end" && event.node === node) return event.payload || {};
  }
  return null;
}

function nthNodeEnd(events, node, occurrenceIndex) {
  let seen = 0;
  for (const event of events) {
    if (event.event_type !== "node_end" || event.node !== node) continue;
    if (seen === occurrenceIndex) return event;
    seen += 1;
  }
  return null;
}

function nthNodeStart(events, node, occurrenceIndex) {
  let seen = 0;
  for (const event of events) {
    if (event.event_type !== "node_start" || event.node !== node) continue;
    if (seen === occurrenceIndex) return event;
    seen += 1;
  }
  return null;
}

function hasNodeStarted(events, node) {
  return events.some((event) => event.event_type === "node_start" && event.node === node);
}

function hasUsefulContent(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}

function updateReportLinks(runId) {
  const markdown = document.getElementById("markdown-link");
  const json = document.getElementById("json-link");
  if (runId) {
    markdown.href = `/api/runs/${runId}/markdown`;
    json.href = `/api/runs/${runId}/report`;
  } else {
    markdown.href = "/docs/runs/software_engineer.md";
    json.href = "/docs/runs/software_engineer.json";
  }
}

function latestActiveNode(events) {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    if (events[index].node && events[index].node !== "server" && events[index].node !== "final") return events[index].node;
  }
  return "";
}

function countRoundEvents(events) {
  return events.filter((event) => event.event_type === "node_end" && event.node === "llm_fix_plan").length;
}

function countRoundStarts(events) {
  return events.filter((event) => event.event_type === "node_start" && event.node === "llm_fix_plan").length;
}

function appendToken(node, token) {
  if (!token) return;
  tokenBuffers[node] = (tokenBuffers[node] || "") + token;
}

function rebuildTokenBuffers(events) {
  clearTokenBuffers();
  for (const event of events) {
    if (event.event_type === "llm_token") appendToken(event.node, event.payload?.token || event.message || "");
  }
}

function clearTokenBuffers() {
  for (const key of Object.keys(tokenBuffers)) delete tokenBuffers[key];
}

function withTokenStream(node, content) {
  const stream = tokenBuffers[node] || "";
  if (!stream || typeof content !== "object" || content === null || Array.isArray(content)) return content;
  return { llm_token_stream: stream, ...content };
}

function compactTimelineEvents(events) {
  const compacted = [];
  const tokenStats = {};
  for (const event of events) {
    if (event.event_type === "llm_token") {
      const node = event.node || "llm";
      const token = event.payload?.token || event.message || "";
      tokenStats[node] = tokenStats[node] || {
        event_type: "llm_token",
        node,
        message: "",
        timestamp: event.timestamp,
        count: 0,
        chars: 0,
      };
      tokenStats[node].count += 1;
      tokenStats[node].chars += token.length;
      tokenStats[node].timestamp = event.timestamp;
      tokenStats[node].message = `${tokenStats[node].count} token chunk(s), ${tokenStats[node].chars} chars streamed`;
      continue;
    }
    if (tokenStats[event.node]) {
      compacted.push(tokenStats[event.node]);
      delete tokenStats[event.node];
    }
    compacted.push(event);
  }
  for (const item of Object.values(tokenStats)) compacted.push(item);
  return compacted;
}

function truncate(value, limit) {
  if (!value || value.length <= limit) return value;
  return `${value.slice(0, limit)}\n... truncated ${value.length - limit} chars`;
}

function renderError(error) {
  setSummary("Failed to load run artifacts");
  document.getElementById("agent-graph").innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  document.getElementById("timeline").innerHTML = "";
  document.getElementById("rounds").innerHTML = "";
}

function closeEventSource() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function setRunButtons(isRunning) {
  document.getElementById("start-run").disabled = isRunning;
  document.getElementById("stop-run").disabled = !isRunning;
}

function setSummary(text) {
  document.getElementById("run-summary").textContent = text;
}

function value(id) {
  return document.getElementById(id).value;
}

function checked(id) {
  return document.getElementById(id).checked;
}

function numberValue(id, fallback) {
  const parsed = Number.parseInt(value(id), 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
