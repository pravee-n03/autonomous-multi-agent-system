/**
 * Autonomous Multi-Agent Studio — Frontend Controller
 * Real-time WebSocket streaming with agent_start & agent_step synchronization,
 * live telemetry updates, autonomous tool execution logging, and executive report viewer.
 */

const AGENTS = [
    { id: "planner",           number: "01", name: "Planner",          role: "Architect",       icon: "📋" },
    { id: "research_plan",     number: "02", name: "Research",         role: "Investigator",    icon: "🔍" },
    { id: "generate",          number: "03", name: "Synthesizer",      role: "Writer",          icon: "✍️" },
    { id: "reflect",           number: "04", name: "Quality Gate",     role: "Auditor",         icon: "⚖️" },
    { id: "research_critique", number: "05", name: "Fact-Checker",     role: "Remediator",      icon: "🧪" },
];

const GRAPH_ORDER = ["planner", "research_plan", "generate", "reflect", "research_critique"];

let completedAgents = new Set();
let currentAgent = null;
let ws = null;
let toolCallCounter = 0;
let currentDraftMarkdown = "";

// ── Quick Presets ─────────────────────────────────────────────────
function setPreset(text) {
    const input = document.getElementById("taskInput");
    input.value = text;
    input.focus();
}

// ── Reset to New Run ──────────────────────────────────────────────
function resetToNewRun() {
    const inputSection = document.getElementById("inputSection");
    inputSection.style.display = "block";
    inputSection.scrollIntoView({ behavior: "smooth", block: "start" });
    document.getElementById("taskInput").focus();
}

