from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

import plotly
import plotly.graph_objects as go

from models.queries import (
    get_mercury_monthly_flows,
    get_avg_days_to_pay,
    get_overall_avg_days_to_pay,
    get_revenue_by_client,
    get_active_subscriptions_by_client,
    get_open_invoices_by_client,
    get_monthly_spend_by_category,
    get_monthly_spend_details,
    SPEND_CATEGORIES,
)

BG_COLOR = "#1a1a2e"
GRID_COLOR = "#2a2a4a"
TEXT_COLOR = "#ffffff"
GREEN = "#2ecc71"
RED = "#e74c3c"
BLUE = "#3498db"


def _chart_months():
    """Return monthly labels from April 2025 through the current month."""
    start = datetime(2025, 4, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    months = []
    dt = start
    while dt.strftime("%Y-%m") <= now.strftime("%Y-%m"):
        months.append(dt.strftime("%Y-%m"))
        dt += relativedelta(months=1)
    return months


def build_in_vs_out_chart() -> str:
    """Build a dark-mode Plotly JSON figure for money in vs money out."""
    data = get_mercury_monthly_flows()
    inflows_by_month = {row["month"]: row["inflows"] for row in data}
    outflows_by_month = {row["month"]: row["outflows"] for row in data}
    distributions_by_month = {row["month"]: row["owner_distributions"] for row in data}

    months = _chart_months()
    inflows = [inflows_by_month.get(m, 0) for m in months]
    outflows = [outflows_by_month.get(m, 0) for m in months]
    distributions = [distributions_by_month.get(m, 0) for m in months]

    # Calculate net (money in minus money out, not including distributions)
    net = [i - o for i, o in zip(inflows, outflows)]
    label_y = [max(i, o, d) for i, o, d in zip(inflows, outflows, distributions)]
    label_text = []
    for n in net:
        sign = "+" if n >= 0 else "-"
        label_text.append(f"{sign}${abs(n):,.0f}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months,
        y=inflows,
        mode="lines+markers",
        name="Money In",
        line=dict(color=GREEN, width=4),
        marker=dict(size=10, color=GREEN),
    ))
    fig.add_trace(go.Scatter(
        x=months,
        y=outflows,
        mode="lines+markers",
        name="Money Out",
        line=dict(color=RED, width=4),
        marker=dict(size=10, color=RED),
    ))
    fig.add_trace(go.Scatter(
        x=months,
        y=distributions,
        mode="lines+markers",
        name="Owner Distributions",
        line=dict(color=BLUE, width=4),
        marker=dict(size=10, color=BLUE),
    ))
    # Net labels above each month
    fig.add_trace(go.Scatter(
        x=months,
        y=label_y,
        mode="text",
        text=label_text,
        textposition="top center",
        textfont=dict(size=12, color=[GREEN if n >= 0 else RED for n in net]),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Right-side summary: 12-mo, 6-mo, 3-mo totals for each line
    summary_metrics = [
        {"label": "Money In",            "values": inflows,       "color": GREEN},
        {"label": "Money Out",           "values": outflows,      "color": RED},
        {"label": "Owner Distributions", "values": distributions, "color": BLUE},
    ]
    periods = [
        {"n": 12, "label": "12-mo"},
        {"n": 6,  "label": "6-mo"},
        {"n": 3,  "label": "3-mo"},
    ]

    # Starting y position (paper coords), shifted down to avoid legend overlap
    y_starts = [0.78, 0.48, 0.18]
    for metric, y_base in zip(summary_metrics, y_starts):
        # Metric label
        fig.add_annotation(
            text=f"<b>{metric['label']}</b>",
            xref="paper", yref="paper",
            x=1.02, y=y_base,
            showarrow=False, xanchor="left",
            font=dict(color=metric["color"], size=13),
        )
        for j, period in enumerate(periods):
            total = sum(metric["values"][-period["n"]:])
            fig.add_annotation(
                text=f"{period['label']}:  <b>${total:,.0f}</b>",
                xref="paper", yref="paper",
                x=1.02, y=y_base - 0.06 - (j * 0.06),
                showarrow=False, xanchor="left",
                font=dict(color=TEXT_COLOR, size=12),
            )

    fig.update_layout(
        title=dict(
            text="Money In vs Money Out by Month",
            font=dict(size=22, color=TEXT_COLOR),
            x=0.45,
        ),
        xaxis=dict(
            dtick="M1",
            tickformat="%b %Y",
            title=dict(text="Month", font=dict(color=TEXT_COLOR)),
            tickfont=dict(color=TEXT_COLOR, size=12),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="Amount ($)", font=dict(color=TEXT_COLOR)),
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(color=TEXT_COLOR, size=12),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=False,
        ),
        legend=dict(
            font=dict(color=TEXT_COLOR, size=13),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        margin=dict(l=70, r=220, t=80, b=50),
        hoverlabel=dict(
            bgcolor="#2a2a4a",
            font_color=TEXT_COLOR,
            font_size=13,
        ),
    )
    return plotly.io.to_json(fig)


def build_profit_margin_chart() -> str:
    """Build a dark-mode profit margin chart. Margin = (Money In - Money Out) / Money In."""
    data = get_mercury_monthly_flows()
    inflows_by_month = {row["month"]: row["inflows"] for row in data}
    outflows_by_month = {row["month"]: row["outflows"] for row in data}

    months = _chart_months()
    inflows = [inflows_by_month.get(m, 0) for m in months]
    outflows = [outflows_by_month.get(m, 0) for m in months]

    margins = []
    for i, o in zip(inflows, outflows):
        if i > 0:
            margins.append(round((i - o) / i * 100, 1))
        else:
            margins.append(0)

    # Color each bar green if positive, red if negative
    bar_colors = [GREEN if m >= 0 else RED for m in margins]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months,
        y=margins,
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=[f"{m:.0f}%" for m in margins],
        textposition="outside",
        textfont=dict(color=TEXT_COLOR, size=13),
        hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>",
    ))
    # Compute trailing averages
    avg_configs = [
        {"n": 12, "label": "12-Month", "color": "#f39c12", "x": 0.15},
        {"n": 6,  "label": "6-Month",  "color": "#9b59b6", "x": 0.50},
        {"n": 3,  "label": "3-Month",  "color": "#1abc9c", "x": 0.85},
    ]
    for cfg in avg_configs:
        recent = [m for m in margins[-cfg["n"]:] if m != 0]
        if recent:
            avg = sum(recent) / len(recent)
            # Subtle dashed reference line across chart
            fig.add_hline(
                y=avg,
                line_dash="dot",
                line_color=cfg["color"],
                line_width=1,
                opacity=0.5,
            )
            # Label above
            fig.add_annotation(
                text=f"<b>{cfg['label']} Avg</b>",
                xref="paper", yref="paper",
                x=cfg["x"], y=1.22,
                showarrow=False,
                font=dict(color=cfg["color"], size=14),
                align="center",
            )
            # Large number below label
            fig.add_annotation(
                text=f"<b>{avg:.0f}%</b>",
                xref="paper", yref="paper",
                x=cfg["x"], y=1.12,
                showarrow=False,
                font=dict(color=cfg["color"], size=28),
                align="center",
            )

    fig.update_layout(
        title=dict(
            text="Net Profit Margin by Month",
            font=dict(size=22, color=TEXT_COLOR),
            x=0.5,
            y=0.98,
        ),
        xaxis=dict(
            dtick="M1",
            tickformat="%b %Y",
            title=dict(text="Month", font=dict(color=TEXT_COLOR)),
            tickfont=dict(color=TEXT_COLOR, size=12),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="Margin (%)", font=dict(color=TEXT_COLOR)),
            ticksuffix="%",
            tickfont=dict(color=TEXT_COLOR, size=12),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=True,
            zerolinecolor=GRID_COLOR,
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        margin=dict(l=70, r=30, t=160, b=50),
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#2a2a4a",
            font_color=TEXT_COLOR,
            font_size=13,
        ),
    )
    return plotly.io.to_json(fig)


