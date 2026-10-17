const form = document.getElementById("shorten-form");
const urlInput = document.getElementById("url");
const customInput = document.getElementById("custom");
const errorEl = document.getElementById("error");
const resultEl = document.getElementById("result");
const linkEl = document.getElementById("short-link");
const copyBtn = document.getElementById("copy");
const historyEl = document.getElementById("history");

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.hidden = !msg;
}

function renderHistory(items) {
  historyEl.replaceChildren();
  for (const item of items) {
    const tr = document.createElement("tr");

    const tdShort = document.createElement("td");
    const a = document.createElement("a");
    a.href = item.short_url;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = item.short_url.replace(/^https?:\/\//, "");
    tdShort.appendChild(a);

    const tdOrig = document.createElement("td");
    tdOrig.className = "orig";
    tdOrig.textContent = item.original_url;
    tdOrig.title = item.original_url;

    const tdClicks = document.createElement("td");
    tdClicks.textContent = item.clicks;

    tr.append(tdShort, tdOrig, tdClicks);
    historyEl.appendChild(tr);
  }
}

async function loadHistory() {
  try {
    const res = await fetch("/api/urls");
    renderHistory(await res.json());
  } catch (_) { /* history is optional */ }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  showError("");
  resultEl.hidden = true;

  const body = { url: urlInput.value };
  if (customInput.value.trim()) body.custom_code = customInput.value.trim();

  try {
    const res = await fetch("/api/shorten", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) return showError(data.error || "Something went wrong.");

    linkEl.href = data.short_url;
    linkEl.textContent = data.short_url;
    resultEl.hidden = false;
    loadHistory();
  } catch (_) {
    showError("Network error. Is the server running?");
  }
});

copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(linkEl.href);
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = "Copy"), 1200);
  } catch (_) {
    showError("Could not copy automatically. Please copy the link manually.");
  }
});

loadHistory();
