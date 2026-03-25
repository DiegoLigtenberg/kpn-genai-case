const $ = (id) => document.getElementById(id);

const LIMIT_FIELDS = [
  ["max_total_eur", "lim-max-total"],
  ["min_invoice_year", "lim-min-year"],
  ["line_total_sum_tolerance_eur", "lim-tol"],
  ["max_line_item_amount_eur", "lim-max-line"],
];

/** Mirrors `src/config/policy.yaml` if the API is unreachable. */
const POLICY_YAML_DEFAULTS = {
  limits: {
    max_total_eur: 500,
    min_invoice_year: 2017,
    line_total_sum_tolerance_eur: 1.0,
    max_line_item_amount_eur: 200,
  },
};

function fillPolicyForm(data) {
  const lim = data.limits || {};
  for (const [key, id] of LIMIT_FIELDS) {
    const el = $(id);
    if (el && lim[key] != null) el.value = String(lim[key]);
  }
}

/** Sync form + server from `policy.yaml` (session reset; file on disk unchanged). */
async function loadPolicy() {
  const msg = $("policy-msg");
  try {
    const res = await fetch("/policy/reset", { method: "POST" });
    if (!res.ok) throw new Error(`${res.status}`);
    const data = await res.json();
    fillPolicyForm(data);
    if (msg) msg.textContent = "";
  } catch (e) {
    fillPolicyForm(POLICY_YAML_DEFAULTS);
    if (msg) {
      msg.textContent =
        "API offline—showing embedded defaults (same numbers as policy.yaml).";
    }
    console.error(e);
  }
}

async function resetPolicyFromFile() {
  const msg = $("policy-msg");
  try {
    const res = await fetch("/policy/reset", { method: "POST" });
    if (!res.ok) throw new Error(`${res.status}`);
    const data = await res.json();
    fillPolicyForm(data);
    if (msg) msg.textContent = "Reloaded from policy.yaml (session + form).";
  } catch (e) {
    fillPolicyForm(POLICY_YAML_DEFAULTS);
    if (msg) msg.textContent = e.message || String(e);
  }
}

async function applyPolicy() {
  const msg = $("policy-msg");
  const limits = {};
  for (const [key, id] of LIMIT_FIELDS) {
    const el = $(id);
    if (!el || el.value === "") continue;
    const n = Number(el.value);
    if (Number.isNaN(n)) continue;
    limits[key] = key === "min_invoice_year" ? Math.round(n) : n;
  }
  try {
    const res = await fetch("/policy", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limits }),
    });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(text || res.statusText);
    }
    if (!res.ok) {
      const d = data.detail;
      const errMsg =
        typeof d === "string"
          ? d
          : Array.isArray(d)
            ? d.map((x) => x.msg || JSON.stringify(x)).join("; ")
            : text || res.statusText;
      throw new Error(errMsg);
    }
    if (msg)
      msg.textContent =
        "Applied for this session only—policy.yaml on disk is unchanged. Use “Reset to policy.yaml” or reload the page to match the file again.";
  } catch (e) {
    if (msg) msg.textContent = e.message || String(e);
  }
}

function renderBatch(payload) {
  const sec = $("batch-section");
  const wrap = $("batch-wrap");
  if (!sec || !wrap) return;
  const rows = (payload.results || [])
    .map((r) => {
      const d = r.policy?.decision || "?";
      const ok = d === "ACCEPT";
      return `<tr><td class="batch-f">${esc(r.filename || "")}</td><td><span class="badge ${ok ? "ok" : "bad"}">${esc(d)}</span></td></tr>`;
    })
    .join("");
  const errRows = (payload.errors || [])
    .map(
      (e) =>
        `<tr class="batch-err"><td class="batch-f">${esc(e.filename)}</td><td>${esc(e.detail)}</td></tr>`
    )
    .join("");
  wrap.innerHTML = `<table class="batch-table"><thead><tr><th>File</th><th>Decision</th></tr></thead><tbody>${rows}${errRows}</tbody></table>`;
  sec.classList.remove("hidden");
}

