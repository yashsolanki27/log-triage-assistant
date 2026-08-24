(() => {
  "use strict";

  const API_BASE = ""; // same-origin

  const CATEGORY_LABELS = {
    "next-tache-error": "Next-tâche error",
    "state-transition-block": "State-transition block",
    "provisioning-fault": "Provisioning fault",
    "api-integration-error": "API-integration error",
    "unclassified": "Unclassified",
  };

  const CATEGORY_VAR = {
    "next-tache-error": "--cat-next-tache",
    "state-transition-block": "--cat-state-transition",
    "provisioning-fault": "--cat-provisioning",
    "api-integration-error": "--cat-api",
    "unclassified": "--cat-unclassified",
  };

  const SAMPLE_LOG = `2024-03-15 10:23:45 ERROR [order-service] - Processing failed
java.lang.NullPointerException: Cannot invoke method getStatus() on null object
    at com.example.OrderProcessor.process(OrderProcessor.java:142)
    at com.example.BatchRunner.run(BatchRunner.java:87)`;

  const main = document.getElementById("main");
  const routeButtons = document.querySelectorAll("[data-route]");

  let historyFilter = "";
  let historyCache = [];

  // ---------------------------------------------------------------------
  // Router
  // ---------------------------------------------------------------------

  function currentRoute() {
    const hash = window.location.hash.replace("#/", "");
    return ["triage", "history", "dashboard"].includes(hash) ? hash : "triage";
  }

  function navigate(route) {
    window.location.hash = `/${route}`;
  }

  function renderRoute() {
    const route = currentRoute();
    routeButtons.forEach((btn) => {
      if (btn.dataset.route === route) {
        btn.setAttribute("aria-current", "page");
      } else {
        btn.removeAttribute("aria-current");
      }
    });

    if (route === "triage") renderTriage();
    else if (route === "history") renderHistory();
    else if (route === "dashboard") renderDashboard();
  }

  routeButtons.forEach((btn) => {
    btn.addEventListener("click", () => navigate(btn.dataset.route));
  });

  window.addEventListener("hashchange", renderRoute);

  // ---------------------------------------------------------------------
  // API helpers
  // ---------------------------------------------------------------------

  async function apiPost(path, body) {
    const res = await fetch(API_BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `Request failed (${res.status})`);
    }
    return data;
  }

  async function apiGet(path) {
    const res = await fetch(API_BASE + path);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `Request failed (${res.status})`);
    }
    return data;
  }

  // ---------------------------------------------------------------------
  // Shared: result card builder
  // ---------------------------------------------------------------------

  function buildResultCard(result) {
    const tpl = document.getElementById("tpl-result-card");
    const node = tpl.content.cloneNode(true);
    const card = node.querySelector(".result-card");

    const catVar = CATEGORY_VAR[result.category] || "--cat-unclassified";
    const badgeDot = card.querySelector(".category-badge .dot");
    badgeDot.style.setProperty("--dot", `var(${catVar})`);
    card.querySelector(".category-name").textContent =
      CATEGORY_LABELS[result.category] || result.category;

    const confidence = Math.max(0, Math.min(100, Math.round(result.confidence)));
    card.querySelector(".gauge-number").textContent = `${confidence}%`;
    const gaugeValue = card.querySelector(".gauge-value");
    const circumference = 157; // matches the arc path length approximation
    const offset = circumference - (circumference * confidence) / 100;
    gaugeValue.style.setProperty("--dot", "");
    requestAnimationFrame(() => {
      gaugeValue.style.strokeDashoffset = String(offset);
    });
    if (confidence < 70) {
      gaugeValue.style.stroke = "var(--danger)";
    } else if (confidence < 85) {
      gaugeValue.style.stroke = "var(--accent)";
    } else {
      gaugeValue.style.stroke = "var(--info)";
    }

    card.querySelector(".extracted-line").textContent = result.extracted_error_line || "—";
    card.querySelector(".summary-text").textContent = result.root_cause_summary || "—";
    card.querySelector(".action-text").textContent = result.suggested_action || "—";

    const unclassifiedBlock = card.querySelector(".unclassified-block");
    if (result.unclassified_reason) {
      unclassifiedBlock.hidden = false;
      card.querySelector(".unclassified-text").textContent = result.unclassified_reason;
    }

    card.querySelector(".raw-text").textContent = result.raw_text || "";

    return card;
  }

  // ---------------------------------------------------------------------
  // View: Triage
  // ---------------------------------------------------------------------

  function renderTriage() {
    const tpl = document.getElementById("tpl-triage");
    main.replaceChildren(tpl.content.cloneNode(true));

    const form = document.getElementById("triage-form");
    const textarea = document.getElementById("log-input");
    const charCount = document.getElementById("char-count");
    const submitBtn = document.getElementById("btn-submit");
    const errorBox = document.getElementById("triage-error");
    const resultPanel = document.getElementById("result-panel");

    textarea.addEventListener("input", () => {
      charCount.textContent = `${textarea.value.length} characters`;
    });

    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        form.requestSubmit();
      }
    });

    document.getElementById("btn-sample").addEventListener("click", () => {
      loadRandomSample();
    });

    document.getElementById("btn-browse-samples").addEventListener("click", () => {
      toggleSampleLogs();
    });

    document.getElementById("btn-clear").addEventListener("click", () => {
      textarea.value = "";
      textarea.dispatchEvent(new Event("input"));
      resultPanel.hidden = true;
      errorBox.hidden = true;
      textarea.focus();
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const logText = textarea.value.trim();
      if (!logText) return;

      errorBox.hidden = true;
      resultPanel.hidden = true;
      submitBtn.disabled = true;
      submitBtn.classList.add("is-loading");

      try {
        const result = await apiPost("/triage", { log_text: logText });
        resultPanel.replaceChildren(buildResultCard(result));
        resultPanel.hidden = false;
      } catch (err) {
        errorBox.textContent = describeError(err);
        errorBox.hidden = false;
      } finally {
        submitBtn.disabled = false;
        submitBtn.classList.remove("is-loading");
      }
    });
  }

  function describeError(err) {
    const msg = err && err.message ? err.message : "Something went wrong.";
    if (msg.includes("API key configured") || msg.includes("API_KEY") || msg.includes("OPENCODE_API_KEY") || msg.includes("GROQ_API_KEY")) {
      return "The classifier isn't configured yet — set GROQ_API_KEY (or OPENCODE_API_KEY / OPENAI_API_KEY) on the server.";
    }
    if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
      return "Couldn't reach the API. Confirm the backend is running.";
    }
    return msg;
  }

  // ---------------------------------------------------------------------
  // View: History
  // ---------------------------------------------------------------------

  function renderHistory() {
    const tpl = document.getElementById("tpl-history");
    main.replaceChildren(tpl.content.cloneNode(true));

    const list = document.getElementById("history-list");
    const empty = document.getElementById("history-empty");
    const chips = document.querySelectorAll("#category-filters .chip");

    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        chips.forEach((c) => c.classList.remove("is-active"));
        chip.classList.add("is-active");
        historyFilter = chip.dataset.cat;
        loadHistory();
      });
    });

    document.getElementById("btn-refresh-history").addEventListener("click", loadHistory);

    async function loadHistory() {
      list.innerHTML = `<p class="field-hint">Loading…</p>`;
      empty.hidden = true;
      try {
        const query = historyFilter ? `?category=${encodeURIComponent(historyFilter)}` : "";
        const items = await apiGet(`/history${query}`);
        historyCache = items;
        renderList(items);
      } catch (err) {
        list.innerHTML = "";
        empty.hidden = false;
        empty.querySelector("p").textContent = describeError(err);
      }
    }

    function renderList(items) {
      list.innerHTML = "";
      if (!items.length) {
        empty.hidden = false;
        return;
      }
      items.forEach((item) => {
        const el = document.createElement("div");
        el.className = "history-item";
        const catVar = CATEGORY_VAR[item.category] || "--cat-unclassified";
        el.innerHTML = `
          <div class="history-item-top">
            <span class="history-item-cat"><span class="dot" style="--dot: var(${catVar})"></span>${
              CATEGORY_LABELS[item.category] || item.category
            }</span>
            <span class="history-item-conf">${Math.round(item.confidence)}% confidence</span>
          </div>
          <p class="history-item-line">${escapeHtml(item.extracted_error_line)}</p>
          <p class="history-item-summary">${escapeHtml(item.root_cause_summary)}</p>
          <div class="history-item-top" style="margin-top:8px; margin-bottom:0;">
            <span class="history-item-time">${formatTime(item.created_at)}</span>
          </div>
        `;
        const detailHolder = document.createElement("div");
        detailHolder.className = "history-detail-panel";
        detailHolder.hidden = true;
        el.appendChild(detailHolder);

        el.addEventListener("click", (e) => {
          if (e.target.closest("details")) return;
          const isOpen = !detailHolder.hidden;
          document
            .querySelectorAll(".history-detail-panel")
            .forEach((p) => (p.hidden = true));
          detailHolder.hidden = isOpen;
          if (!isOpen) {
            detailHolder.replaceChildren(buildResultCard(item));
          }
        });

        list.appendChild(el);
      });
    }

    loadHistory();
  }

  function formatTime(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }

  // ---------------------------------------------------------------------
  // View: Dashboard
  // ---------------------------------------------------------------------

  async function renderDashboard() {
    const tpl = document.getElementById("tpl-dashboard");
    main.replaceChildren(tpl.content.cloneNode(true));

    const statGrid = document.getElementById("stat-grid");
    const donutWrap = document.getElementById("donut-wrap");
    const trendWrap = document.getElementById("trend-wrap");

    statGrid.innerHTML = `<p class="field-hint">Loading…</p>`;

    try {
      const stats = await apiGet("/stats");
      renderStatGrid(stats);
      renderDonut(stats);
      renderTrend(stats);
    } catch (err) {
      statGrid.innerHTML = `<div class="alert alert-error">${escapeHtml(describeError(err))}</div>`;
    }

    function renderStatGrid(stats) {
      const topCategory = Object.entries(stats.by_category || {})
        .filter(([cat]) => cat !== "unclassified")
        .sort((a, b) => b[1].count - a[1].count)[0];

      statGrid.innerHTML = `
        <div class="stat-card">
          <p class="stat-label">Total triaged</p>
          <p class="stat-value">${stats.total}</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">Unclassified rate</p>
          <p class="stat-value ${stats.unclassified_rate > 20 ? "danger" : ""}">${stats.unclassified_rate}%</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">Top category</p>
          <p class="stat-value accent" style="font-size:18px;">${
            topCategory ? CATEGORY_LABELS[topCategory[0]] : "—"
          }</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">Last 14 days</p>
          <p class="stat-value">${(stats.trend || []).reduce((s, d) => s + d.count, 0)}</p>
        </div>
      `;
    }

    function renderDonut(stats) {
      const entries = Object.entries(stats.by_category || {});
      if (!entries.length) {
        donutWrap.innerHTML = emptyStateHtml("No data yet — triage a log to populate this chart.");
        return;
      }
      const total = entries.reduce((s, [, v]) => s + v.count, 0);
      const radius = 60;
      const circumference = 2 * Math.PI * radius;
      let offsetAcc = 0;

      const segments = entries
        .map(([cat, v]) => {
          const frac = total ? v.count / total : 0;
          const dash = frac * circumference;
          const seg = `<circle cx="90" cy="90" r="${radius}" fill="none"
            stroke="var(${CATEGORY_VAR[cat] || "--cat-unclassified"})" stroke-width="20"
            stroke-dasharray="${dash} ${circumference - dash}"
            stroke-dashoffset="${-offsetAcc}"
            transform="rotate(-90 90 90)" />`;
          offsetAcc += dash;
          return seg;
        })
        .join("");

      const legend = entries
        .sort((a, b) => b[1].count - a[1].count)
        .map(
          ([cat, v]) => `
          <div class="donut-legend-item">
            <span class="dot" style="--dot: var(${CATEGORY_VAR[cat] || "--cat-unclassified"})"></span>
            ${CATEGORY_LABELS[cat] || cat}
            <strong>${v.count}</strong>
          </div>`
        )
        .join("");

      donutWrap.innerHTML = `
        <svg viewBox="0 0 180 180" width="180" height="180">${segments}
          <text x="90" y="86" text-anchor="middle" font-family="Space Grotesk, sans-serif"
            font-size="26" font-weight="700" fill="var(--text-primary)">${total}</text>
          <text x="90" y="106" text-anchor="middle" font-family="Inter, sans-serif"
            font-size="10" fill="var(--text-tertiary)" letter-spacing="0.06em">TOTAL</text>
        </svg>
        <div class="donut-legend">${legend}</div>
      `;
    }

    function renderTrend(stats) {
      const trend = stats.trend || [];
      if (!trend.length) {
        trendWrap.innerHTML = emptyStateHtml("No data yet — trend will appear after a few days of triage activity.");
        return;
      }
      const max = Math.max(1, ...trend.map((d) => d.count));
      const bars = trend
        .map((d) => {
          const pct = Math.max(4, Math.round((d.count / max) * 100));
          const label = new Date(d.day).toLocaleDateString(undefined, { day: "numeric", month: "short" }).replace(" ", "\u00A0");
          return `
          <div class="trend-bar-col">
            <div class="trend-bar" style="height:${pct}%" title="${d.count} on ${d.day}"></div>
            <span class="trend-bar-label">${label}</span>
          </div>`;
        })
        .join("");
      trendWrap.innerHTML = `<div class="trend-bars">${bars}</div>`;
    }
  }

  function emptyStateHtml(msg) {
    return `<div class="empty-state" style="padding: var(--space-6) var(--space-3);">
      <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19V10M11 19V5M18 19v-7" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <p class="empty-sub">${escapeHtml(msg)}</p>
    </div>`;
  }

  // ---------------------------------------------------------------------
  // Sample Logs (inline panel)
  // ---------------------------------------------------------------------

  let allSampleLogs = [];
  let sampleFilter = "";

  async function toggleSampleLogs() {
    const panel = document.getElementById("sample-logs-panel");
    if (!panel) return;

    if (!panel.hidden) {
      panel.hidden = true;
      return;
    }

    panel.hidden = false;
    const list = document.getElementById("sample-logs-list");
    const empty = document.getElementById("sample-logs-empty");
    list.innerHTML = `<p class="field-hint">Loading sample logs...</p>`;
    empty.hidden = true;

    try {
      if (!allSampleLogs.length) {
        allSampleLogs = await apiGet("/sample-logs");
      }
      renderSampleLogsList(allSampleLogs);
      buildTagFilters(allSampleLogs);
    } catch (err) {
      list.innerHTML = `<div class="alert alert-error">${escapeHtml(describeError(err))}</div>`;
    }

    const searchInput = document.getElementById("sample-search");
    if (searchInput) searchInput.value = "";
    sampleFilter = "";
  }

  function buildTagFilters(logs) {
    const tags = [...new Set(logs.map((l) => l.tag))].sort();
    const container = document.getElementById("sample-tag-filters");
    if (!container) return;
    container.innerHTML = `<button class="chip is-active" data-tag="">All</button>`;
    tags.forEach((tag) => {
      const btn = document.createElement("button");
      btn.className = "chip";
      btn.dataset.tag = tag;
      btn.textContent = tag.replace(/-/g, " ");
      container.appendChild(btn);
    });
    container.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        container.querySelectorAll(".chip").forEach((c) => c.classList.remove("is-active"));
        chip.classList.add("is-active");
        sampleFilter = chip.dataset.tag;
        filterAndRenderSamples();
      });
    });
  }

  function filterAndRenderSamples() {
    const searchInput = document.getElementById("sample-search");
    const search = searchInput ? searchInput.value.toLowerCase() : "";
    let filtered = allSampleLogs;
    if (sampleFilter) {
      filtered = filtered.filter((l) => l.tag === sampleFilter);
    }
    if (search) {
      filtered = filtered.filter(
        (l) =>
          l.title.toLowerCase().includes(search) ||
          l.tag.toLowerCase().includes(search)
      );
    }
    renderSampleLogsList(filtered);
  }

  function renderSampleLogsList(logs) {
    const list = document.getElementById("sample-logs-list");
    const empty = document.getElementById("sample-logs-empty");
    if (!list) return;
    list.innerHTML = "";

    if (!logs.length) {
      empty.hidden = false;
      return;
    }
    empty.hidden = true;

    logs.forEach((log) => {
      const el = document.createElement("div");
      el.className = "sample-log-item";
      el.innerHTML = `
        <div class="sample-log-header">
          <span class="sample-log-title">${escapeHtml(log.title)}</span>
          <span class="sample-log-tag chip chip-sm">${escapeHtml(log.tag)}</span>
        </div>
        <pre class="sample-log-preview">${escapeHtml(log.log_text.substring(0, 150))}${log.log_text.length > 150 ? "..." : ""}</pre>
      `;
      el.addEventListener("click", () => {
        loadSampleLog(log);
      });
      list.appendChild(el);
    });
  }

  function loadSampleLog(log) {
    const textarea = document.getElementById("log-input");
    const charCount = document.getElementById("char-count");
    const panel = document.getElementById("sample-logs-panel");
    if (textarea) {
      textarea.value = log.log_text;
      textarea.dispatchEvent(new Event("input"));
      if (charCount) charCount.textContent = `${log.log_text.length} characters`;
    }
    if (panel) panel.hidden = true;
    if (textarea) textarea.focus();
  }

  let lastRandomSampleIndex = -1;

  async function loadRandomSample() {
    const textarea = document.getElementById("log-input");
    const charCount = document.getElementById("char-count");
    if (!textarea) return;

    try {
      if (!allSampleLogs.length) {
        allSampleLogs = await apiGet("/sample-logs");
      }
      if (allSampleLogs && allSampleLogs.length > 0) {
        let nextIndex;
        if (allSampleLogs.length > 1) {
          do {
            nextIndex = Math.floor(Math.random() * allSampleLogs.length);
          } while (nextIndex === lastRandomSampleIndex);
        } else {
          nextIndex = 0;
        }
        lastRandomSampleIndex = nextIndex;
        const picked = allSampleLogs[nextIndex];
        textarea.value = picked.log_text;
      } else {
        textarea.value = SAMPLE_LOG;
      }
    } catch {
      textarea.value = SAMPLE_LOG;
    }

    textarea.dispatchEvent(new Event("input"));
    if (charCount) charCount.textContent = `${textarea.value.length} characters`;
    textarea.focus();
  }

  // ---------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------

  if (!window.location.hash) {
    window.location.hash = "/triage";
  }
  renderRoute();

  document.getElementById("btn-close-samples").addEventListener("click", () => {
    const panel = document.getElementById("sample-logs-panel");
    if (panel) panel.hidden = true;
  });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const panel = document.getElementById("sample-logs-panel");
    if (panel && !panel.hidden) {
      panel.hidden = true;
      e.stopPropagation();
    }
  });

  document.getElementById("sample-search").addEventListener("input", filterAndRenderSamples);
})();
