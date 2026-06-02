import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let currentScreen = "config";
let migrationConfig = null;
let schemaMapping = null;

function showScreen(name) {
  $$(".screen").forEach((s) => s.classList.remove("active"));
  $(`#screen-${name}`).classList.add("active");
  $$(".nav-btn").forEach((b) => b.classList.remove("active"));
  $$(`.nav-btn[data-screen="${name}"]`).forEach((b) => {
    b.classList.add("active");
    b.disabled = false;
  });
  currentScreen = name;
}

function showLoading(text = "Carregando...") {
  $("#loading-text").textContent = text;
  $("#loading-overlay").classList.remove("hidden");
}

function hideLoading() {
  $("#loading-overlay").classList.add("hidden");
}

function toast(msg, type = "success") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  $("#toast-container").appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function formatNumber(n) {
  return n.toLocaleString("pt-BR");
}

function formatETA(seconds) {
  if (seconds == null || seconds < 0) return "--";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m${s.toString().padStart(2, "0")}s`;
}

// ---- SCREEN: Config ----

$("#config-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  migrationConfig = {
    source_dialect: $("#source-dialect").value,
    source_dsn: $("#source-dsn").value,
    target_dialect: $("#target-dialect").value,
    target_dsn: $("#target-dsn").value,
    ai_provider: $("#ai-provider").value,
    ai_model: $("#ai-model").value || null,
    ai_key: $("#ai-key").value,
    batch_size: parseInt($("#batch-size").value, 10),
  };

  showLoading("Analisando schema com IA...");
  try {
    const result = await invoke("analyze_schema", { config: migrationConfig });
    schemaMapping = result;
    renderMapping(result);
    showScreen("preview");
    toast("Schema mapeado com sucesso!");
  } catch (err) {
    toast(`Erro: ${err}`, "error");
  } finally {
    hideLoading();
  }
});

// ---- SCREEN: Preview ----

function renderMapping(mapping) {
  const container = $("#mapping-container");
  container.innerHTML = "";

  for (const table of mapping.tables) {
    const tableEl = document.createElement("table");
    tableEl.className = "mapping-table";
    tableEl.innerHTML = `
      <caption>${table.source_table} → ${table.target_table}</caption>
      <thead>
        <tr>
          <th>Coluna Origem</th>
          <th>Tipo Origem</th>
          <th>Coluna Destino</th>
          <th>Tipo Destino</th>
          <th>Transform</th>
        </tr>
      </thead>
      <tbody>
        ${table.columns
          .map(
            (col) => `<tr>
          <td>${col.source_name}</td>
          <td><code>${col.source_type}</code></td>
          <td>${col.target_name}</td>
          <td><code>${col.target_type}</code></td>
          <td class="transform">${col.transform || "—"}</td>
        </tr>`
          )
          .join("")}
      </tbody>
    `;
    container.appendChild(tableEl);
  }

  const warningsEl = $("#warnings-container");
  warningsEl.innerHTML = "";
  if (mapping.warnings && mapping.warnings.length > 0) {
    for (const w of mapping.warnings) {
      const p = document.createElement("p");
      p.className = "warning-item";
      p.textContent = `⚠ ${w}`;
      warningsEl.appendChild(p);
    }
  }

  $("#ddl-output").textContent = mapping.ddl || "";
}

$("#btn-back-config").addEventListener("click", () => showScreen("config"));

$("#btn-approve").addEventListener("click", async () => {
  showLoading("Iniciando migração...");
  try {
    await invoke("start_migration", {
      config: migrationConfig,
      mapping: schemaMapping,
    });
    showScreen("dashboard");
    toast("Migração iniciada!");
  } catch (err) {
    toast(`Erro: ${err}`, "error");
  } finally {
    hideLoading();
  }
});

// ---- SCREEN: Dashboard ----

function updateKPI(data) {
  $("#kpi-rows").textContent = formatNumber(data.rows_processed);
  $("#kpi-rps").textContent = formatNumber(Math.round(data.rows_per_second));
  $("#kpi-mbps").textContent = data.mb_per_second.toFixed(2);
  $("#kpi-eta").textContent = formatETA(data.eta_seconds);

  if (data.total_rows > 0) {
    const pct = Math.min(100, (data.rows_processed / data.total_rows) * 100);
    $("#progress-bar").style.width = `${pct}%`;
    $("#progress-text").textContent = `${pct.toFixed(1)}%`;
  }
}

listen("migration-progress", (event) => {
  updateKPI(event.payload);
});

listen("migration-log", (event) => {
  const log = $("#migration-log");
  log.textContent += event.payload + "\n";
  log.scrollTop = log.scrollHeight;
});

listen("migration-complete", (event) => {
  const report = event.payload;
  $("#audit-report").textContent = report.summary;
  $("#audit-container").classList.remove("hidden");
  toast(
    report.all_match ? "Migração concluída — 100% integridade!" : "Migração concluída com discrepâncias",
    report.all_match ? "success" : "warning"
  );
  updateKPI({
    rows_processed: report.total_source_rows,
    rows_per_second: 0,
    mb_per_second: 0,
    eta_seconds: null,
    total_rows: report.total_source_rows,
  });
  $("#progress-bar").style.width = "100%";
  $("#progress-text").textContent = "100%";
});

listen("migration-error", (event) => {
  toast(`Erro na migração: ${event.payload}`, "error");
});

// ---- Audit PDF Download ----

$("#btn-download-audit").addEventListener("click", async () => {
  try {
    const pdfPath = await invoke("download_audit_pdf");
    toast(`Relatório salvo em: ${pdfPath}`, "success");
  } catch (err) {
    toast(`Erro ao gerar PDF: ${err}`, "error");
  }
});

// ---- Nav buttons ----

$$(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const screen = btn.dataset.screen;
    if (!btn.disabled && screen !== currentScreen) {
      showScreen(screen);
    }
  });
});