ORANGE = "#f39c12"
PURPLE = "#9b59b6"
TEAL = "#1abc9c"


def build_days_to_pay_chart() -> str:
    """Horizontal bar chart showing average days to pay per client."""
    data = get_avg_days_to_pay()
    overall = get_overall_avg_days_to_pay()

    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="No paid invoice data yet",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color=TEXT_COLOR, size=18),
        )
        fig.update_layout(paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR)
        return plotly.io.to_json(fig)

    # Reverse so slowest payers appear at top of chart
    data = list(reversed(data))
    names = [r["customer_name"] for r in data]
    days = [r["avg_days"] for r in data]
    counts = [r["invoice_count"] for r in data]

    # Color: green for fast payers (<14 days), orange for medium, red for slow
    bar_colors = []
    for d in days:
        if d <= 14:
            bar_colors.append(GREEN)
        elif d <= 30:
            bar_colors.append(ORANGE)
        else:
            bar_colors.append(RED)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names,
        x=days,
        orientation="h",
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=[f"{d:.0f} days ({c} inv)" for d, c in zip(days, counts)],
        textposition="outside",
        textfont=dict(color=TEXT_COLOR, size=12),
        hovertemplate="<b>%{y}</b><br>Avg: %{x:.1f} days<extra></extra>",
    ))

    # Overall average vertical line
    if overall["avg_days"]:
        fig.add_vline(
            x=overall["avg_days"],
            line_dash="dash",
            line_color=PURPLE,
            line_width=2,
        )
        fig.add_annotation(
            text=f"Overall Avg: {overall['avg_days']:.0f} days",
            xref="paper", yref="paper",
            x=0.5, y=1.08,
            showarrow=False,
            font=dict(color=PURPLE, size=16),
        )

    # Show worst 15 initially (they're at the top = end of the list)
    visible_count = min(15, len(names))
    y_start = len(names) - visible_count - 0.5
    y_end = len(names) - 0.5

    fig.update_layout(
        title=dict(
            text="Average Days to Pay by Client",
            font=dict(size=20, color=TEXT_COLOR),
            x=0.5,
        ),
        xaxis=dict(
            title=dict(text="Days", font=dict(color=TEXT_COLOR)),
            tickfont=dict(color=TEXT_COLOR, size=11),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(color=TEXT_COLOR, size=11),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            range=[y_start, y_end],
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        margin=dict(l=200, r=100, t=80, b=40),
        height=500,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#2a2a4a",
            font_color=TEXT_COLOR,
            font_size=13,
        ),
    )
    return plotly.io.to_json(fig)