// ── Render Workflow Topology ──────────────────────────────────────
function renderWorkflowGraph() {
    const container = document.getElementById("workflowGraph");
    container.innerHTML = "";

    GRAPH_ORDER.forEach((agentId, index) => {
        const agent = AGENTS.find(a => a.id === agentId);

        if (index > 0) {
            const arrow = document.createElement("div");
            arrow.className = "wf-arrow";
            arrow.id = `arrow-${agentId}`;
            arrow.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12 5 19 12 12 19"></polyline>
                </svg>`;
            container.appendChild(arrow);
        }

        const node = document.createElement("div");
        node.className = "wf-node";
        node.id = `node-${agentId}`;
        node.innerHTML = `
            <div class="wf-node-icon">${agent.icon}</div>
            <div class="wf-node-name">${agent.number}. ${agent.name}</div>
            <div class="wf-node-role">${agent.role}</div>`;

        container.appendChild(node);
    });

    const loopLabel = document.createElement("div");
    loopLabel.className = "wf-loop-label";
    loopLabel.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
        Audit Loop: Score &lt; 8 ➔ Fact-Checker ➔ Revise`;
    container.appendChild(loopLabel);
}

// ── Start Multi-Agent Workflow ────────────────────────────────────
function startWorkflow() {
    const taskInput = document.getElementById("taskInput");
    const revisionsInput = document.getElementById("revisionsInput");

    const task = taskInput.value.trim();
    if (!task) {
        taskInput.focus();
        return;
    }

    completedAgents.clear();
    currentAgent = null;
    toolCallCounter = 0;
    currentDraftMarkdown = "";

    // Show persistent "New Task" button in header
    const btnNewRun = document.getElementById("btnNewRun");
    if (btnNewRun) btnNewRun.style.display = "inline-flex";

    // Reset Telemetry
    document.getElementById("activeAgentVal").textContent = "01. Planner (Architect)";
    document.getElementById("toolCallsVal").textContent = "0";
    document.getElementById("qualityScoreVal").textContent = "— / 10";
    const verdictEl = document.getElementById("verdictVal");
    verdictEl.textContent = "Awaiting Evaluation";
    verdictEl.className = "telemetry-badge verdict-pending";

    // Switch view
    document.getElementById("inputSection").style.display = "none";
    const opsSection = document.getElementById("workflowSection");
    opsSection.style.display = "block";
    opsSection.scrollIntoView({ behavior: "smooth", block: "start" });

    renderWorkflowGraph();

    document.getElementById("activityLog").innerHTML = `
        <div class="activity-empty">
            <div class="clean-spinner"></div>
            <p>Deploying autonomous agents & establishing live tool streams…</p>
        </div>`;

    document.getElementById("reportContent").innerHTML = `
        <div class="document-placeholder">
            <div class="doc-icon-wrap">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#a1a1aa" stroke-width="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
            </div>
            <h4>Synthesizing Executive Report</h4>
            <p>The report will render here with full typography as the Generation Agent synthesizes verified research.</p>
        </div>`;

    setStatus("running", "Agents Active");

    // Open WebSocket
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws/run`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        ws.send(JSON.stringify({
            task: task,
            max_revisions: parseInt(revisionsInput.value, 10),
        }));
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWorkflowEvent(data);
    };

    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        setStatus("error", "Network Error");
    };

    ws.onclose = () => {
        setStatus("complete", "Orchestration Complete");
    };
}

// ── Event Router ──────────────────────────────────────────────────
function handleWorkflowEvent(data) {
    switch (data.type) {
        case "workflow_start":
            setAgentActive("planner");
            document.getElementById("activeAgentVal").textContent = "01. Planner (Architect)";
            break;

        case "agent_start":
            handleAgentStart(data);
            break;

        case "agent_step":
            handleAgentStep(data);
            break;

        case "workflow_complete":
            handleWorkflowComplete();
            break;

        case "error":
            handleWorkflowError(data.message);
            break;
    }
}

// ── Agent Start Handler (Live Real-Time Signal) ───────────────────
function handleAgentStart(data) {
    const { agent_id, agent_name, agent_role, agent_icon, revision_number } = data;
    const meta = AGENTS.find(a => a.id === agent_id);
    const agentNum = meta ? meta.number : "";

    setAgentActive(agent_id);

    // Update Telemetry
    const actionLabelMap = {
        "planner": "Formulating research blueprint & strategic targets",
        "research_plan": "Searching live web & gathering authoritative data",
        "generate": revision_number > 1 ? `Revising draft to v${revision_number} with enriched evidence` : "Synthesizing research into Initial Draft (v1)",
        "reflect": "Auditing draft against factual depth & citation benchmarks",
        "research_critique": "Surgically querying web for missing metrics flagged by Quality Gate"
    };

    const actionText = actionLabelMap[agent_id] || "Executing autonomous task";
    document.getElementById("activeAgentVal").textContent = `${agentNum}. ${agent_name} (${agent_role})`;

    if (agent_id === "reflect") {
        document.getElementById("qualityScoreVal").innerHTML = `<span style="font-size:0.85rem; color:#b45309; font-weight:700;">Auditing...</span>`;
        const verdictEl = document.getElementById("verdictVal");
        verdictEl.textContent = "Auditing Standards...";
        verdictEl.className = "telemetry-badge verdict-revise";
    }

    // Insert live "in-progress" card in feed
    appendInProgressCard({
        agent_id,
        agent_name,
        agent_role,
        agent_icon,
        actionText
    });
}

function appendInProgressCard(info) {
    const log = document.getElementById("activityLog");
    const emptyNotice = log.querySelector(".activity-empty");
    if (emptyNotice) emptyNotice.remove();

    // Remove existing in-progress card if any
    const existingActive = document.getElementById("active-card-in-progress");
    if (existingActive) existingActive.remove();

    const activeCard = document.createElement("div");
    activeCard.id = "active-card-in-progress";
    activeCard.className = "activity-entry active-running";
    activeCard.innerHTML = `
        <div class="activity-entry-header" style="background: #fafafa; border-bottom: none;">
            <div class="agent-badge">
                ${info.agent_icon}
            </div>
            <div class="agent-info">
                <div class="agent-name-flex">
                    <span class="agent-name">${info.agent_name}</span>
                    <span class="agent-role-tag">${info.agent_role}</span>
                    <span class="live-pill">IN PROGRESS</span>
                </div>
                <div class="agent-desc" style="color: #27272a; font-weight: 500; margin-top: 3px;">
                    <span class="mini-spinner"></span> ${escapeHtml(info.actionText)}
                </div>
            </div>
        </div>`;

    log.appendChild(activeCard);
    log.scrollTop = log.scrollHeight;
}

// ── Agent Step Completion Handler ─────────────────────────────────
function handleAgentStep(data) {
    const { agent_id, agent_name, agent_icon, agent_role, reasoning, tool_calls, quality_score, pass_decision, output, detail, revision_number } = data;

    // Remove active in-progress placeholder
    const existingActive = document.getElementById("active-card-in-progress");
    if (existingActive) existingActive.remove();

    // Mark node completed
    setAgentCompleted(agent_id);

    // Update tool call counter
    if (tool_calls && tool_calls.length > 0) {
        toolCallCounter += tool_calls.length;
        document.getElementById("toolCallsVal").textContent = toolCallCounter;
    }

    // Update Quality Score & Verdict immediately
    if (quality_score !== null && quality_score !== undefined && quality_score > 0) {
        document.getElementById("qualityScoreVal").textContent = `${quality_score} / 10`;
        const verdictEl = document.getElementById("verdictVal");
        if (pass_decision) {
            verdictEl.textContent = "PASSED (Certified ✓)";
            verdictEl.className = "telemetry-badge verdict-pass";
        } else {
            verdictEl.textContent = "REVISION REQUIRED (Gaps Found)";
            verdictEl.className = "telemetry-badge verdict-revise";
        }
    }

    // Append full completed activity card
    appendActivityCard({
        agent_id,
        agent_name,
        agent_icon,
        agent_role,
        reasoning,
        tool_calls,
        quality_score,
        pass_decision,
        output,
        detail,
        revision_number
    });

    // Update Report panel if this step generated or revised a draft
    if (agent_id === "generate" && output) {
        updateReport(output, revision_number || 1);
    }
}

function appendActivityCard(step) {
    const log = document.getElementById("activityLog");
    const emptyNotice = log.querySelector(".activity-empty");
    if (emptyNotice) emptyNotice.remove();

    const entry = document.createElement("div");
    entry.className = "activity-entry expanded";

    let toolsHtml = "";
    if (step.tool_calls && step.tool_calls.length > 0) {
        toolsHtml = `
            <div class="agent-tool-section">
                <div class="tool-section-title">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    Live Web Queries Executed (${step.tool_calls.length})
                </div>
                <div class="tools-list">
                    ${step.tool_calls.map(tc => `
                        <div class="tool-call-item">
                            <div class="tool-call-badge">
                                <span class="tool-name">${tc.tool}</span>
                                <span class="tool-query">"${escapeHtml(tc.query)}"</span>
                                <span class="tool-status ${tc.status === 'success' ? 'status-ok' : 'status-warn'}">${tc.status}</span>
                            </div>
                            ${tc.sources && tc.sources.length > 0 ? `
                                <div class="tool-sources">
                                    ${tc.sources.map(s => `
                                        <a href="${s.url}" target="_blank" rel="noopener noreferrer" class="source-tag" title="${escapeHtml(s.title)}">
                                            ↗ ${escapeHtml(s.title || s.url)}
                                        </a>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>`;
    }

    let qualityGateHtml = "";
    if (step.agent_id === "reflect" && step.quality_score) {
        qualityGateHtml = `
            <div class="quality-gate-box ${step.pass_decision ? 'gate-pass' : 'gate-revise'}">
                <div class="gate-header">
                    <div class="gate-score-badge">
                        <span class="gate-score-num">${step.quality_score}</span>
                        <span class="gate-score-max">/ 10</span>
                    </div>
                    <div class="gate-verdict-title">
                        <strong>${step.pass_decision ? 'Quality Standards Verified — Certified Pass' : 'Deficiencies Identified — Surgical Revision Required'}</strong>
                        <p>${step.pass_decision ? 'Report satisfies factual depth, structural standards, and editorial rigor.' : 'Targeted Fact-Checker agent will search specifically for missing evidence.'}</p>
                    </div>
                </div>
            </div>`;
    }

    let reasoningHtml = "";
    if (step.reasoning && (step.reasoning.full_thought || step.reasoning.summary)) {
        const thought = step.reasoning.full_thought || step.reasoning.summary;
        reasoningHtml = `
            <div class="reasoning-block">
                <div class="reasoning-label">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                    Strategic Reasoning
                </div>
                <div class="reasoning-text">${escapeHtml(thought)}</div>
            </div>`;
    }

    entry.innerHTML = `
        <div class="activity-entry-header" onclick="toggleEntry(this)">
            <div class="agent-badge">
                ${step.agent_icon}
            </div>
            <div class="agent-info">
                <div class="agent-name-flex">
                    <span class="agent-name">${step.agent_name}</span>
                    <span class="agent-role-tag">${step.agent_role}</span>
                </div>
                <div class="agent-desc">${escapeHtml(step.agent_description || '')}</div>
            </div>
            <div class="entry-toggle">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
            </div>
        </div>
        <div class="activity-entry-body">
            ${reasoningHtml}
            ${toolsHtml}
            ${qualityGateHtml}
            <div class="activity-output-wrapper">
                <div class="output-label">Payload & Result</div>
                <div class="activity-entry-content">${escapeHtml(step.output || step.detail || '')}</div>
            </div>
        </div>`;

    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function toggleEntry(header) {
    const entry = header.parentElement;
    entry.classList.toggle("expanded");
}

// ── Graph Node Visuals ────────────────────────────────────────────
function setAgentActive(agentId) {
    if (currentAgent && currentAgent !== agentId) {
        const prevNode = document.getElementById(`node-${currentAgent}`);
        if (prevNode) prevNode.classList.remove("active");
    }

    currentAgent = agentId;
    const node = document.getElementById(`node-${agentId}`);
    if (node) {
        node.classList.add("active");
        node.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }

    const arrow = document.getElementById(`arrow-${agentId}`);
    if (arrow) arrow.classList.add("active");
}

function setAgentCompleted(agentId) {
    completedAgents.add(agentId);
    const node = document.getElementById(`node-${agentId}`);
    if (node) {
        node.classList.remove("active");
        node.classList.add("completed");
    }
}

function handleWorkflowComplete() {
    if (currentAgent) {
        const node = document.getElementById(`node-${currentAgent}`);
        if (node) node.classList.remove("active");
    }
    setStatus("complete", "Complete");
    document.getElementById("activeAgentVal").textContent = "All 5 Agents Completed ✓";

    const badge = document.getElementById("revisionBadge");
    if (badge) {
        badge.textContent = "Verified Final Brief (Certified ✓)";
        badge.className = "revision-pill badge-verified";
    }
}

function handleWorkflowError(message) {
    setStatus("error", "Execution Notice");
    const log = document.getElementById("activityLog");
    const errorEntry = document.createElement("div");
    errorEntry.className = "activity-entry";
    errorEntry.innerHTML = `
        <div class="activity-entry-header" style="background: #fff1f2; border-color: #fecdd3;">
            <div class="agent-badge" style="background: #fee2e2; border-color: #fca5a5;">⚠️</div>
            <div class="agent-info">
                <div class="agent-name" style="color: #991b1b;">Workflow Notice</div>
                <div class="agent-desc" style="color: #b91c1c;">${escapeHtml(message)}</div>
            </div>
        </div>`;
    log.appendChild(errorEntry);
}

// ── Markdown Document Renderer ────────────────────────────────────
function updateReport(markdownText, revisionNumber) {
    currentDraftMarkdown = markdownText;
    const reportContent = document.getElementById("reportContent");
    const badge = document.getElementById("revisionBadge");

    const draftLabel = revisionNumber <= 1 ? "Draft v1 (Initial Synthesis)" : `Draft v${revisionNumber} (Enriched Revision)`;
    badge.textContent = draftLabel;
    badge.style.display = "inline-block";

    reportContent.innerHTML = renderMarkdown(markdownText);
}

function copyReport() {
    if (!currentDraftMarkdown) {
        alert("No report generated yet.");
        return;
    }
    navigator.clipboard.writeText(currentDraftMarkdown).then(() => {
        const btn = document.getElementById("btnCopy");
        const orig = btn.innerHTML;
        btn.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>Copied!</span>`;
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
    });
}

function renderMarkdown(text) {
    if (!text) return "";
    let html = escapeHtml(text);

    // Headers
    html = html.replace(/^######\s+(.*)$/gm, '<h6>$1</h6>');
    html = html.replace(/^#####\s+(.*)$/gm, '<h5>$1</h5>');
    html = html.replace(/^####\s+(.*)$/gm, '<h4>$1</h4>');
    html = html.replace(/^###\s+(.*)$/gm, '<h3>$1</h3>');
    html = html.replace(/^##\s+(.*)$/gm, '<h2>$1</h2>');
    html = html.replace(/^#\s+(.*)$/gm, '<h1>$1</h1>');

    // Bold and Italic
    html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Lists
    html = html.replace(/^[-*]\s+(.*)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');

    // Paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';

    // Cleanup empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p>(\s*<h[1-6]>)/g, '$1');
    html = html.replace(/(<\/h[1-6]>\s*)<\/p>/g, '$1');
    html = html.replace(/<p>(\s*<ul>)/g, '$1');
    html = html.replace(/(<\/ul>\s*)<\/p>/g, '$1');

    return html;
}

// ── Helpers ───────────────────────────────────────────────────────
function setStatus(state, text) {
    const dot = document.querySelector(".status-dot");
    const statusText = document.querySelector(".status-text");
    if (dot) dot.className = "status-dot " + state;
    if (statusText) statusText.textContent = text;
}

function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = String(text);
    return div.innerHTML;
}
