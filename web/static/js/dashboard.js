async function pushSlackReport() {
    const btn = document.getElementById("slack-report-btn");
    const label = btn.querySelector("span");
    const original = label.textContent;

    btn.disabled = true;
    label.textContent = "Sending...";

    try {
        const resp = await fetch("/api/slack/mtd-report");
        const data = await resp.json();
        if (data.success) {
            label.textContent = "Sent!";
            btn.style.background = "#2EB67D";
            setTimeout(() => {
                label.textContent = original;
                btn.style.background = "";
                btn.disabled = false;
            }, 3000);
        } else {
            throw new Error(data.error || "Unknown error");
        }
    } catch (err) {
        label.textContent = "Failed";
        btn.style.background = "#e74c3c";
        setTimeout(() => {
            label.textContent = original;
            btn.style.background = "";
            btn.disabled = false;
        }, 3000);
    }
}

async function loadChart(url, elementId) {
    try {
        const resp = await fetch(url);
        const fig = await resp.json();
        Plotly.newPlot(elementId, fig.data, fig.layout, { responsive: true });
    } catch (err) {
        console.error(`Failed to load chart ${elementId}:`, err);
        document.getElementById(elementId).innerHTML =
            '<p style="color:#e74c3c;padding:20px;">Failed to load chart. Is data synced?</p>';
    }
}

function loadAll() {
    loadChart("/api/charts/in-vs-out", "in-vs-out-chart");
    loadChart("/api/charts/profit-margin", "profit-margin-chart");
    loadChart("/api/charts/spend-by-category", "spend-by-category-chart").then(attachSpendClickHandler);
    loadChart("/api/charts/revenue-by-client", "revenue-by-client-chart");
    loadChart("/api/charts/concentration-risk", "concentration-risk-chart");
    loadChart("/api/charts/expected-revenue", "expected-revenue-chart").then(attachExpectedRevenueClickHandler);
    loadChart("/api/charts/days-to-pay", "days-to-pay-chart");
}

// --- Spend detail drill-down modal ---

function showModal() {
    document.getElementById("spend-detail-modal").style.display = "flex";
}

function hideModal() {
    document.getElementById("spend-detail-modal").style.display = "none";
    Plotly.purge("spend-detail-chart");
}

async function loadSpendDetail(month, category) {
    const params = new URLSearchParams({ month, category });
    try {
        const resp = await fetch(`/api/charts/spend-detail?${params}`);
        const fig = await resp.json();
        showModal();
        Plotly.newPlot("spend-detail-chart", fig.data, fig.layout, { responsive: true });
    } catch (err) {
        console.error("Failed to load spend detail:", err);
    }
}

function attachSpendClickHandler() {
    const el = document.getElementById("spend-by-category-chart");
    if (!el || !el.data) return;

    el.on("plotly_click", function (data) {
        if (!data || !data.points || !data.points.length) return;
        const point = data.points[0];
        // Plotly returns dates like "2025-12-01"; normalize to "YYYY-MM"
        const month = String(point.x).slice(0, 7);
        const category = point.data.name;
        if (month && category) {
            loadSpendDetail(month, category);
        }
    });
}

// --- Invoice detail drill-down modal ---

function showInvoiceModal() {
    document.getElementById("invoice-detail-modal").style.display = "flex";
}

function hideInvoiceModal() {
    document.getElementById("invoice-detail-modal").style.display = "none";
    document.getElementById("invoice-table-body").innerHTML = "";
}