def build_revenue_by_client_chart() -> str:
    """Horizontal bar chart showing total revenue per client (top 15)."""
    data = get_revenue_by_client()

    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="No paid invoice data yet",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color=TEXT_COLOR, size=18),
        )
        fig.update_layout(paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR)
        return plotly.io.to_json(fig)

    # Show all clients but chart is fixed height — Plotly scrolls via range
    total_all = sum(r["total_revenue"] for r in data)
    # Reverse so #1 is at top in horizontal bar
    display = list(reversed(data))
    names = [r["customer_name"] for r in display]
    revenues = [r["total_revenue"] for r in display]

    palette = [GREEN, TEAL, BLUE, PURPLE, ORANGE, "#e67e22", "#95a5a6"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names,
        x=revenues,
        orientation="h",
        marker=dict(
            color=[palette[i % len(palette)] for i in range(len(names))],
            line=dict(width=0),
        ),
        text=[f"${r:,.0f} ({r/total_all*100:.0f}%)" for r in revenues],
        textposition="outside",
        textfont=dict(color=TEXT_COLOR, size=11),
        hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
    ))

    fig.add_annotation(
        text=f"<b>Total Revenue: ${total_all:,.0f}</b>",
        xref="paper", yref="paper",
        x=0.5, y=1.06,
        showarrow=False,
        font=dict(color=GREEN, size=15),
    )

    # Show top 15 in initial view; user can scroll to see the rest
    visible_count = min(15, len(names))
    y_start = len(names) - visible_count - 0.5
    y_end = len(names) - 0.5

    fig.update_layout(
        title=dict(
            text="Revenue by Client",
            font=dict(size=20, color=TEXT_COLOR),
            x=0.5,
        ),
        xaxis=dict(
            title=dict(text="Total Paid ($)", font=dict(color=TEXT_COLOR)),
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(color=TEXT_COLOR, size=11),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(color=TEXT_COLOR, size=11),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            range=[y_start, y_end],
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        margin=dict(l=180, r=100, t=70, b=40),
        height=500,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#2a2a4a",
            font_color=TEXT_COLOR,
            font_size=13,
        ),
    )
    return plotly.io.to_json(fig)


