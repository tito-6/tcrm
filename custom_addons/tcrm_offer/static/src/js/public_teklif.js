/** Public teklif interactive selection + approve flow */
(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") fn();
        else document.addEventListener("DOMContentLoaded", fn);
    }

    function csrf() {
        const root = document.querySelector(".tcrm-teklif-view");
        return root ? root.dataset.csrf : "";
    }

    function token() {
        const root = document.querySelector(".tcrm-teklif-view");
        return root ? root.dataset.token : "";
    }

    function isReadonly() {
        const root = document.querySelector(".tcrm-teklif-view");
        return root && root.dataset.readonly === "1";
    }

    function selectedIds() {
        // Required checkboxes are disabled+checked; still include them
        const ids = new Set();
        document.querySelectorAll(".teklif-item-check").forEach((el) => {
            if (el.checked || el.disabled) {
                // only disabled if required — include those that are checked OR required container
                const article = el.closest(".teklif-item");
                if (el.checked || (article && article.dataset.required === "1")) {
                    ids.add(parseInt(el.value, 10));
                }
            }
        });
        // Explicitly add required items
        document.querySelectorAll('.teklif-item[data-required="1"] .teklif-item-check').forEach((el) => {
            ids.add(parseInt(el.value, 10));
        });
        return Array.from(ids);
    }

    function adBudget() {
        const el = document.getElementById("ad_budget");
        return el ? parseFloat(el.value || "0") : 0;
    }

    function enforceExclusive(changed) {
        const group = changed.closest(".teklif-item")?.dataset.group;
        if (!group || !changed.checked) return;
        document.querySelectorAll(`.teklif-item[data-group="${group}"] .teklif-item-check`).forEach((el) => {
            if (el !== changed) el.checked = false;
        });
    }

    async function refreshQuote() {
        const res = await fetch(`/teklif/${token()}/quote?csrf_token=${encodeURIComponent(csrf())}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                selected_ids: selectedIds(),
                ad_budget: adBudget(),
            }),
            credentials: "same-origin",
        });
        const data = await res.json();
        if (!data.ok) {
            console.warn("quote error", data);
            return null;
        }
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        set("sum-monthly", data.monthly_fmt);
        set("sum-onetime", data.one_time_fmt);
        set("sum-session", data.per_session_fmt);
        set("sum-tax", data.tax_fmt);
        set("sum-gross", data.gross_fmt);
        return data;
    }

    function uuid() {
        if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
        return "idemp-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    }

    let lastQuote = null;
    let approving = false;
    let idempotencyKey = uuid();

    ready(function () {
        const root = document.querySelector(".tcrm-teklif-view");
        if (!root || isReadonly()) return;

        document.querySelectorAll(".teklif-item-check").forEach((el) => {
            el.addEventListener("change", async (ev) => {
                enforceExclusive(ev.target);
                lastQuote = await refreshQuote();
            });
        });
        const budget = document.getElementById("ad_budget");
        if (budget) {
            budget.addEventListener("change", async () => {
                lastQuote = await refreshQuote();
            });
            budget.addEventListener("input", () => {
                // debounce lightly
                clearTimeout(budget._t);
                budget._t = setTimeout(async () => {
                    lastQuote = await refreshQuote();
                }, 300);
            });
        }

        refreshQuote().then((q) => {
            lastQuote = q;
        });

        const btn = document.getElementById("btn-approve");
        const confirmBtn = document.getElementById("btn-confirm-approve");
        if (!btn) return;

        btn.addEventListener("click", async () => {
            if (
                !document.getElementById("accepted_services")?.checked ||
                !document.getElementById("accepted_terms")?.checked ||
                !document.getElementById("accepted_kvkk")?.checked
            ) {
                alert("Lütfen tüm onay kutularını işaretleyin.");
                return;
            }
            const name = document.getElementById("approver_name")?.value?.trim();
            const email = document.getElementById("approver_email")?.value?.trim();
            if (!name || !email) {
                alert("Yetkili adı ve e-posta zorunludur.");
                return;
            }
            lastQuote = (await refreshQuote()) || lastQuote;
            if (!lastQuote) {
                alert("Fiyat özeti alınamadı. Lütfen tekrar deneyin.");
                return;
            }
            const lines = document.getElementById("confirm-lines");
            if (lines) {
                lines.innerHTML = "";
                (lastQuote.lines || []).forEach((l) => {
                    const li = document.createElement("li");
                    li.textContent = `${l.name} — ${l.net_fmt}`;
                    lines.appendChild(li);
                });
            }
            const set = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val;
            };
            set("confirm-monthly", lastQuote.monthly_fmt);
            set("confirm-onetime", lastQuote.one_time_fmt);
            set("confirm-session", lastQuote.per_session_fmt);
            set("confirm-tax", lastQuote.tax_fmt);
            set("confirm-gross", lastQuote.gross_fmt);

            const modalEl = document.getElementById("teklifConfirmModal");
            if (window.bootstrap && modalEl) {
                bootstrap.Modal.getOrCreateInstance(modalEl).show();
            } else if (modalEl) {
                modalEl.classList.add("show");
                modalEl.style.display = "block";
            }
        });

        if (confirmBtn) {
            confirmBtn.addEventListener("click", async () => {
                if (approving) return;
                approving = true;
                confirmBtn.disabled = true;
                try {
                    const res = await fetch(
                        `/teklif/${token()}/approve?csrf_token=${encodeURIComponent(csrf())}`,
                        {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            selected_ids: selectedIds(),
                            ad_budget: adBudget(),
                            approver_name: document.getElementById("approver_name")?.value?.trim(),
                            approver_company: document.getElementById("approver_company")?.value?.trim(),
                            approver_email: document.getElementById("approver_email")?.value?.trim(),
                            approver_phone: document.getElementById("approver_phone")?.value?.trim(),
                            accepted_services: true,
                            accepted_terms: true,
                            accepted_kvkk: true,
                            idempotency_key: idempotencyKey,
                        }),
                        credentials: "same-origin",
                    });
                    const data = await res.json();
                    if (data.ok && data.redirect) {
                        window.location.href = data.redirect;
                        return;
                    }
                    alert(data.error || "Onay başarısız.");
                    idempotencyKey = uuid();
                } catch (e) {
                    alert("Bağlantı hatası. Lütfen tekrar deneyin.");
                    idempotencyKey = uuid();
                } finally {
                    approving = false;
                    confirmBtn.disabled = false;
                }
            });
        }
    });
})();
