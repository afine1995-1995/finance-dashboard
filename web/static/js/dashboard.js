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

async function refreshData() {
    const btn = document.getElementById("refresh-data-btn");
    const label = btn.querySelector("span");
    const original = label.textContent;

    btn.disabled = true;
    label.textContent = "Syncing...";

    try {
        const resp = await fetch("/api/sync", { method: "POST" });
        const data = await resp.json();
        if (data.success) {
            label.textContent = "Done!";
            btn.style.background = "#27ae60";
            loadAll();
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

async function remindAllOverdue() {
    if (!confirm("This will send reminder emails to all overdue clients. Continue?")) return;

    const btn = document.getElementById("remind-all-btn");
    const label = btn.querySelector("span");
    const original = label.textContent;

    btn.disabled = true;
    label.textContent = "Sending...";

    try {
        const resp = await fetch("/api/invoices/remind-all-overdue", { method: "POST" });
        const data = await resp.json();
        if (data.success) {
            label.textContent = `Sent ${data.sent}!`;
            btn.style.background = "#2EB67D";
            if (data.failed > 0) {
                label.textContent += ` (${data.failed} failed)`;
            }
            setTimeout(() => {
                label.textContent = original;
                btn.style.background = "";
                btn.disabled = false;
            }, 5000);
        } else {
            throw new Error(data.error || "Unknown error");
        }
    } catch (err) {
        label.textContent = "Failed";
        btn.style.background = "#c0392b";
        setTimeout(() => {
            label.textContent = original;
            btn.style.background = "";
            btn.disabled = false;
        }, 3000);
    }
}

function isMobile() {
    return window.innerWidth <= 768;
}

function applyMobileLayout(fig, elementId) {
    if (!isMobile()) return;

    // --- Detect chart characteristics ---
    var hasHorizontalBars = false;
    var hasPie = false;
    if (fig.data) {
        fig.data.forEach(function (trace) {
            if (trace.orientation === "h") hasHorizontalBars = true;
            if (trace.type === "pie") hasPie = true;
        });
    }

    // --- Process annotations ---
    var hasTopAnnotations = false;
    var manyTopAnnotations = false; // 3+ pairs like expected-revenue
    if (fig.layout.annotations) {
        var topAnns = [];
        var otherAnns = [];
        fig.layout.annotations.forEach(function (a) {
            // Remove right-side panel annotations (in-vs-out summary)
            if (a.xref === "paper" && a.x > 1.0) return;
            if (a.yref === "paper" && a.y > 1.05) {
                topAnns.push(a);
            } else {
                if (a.font && a.font.size) a.font.size = Math.min(a.font.size, 9);
                otherAnns.push(a);
            }
        });

        if (topAnns.length > 0) {
            hasTopAnnotations = true;
            manyTopAnnotations = topAnns.length > 2;

            // Group by x position to merge label+number pairs
            var groups = {};
            topAnns.forEach(function (a) {
                var key = Math.round(a.x * 100);
                if (!groups[key]) groups[key] = [];
                groups[key].push(a);
            });

            var merged = [];
            Object.keys(groups).forEach(function (key) {
                var group = groups[key];
                var labelAnn = null;
                var numberAnn = null;
                group.forEach(function (a) {
                    if (a.font && a.font.size >= 20) numberAnn = a;
                    else labelAnn = a;
                });

                if (labelAnn && numberAnn) {
                    var labelText = labelAnn.text.replace(/<\/?b>/g, "");
                    merged.push({
                        text: labelText + "<br>" + numberAnn.text,
                        xref: "paper", yref: "paper",
                        x: numberAnn.x, y: 1.12,
                        showarrow: false,
                        font: { color: numberAnn.font.color, size: hasHorizontalBars ? 8 : 10 },
                        align: "center",
                    });
                } else {
                    // Unpaired (e.g. "Total Revenue", "Overall Avg")
                    group.forEach(function (a) {
                        if (a.font) a.font.size = Math.min(a.font.size, 9);
                        a.y = Math.max(a.y, 1.12);
                        merged.push(a);
                    });
                }
            });
            fig.layout.annotations = otherAnns.concat(merged);
        } else {
            fig.layout.annotations = otherAnns;
        }
    }

    // --- Margins per chart type ---
    if (hasPie) {
        fig.layout.margin = { l: 10, r: 10, t: 50, b: 10 };
    } else if (hasHorizontalBars) {
        // Charts with many top annotations (expected-revenue) need more
        // horizontal room for the 3 side-by-side labels, so use narrower l
        fig.layout.margin = {
            l: manyTopAnnotations ? 80 : 110,
            r: manyTopAnnotations ? 35 : 50,
            t: hasTopAnnotations ? 65 : 50,
            b: 40
        };
    } else {
        fig.layout.margin = { l: 35, r: 8, t: hasTopAnnotations ? 50 : 30, b: 60 };
    }

    // Cap explicit height for horizontal bar charts (skip scrollable charts)
    if (fig.layout.height && hasHorizontalBars && elementId !== "expected-revenue-chart") {
        fig.layout.height = Math.min(fig.layout.height, 350);
    }

    // --- Title ---
    if (fig.layout.title && fig.layout.title.font) {
        fig.layout.title.font.size = 13;
    }

    // --- Axes: shrink ticks, remove titles, angle x-axis ---
    ["xaxis", "yaxis"].forEach(function (axis) {
        var ax = fig.layout[axis];
        if (!ax) return;
        if (ax.tickfont) ax.tickfont.size = 9;
        if (ax.title) ax.title.text = "";
    });
    if (!hasHorizontalBars && !hasPie && fig.layout.xaxis) {
        fig.layout.xaxis.tickangle = -45;
    }

    // --- Legend: small horizontal row below chart ---
    if (fig.layout.legend) {
        fig.layout.legend.font = fig.layout.legend.font || {};
        fig.layout.legend.font.size = 8;
        fig.layout.legend.orientation = "h";
        fig.layout.legend.x = 0.5;
        fig.layout.legend.xanchor = "center";
        fig.layout.legend.y = -0.18;
        fig.layout.legend.yanchor = "top";
    }

    // --- Traces ---
    if (fig.data) {
        fig.data.forEach(function (trace) {
            // Hide text-only scatter traces (net labels on in-vs-out)
            if (trace.mode === "text") {
                trace.visible = false;
                return;
            }

            // Horizontal bar "outside" text clips off-screen — use auto
            if (trace.textposition === "outside" && hasHorizontalBars) {
                trace.textposition = "auto";
            }

            // Shrink all trace text
            if (trace.textfont) {
                trace.textfont.size = Math.min(trace.textfont.size || 12, 9);
            }
        });
    }
}

async function loadChart(url, elementId, opts = {}) {
    try {
        const resp = await fetch(url);
        const fig = await resp.json();
        applyMobileLayout(fig, elementId);
        Plotly.newPlot(elementId, fig.data, fig.layout, {
            responsive: opts.responsive !== false,
            displayModeBar: !isMobile()
        });
    } catch (err) {
        console.error(`Failed to load chart ${elementId}:`, err);
        document.getElementById(elementId).innerHTML =
            '<p style="color:#e74c3c;padding:20px;">Failed to load chart. Is data synced?</p>';
    }
}

let _arrCollected = 0;
let _arrInvoiced = 0;
let _arrUseInvoiced = false;

async function loadBalances() {
    try {
        const resp = await fetch("/api/balances");
        const data = await resp.json();
        const fmt = (n) => "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        document.getElementById("kpi-mercury").textContent = fmt(data.mercury);
        const stripeTotal = Number(data.stripe_available) + Number(data.stripe_pending);
        document.getElementById("kpi-stripe").textContent = fmt(stripeTotal);
        const fmtWhole = (n) => "$" + Math.round(Number(n)).toLocaleString("en-US");
        _arrCollected = data.run_rate_arr;
        _arrInvoiced = data.invoiced_arr;
        document.getElementById("kpi-arr").textContent = fmtWhole(_arrUseInvoiced ? _arrInvoiced : _arrCollected);
        document.getElementById("kpi-ytd").textContent = fmtWhole(data.ytd_collected);
        document.getElementById("kpi-distributions").textContent = fmtWhole(data.ytd_distributions);
        document.getElementById("kpi-outflows").textContent = fmtWhole(data.ytd_outflows);
    } catch (err) {
        console.error("Failed to load balances:", err);
    }
}

function toggleArrMode() {
    _arrUseInvoiced = !_arrUseInvoiced;
    const btn = document.getElementById("arr-mode-btn");
    const label = document.getElementById("kpi-arr-label");
    const fmtWhole = (n) => "$" + Math.round(Number(n)).toLocaleString("en-US");
    if (_arrUseInvoiced) {
        document.getElementById("kpi-arr").textContent = fmtWhole(_arrInvoiced);
        label.innerHTML = 'Run Rate ARR <span style="font-size:11px;color:#f39c12;">(Invoiced)</span>';
        btn.textContent = "◉ Using Invoiced ARR";
        btn.classList.remove("btn-chart-toggle-off");
        btn.classList.add("btn-chart-toggle-on");
    } else {
        document.getElementById("kpi-arr").textContent = fmtWhole(_arrCollected);
        label.innerHTML = 'Run Rate ARR <span style="font-size:11px;color:#888;">(Collected)</span>';
        btn.textContent = "○ Use Invoiced ARR";
        btn.classList.remove("btn-chart-toggle-on");
        btn.classList.add("btn-chart-toggle-off");
    }
}

function loadAll() {
    loadBalances();
    loadChart("/api/charts/in-vs-out", "in-vs-out-chart").then(attachInVsOutClickHandler);
    loadChart("/api/charts/profit-margin", "profit-margin-chart").then(attachMarginClickHandler);
    loadChart("/api/charts/spend-by-category", "spend-by-category-chart").then(attachSpendClickHandler);
    loadChart("/api/charts/revenue-by-client", "revenue-by-client-chart");
    loadChart("/api/charts/concentration-risk", "concentration-risk-chart");
    loadChart("/api/charts/expected-revenue", "expected-revenue-chart", { responsive: false }).then(attachExpectedRevenueClickHandler);
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
        applyMobileLayout(fig);
        showModal();
        Plotly.newPlot("spend-detail-chart", fig.data, fig.layout, {
            responsive: true,
            displayModeBar: !isMobile()
        });
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
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:24px;color:#888;">Loading...</td></tr>';
    showInvoiceModal();

    try {
        const resp = await fetch("/api/invoices/open?client=" + encodeURIComponent(client));
        const invoices = await resp.json();

        if (!invoices.length) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:24px;color:#888;">No open invoices found.</td></tr>';
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
            if (inv.due_date) {
                const [y, mo, d] = inv.due_date.split("-");
                tdDue.textContent = new Date(Number(y), Number(mo) - 1, Number(d))
                    .toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
            } else {
                tdDue.textContent = "Not set";
                tdDue.style.color = "#888";
            }
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

            // Notify Email with Save button
            const tdNotifyEmail = document.createElement("td");
            tdNotifyEmail.className = "notify-email-cell";
            const currentNotifyEmail = inv.notify_email || inv.customer_email || "";
            const emailInput = document.createElement("input");
            emailInput.type = "email";
            emailInput.value = currentNotifyEmail;
            emailInput.dataset.savedValue = currentNotifyEmail;
            emailInput.className = "notify-email-input";
            emailInput.placeholder = "Notification email";
            emailInput.addEventListener("keydown", function (e) {
                if (e.key === "Enter") saveBtn.click();
            });
            const saveBtn = document.createElement("button");
            saveBtn.textContent = "Save";
            saveBtn.className = "btn-save-email";
            saveBtn.addEventListener("click", function () {
                saveNotifyEmail(inv.id, emailInput, saveBtn);
            });
            tdNotifyEmail.appendChild(emailInput);
            tdNotifyEmail.appendChild(saveBtn);

            // Last Reminded
            const tdLastReminded = document.createElement("td");
            tdLastReminded.className = "last-reminded";
            if (inv.last_reminded) {
                tdLastReminded.textContent = formatReminderDate(inv.last_reminded);
                tdLastReminded.title = new Date(inv.last_reminded).toLocaleString();
            } else {
                tdLastReminded.textContent = "Never";
            }

            // Action (Send Reminder)
            const tdAction = document.createElement("td");
            if (inv.is_overdue) {
                const btn = document.createElement("button");
                btn.textContent = "Send Reminder";
                btn.className = "btn-reminder";
                btn.addEventListener("click", function () {
                    sendReminder(btn, inv.id, emailInput, tdLastReminded);
                });
                tdAction.appendChild(btn);
            }

            // Disregard
            const tdDisregard = document.createElement("td");
            const disBtn = document.createElement("button");
            disBtn.textContent = "Disregard";
            disBtn.className = "btn-disregard";
            disBtn.title = "Remove this invoice from the dashboard (e.g. paid by check)";
            disBtn.addEventListener("click", function () {
                disregardInvoice(inv.id, tr, disBtn);
            });
            tdDisregard.appendChild(disBtn);

            tr.appendChild(tdNotifyEmail);
            tr.appendChild(tdLastReminded);
            tr.appendChild(tdAction);
            tr.appendChild(tdDisregard);

            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to load invoices:", err);
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:24px;color:#e74c3c;">Failed to load invoices.</td></tr>';
    }
}

function formatReminderDate(isoString) {
    const d = new Date(isoString);
    const month = d.toLocaleString("default", { month: "short" });
    const day = d.getDate();
    const year = d.getFullYear();
    return month + " " + day + ", " + year;
}

async function saveNotifyEmail(invoiceId, emailInput, saveBtn) {
    const email = emailInput.value.trim();
    if (!email) return;
    const orig = emailInput.dataset.savedValue || "";
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = "Saving..."; }
    try {
        const resp = await fetch("/api/invoices/" + encodeURIComponent(invoiceId) + "/notify-email", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email }),
        });
        if (resp.ok) {
            emailInput.dataset.savedValue = email;
            if (saveBtn) {
                saveBtn.textContent = "Saved \u2713";
                saveBtn.classList.add("btn-save-email-success");
                setTimeout(function () {
                    saveBtn.textContent = "Save";
                    saveBtn.classList.remove("btn-save-email-success");
                    saveBtn.disabled = false;
                }, 2000);
            }
        } else {
            emailInput.value = orig;
            if (saveBtn) { saveBtn.textContent = "Error"; saveBtn.disabled = false; }
        }
    } catch (err) {
        console.error("Failed to save notify email:", err);
        emailInput.value = orig;
        if (saveBtn) { saveBtn.textContent = "Error"; saveBtn.disabled = false; }
    }
}