async function runAll() {
  const status = $("status");
  const btn = $("run-all-btn");
  const run = $("run-btn");
  $("result")?.classList.add("hidden");
  $("batch-section")?.classList.add("hidden");
  status.classList.remove("hidden", "err");
  status.classList.add("loading");
  status.textContent = "Running every invoice in data/…";
  btn.disabled = true;
  run.disabled = true;
  try {
    const res = await fetch("/invoices/process-preset?data_dir=data", { method: "POST" });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(text || res.statusText);
    }
    if (!res.ok) {
      const d = data.detail;
      const msg =
        typeof d === "string"
          ? d
          : Array.isArray(d)
            ? d.map((x) => x.msg || JSON.stringify(x)).join("; ")
            : text || res.statusText;
      throw new Error(msg);
    }
    renderBatch(data);
    const n = (data.results || []).length;
    const e = (data.errors || []).length;
    status.textContent = `Batch done: ${n} file(s), ${e} error(s).`;
    status.classList.remove("loading");
  } catch (e) {
    status.classList.add("err");
    status.classList.remove("loading");
    status.textContent = e.message || String(e);
  } finally {
    btn.disabled = false;
    run.disabled = !fileSelect.value;
  }
}

async function loadFiles() {
  const sel = $("file-select");
  const hint = $("data-dir");
  const run = $("run-btn");
  try {
    const res = await fetch("/invoices/data-files");
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();
    if (hint) hint.textContent = "";
    sel.innerHTML = "";
    const files = data.files || [];
    if (files.length === 0) {
      sel.innerHTML = `<option value="">No files in ./data</option>`;
      sel.disabled = true;
      run.disabled = true;
      return;
    }
    sel.appendChild(new Option("— choose —", ""));
    for (const name of files) {
      sel.appendChild(new Option(name, name));
    }
    sel.disabled = false;
    run.disabled = true;
  } catch (e) {
    sel.innerHTML = `<option value="">Could not load list</option>`;
    hint.textContent =
      "Is the API running? python run.py from repo root (port 8000).";
    console.error(e);
  }
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

function rawDataUrl(filename) {
  const q = new URLSearchParams({ filename });
  return `/invoices/raw-data-file?${q}`;
}

function atomicPreviewUrl(filename) {
  const q = new URLSearchParams({ filename });
  return `/invoices/atomic-preview?${q}`;
}

async function loadLlm() {
  try {
    const res = await fetch("/invoices/llm");
    if (!res.ok) return;
    const data = await res.json();
    const sel = $("llm-select");
    if (sel && data.llm_type) sel.value = data.llm_type;
  } catch (e) {
    console.error(e);
  }
}

async function onLlmChange() {
  const sel = $("llm-select");
  const msg = $("llm-msg");
  if (!sel) return;
  try {
    const res = await fetch("/invoices/llm", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ llm_type: sel.value }),
    });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(text || res.statusText);
    }
    if (!res.ok) {
      const d = data.detail;
      const errMsg =
        typeof d === "string"
          ? d
          : Array.isArray(d)
            ? d.map((x) => x.msg || JSON.stringify(x)).join("; ")
            : text || res.statusText;
      throw new Error(errMsg);
    }
    if (msg) msg.textContent = `Using ${data.llm_type === "openai" ? "Azure OpenAI" : "Ollama (qwen3.5, vision)"}.`;
  } catch (e) {
    if (msg) msg.textContent = e.message || String(e);
    await loadLlm();
  }
}