def build_concentration_risk_chart() -> str:
    """Pie chart showing monthly revenue share from active subscriptions only."""
    data = get_active_subscriptions_by_client()

    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="No active client data yet",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color=TEXT_COLOR, size=18),
        )
        fig.update_layout(paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR)
        return plotly.io.to_json(fig)

    names = [r["customer_name"] for r in data]
    amounts = [r["monthly_revenue"] for r in data]
    total = sum(amounts)

    palette = [GREEN, TEAL, BLUE, PURPLE, ORANGE, "#e67e22", "#e74c3c",
               "#95a5a6", "#7f8c8d", "#bdc3c7", "#16a085", "#2980b9",
               "#8e44ad", "#d35400", "#c0392b"]

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=names,
        values=amounts,
        hole=0,
        marker=dict(
            colors=[palette[i % len(palette)] for i in range(len(names))],
            line=dict(color=BG_COLOR, width=2),
        ),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f}/mo (%{percent})<extra></extra>",
    ))

    fig.add_annotation(
        text=f"<b>MRR: ${total:,.0f}</b>",
        xref="paper", yref="paper",
        x=0.5, y=1.12,
        showarrow=False,
        font=dict(color=GREEN, size=15),
    )

    fig.update_layout(
        title=dict(
            text="Active Client Revenue Share",
            font=dict(size=20, color=TEXT_COLOR),
            x=0.5,
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        margin=dict(l=30, r=30, t=70, b=30),
        height=500,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#2a2a4a",
            font_color=TEXT_COLOR,
            font_size=13,
        ),
    )
    return plotly.io.to_json(fig)


YELLOW = "#f1c40f"


