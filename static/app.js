(function () {
  "use strict";

  const historyList = document.getElementById("history-list");

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  async function callFunction(name, args) {
    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ function: name, args: args }),
      });
      return await response.json();
    } catch (err) {
      return {
        ok: false,
        call: name + "(…)",
        error: { type: "NetworkError", message: String(err) },
      };
    }
  }

  function render(output, data) {
    output.replaceChildren();
    output.className = "result " + (data.ok ? "ok" : "err");
    if (data.call) output.append(el("div", "call", data.call));
    if (data.ok) {
      const line = el("div", "value");
      line.append(el("span", "arrow", "→ "), el("code", "", data.result));
      output.append(line, el("div", "type", "type: " + data.result_type));
    } else {
      const line = el("div", "value");
      line.append(el("strong", "", data.error.type), document.createTextNode(": " + data.error.message));
      output.append(line);
    }
  }

  function addHistory(data) {
    const item = el("li", data.ok ? "ok" : "err");
    item.append(el("code", "", data.call || data.function || "request"));
    const outcome = data.ok
      ? "→ " + data.result + "  (" + data.result_type + ")"
      : "✕ " + data.error.type + ": " + data.error.message;
    item.append(el("span", "", outcome));
    historyList.prepend(item);
    while (historyList.children.length > 50) historyList.lastChild.remove();
  }

  async function runForm(form) {
    const name = form.dataset.function;
    const args = Array.from(form.querySelectorAll("input")).map((i) => i.value);
    const output = form.parentElement.querySelector("output");
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    const data = await callFunction(name, args);
    button.disabled = false;
    render(output, data);
    addHistory(data);
    return data;
  }

  document.querySelectorAll(".run-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      runForm(form);
    });
    form.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const args = JSON.parse(chip.dataset.args);
        form.querySelectorAll("input").forEach((input, i) => {
          input.value = args[i] !== undefined ? args[i] : "";
        });
        runForm(form);
      });
    });
  });

  document.getElementById("run-all").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    let passed = 0;
    let raised = 0;
    for (const form of document.querySelectorAll(".run-form")) {
      if (form.closest(".card").hidden) continue;
      for (const chip of form.querySelectorAll(".chip")) {
        const args = JSON.parse(chip.dataset.args);
        form.querySelectorAll("input").forEach((input, i) => {
          input.value = args[i] !== undefined ? args[i] : "";
        });
        const data = await runForm(form);
        if (data.ok) passed += 1; else raised += 1;
      }
    }
    button.disabled = false;
    button.textContent = "Run every example (" + passed + " results, " + raised + " errors)";
  });

  document.getElementById("clear-history").addEventListener("click", () => {
    historyList.replaceChildren();
  });

  document.querySelectorAll(".filter").forEach((filter) => {
    filter.addEventListener("click", () => {
      document.querySelectorAll(".filter").forEach((f) => {
        f.classList.toggle("active", f === filter);
        f.setAttribute("aria-selected", String(f === filter));
      });
      const wanted = filter.dataset.filter;
      document.querySelectorAll(".card").forEach((card) => {
        card.hidden = wanted !== "all" && card.dataset.category !== wanted;
      });
    });
  });

  // The footer SHA comes from /health so it always shows the live deploy.
  async function loadHealth() {
    const dot = document.getElementById("health-dot");
    const text = document.getElementById("health-text");
    try {
      const response = await fetch("/health", { cache: "no-store" });
      const data = await response.json();
      const sha = data.commit || "unknown";
      dot.className = "dot up";
      text.textContent = "Live · commit " + sha.slice(0, 7) + " · Python " + data.python;
      const code = document.getElementById("commit-sha");
      code.textContent = sha.slice(0, 7);
      code.dataset.sha = sha;
      code.title = sha;
      document.getElementById("commit-link").href = window.REPO_URL + "/commit/" + sha;
    } catch (err) {
      dot.className = "dot down";
      text.textContent = "Health check failed";
    }
  }
  loadHealth();
})();