function formatMoney(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("en-NL", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Formatted amount with a leading $ (per-item gross block). */
function formatMoneyUsd(n) {
  const m = formatMoney(n);
  return m === "—" ? "—" : `$ ${m}`;
}

function formatInvoiceId(n) {
  if (n == null || n === "") return null;
  return String(n);
}

function buildPreviewHtml(filename) {
  if (!filename) {
    return `<p class="preview-empty">Select a file and run the pipeline.</p>`;
  }
  const atomicUrl = atomicPreviewUrl(filename);
  const originalUrl = rawDataUrl(filename);
  return `
    <div class="preview-wrap atomic-preview">
      <div class="pdf-toolbar">
        <a class="preview-open" href="${esc(originalUrl)}" target="_blank" rel="noopener">Open original file</a>
        <div class="pdf-zoom-controls">
          <button type="button" class="pdf-zoom-out" aria-label="Zoom out">−</button>
          <span class="pdf-zoom-pct" aria-live="polite">100%</span>
          <button type="button" class="pdf-zoom-in" aria-label="Zoom in">+</button>
        </div>
      </div>
      <p class="pdf-zoom-hint">Scroll wheel to zoom · drag to pan · normalized PNG (model input after atomic_image)</p>
      <div class="pdf-zoom-outer" tabindex="0" aria-label="Invoice preview, scroll to zoom, drag to pan">
        <div class="pdf-zoom-inner">
          <img class="img-preview zoom-target" alt="Normalized invoice image" src="${esc(atomicUrl)}" draggable="false" />
        </div>
      </div>
    </div>`;
}

function setupPreviewZoom(resultRoot) {
  const inner = resultRoot.querySelector(".pdf-zoom-inner");
  const btnOut = resultRoot.querySelector(".pdf-zoom-out");
  const btnIn = resultRoot.querySelector(".pdf-zoom-in");
  const label = resultRoot.querySelector(".pdf-zoom-pct");
  const outer = resultRoot.querySelector(".pdf-zoom-outer");
  const img = inner?.querySelector("img.zoom-target");
  const iframe = inner?.querySelector("iframe.pdf-frame");
  const target = img || iframe;
  if (!inner || !target || !btnOut || !btnIn || !label || !outer) return;

  let zoom = 1;
  let panX = 0;
  let panY = 0;
  const MIN = 0.35;
  const MAX = 4;
  const BTN_STEP = 0.12;

  function apply() {
    inner.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
    inner.style.transformOrigin = "0 0";
    label.textContent = `${Math.round(zoom * 100)}%`;
  }

  function clampPan() {
    const ow = outer.clientWidth;
    const oh = outer.clientHeight;
    const sw = inner.offsetWidth * zoom;
    const sh = inner.offsetHeight * zoom;
    if (sw <= ow) panX = 0;
    else panX = Math.max(ow - sw, Math.min(0, panX));
    if (sh <= oh) panY = 0;
    else panY = Math.max(oh - sh, Math.min(0, panY));
  }

  btnOut.addEventListener("click", () => {
    zoom = Math.max(MIN, zoom - BTN_STEP);
    clampPan();
    apply();
  });
  btnIn.addEventListener("click", () => {
    zoom = Math.min(MAX, zoom + BTN_STEP);
    clampPan();
    apply();
  });

  outer.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 0.94 : 1.06;
      zoom = Math.min(MAX, Math.max(MIN, zoom * factor));
      clampPan();
      apply();
    },
    { passive: false }
  );

  outer.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const startX = e.clientX;
    const startY = e.clientY;
    const startPanX = panX;
    const startPanY = panY;
    outer.classList.add("is-panning");

    function move(ev) {
      panX = startPanX + (ev.clientX - startX);
      panY = startPanY + (ev.clientY - startY);
      apply();
    }

    function up() {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
      outer.classList.remove("is-panning");
      clampPan();
      apply();
    }

    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup", up);
  });

  const onImgLoad = () => {
    clampPan();
    apply();
  };
  if (img) {
    if (img.complete) onImgLoad();
    else img.addEventListener("load", onImgLoad, { once: true });
  }

  apply();
}

function cleanMeta(meta) {
  if (!meta || typeof meta !== "object") return {};
  const skip = new Set(["image_mime_type", "image_bytes_on_disk"]);
  const out = {};
  for (const [k, v] of Object.entries(meta)) {
    if (!skip.has(k)) out[k] = v;
  }
  return out;
}