function formatCurrency(amount) {
    return "$" + Number(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function loadInvoicesForClient(client) {
    document.getElementById("invoice-modal-title").textContent = "Open Invoices — " + client;
    const tbody = document.getElementById("invoice-table-body");
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:#888;">Loading...</td></tr>';
    showInvoiceModal();

    try {
        const resp = await fetch("/api/invoices/open?client=" + encodeURIComponent(client));
        const invoices = await resp.json();

        if (!invoices.length) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:#888;">No open invoices found.</td></tr>';
            return;
        }

        tbody.innerHTML = "";
        invoices.forEach(function (inv) {
            const tr = document.createElement("tr");

            // Invoice number (linked to hosted URL)
            const tdNum = document.createElement("td");
            if (inv.hosted_invoice_url) {
                const a = document.createElement("a");
                a.href = inv.hosted_invoice_url;
                a.target = "_blank";
                a.rel = "noopener";
                a.textContent = inv.number || inv.id;
                a.className = "invoice-link";
                tdNum.appendChild(a);
            } else {
                tdNum.textContent = inv.number || inv.id;
            }
            tr.appendChild(tdNum);

            // Amount
            const tdAmt = document.createElement("td");
            tdAmt.textContent = formatCurrency(inv.amount_due);
            tdAmt.className = "text-right";
            tr.appendChild(tdAmt);

            // Due date
            const tdDue = document.createElement("td");
            tdDue.textContent = inv.due_date || "—";
            tr.appendChild(tdDue);

            // Status badge
            const tdStatus = document.createElement("td");
            const badge = document.createElement("span");
            if (inv.is_overdue) {
                badge.textContent = "Overdue";
                badge.className = "badge badge-overdue";
            } else {
                badge.textContent = "Outstanding";
                badge.className = "badge badge-outstanding";
            }
            tdStatus.appendChild(badge);
            tr.appendChild(tdStatus);

            // Action
            const tdAction = document.createElement("td");
            if (inv.is_overdue) {
                const btn = document.createElement("button");
                if (inv.email_sent) {
                    btn.textContent = "Sent \u2713";
                    btn.className = "btn-reminder btn-reminder-sent";
                    btn.disabled = true;
                } else {
                    btn.textContent = "Send Reminder";
                    btn.className = "btn-reminder";
                    btn.addEventListener("click", function () {
                        sendReminder(btn, inv.id);
                    });
                }
                tdAction.appendChild(btn);
            }
            tr.appendChild(tdAction);

            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to load invoices:", err);
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:#e74c3c;">Failed to load invoices.</td></tr>';
    }
}

async function sendReminder(btn, invoiceId) {
    btn.disabled = true;
    btn.textContent = "Sending...";
    btn.className = "btn-reminder btn-reminder-sending";

    try {
        const resp = await fetch("/api/invoices/send-reminder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ invoice_id: invoiceId }),
        });
        const result = await resp.json();

        if (resp.ok && result.success) {
            btn.textContent = "Sent \u2713";
            btn.className = "btn-reminder btn-reminder-sent";
        } else {
            btn.textContent = "Error";
            btn.className = "btn-reminder btn-reminder-error";
            btn.title = result.error || "Unknown error";
            setTimeout(function () {
                btn.textContent = "Retry";
                btn.className = "btn-reminder";
                btn.disabled = false;
            }, 3000);
        }
    } catch (err) {
        console.error("Send reminder failed:", err);
        btn.textContent = "Error";
        btn.className = "btn-reminder btn-reminder-error";
        setTimeout(function () {
            btn.textContent = "Retry";
            btn.className = "btn-reminder";
            btn.disabled = false;
        }, 3000);
    }
}

function attachExpectedRevenueClickHandler() {
    const el = document.getElementById("expected-revenue-chart");
    if (!el || !el.data) return;

    el.on("plotly_click", function (data) {
        if (!data || !data.points || !data.points.length) return;
        const client = data.points[0].y;
        if (client) {
            loadInvoicesForClient(client);
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    loadAll();

    // Close spend detail modal on X button or backdrop click
    document.getElementById("modal-close-btn").addEventListener("click", hideModal);
    document.getElementById("spend-detail-modal").addEventListener("click", function (e) {
        if (e.target === this) hideModal();
    });

    // Close invoice detail modal on X button or backdrop click
    document.getElementById("invoice-modal-close-btn").addEventListener("click", hideInvoiceModal);
    document.getElementById("invoice-detail-modal").addEventListener("click", function (e) {
        if (e.target === this) hideInvoiceModal();
    });

    // Refresh chart data every hour
    setInterval(loadAll, 60 * 60 * 1000);
});
