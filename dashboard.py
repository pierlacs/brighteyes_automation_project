from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import streamlit as st


# --------------------------------------------------------------------------------------
# Page config (required structure)
# --------------------------------------------------------------------------------------

st.set_page_config(layout="wide", page_title="BrightEyes Dashboard", page_icon="👁️")


# --------------------------------------------------------------------------------------
# Custom CSS (required structure)
# --------------------------------------------------------------------------------------

st.markdown(
    """
<style>
  /* Reduce default Streamlit chrome */
  header { visibility: hidden; }

  /* Page spacing */
  .block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
  }

  /* Sidebar styling */
  section[data-testid="stSidebar"] {
    background: #1E3A5F;
  }
  section[data-testid="stSidebar"] * {
    color: white !important;
  }

  /* Brand accents inside sidebar */
  .be-sidebar-logo {
    font-weight: 900;
    font-size: 1.35rem;
    letter-spacing: 0.4px;
    margin-bottom: 0.15rem;
  }
  .be-sidebar-tagline {
    font-size: 0.85rem;
    color: #00B4D8 !important;
    margin-bottom: 0.9rem;
  }

  /* Headings */
  h1, h2, h3 { color: #1E3A5F; }
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------------------
# Helpers: file loading (KEEP existing file-reading logic)
# --------------------------------------------------------------------------------------

APP_DIR = Path(__file__).parent


def _warn_missing(demo_n: int, rel_path: str) -> None:
    st.warning(f'Run demo {demo_n} first to see this output (missing: `{rel_path}`)')


def read_text_or_warn(*, demo_n: int, rel_path: str) -> Optional[str]:
    path = APP_DIR / rel_path
    if not path.exists():
        _warn_missing(demo_n, rel_path)
        return None
    return path.read_text(encoding="utf-8")


def read_json_or_warn(*, demo_n: int, rel_path: str) -> Optional[dict[str, Any]]:
    raw = read_text_or_warn(demo_n=demo_n, rel_path=rel_path)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            st.warning(f"Unexpected JSON structure in `{rel_path}` (expected an object).")
            return None
        return data
    except Exception as e:
        st.warning(f"Could not parse `{rel_path}` as JSON: {e}")
        return None


def read_csv_or_warn(*, demo_n: int, rel_path: str) -> Optional[pd.DataFrame]:
    path = APP_DIR / rel_path
    if not path.exists():
        _warn_missing(demo_n, rel_path)
        return None
    try:
        return pd.read_csv(path)
    except Exception as e:
        st.warning(f"Could not read `{rel_path}` as CSV: {e}")
        return None


# --------------------------------------------------------------------------------------
# Load data (KEEP existing paths + pandas/JSON/Markdown reads)
# --------------------------------------------------------------------------------------

tender_md = read_text_or_warn(
    demo_n=1, rel_path="demo1_tender/output/tender_analysis_TENDER-2026-OPH-0187.md"
)
proposal_md = read_text_or_warn(
    demo_n=2, rel_path="demo2_proposal/output/proposal_Clinica_Oculistica_Milano.md"
)
purchase_df = read_csv_or_warn(demo_n=3, rel_path="demo3_supplier/data/purchase_history.csv")
install_json = read_json_or_warn(
    demo_n=4, rel_path="demo4_installation/output/installation_data_verdi.json"
)
wbr_df = read_csv_or_warn(demo_n=5, rel_path="demo5_wbr/data/weekly_metrics.csv")


# --------------------------------------------------------------------------------------
# Sidebar (required structure)
# --------------------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<div class="be-sidebar-logo">BrightEyes</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="be-sidebar-tagline">AI-Powered Operations Dashboard</div>',
        unsafe_allow_html=True,
    )

    tabs = ["Overview", "Commercial Automation", "Supplier Intelligence", "Installation Intelligence", "Weekly Business Review"]

    # Store selection in session state under the exact key requested.
    st.radio("Navigation", tabs, key="tab")


# --------------------------------------------------------------------------------------
# Main area (required structure)
# --------------------------------------------------------------------------------------

tab = st.session_state.get("tab", "Overview")

if tab == "Overview":
    st.markdown("## Executive Dashboard")
    st.markdown(
        '<div style="color: rgba(0,0,0,0.45); margin-top:-0.25rem; margin-bottom:1rem; font-size:0.95rem;">'
        "Unified view across 5 AI demos — use the week range to filter all metrics"
        "</div>",
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Week range slider (drives all KPIs and charts below)
    # ------------------------------------------------------------------
    st.slider("Select week range", 1, 12, (1, 12), key="overview_week_range")
    start_w, end_w = st.session_state.get("overview_week_range", (1, 12))

    # ------------------------------------------------------------------
    # Load & filter WBR data
    # ------------------------------------------------------------------
    wbr_path = Path(__file__).parent / "demo5_wbr/data/weekly_metrics.csv"
    wbr_ok = wbr_path.exists()
    wbr_f: Optional[pd.DataFrame] = None

    if wbr_ok:
        try:
            _wbr_raw = pd.read_csv(wbr_path)
            _wbr_raw["week_num"] = (
                _wbr_raw["week"].astype(str).str.replace("W", "", regex=False).astype("Int64")
            )
            for _col in [
                "revenue_eur", "proposals_sent", "proposals_won",
                "installations_completed", "csat_score",
                "support_tickets_open", "support_tickets_closed",
                "new_leads", "demo_requests",
            ]:
                if _col in _wbr_raw.columns:
                    _wbr_raw[_col] = pd.to_numeric(_wbr_raw[_col], errors="coerce")
            wbr_f = _wbr_raw[
                (_wbr_raw["week_num"] >= int(start_w)) & (_wbr_raw["week_num"] <= int(end_w))
            ].copy()
        except Exception as _e:
            st.warning(f"Could not read WBR CSV: {_e}")

    # ------------------------------------------------------------------
    # Derive KPI values from the filtered range
    # ------------------------------------------------------------------

    # 1. Total Revenue — sum of revenue_eur in range
    kpi_revenue: Optional[float] = (
        float(wbr_f["revenue_eur"].fillna(0).sum()) if wbr_f is not None else None
    )

    # 2. Open Pipeline Value (derived metric)
    # Logic: proposals_in_flight = proposals_sent - proposals_won (not yet closed deals).
    # We multiply by the company's average deal size (€27,000 per company_context.md).
    # This is an estimate of revenue still to be realised from active proposals.
    AVG_DEAL_SIZE_EUR = 27_000
    kpi_pipeline: Optional[float] = None
    if wbr_f is not None:
        _sent = int(wbr_f["proposals_sent"].fillna(0).sum())
        _won  = int(wbr_f["proposals_won"].fillna(0).sum())
        _in_flight = max(0, _sent - _won)
        kpi_pipeline = float(_in_flight * AVG_DEAL_SIZE_EUR)

    # 3. Win Rate — proposals_won / proposals_sent (as %)
    kpi_win_rate: Optional[float] = None
    if wbr_f is not None:
        _s = float(wbr_f["proposals_sent"].fillna(0).sum())
        _w = float(wbr_f["proposals_won"].fillna(0).sum())
        kpi_win_rate = (_w / _s * 100) if _s > 0 else 0.0

    # 4. Installations Completed — sum in range
    kpi_installs: Optional[int] = (
        int(wbr_f["installations_completed"].fillna(0).sum()) if wbr_f is not None else None
    )

    # 5. CSAT — average across range (more informative than latest single value)
    kpi_csat: Optional[float] = (
        float(wbr_f["csat_score"].dropna().mean()) if wbr_f is not None else None
    )

    # 6. High-Risk Suppliers — computed from purchase history (independent of week range)
    # Reuse purchase_df loaded at the top of the file.
    kpi_high_risk_suppliers: int = 0
    if purchase_df is not None:
        _p = purchase_df.copy()
        _p["quality_rating"] = pd.to_numeric(_p.get("quality_rating", pd.Series(dtype=float)), errors="coerce")
        _p["notes"] = _p["notes"].fillna("").astype(str) if "notes" in _p.columns else ""
        _issue_mask = _p["notes"].str.contains(r"(defective|late|scratch)", case=False, regex=True)
        _p["issue_flag"] = _issue_mask
        _agg = (
            _p.groupby("supplier", dropna=False)
            .agg(avg_quality=("quality_rating", "mean"), issue_count=("issue_flag", "sum"))
            .reset_index()
        )
        kpi_high_risk_suppliers = int((_agg["avg_quality"] < 3.5).sum())

    # ------------------------------------------------------------------
    # Helper: render a styled KPI card
    # ------------------------------------------------------------------
    def kpi_card(
        *,
        label: str,
        value: str,
        subtitle: str,
        border_color: str = "#00B4D8",
        value_color: str = "#1E3A5F",
    ) -> None:
        st.markdown(
            f"""
<div style="
  border: 1px solid rgba(0,0,0,0.07);
  border-top: 4px solid {border_color};
  border-radius: 12px;
  padding: 16px 18px 14px;
  background: white;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  height: 100%;
">
  <div style="font-size:0.75rem; font-weight:700; letter-spacing:0.08em;
              text-transform:uppercase; color:rgba(0,0,0,0.45); margin-bottom:6px;">
    {label}
  </div>
  <div style="font-size:1.75rem; font-weight:800; color:{value_color}; line-height:1.1;">
    {value}
  </div>
  <div style="font-size:0.78rem; color:rgba(0,0,0,0.45); margin-top:5px;">
    {subtitle}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Row 1 — 6 KPI cards
    # ------------------------------------------------------------------
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        kpi_card(
            label="Revenue",
            value=f"€{kpi_revenue:,.0f}" if kpi_revenue is not None else "—",
            subtitle=f"W{start_w}–W{end_w} booked",
            border_color="#00B4D8",
        )
    with c2:
        kpi_card(
            label="Open Pipeline",
            value=f"€{kpi_pipeline:,.0f}" if kpi_pipeline is not None else "—",
            subtitle="Proposals in flight × avg deal",
            border_color="#1E3A5F",
        )
    with c3:
        kpi_card(
            label="Win Rate",
            value=f"{kpi_win_rate:.0f}%" if kpi_win_rate is not None else "—",
            subtitle="Proposals won / sent",
            border_color="#2ECC71" if (kpi_win_rate or 0) >= 50 else "#FFC300",
            value_color="#2ECC71" if (kpi_win_rate or 0) >= 50 else "#E67E22",
        )
    with c4:
        kpi_card(
            label="Installations",
            value=str(kpi_installs) if kpi_installs is not None else "—",
            subtitle="Completed in range",
            border_color="#00B4D8",
        )
    with c5:
        _csat_color = "#2ECC71" if (kpi_csat or 0) >= 4.0 else "#E74C3C"
        kpi_card(
            label="Avg CSAT",
            value=f"{kpi_csat:.2f} / 5" if kpi_csat is not None else "—",
            subtitle="Customer satisfaction score",
            border_color=_csat_color,
            value_color=_csat_color,
        )
    with c6:
        _risk_color = "#E74C3C" if kpi_high_risk_suppliers > 0 else "#2ECC71"
        kpi_card(
            label="High-Risk Suppliers",
            value=str(kpi_high_risk_suppliers),
            subtitle="Of 5 active suppliers",
            border_color=_risk_color,
            value_color=_risk_color,
        )

    st.markdown("<div style='margin-top:1.25rem;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Row 2 — Two trend charts side by side
    # ------------------------------------------------------------------
    if wbr_f is not None:
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except Exception:
            st.warning("Plotly is required for charts. Install with `pip install plotly`.")
        else:
            chart_left, chart_right = st.columns(2)

            # ── Chart A: Commercial Momentum ──────────────────────────────
            with chart_left:
                fig_a = make_subplots(specs=[[{"secondary_y": True}]])

                fig_a.add_trace(
                    go.Bar(
                        x=wbr_f["week"].tolist(),
                        y=wbr_f["revenue_eur"].tolist(),
                        name="Revenue (€)",
                        marker_color="#00B4D8",
                        hovertemplate="<b>%{x}</b><br>Revenue: €%{y:,.0f}<extra></extra>",
                    ),
                    secondary_y=False,
                )
                fig_a.add_trace(
                    go.Scatter(
                        x=wbr_f["week"].tolist(),
                        y=wbr_f["proposals_sent"].tolist(),
                        name="Proposals Sent",
                        mode="lines+markers",
                        line=dict(color="#1E3A5F", width=2.5),
                        marker=dict(size=6),
                        hovertemplate="<b>%{x}</b><br>Proposals Sent: %{y}<extra></extra>",
                    ),
                    secondary_y=True,
                )
                fig_a.add_trace(
                    go.Scatter(
                        x=wbr_f["week"].tolist(),
                        y=wbr_f["proposals_won"].tolist(),
                        name="Proposals Won",
                        mode="lines+markers",
                        line=dict(color="#2ECC71", width=2, dash="dot"),
                        marker=dict(size=6),
                        hovertemplate="<b>%{x}</b><br>Proposals Won: %{y}<extra></extra>",
                    ),
                    secondary_y=True,
                )
                # Trade show annotations — use add_shape instead of add_vline
                # because add_vline doesn't support string/categorical x-axes in all Plotly versions.
                weeks_list = wbr_f["week"].tolist()
                for ts_week in ("W6", "W10"):
                    if ts_week in weeks_list:
                        ts_idx = weeks_list.index(ts_week)
                        fig_a.add_shape(
                            type="line",
                            xref="x", yref="paper",
                            x0=ts_idx, x1=ts_idx,
                            y0=0, y1=1,
                            line=dict(color="rgba(30,58,95,0.4)", width=1.5, dash="dash"),
                        )
                        fig_a.add_annotation(
                            x=ts_idx, xref="x",
                            y=1, yref="paper",
                            text="📍 Trade Show",
                            showarrow=False,
                            yanchor="bottom",
                            font=dict(size=11, color="rgba(30,58,95,0.7)"),
                        )
                fig_a.update_layout(
                    title="Commercial Momentum",
                    template="plotly_white",
                    height=360,
                    hovermode="x unified",
                    margin=dict(l=10, r=10, t=55, b=30),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                fig_a.update_yaxes(title_text="Revenue (€)", tickprefix="€", secondary_y=False)
                fig_a.update_yaxes(title_text="Proposals", secondary_y=True)
                st.plotly_chart(fig_a, use_container_width=True)

            # ── Chart B: Delivery & Customer Health ───────────────────────
            with chart_right:
                fig_b = make_subplots(specs=[[{"secondary_y": True}]])

                fig_b.add_trace(
                    go.Bar(
                        x=wbr_f["week"].tolist(),
                        y=wbr_f["installations_completed"].tolist(),
                        name="Installations",
                        marker_color="rgba(30,58,95,0.75)",
                        hovertemplate="<b>%{x}</b><br>Installations: %{y}<extra></extra>",
                    ),
                    secondary_y=False,
                )
                fig_b.add_trace(
                    go.Scatter(
                        x=wbr_f["week"].tolist(),
                        y=wbr_f["support_tickets_open"].tolist(),
                        name="Open Tickets",
                        mode="lines+markers",
                        line=dict(color="#E74C3C", width=2.5),
                        marker=dict(size=6),
                        hovertemplate="<b>%{x}</b><br>Open Tickets: %{y}<extra></extra>",
                    ),
                    secondary_y=False,
                )
                fig_b.add_trace(
                    go.Scatter(
                        x=wbr_f["week"].tolist(),
                        y=wbr_f["csat_score"].tolist(),
                        name="CSAT",
                        mode="lines+markers",
                        line=dict(color="#00B4D8", width=2.5),
                        marker=dict(size=6),
                        hovertemplate="<b>%{x}</b><br>CSAT: %{y:.2f}<extra></extra>",
                    ),
                    secondary_y=True,
                )
                # CSAT minimum target line — drawn as a flat scatter trace on the secondary axis.
                # add_hline with secondary_y=True is broken in some Plotly versions, so we
                # use a constant-value line trace instead, which works reliably.
                fig_b.add_trace(
                    go.Scatter(
                        x=wbr_f["week"].tolist(),
                        y=[4.0] * len(wbr_f),
                        name="CSAT target (4.0)",
                        mode="lines",
                        line=dict(color="rgba(0,180,216,0.45)", width=1.5, dash="dot"),
                        showlegend=True,
                        hoverinfo="skip",
                    ),
                    secondary_y=True,
                )
                fig_b.update_layout(
                    title="Delivery & Customer Health",
                    template="plotly_white",
                    height=360,
                    hovermode="x unified",
                    margin=dict(l=10, r=10, t=55, b=30),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                fig_b.update_yaxes(title_text="Count", secondary_y=False)
                fig_b.update_yaxes(title_text="CSAT (0–5)", range=[3.0, 5.0], secondary_y=True)
                st.plotly_chart(fig_b, use_container_width=True)

    # ------------------------------------------------------------------
    # Row 3 — Dynamic executive alerts / key takeaways
    # ------------------------------------------------------------------
    st.markdown("### 📋 Key Business Signals")

    alerts: list[tuple[str, str, str]] = []  # (icon, message, color)

    if wbr_f is not None:
        # Supplier risk
        if kpi_high_risk_suppliers > 0:
            alerts.append((
                "🔴",
                f"**Supply chain risk elevated** — {kpi_high_risk_suppliers} supplier(s) rated HIGH risk. "
                "Review Shenzhen Optocore quality issues before next order.",
                "#E74C3C",
            ))

        # Ticket backlog: latest open > latest closed in range
        if "support_tickets_open" in wbr_f.columns and len(wbr_f) > 0:
            _latest_open   = float(wbr_f["support_tickets_open"].iloc[-1])
            _latest_closed = float(wbr_f["support_tickets_closed"].iloc[-1]) if "support_tickets_closed" in wbr_f.columns else 0.0
            if _latest_open > _latest_closed:
                alerts.append((
                    "🟡",
                    f"**Support ticket backlog growing** — {int(_latest_open)} open vs "
                    f"{int(_latest_closed)} closed in the latest week. Assign to Support Lead.",
                    "#E67E22",
                ))

        # CSAT below 4.0
        if kpi_csat is not None and kpi_csat < 4.0:
            alerts.append((
                "🔴",
                f"**CSAT below target** — average {kpi_csat:.2f}/5 in selected range "
                "(target: 4.0). Review latest support interactions.",
                "#E74C3C",
            ))
        elif kpi_csat is not None and kpi_csat >= 4.3:
            alerts.append((
                "🟢",
                f"**Customer satisfaction strong** — CSAT averaging {kpi_csat:.2f}/5 across the period.",
                "#2ECC71",
            ))

        # Proposal volume check: win rate
        if kpi_win_rate is not None and kpi_win_rate < 40:
            alerts.append((
                "🟡",
                f"**Win rate low** — only {kpi_win_rate:.0f}% of proposals converting. "
                "Consider reviewing proposal quality or targeting.",
                "#E67E22",
            ))
        elif kpi_win_rate is not None and kpi_win_rate >= 55:
            alerts.append((
                "🟢",
                f"**Strong conversion rate** — {kpi_win_rate:.0f}% win rate in selected period.",
                "#2ECC71",
            ))

    if not wbr_f is not None or not alerts:
        alerts.append(("ℹ️", "No significant signals detected in the selected range.", "#888888"))

    # Render alerts as styled cards in a single column layout
    for icon, message, color in alerts:
        st.markdown(
            f"""
<div style="
  border-left: 4px solid {color};
  background: white;
  border-radius: 8px;
  padding: 10px 16px;
  margin-bottom: 8px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.05);
  font-size: 0.92rem;
  color: #1E3A5F;
">
  {icon}&nbsp;&nbsp;{message}
</div>
""",
            unsafe_allow_html=True,
        )
elif tab == "Commercial Automation":
    # ──────────────────────────────────────────────────────────────────────────
    # COMMERCIAL AUTOMATION — Tender to Proposal
    # Shows the end-to-end AI-assisted workflow for a single commercial
    # opportunity: from tender qualification (Demo 1) to proposal generation
    # (Demo 2). All metrics on this page are case-level, not YTD aggregates.
    # ──────────────────────────────────────────────────────────────────────────

    st.markdown("## Commercial Automation")
    st.markdown(
        '<div style="color:rgba(0,0,0,0.45); margin-top:-0.25rem; margin-bottom:1rem; font-size:0.95rem;">'
        "From tender qualification to proposal generation — one opportunity, end-to-end"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Load outputs from Demo 1 (tender) and Demo 2 (proposal) ───────────────
    tender_path   = Path(__file__).parent / "demo1_tender/output/tender_analysis_TENDER-2026-OPH-0187.md"
    proposal_path = Path(__file__).parent / "demo2_proposal/output/proposal_Clinica_Oculistica_Milano.md"
    tender_text   = tender_path.read_text(encoding="utf-8")   if tender_path.exists()   else ""
    proposal_text = proposal_path.read_text(encoding="utf-8") if proposal_path.exists() else ""

    # ── Derive case-level facts from the tender output ────────────────────────
    # Tender ID comes from the filename and is confirmed in the report header.
    TENDER_ID = "TENDER-2026-OPH-0187"

    # Buyer: extracted from the tender analysis report (line starting with "Buyer").
    import re as _re
    _buyer_m = _re.search(r"\*\*Buyer\*\*[:\s]+(.+)", tender_text)
    TENDER_BUYER = _buyer_m.group(1).strip() if _buyer_m else "Ospedale Policlinico di Milano"

    # Budget: the tender states an estimated budget per lot; we use the text as-is.
    _budget_m = _re.search(r"\*\*Budget[^*]*\*\*[:\s]+(.+)", tender_text)
    TENDER_BUDGET_TEXT = _budget_m.group(1).strip() if _budget_m else "See tender conditions"

    # Verdict: look for "GO_WITH_RISKS", "NO_GO", or "GO" in the report.
    if "GO_WITH_RISKS" in tender_text:
        VERDICT = "GO_WITH_RISKS"
        VERDICT_COLOR = "#FFC300"
    elif "NO_GO" in tender_text:
        VERDICT = "NO_GO"
        VERDICT_COLOR = "#E74C3C"
    elif tender_text:
        VERDICT = "GO"
        VERDICT_COLOR = "#2ECC71"
    else:
        VERDICT = "—"
        VERDICT_COLOR = "#888888"

    # Count RISK items in the tender report (lines containing "RISK:").
    RISK_COUNT = len(_re.findall(r"RISK:", tender_text, _re.IGNORECASE))

    # ── Proposal toggle (core vs. full bundle) — case-level pricing ───────────
    # Source: Demo 2 proposal generator output.
    # Core bundle (RetinaScan + OCT, 2 products) → 5% discount applied.
    # Full bundle (+ 2× AutoRef, 3+ products) → 8% discount applied.
    # List prices from company_context.md: RetinaScan €38k, OCT €62k, AutoRef €12k each.
    st.radio(
        "Proposal scope",
        ["Core bundle (RetinaScan + OCT)", "Full bundle (+ 2× AutoRef)"],
        horizontal=True,
        key="proposal_toggle",
    )
    toggle = st.session_state.get("proposal_toggle", "Core bundle (RetinaScan + OCT)")

    if toggle == "Full bundle (+ 2× AutoRef)":
        # List prices: 38k + 62k + 2×12k = 124k → 8% bundle discount
        LIST_PRICE      = 124_000.0
        DISCOUNT_RATE   = 0.08
        PROPOSAL_VALUE  = LIST_PRICE * (1 - DISCOUNT_RATE)   # = 114,080 → rounded to 114k
        DISCOUNT_AMOUNT = LIST_PRICE - PROPOSAL_VALUE
        SCOPE_LABEL     = "RetinaScan Pro + OCT-3000 + 2× AutoRef 500"
        PRODUCTS_N      = 3
    else:
        # List prices: 38k + 62k = 100k → 5% bundle discount
        LIST_PRICE      = 100_000.0
        DISCOUNT_RATE   = 0.05
        PROPOSAL_VALUE  = LIST_PRICE * (1 - DISCOUNT_RATE)   # = 95,000
        DISCOUNT_AMOUNT = LIST_PRICE - DISCOUNT_RATE * LIST_PRICE - PROPOSAL_VALUE + DISCOUNT_RATE * LIST_PRICE
        # Simpler:
        DISCOUNT_AMOUNT = LIST_PRICE * DISCOUNT_RATE          # = 5,000
        SCOPE_LABEL     = "RetinaScan Pro + OCT-3000"
        PRODUCTS_N      = 2

    # Client budget ceiling: stated in call notes (Dr. Rossi said "around €150k").
    # Note: the proposal (Demo 2) is for Dr. Rossi's private clinic; the tender (Demo 1)
    # is a separate public procurement. They are shown together as two commercial automation
    # demos. The budget comparison uses the Dr. Rossi figure (€150k) for the proposal gauge.
    CLIENT_BUDGET_CEILING = 150_000.0
    BUDGET_HEADROOM       = CLIENT_BUDGET_CEILING - PROPOSAL_VALUE

    # ── Row 1 — 6 opportunity summary KPI cards ───────────────────────────────
    def _opp_card(label: str, value: str, subtitle: str,
                  border: str = "#00B4D8", val_color: str = "#1E3A5F") -> None:
        st.markdown(
            f"""<div style="border:1px solid rgba(0,0,0,0.07);border-top:4px solid {border};
border-radius:12px;padding:16px 18px 14px;background:white;
box-shadow:0 2px 12px rgba(0,0,0,0.06);height:100%;">
  <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.08em;
              text-transform:uppercase;color:rgba(0,0,0,0.4);margin-bottom:6px;">{label}</div>
  <div style="font-size:1.45rem;font-weight:800;color:{val_color};line-height:1.1;">{value}</div>
  <div style="font-size:0.78rem;color:rgba(0,0,0,0.42);margin-top:5px;">{subtitle}</div>
</div>""",
            unsafe_allow_html=True,
        )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        _opp_card("Tender ID", TENDER_ID[-11:], "Public procurement ref.", border="#1E3A5F")
    with c2:
        _opp_card("Buyer / Client", TENDER_BUYER[:22] + ("…" if len(TENDER_BUYER) > 22 else ""),
                  "Issuing institution", border="#1E3A5F")
    with c3:
        _opp_card("Budget Range", TENDER_BUDGET_TEXT[:24], "From tender conditions", border="#00B4D8")
    with c4:
        _opp_card("Go / No-Go", VERDICT, f"{RISK_COUNT} risk items identified",
                  border=VERDICT_COLOR, val_color=VERDICT_COLOR)
    with c5:
        _opp_card("Proposal Value",
                  f"€{PROPOSAL_VALUE:,.0f}",
                  f"{SCOPE_LABEL} · {int(DISCOUNT_RATE*100)}% discount",
                  border="#00B4D8")
    with c6:
        headroom_color = "#2ECC71" if BUDGET_HEADROOM >= 0 else "#E74C3C"
        headroom_label = f"€{abs(BUDGET_HEADROOM):,.0f} {'below' if BUDGET_HEADROOM >= 0 else 'above'} ceiling"
        _opp_card("Budget Headroom",
                  headroom_label,
                  f"vs. Dr. Rossi ceiling €{CLIENT_BUDGET_CEILING:,.0f}",
                  border=headroom_color, val_color=headroom_color)

    st.markdown("<div style='margin-top:1.25rem;'></div>", unsafe_allow_html=True)

    # ── Row 2 — Workflow stepper + Risk panel ─────────────────────────────────
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown("### Workflow Progress")
        st.markdown(
            '<div style="font-size:0.82rem;color:rgba(0,0,0,0.45);margin-top:-0.4rem;margin-bottom:0.9rem;">'
            "AI-assisted steps — status inferred from available output files"
            "</div>",
            unsafe_allow_html=True,
        )

        # Infer step completion from actual file contents
        has_tender   = bool(tender_text)
        has_verdict  = VERDICT != "—"
        has_risks    = RISK_COUNT > 0
        has_rec      = VERDICT in ("GO", "GO_WITH_RISKS", "NO_GO")
        has_proposal = bool(proposal_text)
        # Submission ready: bid is recommended AND no blocking NO_GO AND proposal exists
        is_submission_ready = has_proposal and VERDICT != "NO_GO" and RISK_COUNT == 0

        steps = [
            ("Tender received",        has_tender,           "Demo 1 input file loaded"),
            ("Eligibility checked",    has_verdict,          f"Verdict: {VERDICT}"),
            ("Risks identified",       has_risks,            f"{RISK_COUNT} risk item(s) flagged"),
            ("Bid recommendation",     has_rec,              "Go/No-Go decision made"),
            ("Proposal generated",     has_proposal,         "Demo 2 output file exists"),
            ("Submission ready",       is_submission_ready,  "No blockers → ready" if is_submission_ready else "Pending: resolve open risks"),
        ]

        # Render as a vertical stepper using HTML
        stepper_html = '<div style="position:relative;padding-left:12px;">'
        for i, (label, done, detail) in enumerate(steps):
            is_last = (i == len(steps) - 1)
            if done:
                dot_bg, dot_border, dot_char = "#2ECC71", "#2ECC71", "✓"
                label_color, detail_color = "#1E3A5F", "rgba(0,0,0,0.5)"
            elif not done and i > 0 and steps[i-1][1]:
                # Previous step done but this one isn't → in progress / blocked
                dot_bg, dot_border, dot_char = "#FFC300", "#FFC300", "…"
                label_color, detail_color = "#1E3A5F", "rgba(0,0,0,0.5)"
            else:
                dot_bg, dot_border, dot_char = "white", "#CBD5E0", "○"
                label_color, detail_color = "rgba(0,0,0,0.35)", "rgba(0,0,0,0.3)"

            connector = (
                "" if is_last else
                '<div style="position:absolute;left:19px;top:0;width:2px;height:100%;'
                'background:rgba(0,0,0,0.1);z-index:0;"></div>'
            )
            stepper_html += f"""
<div style="display:flex;align-items:flex-start;gap:14px;margin-bottom:18px;position:relative;">
  <div style="flex-shrink:0;width:28px;height:28px;border-radius:50%;
              background:{dot_bg};border:2px solid {dot_border};
              display:flex;align-items:center;justify-content:center;
              font-size:0.85rem;font-weight:700;color:white;z-index:1;">
    {dot_char}
  </div>
  <div style="padding-top:3px;">
    <div style="font-weight:700;color:{label_color};font-size:0.95rem;">{label}</div>
    <div style="font-size:0.8rem;color:{detail_color};margin-top:2px;">{detail}</div>
  </div>
</div>"""
        stepper_html += "</div>"
        st.markdown(stepper_html, unsafe_allow_html=True)

    with right_col:
        st.markdown("### Key Risks & Blockers")
        st.markdown(
            '<div style="font-size:0.82rem;color:rgba(0,0,0,0.45);margin-top:-0.4rem;margin-bottom:0.9rem;">'
            "Extracted from tender analysis — must be addressed before submission"
            "</div>",
            unsafe_allow_html=True,
        )

        # Extract up to 5 RISK lines from the tender report
        _risk_lines = _re.findall(r"RISK:\s*(.+?)(?=\n|$)", tender_text)[:5]

        # Classify each risk (heuristic: CE/certification → blocking; references/SLA → caution)
        def _classify_risk(text: str) -> tuple[str, str, str]:
            tl = text.lower()
            if any(k in tl for k in ["ce mark", "certification", "class ii", "eligible", "revenue"]):
                return "🔴", "Blocking", "#E74C3C"
            elif any(k in tl for k in ["reference", "hospital", "48h", "maintenance", "sla"]):
                return "🟡", "Caution", "#E67E22"
            else:
                return "ℹ️", "Info", "#888888"

        if _risk_lines:
            for rline in _risk_lines:
                icon, badge, color = _classify_risk(rline)
                st.markdown(
                    f"""<div style="border-left:4px solid {color};background:white;
border-radius:8px;padding:10px 14px;margin-bottom:8px;
box-shadow:0 1px 6px rgba(0,0,0,0.05);">
  <div style="font-size:0.72rem;font-weight:700;color:{color};letter-spacing:0.06em;
              text-transform:uppercase;margin-bottom:3px;">{icon} {badge}</div>
  <div style="font-size:0.85rem;color:#1E3A5F;line-height:1.45;">{rline[:120]}</div>
</div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Run demo 1 to extract risk items from the tender analysis.")

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

    # ── Row 3 — Gauge + Radar ─────────────────────────────────────────────────
    try:
        import plotly.graph_objects as go
    except Exception:
        st.warning("Plotly is required. Install with `pip install plotly`.")
    else:
        gauge_col, radar_col = st.columns(2)

        # ── Gauge: Proposal pricing fit against client budget ─────────────────
        with gauge_col:
            st.markdown("### Pricing Fit vs. Client Budget")
            st.markdown(
                '<div style="font-size:0.82rem;color:rgba(0,0,0,0.45);margin-top:-0.4rem;margin-bottom:0.6rem;">'
                f"Single-opportunity view · {SCOPE_LABEL}"
                "</div>",
                unsafe_allow_html=True,
            )
            gauge_max = CLIENT_BUDGET_CEILING * 1.25

            # Delta label: "below budget ceiling" = positive headroom (good)
            # "above budget ceiling" = negative (bad)
            gauge_fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=PROPOSAL_VALUE,
                number={"prefix": "€", "valueformat": ",.0f"},
                delta={
                    "reference": CLIENT_BUDGET_CEILING,
                    "relative": False,
                    "valueformat": ",.0f",
                    "prefix": "€",
                    "suffix": " vs. budget ceiling",
                    # negative delta = below ceiling = GOOD (inverse)
                    "increasing": {"color": "#E74C3C"},
                    "decreasing": {"color": "#2ECC71"},
                },
                title={"text": f"Proposal: €{PROPOSAL_VALUE:,.0f}<br>"
                               f"<span style='font-size:0.8em;color:gray'>"
                               f"List: €{LIST_PRICE:,.0f} · {int(DISCOUNT_RATE*100)}% bundle discount = "
                               f"€{DISCOUNT_AMOUNT:,.0f} off list</span>"},
                gauge={
                    "axis": {"range": [0, gauge_max]},
                    "bar": {"color": "#1E3A5F"},
                    "steps": [
                        {"range": [0, CLIENT_BUDGET_CEILING * 0.80], "color": "rgba(46,204,113,0.2)"},
                        {"range": [CLIENT_BUDGET_CEILING * 0.80, CLIENT_BUDGET_CEILING], "color": "rgba(255,195,0,0.2)"},
                        {"range": [CLIENT_BUDGET_CEILING, gauge_max], "color": "rgba(231,76,60,0.18)"},
                    ],
                    "threshold": {
                        "line": {"color": "#E74C3C", "width": 3},
                        "value": CLIENT_BUDGET_CEILING,
                    },
                },
            ))
            gauge_fig.update_layout(
                template="plotly_white",
                height=380,
                margin=dict(l=20, r=20, t=90, b=20),
            )
            gauge_fig.add_annotation(
                x=0.5, y=0.0, xref="paper", yref="paper", showarrow=False,
                text=f"Budget headroom: €{BUDGET_HEADROOM:,.0f} below client ceiling",
                font=dict(color="rgba(0,0,0,0.55)", size=12),
            )
            st.plotly_chart(gauge_fig, use_container_width=True)

        # ── Radar: Tender criteria weight vs. BrightEyes estimated fit ────────
        with radar_col:
            st.markdown("### Tender Criteria Fit")
            st.markdown(
                '<div style="font-size:0.82rem;color:rgba(0,0,0,0.45);margin-top:-0.4rem;margin-bottom:0.6rem;">'
                "Tender weight (what the buyer scores) vs. BrightEyes estimated capability<br>"
                "<em>Strength values are internal estimates — not guaranteed scores</em>"
                "</div>",
                unsafe_allow_html=True,
            )

            # Criteria and weights sourced directly from the tender document (Demo 1 input).
            # Section 4 of tender_hospital_milan.md: Technical 50%, Price 30%, Delivery 10%, After-Sales 10%.
            # BrightEyes estimated strength (heuristic, normalized to same 0–50 scale):
            #   Technical: 40/50 — strong specs, minor integration gap (Dedalus ORBIS)
            #   Price:     26/30 — proposal is within budget, some room
            #   Delivery:   8/10 — 12-week timeline is tight but feasible
            #   After-Sales: 6/10 — 48h SLA not formally evidenced yet
            categories = ["Technical (50%)", "Price (30%)", "Delivery (10%)", "After-Sales (10%)"]
            tender_weight_vals = [50, 30, 10, 10]
            estimated_strength = [40, 26, 8, 6]

            radar_fig = go.Figure()
            radar_fig.add_trace(go.Scatterpolar(
                r=tender_weight_vals + [tender_weight_vals[0]],
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor="rgba(0,180,216,0.25)",
                line=dict(color="#00B4D8", width=2.5),
                name="Tender weight (buyer scoring)",
            ))
            radar_fig.add_trace(go.Scatterpolar(
                r=estimated_strength + [estimated_strength[0]],
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor="rgba(30,58,95,0.25)",
                line=dict(color="#1E3A5F", width=2.5),
                name="BrightEyes estimated fit (internal)",
            ))
            radar_fig.update_layout(
                template="plotly_white",
                height=380,
                margin=dict(l=30, r=30, t=30, b=30),
                polar=dict(radialaxis=dict(visible=True, range=[0, 55])),
                legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5),
            )
            st.plotly_chart(radar_fig, use_container_width=True)

    # ── Row 4 — Generated output previews ────────────────────────────────────
    st.markdown("### Generated Outputs")
    st.markdown(
        '<div style="font-size:0.82rem;color:rgba(0,0,0,0.45);margin-bottom:0.75rem;">'
        "Full AI-generated reports from Demo 1 (tender analysis) and Demo 2 (proposal)"
        "</div>",
        unsafe_allow_html=True,
    )

    out_tab1, out_tab2 = st.tabs(["📄 Tender Analysis (Demo 1)", "📝 Client Proposal (Demo 2)"])

    with out_tab1:
        if tender_text:
            st.markdown(tender_text)
        else:
            st.warning("Run `python3 demo1_tender/tender_parser.py` to generate this report.")

    with out_tab2:
        if proposal_text:
            st.markdown(proposal_text)
        else:
            st.warning("Run `python3 demo2_proposal/proposal_generator.py` to generate this report.")

elif tab == "Installation Intelligence":
    st.markdown("## Installation Intelligence")

    install_path = Path(__file__).parent / "demo4_installation/output/installation_data_verdi.json"
    if not install_path.exists():
        st.warning(
            "Run demo 4 first to see this output "
            "(missing: `demo4_installation/output/installation_data_verdi.json`)"
        )
        installation = None
    else:
        try:
            installation = json.loads(install_path.read_text(encoding="utf-8"))
        except Exception as e:
            st.warning(f"Could not read installation JSON: {e}")
            installation = None

    devices_list = []
    issues_list = []
    satisfaction_score: Optional[float] = None

    if isinstance(installation, dict):
        devices_list = installation.get("devices") if isinstance(installation.get("devices"), list) else []
        issues_list = installation.get("issues") if isinstance(installation.get("issues"), list) else []
        raw_score = installation.get("satisfaction_score")
        try:
            satisfaction_score = float(raw_score) if raw_score is not None else None
        except Exception:
            satisfaction_score = None

    total_devices = len(devices_list)
    total_issues = len(issues_list)
    resolved_on_site = sum(
        1
        for i in issues_list
        if isinstance(i, dict) and i.get("was_fixed_on_site") is True
    )

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Devices Installed", total_devices)
    with m2:
        st.metric("Issues Resolved On-Site", f"{resolved_on_site} / {total_issues}")
    with m3:
        if satisfaction_score is None:
            st.metric("Client Satisfaction", "—", delta="—")
        else:
            delta = satisfaction_score - 5.0
            st.metric("Client Satisfaction", f"{satisfaction_score:.1f} / 5.0", delta=f"{delta:+.1f} vs 5.0")

    left, right = st.columns(2)

    # --- Left: Issue Breakdown donut (two rings) ---
    with left:
        if not issues_list:
            st.warning("No issues found in the installation JSON (or file missing).")
        else:
            try:
                import plotly.graph_objects as go
            except Exception:
                st.warning("Plotly is required for the issue breakdown chart. Install it with `pip install plotly`.")
            else:
                categories = ["Mechanical", "Software", "Quality Control", "Process"]
                inner_colors = {
                    "Mechanical": "#00B4D8",
                    "Software": "#1E3A5F",
                    "Quality Control": "#FFC300",
                    "Process": "#2ECC71",
                }

                # Inner ring: count by category
                cat_counts = {c: 0 for c in categories}
                cat_resolved = {c: 0 for c in categories}
                cat_escalated = {c: 0 for c in categories}

                for issue in issues_list:
                    if not isinstance(issue, dict):
                        continue
                    cat = issue.get("category")
                    if cat not in cat_counts:
                        continue
                    cat_counts[cat] += 1
                    if issue.get("was_fixed_on_site") is True:
                        cat_resolved[cat] += 1
                    else:
                        cat_escalated[cat] += 1

                inner_labels = categories
                inner_values = [cat_counts[c] for c in categories]
                inner_marker_colors = [inner_colors[c] for c in categories]

                # Outer ring: for each category, split resolved/escalated
                outer_labels = []
                outer_values = []
                outer_colors = []
                for c in categories:
                    if cat_counts[c] == 0:
                        continue
                    outer_labels.extend([f"{c} — Resolved on-site", f"{c} — Escalated"])
                    outer_values.extend([cat_resolved[c], cat_escalated[c]])
                    outer_colors.extend(["#2ECC71", "#F39C12"])

                fig = go.Figure()
                fig.add_trace(
                    go.Pie(
                        labels=inner_labels,
                        values=inner_values,
                        hole=0.70,
                        sort=False,
                        direction="clockwise",
                        marker=dict(colors=inner_marker_colors),
                        textinfo="label+value",
                        showlegend=True,
                        domain={"x": [0, 1], "y": [0, 1]},
                    )
                )
                fig.add_trace(
                    go.Pie(
                        labels=outer_labels,
                        values=outer_values,
                        hole=0.40,
                        sort=False,
                        direction="clockwise",
                        marker=dict(colors=outer_colors),
                        textinfo="none",
                        showlegend=False,
                        domain={"x": [0, 1], "y": [0, 1]},
                    )
                )
                fig.update_layout(
                    title="Issue Breakdown",
                    template="plotly_white",
                    height=420,
                    margin=dict(l=20, r=20, t=60, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

    # --- Right: severity bar + devices table ---
    with right:
        if not issues_list:
            st.warning("No issues found in the installation JSON (or file missing).")
        else:
            try:
                import plotly.graph_objects as go
            except Exception:
                st.warning("Plotly is required for the severity chart. Install it with `pip install plotly`.")
            else:
                sev_order = ["LOW", "MEDIUM", "HIGH"]
                sev_colors = {"LOW": "#2ECC71", "MEDIUM": "#FFC300", "HIGH": "#E74C3C"}
                sev_counts = {s: 0 for s in sev_order}

                for issue in issues_list:
                    if not isinstance(issue, dict):
                        continue
                    sev = str(issue.get("severity") or "").upper()
                    if sev in sev_counts:
                        sev_counts[sev] += 1

                bar = go.Figure(
                    go.Bar(
                        x=sev_order,
                        y=[sev_counts[s] for s in sev_order],
                        marker_color=[sev_colors[s] for s in sev_order],
                    )
                )
                bar.update_layout(
                    title="Issues by Severity",
                    template="plotly_white",
                    height=320,
                    margin=dict(l=20, r=20, t=60, b=20),
                )
                st.plotly_chart(bar, use_container_width=True)

        # Devices table
        if devices_list:
            device_rows = []
            for d in devices_list:
                if not isinstance(d, dict):
                    continue
                device_rows.append(
                    {
                        "Device": d.get("product_name") or d.get("device_name") or "—",
                        "Serial Number": d.get("serial_number") or "—",
                        "Status": d.get("status") or "—",
                    }
                )
            devices_df = pd.DataFrame(device_rows)
            st.dataframe(devices_df, use_container_width=True)
        else:
            st.warning("No devices found in the installation JSON (or file missing).")

    st.selectbox(
        "Filter issues by category",
        ["All", "Mechanical", "Software", "Quality Control", "Process"],
        key="issue_filter",
    )

    # Filtered issues table
    selected_category = st.session_state.get("issue_filter", "All")
    if issues_list:
        issue_rows = []
        for i in issues_list:
            if not isinstance(i, dict):
                continue
            cat = i.get("category")
            if selected_category != "All" and cat != selected_category:
                continue
            issue_rows.append(
                {
                    "Title": i.get("title") or "—",
                    "Category": cat or "—",
                    "Severity": i.get("severity") or "—",
                    "Assigned Team": i.get("routed_team") or "—",
                    "Fixed On-Site": bool(i.get("was_fixed_on_site") is True),
                }
            )
        issues_df = pd.DataFrame(issue_rows)
        st.dataframe(issues_df, use_container_width=True)
    else:
        st.warning("No issues found in the installation JSON (or file missing).")

    # Weekly Ops Rhythm line chart from WBR CSV (all 12 weeks)
    wbr_path = Path(__file__).parent / "demo5_wbr/data/weekly_metrics.csv"
    if not wbr_path.exists():
        st.warning("Run demo 5 first to see this output (missing: `demo5_wbr/data/weekly_metrics.csv`)")
    else:
        try:
            ops_wbr = pd.read_csv(wbr_path)
        except Exception as e:
            st.warning(f"Could not read `demo5_wbr/data/weekly_metrics.csv` as CSV: {e}")
            ops_wbr = None

        if ops_wbr is not None:
            if "week" not in ops_wbr.columns:
                st.warning("Weekly metrics file is missing a `week` column.")
            else:
                ops_wbr = ops_wbr.copy()
                ops_wbr["week_num"] = (
                    ops_wbr["week"].astype(str).str.replace("W", "", regex=False).astype("Int64")
                )

                for col in ["installations_completed", "support_tickets_open", "support_tickets_closed"]:
                    if col in ops_wbr.columns:
                        ops_wbr[col] = pd.to_numeric(ops_wbr[col], errors="coerce")

                try:
                    import plotly.graph_objects as go
                except Exception:
                    st.warning("Plotly is required for the weekly ops chart. Install it with `pip install plotly`.")
                else:
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=ops_wbr["week_num"],
                            y=ops_wbr["installations_completed"] if "installations_completed" in ops_wbr.columns else [],
                            mode="lines+markers",
                            name="Installations Completed",
                            line=dict(color="#2ECC71", width=3),
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=ops_wbr["week_num"],
                            y=ops_wbr["support_tickets_open"] if "support_tickets_open" in ops_wbr.columns else [],
                            mode="lines+markers",
                            name="Support Tickets Open",
                            line=dict(color="#E74C3C", width=3),
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=ops_wbr["week_num"],
                            y=ops_wbr["support_tickets_closed"] if "support_tickets_closed" in ops_wbr.columns else [],
                            mode="lines+markers",
                            name="Support Tickets Closed",
                            line=dict(color="#00B4D8", width=3),
                        )
                    )

                    fig.update_layout(
                        title="Weekly Ops Rhythm",
                        template="plotly_white",
                        height=420,
                        margin=dict(l=20, r=20, t=60, b=30),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    fig.update_xaxes(title_text="Week", tickmode="linear", dtick=1)

                    # Note annotation at W11
                    fig.add_annotation(
                        x=11,
                        y=1,
                        xref="x",
                        yref="paper",
                        text="⚠️ Ticket backlog forming",
                        showarrow=False,
                        yanchor="bottom",
                        font=dict(color="rgba(0,0,0,0.65)"),
                    )

                    st.plotly_chart(fig, use_container_width=True)
elif tab == "Supplier Intelligence":
    st.markdown("## Supply Chain — Supplier Risk & Spend")

    def _eur(x: float) -> str:
        return f"€{x:,.0f}"

    purchase_path = Path(__file__).parent / "demo3_supplier/data/purchase_history.csv"
    if not purchase_path.exists():
        st.warning(
            "Run demo 3 first to see this output (missing: `demo3_supplier/data/purchase_history.csv`)"
        )
        purchase = None
    else:
        try:
            purchase = pd.read_csv(purchase_path)
        except Exception as e:
            st.warning(f"Could not read `demo3_supplier/data/purchase_history.csv` as CSV: {e}")
            purchase = None

    if purchase is not None:
        required_cols = {
            "date",
            "supplier",
            "total_eur",
            "quality_rating",
            "delivery_days",
            "notes",
            "unit_price_eur",
        }
        missing = required_cols - set(purchase.columns)
        if missing:
            st.warning(f"Unexpected purchase history format (missing columns: {sorted(missing)})")
        else:
            df = purchase.copy()
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["total_eur"] = pd.to_numeric(df["total_eur"], errors="coerce")
            df["quality_rating"] = pd.to_numeric(df["quality_rating"], errors="coerce")
            df["delivery_days"] = pd.to_numeric(df["delivery_days"], errors="coerce")
            df["unit_price_eur"] = pd.to_numeric(df["unit_price_eur"], errors="coerce")
            df["notes"] = df["notes"].fillna("").astype(str)

            issue_mask = df["notes"].str.contains(r"(defective|late|scratch)", case=False, regex=True)
            df["issue_flag"] = issue_mask

            def _price_trend(g: pd.DataFrame) -> float:
                gg = g.sort_values("date")
                first = gg["unit_price_eur"].dropna()
                if first.empty:
                    return float("nan")
                return float(first.iloc[-1] - first.iloc[0])

            agg = (
                df.groupby("supplier", dropna=False)
                .agg(
                    total_spend=("total_eur", "sum"),
                    avg_quality=("quality_rating", "mean"),
                    avg_delivery_days=("delivery_days", "mean"),
                    issue_count=("issue_flag", "sum"),
                )
                .reset_index()
            )

            trends = df.groupby("supplier", dropna=False).apply(_price_trend).reset_index(name="price_trend")
            agg = agg.merge(trends, on="supplier", how="left")

            def _risk(row: pd.Series) -> str:
                avg_q = float(row["avg_quality"]) if pd.notna(row["avg_quality"]) else 0.0
                issues = int(row["issue_count"]) if pd.notna(row["issue_count"]) else 0
                if avg_q < 3.5:
                    return "HIGH"
                if avg_q < 4.0 or issues > 2:
                    return "MEDIUM"
                return "LOW"

            agg["risk"] = agg.apply(_risk, axis=1)

            # Sidebar filter (rendered only when Supply Chain is active)
            supplier_options = sorted(agg["supplier"].astype(str).unique().tolist())
            selected_suppliers = st.sidebar.multiselect(
                "Filter suppliers",
                options=supplier_options,
                default=supplier_options,
                key="supplier_filter",
            )

            agg_f = agg[agg["supplier"].astype(str).isin(selected_suppliers)].copy()
            df_f = df[df["supplier"].astype(str).isin(selected_suppliers)].copy()

            total_spend = float(agg_f["total_spend"].fillna(0).sum())
            high_risk_count = int((agg_f["risk"] == "HIGH").sum())
            savings_target = total_spend * 0.05

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Total Spend", _eur(total_spend))
            with m2:
                st.metric("HIGH-risk suppliers", high_risk_count)
            with m3:
                st.metric("Savings Target at 5%", _eur(savings_target))

            # --- Supplier Risk Matrix (scatter) ---
            try:
                import plotly.express as px
            except Exception:
                st.warning("Plotly is required for Supply Chain charts. Install it with `pip install plotly`.")
            else:
                risk_color = {"LOW": "#2ECC71", "MEDIUM": "#FFC300", "HIGH": "#E74C3C"}
                plot_df = agg_f.copy()
                plot_df["risk_color"] = plot_df["risk"].map(risk_color).fillna("#999999")

                # bubble sizing: scale total_spend into 20–80 px range
                spend_min = float(plot_df["total_spend"].min()) if not plot_df.empty else 0.0
                spend_max = float(plot_df["total_spend"].max()) if not plot_df.empty else 0.0

                def _bubble_size(v: float) -> float:
                    if spend_max <= spend_min:
                        return 50.0
                    return 20.0 + (float(v) - spend_min) * (60.0 / (spend_max - spend_min))

                plot_df["bubble_size"] = plot_df["total_spend"].apply(lambda v: _bubble_size(float(v or 0.0)))

                fig = px.scatter(
                    plot_df,
                    x="avg_delivery_days",
                    y="avg_quality",
                    size="bubble_size",
                    color="risk",
                    color_discrete_map=risk_color,
                    text="supplier",
                    hover_data={
                        "total_spend": ":,.0f",
                        "avg_delivery_days": ":.1f",
                        "avg_quality": ":.2f",
                        "issue_count": True,
                        "price_trend": ":.2f",
                    },
                    title="Supplier Risk Matrix",
                    template="plotly_white",
                )
                fig.update_traces(textposition="top center")
                fig.update_yaxes(range=[0, 5], title="Avg Quality (0–5)")
                fig.update_xaxes(title="Avg Delivery Days")

                # Risk Zone: bottom-right quadrant (high delivery + low quality)
                x0 = 30
                x1 = float(plot_df["avg_delivery_days"].max()) if not plot_df.empty else 60.0
                y0 = 0
                y1 = 3.5
                fig.add_shape(
                    type="rect",
                    x0=x0,
                    x1=x1,
                    y0=y0,
                    y1=y1,
                    fillcolor="rgba(231, 76, 60, 0.12)",
                    line=dict(color="rgba(231, 76, 60, 0.35)", width=1),
                    layer="below",
                )
                fig.add_annotation(
                    x=(x0 + x1) / 2,
                    y=y1 - 0.15,
                    text="Risk Zone",
                    showarrow=False,
                    font=dict(color="rgba(231, 76, 60, 0.9)", size=12),
                )

                st.plotly_chart(fig, use_container_width=True)

                # --- Two-column: Price trend + Spend concentration ---
                left, right = st.columns(2)

                with left:
                    st.markdown("### Price Trend by Supplier")
                    if df_f.empty:
                        st.warning("No rows match the selected supplier filter.")
                    else:
                        price_df = df_f.dropna(subset=["date"]).sort_values("date")
                        price_fig = px.line(
                            price_df,
                            x="date",
                            y="unit_price_eur",
                            color="supplier",
                            title="Price Trend by Supplier",
                            template="plotly_white",
                        )
                        st.plotly_chart(price_fig, use_container_width=True)

                with right:
                    try:
                        import plotly.graph_objects as go
                    except Exception:
                        st.warning("Plotly is required for Spend Concentration chart.")
                    else:
                        st.markdown("### Spend Concentration by Risk")
                        spend_sorted = agg_f.sort_values("total_spend", ascending=False)
                        spend_fig = go.Figure()
                        for _, row in spend_sorted.iterrows():
                            supplier = str(row["supplier"])
                            spend = float(row["total_spend"] or 0.0)
                            risk = str(row["risk"])
                            spend_fig.add_trace(
                                go.Bar(
                                    y=["Total Spend"],
                                    x=[spend],
                                    name=supplier,
                                    orientation="h",
                                    marker_color=risk_color.get(risk, "#999999"),
                                    hovertemplate=f"{supplier}<br>Spend: €%{{x:,.0f}}<extra></extra>",
                                )
                            )
                        spend_fig.update_layout(
                            barmode="stack",
                            title="Spend Concentration by Risk",
                            template="plotly_white",
                            height=360,
                            margin=dict(l=20, r=20, t=60, b=20),
                            legend=dict(orientation="v"),
                        )
                        st.plotly_chart(spend_fig, use_container_width=True)

                with st.expander("📋 Full Purchase History", expanded=False):
                    st.dataframe(
                        df_f.sort_values(["supplier", "date"]),
                        use_container_width=True,
                    )
elif tab == "Weekly Business Review":
    st.markdown("## Weekly Business Review — W1 to W12")

    wbr = read_csv_or_warn(demo_n=5, rel_path="demo5_wbr/data/weekly_metrics.csv")

    if wbr is not None:
        try:
            import plotly.graph_objects as go
            import plotly.express as px
        except Exception:
            st.warning("Plotly is required for Weekly Review charts. Install with `pip install plotly`.")
        else:
            # ------------------------------------------------------------------
            # Data preparation
            # ------------------------------------------------------------------
            df = wbr.copy()
            df["revenue_eur"]           = pd.to_numeric(df["revenue_eur"],           errors="coerce")
            df["units_sold"]            = pd.to_numeric(df["units_sold"],             errors="coerce")
            df["csat_score"]            = pd.to_numeric(df["csat_score"],             errors="coerce")
            df["support_tickets_open"]  = pd.to_numeric(df["support_tickets_open"],  errors="coerce")
            df["support_tickets_closed"]= pd.to_numeric(df["support_tickets_closed"],errors="coerce")
            df["marketing_spend_eur"]   = pd.to_numeric(df["marketing_spend_eur"],   errors="coerce")
            df["demo_requests"]         = pd.to_numeric(df["demo_requests"],          errors="coerce")

            # Week-over-week % changes
            df["rev_wow"]     = df["revenue_eur"].pct_change() * 100
            df["tickets_wow"] = df["support_tickets_open"].pct_change() * 100
            df["csat_wow"]    = df["csat_score"].pct_change() * 100

            # Alert flag per row
            def _is_alert(row: pd.Series) -> bool:
                rev_drop     = pd.notna(row["rev_wow"])     and row["rev_wow"]     < -20
                ticket_spike = pd.notna(row["tickets_wow"]) and row["tickets_wow"] >  20
                csat_low     = pd.notna(row["csat_score"])  and row["csat_score"]  <  4.0
                return bool(rev_drop or ticket_spike or csat_low)

            df["is_alert"] = df.apply(_is_alert, axis=1)

            # Trade show weeks
            trade_show_weeks = {"W6", "W10"}

            # Revenue quartile for scatter colouring (1=lowest … 4=highest)
            df["rev_quartile"] = pd.qcut(
                df["revenue_eur"].fillna(0), q=4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop"
            )

            # ------------------------------------------------------------------
            # Alerts-only toggle
            # ------------------------------------------------------------------
            alerts_only = st.toggle("Show alerts only", key="alerts_only")

            # Helper: opacity array — grey out non-alert weeks when toggle is on
            def _opacity(series_weeks: pd.Series) -> list[float]:
                if not alerts_only:
                    return [1.0] * len(series_weeks)
                return [
                    1.0 if df.loc[df["week"] == w, "is_alert"].any() else 0.2
                    for w in series_weeks
                ]

            weeks      = df["week"].tolist()
            week_opac  = _opacity(pd.Series(weeks))

            # ------------------------------------------------------------------
            # Row 1 — Revenue bars + Units Sold line (dual Y-axis)
            # ------------------------------------------------------------------
            st.markdown("### Revenue & Units Sold by Week")
            fig_rev = go.Figure()

            # Revenue bars
            fig_rev.add_trace(go.Bar(
                x=weeks,
                y=df["revenue_eur"].tolist(),
                name="Revenue (€)",
                marker_color=[
                    f"rgba(0,180,216,{o})" for o in week_opac
                ],
                yaxis="y1",
                hovertemplate="<b>%{x}</b><br>Revenue: €%{y:,.0f}<extra></extra>",
            ))

            # Units sold line
            fig_rev.add_trace(go.Scatter(
                x=weeks,
                y=df["units_sold"].tolist(),
                name="Units Sold",
                mode="lines+markers",
                line=dict(color="#1E3A5F", width=2),
                marker=dict(
                    color="#1E3A5F",
                    opacity=week_opac,
                    size=7,
                ),
                yaxis="y2",
                hovertemplate="<b>%{x}</b><br>Units: %{y}<extra></extra>",
            ))

            # Trade-show markers + annotations
            for ts_week in trade_show_weeks:
                if ts_week in df["week"].values:
                    ts_row = df[df["week"] == ts_week].iloc[0]
                    fig_rev.add_trace(go.Scatter(
                        x=[ts_week],
                        y=[ts_row["revenue_eur"]],
                        mode="markers+text",
                        marker=dict(symbol="star", size=16, color="#FFC300"),
                        text=["📍 Trade Show"],
                        textposition="top center",
                        showlegend=False,
                        yaxis="y1",
                        hoverinfo="skip",
                    ))

            fig_rev.update_layout(
                template="plotly_white",
                hovermode="x unified",
                yaxis=dict(title="Revenue (€)", tickprefix="€"),
                yaxis2=dict(title="Units Sold", overlaying="y", side="right"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=40, b=40),
            )
            st.plotly_chart(fig_rev, use_container_width=True)

            # ------------------------------------------------------------------
            # Row 2 — CSAT trend (left) + Marketing spend vs demo requests (right)
            # ------------------------------------------------------------------
            left_col, right_col = st.columns([3, 2])

            with left_col:
                st.markdown("### CSAT Score Trend")
                fig_csat = go.Figure()

                # Light-red fill below the 4.0 threshold line
                fig_csat.add_trace(go.Scatter(
                    x=weeks + weeks[::-1],
                    y=[min(float(v), 4.0) for v in df["csat_score"].fillna(4.0)]
                      + [4.0] * len(weeks),
                    fill="toself",
                    fillcolor="rgba(231,76,60,0.12)",
                    line=dict(color="rgba(0,0,0,0)"),
                    showlegend=False,
                    hoverinfo="skip",
                ))

                # CSAT line
                fig_csat.add_trace(go.Scatter(
                    x=weeks,
                    y=df["csat_score"].tolist(),
                    mode="lines+markers",
                    name="CSAT",
                    line=dict(color="#00B4D8", width=2.5),
                    marker=dict(
                        color="#00B4D8",
                        opacity=week_opac,
                        size=7,
                    ),
                    hovertemplate="<b>%{x}</b><br>CSAT: %{y:.2f}<extra></extra>",
                ))

                # Red dashed threshold
                fig_csat.add_hline(
                    y=4.0,
                    line_dash="dash",
                    line_color="#E74C3C",
                    annotation_text="Minimum Target (4.0)",
                    annotation_position="bottom right",
                    annotation_font_color="#E74C3C",
                )

                fig_csat.update_layout(
                    template="plotly_white",
                    hovermode="x unified",
                    yaxis=dict(title="CSAT Score", range=[3.0, 5.0]),
                    showlegend=False,
                    margin=dict(t=30, b=30),
                )
                st.plotly_chart(fig_csat, use_container_width=True)

            with right_col:
                st.markdown("### Marketing Spend vs. Demo Requests")
                quartile_colors = {"Q1": "#BDE0F0", "Q2": "#6EC8E0", "Q3": "#1E90C0", "Q4": "#1E3A5F"}
                scatter_colors = [
                    quartile_colors.get(str(q), "#00B4D8")
                    for q in df["rev_quartile"].tolist()
                ]

                fig_scatter = go.Figure()
                fig_scatter.add_trace(go.Scatter(
                    x=df["marketing_spend_eur"].tolist(),
                    y=df["demo_requests"].tolist(),
                    mode="markers+text",
                    text=weeks,
                    textposition="top center",
                    marker=dict(
                        color=scatter_colors,
                        size=10,
                        opacity=[o for o in week_opac],
                        line=dict(color="white", width=1),
                    ),
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "Marketing spend: €%{x:,.0f}<br>"
                        "Demo requests: %{y}<extra></extra>"
                    ),
                ))

                fig_scatter.update_layout(
                    template="plotly_white",
                    xaxis=dict(title="Marketing Spend (€)", tickprefix="€"),
                    yaxis=dict(title="Demo Requests"),
                    margin=dict(t=30, b=30),
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

            # ------------------------------------------------------------------
            # Row 3 — Support ticket backlog (area chart)
            # ------------------------------------------------------------------
            st.markdown("### Support Ticket Backlog")
            fig_tickets = go.Figure()

            fig_tickets.add_trace(go.Scatter(
                x=weeks,
                y=df["support_tickets_open"].tolist(),
                name="Tickets Open",
                mode="lines",
                line=dict(color="#E74C3C", width=2),
                fill="tozeroy",
                fillcolor="rgba(231,76,60,0.35)",
                hovertemplate="<b>%{x}</b><br>Open: %{y}<extra></extra>",
            ))

            fig_tickets.add_trace(go.Scatter(
                x=weeks,
                y=df["support_tickets_closed"].tolist(),
                name="Tickets Closed",
                mode="lines",
                line=dict(color="#2ECC71", width=2),
                fill="tozeroy",
                fillcolor="rgba(46,204,113,0.35)",
                hovertemplate="<b>%{x}</b><br>Closed: %{y}<extra></extra>",
            ))

            # Annotation at W12
            if "W12" in weeks:
                w12_row = df[df["week"] == "W12"].iloc[0]
                fig_tickets.add_annotation(
                    x="W12",
                    y=float(w12_row["support_tickets_open"]),
                    text="⚠️ Backlog growing",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#E74C3C",
                    font=dict(color="#E74C3C", size=12),
                    ay=-40,
                )

            fig_tickets.update_layout(
                template="plotly_white",
                hovermode="x unified",
                yaxis=dict(title="Tickets"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=40, b=30),
            )
            st.plotly_chart(fig_tickets, use_container_width=True)

            # ------------------------------------------------------------------
            # Alerts table
            # ------------------------------------------------------------------
            st.markdown("### 🚨 Alert Weeks")
            alert_rows = []
            for _, row in df.iterrows():
                if not row["is_alert"]:
                    continue
                if pd.notna(row["rev_wow"]) and row["rev_wow"] < -20:
                    alert_rows.append({
                        "Week": row["week"],
                        "Metric Triggered": "Revenue drop",
                        "Value": f"€{row['revenue_eur']:,.0f}",
                        "Change %": f"{row['rev_wow']:+.1f}%",
                        "Severity": "HIGH",
                    })
                if pd.notna(row["tickets_wow"]) and row["tickets_wow"] > 20:
                    alert_rows.append({
                        "Week": row["week"],
                        "Metric Triggered": "Support tickets spike",
                        "Value": str(int(row["support_tickets_open"])),
                        "Change %": f"{row['tickets_wow']:+.1f}%",
                        "Severity": "HIGH",
                    })
                if pd.notna(row["csat_score"]) and row["csat_score"] < 4.0:
                    alert_rows.append({
                        "Week": row["week"],
                        "Metric Triggered": "CSAT below target",
                        "Value": f"{row['csat_score']:.2f}",
                        "Change %": f"{row['csat_wow']:+.1f}%" if pd.notna(row["csat_wow"]) else "—",
                        "Severity": "HIGH",
                    })

            if alert_rows:
                alert_df = pd.DataFrame(alert_rows)

                def _style_severity(val: str) -> str:
                    if val == "HIGH":
                        return "color: #E74C3C; font-weight: bold;"
                    return ""

                styled = alert_df.style.applymap(_style_severity, subset=["Severity"])
                st.dataframe(styled, use_container_width=True, hide_index=True)
            else:
                st.success("No alert weeks detected in the selected range.")
else:
    # Defensive fallback (shouldn't happen unless session state is manually edited).
    st.write("Coming soon")


# --------------------------------------------------------------------------------------
# Footer (required structure)
# --------------------------------------------------------------------------------------

st.markdown(
    '<div style="margin-top:1rem; color: rgba(0,0,0,0.55); font-size: 0.85rem;">'
    "Generated by BrightEyes AI Demo Suite — Group E"
    "</div>",
    unsafe_allow_html=True,
)