function renderResult(payload) {
  const root = $("result");
  const ext = payload.extracted;
  const pol = payload.policy || {};
  const accept = pol.decision === "ACCEPT";
  const violations = pol.violations || [];
  const filename = payload.filename || "";
  const invId = ext ? formatInvoiceId(ext.invoice_no) : null;

  let detail = "";

  detail += `<div class="invoice-hero">`;
  detail += `<div class="invoice-id" title="Extracted invoice number">`;
  detail += invId != null
    ? `<span class="invoice-id-label">Invoice</span><span class="invoice-id-num">#${esc(invId)}</span>`
    : `<span class="invoice-id-missing">Invoice number not extracted</span>`;
  detail += `</div>`;
  if (filename) {
    detail += `<div class="invoice-source">${esc(filename)}</div>`;
  }
  detail += `<div class="decision-row">`;
  detail += `<span class="badge ${accept ? "ok" : "bad"}">${esc(pol.decision || "?")}</span>`;
  detail += `</div>`;
  detail += `</div>`;

  if (ext) {
    detail += `<div class="grid">`;
    const rows = [
      ["Vendor", ext.vendor ?? "—"],
      ["Buyer", ext.buyer_name ?? "—"],
      ["Invoice date", ext.invoice_date_raw ?? "—"],
      ["Total gross", formatMoney(ext.total_gross_worth)],
      ["Duplicate", ext.already_exists ? "Yes" : "No"],
    ];
    for (const [k, v] of rows) {
      detail += `<div class="kv"><div class="k">${esc(k)}</div><div class="v">${esc(v)}</div></div>`;
    }
    detail += `</div>`;

    // extracted.per_item_gross_worths: one gross amount per invoiced row (Items table)
    const lines = ext.per_item_gross_worths || [];
    if (lines.length) {
      const sum = lines.reduce((a, x) => a + Number(x), 0);
      const total = ext.total_gross_worth;
      let sumNote = "";
      if (total != null && !Number.isNaN(sum)) {
        const diff = Math.abs(sum - Number(total));
        sumNote =
          diff < 0.02
            ? " (matches total gross)"
            : ` (Δ vs total: ${formatMoney(diff)})`;
      }
      detail += `<div class="line-block">`;
      detail += `<div class="line-block-title">Per-item gross worth</div>`;
      detail += `<p class="line-block-hint">One amount per invoiced row (e.g. Gross worth column). Together they sum to the invoice total.</p>`;
      detail += `<ul class="line-amounts">`;
      for (let i = 0; i < lines.length; i++) {
        detail += `<li><span class="line-idx">${i + 1}.</span>${esc(formatMoneyUsd(lines[i]))}</li>`;
      }
      detail += `</ul>`;
      detail += `<div class="line-sum">Sum of per-item gross: <strong>${esc(formatMoneyUsd(sum))}</strong>${esc(sumNote)}</div>`;
      detail += `</div>`;
    }
  }

  if (violations.length) {
    detail += `<ul class="violations">`;
    for (const v of violations) {
      detail += `<li><strong>${esc(v.rule_id)}</strong> — ${esc(v.message)}</li>`;
    }
    detail += `</ul>`;
  }

  if (payload.error) {
    detail += `<div class="err-detail">${esc(payload.error)}</div>`;
  }

  const metaClean = cleanMeta(payload.meta);
  if (Object.keys(metaClean).length) {
    detail += `<div class="meta">${esc(JSON.stringify(metaClean, null, 2))}</div>`;
  }

  const previewHtml = buildPreviewHtml(filename);
  root.innerHTML = `
    <div class="panel result-inner">
      <div class="result-split">
        <aside class="preview-col">${previewHtml}</aside>
        <div class="detail-col">${detail}</div>
      </div>
    </div>`;
  root.classList.remove("hidden");
  $("batch-section")?.classList.add("hidden");
  setupPreviewZoom(root);
}

async function runPipeline() {
  const sel = $("file-select");
  const name = sel.value;
  if (!name) return;

  const status = $("status");
  const run = $("run-btn");
  status.classList.remove("hidden", "err");
  status.classList.add("loading");
  status.textContent = "Running LangGraph: extract, policy, final decision…";
  $("result").classList.add("hidden");
  $("batch-section")?.classList.add("hidden");

  run.disabled = true;
  $("run-all-btn").disabled = true;
  try {
    const q = new URLSearchParams({ filename: name });
    const res = await fetch(`/invoices/process-data-file?${q}`, { method: "POST" });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(text || res.statusText);
    }
    if (!res.ok) {
      const d = data.detail;
      const msg =
        typeof d === "string"
          ? d
          : Array.isArray(d)
            ? d.map((x) => x.msg || JSON.stringify(x)).join("; ")
            : text || res.statusText;
      throw new Error(msg);
    }
    renderResult(data);
    status.textContent = "Done.";
    status.classList.remove("loading");
  } catch (e) {
    status.classList.add("err");
    status.classList.remove("loading");
    status.textContent = e.message || String(e);
  } finally {
    run.disabled = !sel.value;
    $("run-all-btn").disabled = false;
  }
}

const fileSelect = $("file-select");
const runBtn = $("run-btn");
const runAllBtn = $("run-all-btn");
runBtn.addEventListener("click", runPipeline);
runAllBtn.addEventListener("click", runAll);
$("policy-apply")?.addEventListener("click", applyPolicy);
$("policy-reset")?.addEventListener("click", resetPolicyFromFile);
fileSelect.addEventListener("change", () => {
  runBtn.disabled = !fileSelect.value;
});
loadFiles();
loadPolicy();
loadLlm();
$("llm-select")?.addEventListener("change", onLlmChange);