async function disregardInvoice(invoiceId, row, btn) {
    if (!confirm("Remove this invoice from the dashboard? This cannot be undone from the UI.")) return;
    btn.disabled = true;
    btn.textContent = "Removing...";
    try {
        const resp = await fetch("/api/invoices/" + encodeURIComponent(invoiceId) + "/disregard", {
            method: "POST",
        });
        if (resp.ok) {
            row.style.opacity = "0";
            row.style.transition = "opacity 0.3s";
            setTimeout(function () { row.remove(); }, 300);
        } else {
            btn.textContent = "Error";
            btn.disabled = false;
        }
    } catch (err) {
        console.error("Failed to disregard invoice:", err);
        btn.textContent = "Error";
        btn.disabled = false;
    }
}

async function sendReminder(btn, invoiceId, emailInput, lastRemindedSpan) {
    btn.disabled = true;
    btn.textContent = "Sending...";
    btn.className = "btn-reminder btn-reminder-sending";
    const notifyEmail = emailInput ? emailInput.value.trim() : null;

    try {
        const resp = await fetch("/api/invoices/send-reminder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ invoice_id: invoiceId, notify_email: notifyEmail || undefined }),
        });
        const result = await resp.json();

        if (resp.ok && result.success) {
            btn.textContent = "Sent \u2713";
            btn.className = "btn-reminder btn-reminder-sent";
            btn.disabled = false;
            setTimeout(function () {
                btn.textContent = "Send Reminder";
                btn.className = "btn-reminder";
            }, 2000);
            if (lastRemindedSpan && result.last_reminded) {
                lastRemindedSpan.textContent = formatReminderDate(result.last_reminded);
                lastRemindedSpan.title = new Date(result.last_reminded).toLocaleString();
            }
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

// --- Margin detail modal ---

function showMarginModal() {
    document.getElementById("margin-detail-modal").style.display = "flex";
}

function hideMarginModal() {
    document.getElementById("margin-detail-modal").style.display = "none";
}

async function loadMarginDetail() {
    const tbody = document.getElementById("margin-detail-body");
    const tfoot = document.getElementById("margin-detail-foot");
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:#888;">Loading...</td></tr>';
    tfoot.innerHTML = "";
    showMarginModal();

    try {
        const resp = await fetch("/api/margin-detail");
        const data = await resp.json();
        const months = data.months;

        const fmtWhole = (n) => "$" + Math.round(Number(n)).toLocaleString("en-US");
        const monthName = (m) => {
            const [y, mo] = m.split("-");
            const d = new Date(Number(y), Number(mo) - 1);
            return d.toLocaleString("default", { month: "short", year: "numeric" });
        };

        tbody.innerHTML = "";
        months.forEach(function (row) {
            const tr = document.createElement("tr");

            const tdMonth = document.createElement("td");
            tdMonth.textContent = monthName(row.month);
            tr.appendChild(tdMonth);

            const tdIn = document.createElement("td");
            tdIn.className = "text-right";
            tdIn.textContent = fmtWhole(row.inflows);
            tdIn.style.color = "#2ecc71";
            tr.appendChild(tdIn);

            const tdOut = document.createElement("td");
            tdOut.className = "text-right";
            tdOut.textContent = fmtWhole(row.outflows);
            tdOut.style.color = "#e74c3c";
            tr.appendChild(tdOut);

            const tdNet = document.createElement("td");
            tdNet.className = "text-right";
            const sign = row.net >= 0 ? "+" : "-";
            tdNet.textContent = sign + "$" + Math.round(Math.abs(row.net)).toLocaleString("en-US");
            tdNet.style.color = row.net >= 0 ? "#2ecc71" : "#e74c3c";
            tr.appendChild(tdNet);

            const tdMargin = document.createElement("td");
            tdMargin.className = "text-right";
            tdMargin.textContent = row.margin.toFixed(1) + "%";
            tdMargin.style.fontWeight = "600";
            tdMargin.style.color = row.margin >= 0 ? "#2ecc71" : "#e74c3c";
            tr.appendChild(tdMargin);

            tbody.appendChild(tr);
        });

        // Averages footer
        const nonZero = months.filter(function (r) { return r.inflows > 0; });
        if (nonZero.length > 0) {
            const avgIn = nonZero.reduce(function (s, r) { return s + r.inflows; }, 0) / nonZero.length;
            const avgOut = nonZero.reduce(function (s, r) { return s + r.outflows; }, 0) / nonZero.length;
            const avgNet = avgIn - avgOut;
            const avgMargin = nonZero.reduce(function (s, r) { return s + r.margin; }, 0) / nonZero.length;

            tfoot.innerHTML = "";
            const footTr = document.createElement("tr");
            footTr.style.borderTop = "2px solid #2a2a4a";

            const tdLabel = document.createElement("td");
            tdLabel.style.fontWeight = "600";
            tdLabel.style.color = "#a0a0b8";
            tdLabel.style.padding = "12px 12px";
            tdLabel.textContent = "Average";
            footTr.appendChild(tdLabel);

            const tdAvgIn = document.createElement("td");
            tdAvgIn.className = "text-right";
            tdAvgIn.style.fontWeight = "600";
            tdAvgIn.style.padding = "12px 12px";
            tdAvgIn.style.color = "#2ecc71";
            tdAvgIn.textContent = fmtWhole(avgIn);
            footTr.appendChild(tdAvgIn);

            const tdAvgOut = document.createElement("td");
            tdAvgOut.className = "text-right";
            tdAvgOut.style.fontWeight = "600";
            tdAvgOut.style.padding = "12px 12px";
            tdAvgOut.style.color = "#e74c3c";
            tdAvgOut.textContent = fmtWhole(avgOut);
            footTr.appendChild(tdAvgOut);

            const tdAvgNet = document.createElement("td");
            tdAvgNet.className = "text-right";
            tdAvgNet.style.fontWeight = "600";
            tdAvgNet.style.padding = "12px 12px";
            const avgSign = avgNet >= 0 ? "+" : "-";
            tdAvgNet.textContent = avgSign + "$" + Math.round(Math.abs(avgNet)).toLocaleString("en-US");
            tdAvgNet.style.color = avgNet >= 0 ? "#2ecc71" : "#e74c3c";
            footTr.appendChild(tdAvgNet);

            const tdAvgMargin = document.createElement("td");
            tdAvgMargin.className = "text-right";
            tdAvgMargin.style.fontWeight = "600";
            tdAvgMargin.style.padding = "12px 12px";
            tdAvgMargin.textContent = avgMargin.toFixed(1) + "%";
            tdAvgMargin.style.color = avgMargin >= 0 ? "#2ecc71" : "#e74c3c";
            footTr.appendChild(tdAvgMargin);

            tfoot.appendChild(footTr);
        }
    } catch (err) {
        console.error("Failed to load margin detail:", err);
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:#e74c3c;">Failed to load margin detail.</td></tr>';
    }
}

function attachMarginClickHandler() {
    const el = document.getElementById("profit-margin-chart");
    if (!el || !el.data) return;

    el.on("plotly_click", function () {
        loadMarginDetail();
    });
}

function attachInVsOutClickHandler() {
    const el = document.getElementById("in-vs-out-chart");
    if (!el || !el.data) return;

    el.on("plotly_click", function (data) {
        if (!data || !data.points || !data.points.length) return;
        const point = data.points[0];
        // curveNumber 0 = Total Invoiced trace
        if (point.curveNumber === 0) {
            const month = String(point.x).slice(0, 7);
            if (month) loadInvoicedBreakdown(month);
        }
    });
}

let invoicedTraceVisible = true;

function toggleTotalInvoiced() {
    const btn = document.getElementById("invoiced-toggle-btn");
    invoicedTraceVisible = !invoicedTraceVisible;
    Plotly.restyle("in-vs-out-chart", { visible: invoicedTraceVisible }, [0]);
    // Money In labels: show when invoiced is OFF, plain line when invoiced is ON
    const moneyInMode = invoicedTraceVisible ? "lines+markers" : "lines+markers+text";
    Plotly.restyle("in-vs-out-chart", { mode: moneyInMode }, [1]);
    if (invoicedTraceVisible) {
        btn.textContent = "◉ Total Invoiced";
        btn.classList.remove("btn-chart-toggle-off");
        btn.classList.add("btn-chart-toggle-on");
    } else {
        btn.textContent = "○ Total Invoiced";
        btn.classList.remove("btn-chart-toggle-on");
        btn.classList.add("btn-chart-toggle-off");
    }
}

let marginUseInvoiced = false;

async function toggleMarginMode() {
    const btn = document.getElementById("margin-mode-btn");
    marginUseInvoiced = !marginUseInvoiced;
    if (marginUseInvoiced) {
        btn.textContent = "◉ Using Invoiced Margin";
        btn.classList.remove("btn-chart-toggle-off");
        btn.classList.add("btn-chart-toggle-on");
    } else {
        btn.textContent = "○ Use Invoiced Margin";
        btn.classList.remove("btn-chart-toggle-on");
        btn.classList.add("btn-chart-toggle-off");
    }
    const mode = marginUseInvoiced ? "invoiced" : "collected";
    try {
        const resp = await fetch("/api/charts/profit-margin?mode=" + mode);
        const fig = await resp.json();
        applyMobileLayout(fig, "profit-margin-chart");
        Plotly.react("profit-margin-chart", fig.data, fig.layout, {
            responsive: true,
            displayModeBar: !isMobile(),
        });
        attachMarginClickHandler();
    } catch (err) {
        console.error("Failed to toggle margin mode:", err);
    }
}

function showInvoicedModal() {
    document.getElementById("invoiced-breakdown-modal").style.display = "flex";
}

function hideInvoicedModal() {
    document.getElementById("invoiced-breakdown-modal").style.display = "none";
    document.getElementById("invoiced-breakdown-content").innerHTML = "";
}

async function loadInvoicedBreakdown(month) {
    document.getElementById("invoiced-modal-title").textContent = "Invoiced Breakdown — Loading...";
    document.getElementById("invoiced-breakdown-content").innerHTML =
        '<p style="text-align:center;color:#888;padding:24px;">Loading...</p>';
    showInvoicedModal();

    try {
        const resp = await fetch("/api/invoiced-breakdown?month=" + encodeURIComponent(month));
        const data = await resp.json();

        const [y, mo] = month.split("-");
        const monthLabel = new Date(Number(y), Number(mo) - 1).toLocaleString("default", { month: "long", year: "numeric" });
        document.getElementById("invoiced-modal-title").textContent = "Invoiced Breakdown — " + monthLabel;

        const fmt = (n) => "$" + Math.round(Number(n)).toLocaleString("en-US");

        let html = '<div class="invoiced-breakdown-total">Total Invoiced: <strong>' + fmt(data.total) + "</strong></div>";

        if (data.stripe_invoices && data.stripe_invoices.length > 0) {
            html += '<h3 class="breakdown-section-title">Stripe Invoices — ' + fmt(data.stripe_total) + "</h3>";
            html += '<div class="invoice-table-container"><table class="invoice-table"><thead><tr>';
            html += "<th>Client</th><th>Invoice #</th><th class=\"text-right\">Amount</th><th>Status</th>";
            html += "</tr></thead><tbody>";
            data.stripe_invoices.forEach(function (inv) {
                const badgeClass = inv.status === "paid" ? "badge-outstanding" : inv.status === "open" ? "badge-overdue" : "";
                html += "<tr><td>" + (inv.customer_name || "—") + "</td><td>" + (inv.number || "—") + "</td>" +
                    "<td class=\"text-right\">" + fmt(inv.amount_due) + "</td>" +
                    "<td><span class=\"badge " + badgeClass + "\">" + inv.status + "</span></td></tr>";
            });
            html += "</tbody></table></div>";
        }

        if (data.mercury_direct && data.mercury_direct.length > 0) {
            html += '<h3 class="breakdown-section-title" style="margin-top:20px;">Mercury Direct Payments — ' + fmt(data.mercury_total) + "</h3>";
            html += '<div class="invoice-table-container"><table class="invoice-table"><thead><tr>';
            html += "<th>Counterparty</th><th class=\"text-right\">Amount</th>";
            html += "</tr></thead><tbody>";
            data.mercury_direct.forEach(function (p) {
                html += "<tr><td>" + p.counterparty + "</td><td class=\"text-right\">" + fmt(p.amount) + "</td></tr>";
            });
            html += "</tbody></table></div>";
        }

        if ((!data.stripe_invoices || data.stripe_invoices.length === 0) && (!data.mercury_direct || data.mercury_direct.length === 0)) {
            html += '<p style="color:#888;padding:24px;text-align:center;">No invoiced data for this month.</p>';
        }

        document.getElementById("invoiced-breakdown-content").innerHTML = html;
    } catch (err) {
        console.error("Failed to load invoiced breakdown:", err);
        document.getElementById("invoiced-breakdown-content").innerHTML =
            '<p style="color:#e74c3c;padding:24px;text-align:center;">Failed to load breakdown.</p>';
    }
}

// --- ARR history modal ---

function showArrModal() {
    document.getElementById("arr-history-modal").style.display = "flex";
}

function hideArrModal() {
    document.getElementById("arr-history-modal").style.display = "none";
}

async function loadArrHistory() {
    const tbody = document.getElementById("arr-history-body");
    const tfoot = document.getElementById("arr-history-foot");
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:#888;">Loading...</td></tr>';
    tfoot.innerHTML = "";
    showArrModal();

    try {
        const resp = await fetch("/api/arr-history");
        const data = await resp.json();
        const months = data.months;

        const fmtWhole = (n) => "$" + Math.round(Number(n)).toLocaleString("en-US");
        const fmtChange = (n) => {
            const sign = n >= 0 ? "+" : "";
            return sign + "$" + Math.round(Math.abs(n)).toLocaleString("en-US");
        };
        const monthName = (m) => {
            const [y, mo] = m.split("-");
            const d = new Date(Number(y), Number(mo) - 1);
            return d.toLocaleString("default", { month: "short", year: "numeric" });
        };

        tbody.innerHTML = "";
        months.forEach(function (row, i) {
            const tr = document.createElement("tr");

            const tdMonth = document.createElement("td");
            tdMonth.textContent = monthName(row.month);
            tr.appendChild(tdMonth);

            const tdCollected = document.createElement("td");
            tdCollected.className = "text-right";
            tdCollected.textContent = fmtWhole(row.collected);
            tr.appendChild(tdCollected);

            const tdArr = document.createElement("td");
            tdArr.className = "text-right";
            tdArr.textContent = fmtWhole(row.arr);
            tr.appendChild(tdArr);

            const tdChange = document.createElement("td");
            tdChange.className = "text-right";
            const tdPct = document.createElement("td");
            tdPct.className = "text-right";
            if (i === 0) {
                tdChange.textContent = "—";
                tdChange.style.color = "#888";
                tdPct.textContent = "—";
                tdPct.style.color = "#888";
            } else {
                const prevArr = months[i - 1].arr;
                const change = row.arr - prevArr;
                tdChange.textContent = fmtChange(change);
                tdChange.style.color = change >= 0 ? "#2ecc71" : "#e74c3c";
                const pct = prevArr !== 0 ? (change / prevArr) * 100 : 0;
                const pctSign = pct >= 0 ? "+" : "";
                tdPct.textContent = pctSign + pct.toFixed(1) + "%";
                tdPct.style.color = pct >= 0 ? "#2ecc71" : "#e74c3c";
            }
            tr.appendChild(tdChange);
            tr.appendChild(tdPct);

            tbody.appendChild(tr);
        });

        // Average MoM change footer
        tfoot.innerHTML = "";
        const footTr = document.createElement("tr");
        footTr.style.borderTop = "2px solid #2a2a4a";

        const tdLabel = document.createElement("td");
        tdLabel.colSpan = 3;
        tdLabel.style.fontWeight = "600";
        tdLabel.style.color = "#a0a0b8";
        tdLabel.style.padding = "12px 12px";
        tdLabel.textContent = "Avg Month-over-Month Change";
        footTr.appendChild(tdLabel);

        const tdAvg = document.createElement("td");
        tdAvg.className = "text-right";
        tdAvg.style.fontWeight = "600";
        tdAvg.style.padding = "12px 12px";
        tdAvg.textContent = fmtChange(data.avg_mom_change);
        tdAvg.style.color = data.avg_mom_change >= 0 ? "#2ecc71" : "#e74c3c";
        footTr.appendChild(tdAvg);

        // Average % change
        var pctChanges = [];
        for (var j = 1; j < months.length; j++) {
            var prev = months[j - 1].arr;
            if (prev !== 0) pctChanges.push(((months[j].arr - prev) / prev) * 100);
        }
        var avgPct = pctChanges.length > 0 ? pctChanges.reduce(function (s, v) { return s + v; }, 0) / pctChanges.length : 0;
        const tdAvgPct = document.createElement("td");
        tdAvgPct.className = "text-right";
        tdAvgPct.style.fontWeight = "600";
        tdAvgPct.style.padding = "12px 12px";
        var avgPctSign = avgPct >= 0 ? "+" : "";
        tdAvgPct.textContent = avgPctSign + avgPct.toFixed(1) + "%";
        tdAvgPct.style.color = avgPct >= 0 ? "#2ecc71" : "#e74c3c";
        footTr.appendChild(tdAvgPct);

        tfoot.appendChild(footTr);
    } catch (err) {
        console.error("Failed to load ARR history:", err);
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:#e74c3c;">Failed to load ARR history.</td></tr>';
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadAll();

    // Close spend detail modal on X button or backdrop click
    document.getElementById("modal-close-btn").addEventListener("click", hideModal);
    document.getElementById("spend-detail-modal").addEventListener("click", function (e) {
        if (e.target === this) hideModal();
    });

    // Close invoiced breakdown modal on X button or backdrop click
    document.getElementById("invoiced-modal-close-btn").addEventListener("click", hideInvoicedModal);
    document.getElementById("invoiced-breakdown-modal").addEventListener("click", function (e) {
        if (e.target === this) hideInvoicedModal();
    });

    // Close invoice detail modal on X button or backdrop click
    document.getElementById("invoice-modal-close-btn").addEventListener("click", hideInvoiceModal);
    document.getElementById("invoice-detail-modal").addEventListener("click", function (e) {
        if (e.target === this) hideInvoiceModal();
    });

    // Close margin detail modal on X button or backdrop click
    document.getElementById("margin-modal-close-btn").addEventListener("click", hideMarginModal);
    document.getElementById("margin-detail-modal").addEventListener("click", function (e) {
        if (e.target === this) hideMarginModal();
    });

    // Close ARR history modal on X button or backdrop click
    document.getElementById("arr-modal-close-btn").addEventListener("click", hideArrModal);
    document.getElementById("arr-history-modal").addEventListener("click", function (e) {
        if (e.target === this) hideArrModal();
    });

    // Refresh chart data every hour
    setInterval(loadAll, 60 * 60 * 1000);
});