def build_expected_revenue_chart() -> str:
    """Stacked horizontal bar chart: outstanding vs overdue invoices by client."""
    data = get_open_invoices_by_client()

    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="No open invoices — all caught up!",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color=GREEN, size=18),
        )
        fig.update_layout(paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR)
        return plotly.io.to_json(fig)

    # Reverse so largest total is at top in horizontal bar layout
    display = list(reversed(data))
    names = [r["customer_name"] for r in display]
    outstanding = [r["outstanding"] for r in display]
    overdue = [r["overdue"] for r in display]

    total_outstanding = sum(r["outstanding"] for r in data)
    total_overdue = sum(r["overdue"] for r in data)
    total_all = total_outstanding + total_overdue

    fig = go.Figure()

    # Outstanding bars (yellow)
    fig.add_trace(go.Bar(
        y=names,
        x=outstanding,
        orientation="h",
        name="Outstanding",
        marker=dict(color=YELLOW, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>Outstanding: $%{x:,.0f}<extra></extra>",
    ))

    # Overdue bars (red), stacked
    fig.add_trace(go.Bar(
        y=names,
        x=overdue,
        orientation="h",
        name="Overdue",
        marker=dict(color=RED, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>Overdue: $%{x:,.0f}<extra></extra>",
    ))

    # Summary annotations at top
    fig.add_annotation(
        text="<b>Outstanding</b>",
        xref="paper", yref="paper",
        x=0.2, y=1.18,
        showarrow=False,
        font=dict(color=YELLOW, size=13),
    )
    fig.add_annotation(
        text=f"<b>${total_outstanding:,.0f}</b>",
        xref="paper", yref="paper",
        x=0.2, y=1.09,
        showarrow=False,
        font=dict(color=YELLOW, size=24),
    )
    fig.add_annotation(
        text="<b>Overdue</b>",
        xref="paper", yref="paper",
        x=0.5, y=1.18,
        showarrow=False,
        font=dict(color=RED, size=13),
    )
    fig.add_annotation(
        text=f"<b>${total_overdue:,.0f}</b>",
        xref="paper", yref="paper",
        x=0.5, y=1.09,
        showarrow=False,
        font=dict(color=RED, size=24),
    )
    fig.add_annotation(
        text="<b>Total Owed</b>",
        xref="paper", yref="paper",
        x=0.8, y=1.18,
        showarrow=False,
        font=dict(color=TEXT_COLOR, size=13),
    )
    fig.add_annotation(
        text=f"<b>${total_all:,.0f}</b>",
        xref="paper", yref="paper",
        x=0.8, y=1.09,
        showarrow=False,
        font=dict(color=TEXT_COLOR, size=24),
    )

    # Show 15 clients at a time, scroll for more
    visible_count = min(15, len(names))
    y_start = len(names) - visible_count - 0.5
    y_end = len(names) - 0.5

    fig.update_layout(
        barmode="stack",
        title=dict(
            text="Expected Revenue — Open Invoices",
            font=dict(size=20, color=TEXT_COLOR),
            x=0.5,
            y=0.98,
        ),
        xaxis=dict(
            title=dict(text="Amount ($)", font=dict(color=TEXT_COLOR)),
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(color=TEXT_COLOR, size=11),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(color=TEXT_COLOR, size=11),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            range=[y_start, y_end],
        ),
        legend=dict(
            font=dict(color=TEXT_COLOR, size=12),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            x=0.5, xanchor="center",
            y=-0.18,
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        margin=dict(l=200, r=40, t=140, b=90),
        height=550,
        hoverlabel=dict(
            bgcolor="#2a2a4a",
            font_color=TEXT_COLOR,
            font_size=13,
        ),
    )
    return plotly.io.to_json(fig)


# Category colors
CATEGORY_COLORS = {
    "Salaries":             "#3498db",
    "Labor":                "#e74c3c",
    "Tech Vendors":         "#9b59b6",
    "Email Infrastructure": "#1abc9c",
    "Taxes":                "#f39c12",
    "Travel":               "#e67e22",
    "Miscellaneous":        "#95a5a6",
}


def build_spend_by_category_chart() -> str:
    """Stacked area chart showing monthly spending by category with vendor detail on hover."""
    cat_data = get_monthly_spend_by_category()
    detail_data = get_monthly_spend_details()

    if not cat_data:
        fig = go.Figure()
        fig.add_annotation(
            text="No spending data yet",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color=TEXT_COLOR, size=18),
        )
        fig.update_layout(paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR)
        return plotly.io.to_json(fig)

    months = _chart_months()

    fig = go.Figure()

    for category in SPEND_CATEGORIES:
        amounts = [cat_data.get(m, {}).get(category, 0) for m in months]

        # Skip categories with zero spend across all months
        if sum(amounts) == 0:
            continue

        # Build hover text showing vendor breakdown
        hover_texts = []
        for m in months:
            vendors = detail_data.get(m, {}).get(category, [])
            if vendors:
                lines = [f"<b>{category} — ${sum(a for _, a in vendors):,.0f}</b>", ""]
                for name, amt in vendors[:8]:
                    lines.append(f"  {name}: ${amt:,.0f}")
                if len(vendors) > 8:
                    lines.append(f"  +{len(vendors) - 8} more")
                hover_texts.append("<br>".join(lines))
            else:
                hover_texts.append(f"<b>{category}</b><br>$0")

        fig.add_trace(go.Bar(
            x=months,
            y=amounts,
            name=category,
            marker=dict(color=CATEGORY_COLORS.get(category, "#95a5a6"), line=dict(width=0)),
            hovertext=hover_texts,
            hoverinfo="text",
        ))

    fig.update_layout(
        barmode="stack",
        title=dict(
            text="Spending by Category",
            font=dict(size=22, color=TEXT_COLOR),
            x=0.5,
        ),
        xaxis=dict(
            dtick="M1",
            tickformat="%b %Y",
            title=dict(text="Month", font=dict(color=TEXT_COLOR)),
            tickfont=dict(color=TEXT_COLOR, size=12),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="Spend ($)", font=dict(color=TEXT_COLOR)),
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(color=TEXT_COLOR, size=12),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=False,
        ),
        legend=dict(
            font=dict(color=TEXT_COLOR, size=12),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            x=0.5, xanchor="center",
            y=-0.12,
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        margin=dict(l=80, r=30, t=80, b=80),
        hoverlabel=dict(
            bgcolor="#2a2a4a",
            font_color=TEXT_COLOR,
            font_size=12,
        ),
    )
    return plotly.io.to_json(fig)


def build_spend_detail_chart(month: str, category: str) -> str:
    """Build a horizontal bar chart showing vendor-level spend for one month+category."""
    detail_data = get_monthly_spend_details()
    vendors = detail_data.get(month, {}).get(category, [])

    fig = go.Figure()

    if not vendors:
        fig.add_annotation(
            text="No data for this selection",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color=TEXT_COLOR, size=18),
        )
        fig.update_layout(paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR)
        return plotly.io.to_json(fig)

    # Sort by amount ascending so largest appears at top in horizontal bar
    vendors_sorted = sorted(vendors, key=lambda v: v[1])
    names = [v[0] for v in vendors_sorted]
    amounts = [v[1] for v in vendors_sorted]

    color = CATEGORY_COLORS.get(category, "#95a5a6")

    fig.add_trace(go.Bar(
        y=names,
        x=amounts,
        orientation="h",
        marker=dict(color=color, line=dict(width=0)),
        text=[f"${a:,.0f}" for a in amounts],
        textposition="outside",
        textfont=dict(color=TEXT_COLOR, size=12),
        hovertemplate="<b>%{y}</b><br>$%{x:,.0f}<extra></extra>",
    ))

    # Format month label: "2025-12" -> "Dec 2025"
    try:
        month_label = datetime.strptime(month, "%Y-%m").strftime("%b %Y")
    except ValueError:
        month_label = month

    total = sum(amounts)
    fig.add_annotation(
        text=f"<b>Total: ${total:,.0f}</b>",
        xref="paper", yref="paper",
        x=0.5, y=1.06,
        showarrow=False,
        font=dict(color=color, size=15),
    )

    # Show up to 15 vendors; user can scroll for more
    visible_count = min(15, len(names))
    y_start = len(names) - visible_count - 0.5
    y_end = len(names) - 0.5

    fig.update_layout(
        title=dict(
            text=f"{category} \u2014 {month_label}",
            font=dict(size=20, color=TEXT_COLOR),
            x=0.5,
        ),
        xaxis=dict(
            title=dict(text="Amount ($)", font=dict(color=TEXT_COLOR)),
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(color=TEXT_COLOR, size=11),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(color=TEXT_COLOR, size=11),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            range=[y_start, y_end],
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        margin=dict(l=200, r=80, t=80, b=40),
        height=max(350, min(len(names) * 30 + 120, 550)),
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#2a2a4a",
            font_color=TEXT_COLOR,
            font_size=13,
        ),
    )
    return plotly.io.to_json(fig)
