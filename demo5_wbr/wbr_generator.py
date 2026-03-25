#!/usr/bin/env python3
"""
Weekly Business Review (WBR) — Demo 5 (3C Card)

Goal
-----
Read weekly business metrics (CSV) and generate an executive WBR snapshot:
- week-over-week changes for key metrics
- anomaly alerts when a metric moves >20% in the wrong direction
- YTD aggregates + derived KPIs (win rate, marketing ROI)
- data-driven narrative + action items with named owners

Constraints
-----------
- Rule-based analysis only (no external APIs).
- All output in English.
- Use emojis in terminal output and in the Markdown report for scannability.
"""

from __future__ import annotations

import csv
import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional, Tuple


# -----------------------------
# Data model
# -----------------------------


@dataclass(frozen=True)
class WeeklyRow:
    week: str
    week_start: _dt.date
    revenue_eur: float
    units_sold: int
    new_leads: int
    proposals_sent: int
    proposals_won: int
    installations_completed: int
    support_tickets_open: int
    support_tickets_closed: int
    avg_resolution_hours: float
    csat_score: float
    marketing_spend_eur: float
    trade_shows: int
    website_visits: int
    demo_requests: int


# -----------------------------
# Utilities
# -----------------------------


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _format_eur(amount: float) -> str:
    return f"€{amount:,.0f}"


def _format_int(n: int) -> str:
    return f"{n:,}"


def _safe_div(n: float, d: float) -> Optional[float]:
    if d == 0:
        return None
    return n / d


def _pct(delta: Optional[float]) -> str:
    if delta is None:
        return "n/a"
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta*100:.1f}%"


def _parse_date_yyyy_mm_dd(s: str) -> _dt.date:
    return _dt.datetime.strptime(s.strip(), "%Y-%m-%d").date()


def _status_emoji_label(is_strong: bool) -> str:
    return "🟢 STRONG" if is_strong else "🔴 ALERT"


def _priority_emoji(priority: str) -> str:
    p = (priority or "").strip().lower()
    if p == "high":
        return "🔴 High"
    return "🟡 Medium"


# -----------------------------
# Loading
# -----------------------------


def load_weekly_metrics(csv_path: Path) -> List[WeeklyRow]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {
            "week",
            "week_start",
            "revenue_eur",
            "units_sold",
            "new_leads",
            "proposals_sent",
            "proposals_won",
            "installations_completed",
            "support_tickets_open",
            "support_tickets_closed",
            "avg_resolution_hours",
            "csat_score",
            "marketing_spend_eur",
            "trade_shows",
            "website_visits",
            "demo_requests",
        }
        if not reader.fieldnames or any(k not in reader.fieldnames for k in required):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

        out: List[WeeklyRow] = []
        for r in reader:
            out.append(
                WeeklyRow(
                    week=(r["week"] or "").strip(),
                    week_start=_parse_date_yyyy_mm_dd(r["week_start"] or ""),
                    revenue_eur=float(r["revenue_eur"] or 0.0),
                    units_sold=int(float(r["units_sold"] or 0)),
                    new_leads=int(float(r["new_leads"] or 0)),
                    proposals_sent=int(float(r["proposals_sent"] or 0)),
                    proposals_won=int(float(r["proposals_won"] or 0)),
                    installations_completed=int(float(r["installations_completed"] or 0)),
                    support_tickets_open=int(float(r["support_tickets_open"] or 0)),
                    support_tickets_closed=int(float(r["support_tickets_closed"] or 0)),
                    avg_resolution_hours=float(r["avg_resolution_hours"] or 0.0),
                    csat_score=float(r["csat_score"] or 0.0),
                    marketing_spend_eur=float(r["marketing_spend_eur"] or 0.0),
                    trade_shows=int(float(r["trade_shows"] or 0)),
                    website_visits=int(float(r["website_visits"] or 0)),
                    demo_requests=int(float(r["demo_requests"] or 0)),
                )
            )

    out.sort(key=lambda x: x.week_start)
    return out


# -----------------------------
# KPI calculations
# -----------------------------


def win_rate(row: WeeklyRow) -> Optional[float]:
    return _safe_div(row.proposals_won, row.proposals_sent)


def wow_change(cur: float, prev: float) -> Optional[float]:
    """
    Returns fractional change (cur-prev)/prev.
    If prev == 0, return None (undefined) unless cur == prev (then 0.0).
    """
    if prev == 0:
        return 0.0 if cur == 0 else None
    return (cur - prev) / prev


def marketing_roi_revenue_per_eur_spend(row: WeeklyRow) -> Optional[float]:
    """
    Simple marketing ROI proxy: revenue per € of marketing spend.
    (Not causal; used as a weekly efficiency indicator.)
    """
    return _safe_div(row.revenue_eur, row.marketing_spend_eur)


def is_bad_move(metric_name: str, wow: Optional[float], cur: float, prev: float) -> Optional[bool]:
    """
    Alert if any metric moves >20% in the *wrong* direction.
    Returns None if metric_name isn't scored.
    """
    higher_is_better = {
        "revenue_eur",
        "units_sold",
        "new_leads",
        "proposals_sent",
        "proposals_won",
        "installations_completed",
        "support_tickets_closed",
        "csat_score",
        "website_visits",
        "demo_requests",
        "win_rate",
        "marketing_roi",
    }
    lower_is_better = {
        "support_tickets_open",
        "avg_resolution_hours",
    }

    if metric_name in higher_is_better:
        if wow is not None:
            return wow <= -0.20
        # prev==0 → cur>0 means it rose from 0 (not "bad")
        return False

    if metric_name in lower_is_better:
        if wow is not None:
            return wow >= 0.20
        # prev==0 and cur>0 means backlog/resolution appeared from zero (bad signal)
        return cur > prev

    return None


def ytd_aggregates(rows: List[WeeklyRow]) -> Dict[str, object]:
    rev = sum(r.revenue_eur for r in rows)
    units = sum(r.units_sold for r in rows)
    leads = sum(r.new_leads for r in rows)
    sent = sum(r.proposals_sent for r in rows)
    won = sum(r.proposals_won for r in rows)
    installs = sum(r.installations_completed for r in rows)
    csat_avg = float(mean([r.csat_score for r in rows])) if rows else 0.0
    spend = sum(r.marketing_spend_eur for r in rows)
    roi = _safe_div(rev, spend)
    tickets_open_avg = float(mean([r.support_tickets_open for r in rows])) if rows else 0.0
    tickets_open_latest = rows[-1].support_tickets_open if rows else 0
    res_hours_avg = float(mean([r.avg_resolution_hours for r in rows])) if rows else 0.0

    return {
        "revenue_eur": rev,
        "units_sold": units,
        "new_leads": leads,
        "proposals_sent": sent,
        "proposals_won": won,
        "win_rate": _safe_div(won, sent),
        "installations_completed": installs,
        "csat_avg": csat_avg,
        "marketing_spend_eur": spend,
        "marketing_roi": roi,
        "tickets_open_latest": tickets_open_latest,
        "tickets_open_avg": tickets_open_avg,
        "avg_resolution_hours_avg": res_hours_avg,
    }


# -----------------------------
# Narrative + actions (rule-based)
# -----------------------------


def build_narrative(cur: WeeklyRow, prev: WeeklyRow) -> str:
    wr_cur = win_rate(cur)
    wr_prev = win_rate(prev)
    wr_wow = wow_change(wr_cur, wr_prev) if (wr_cur is not None and wr_prev is not None) else None

    revenue_wow = wow_change(cur.revenue_eur, prev.revenue_eur)
    leads_wow = wow_change(cur.new_leads, prev.new_leads)
    csat_wow = wow_change(cur.csat_score, prev.csat_score)
    tickets_wow = wow_change(cur.support_tickets_open, prev.support_tickets_open)

    bits: List[str] = []
    bits.append(
        f"In {cur.week} (starting {cur.week_start.isoformat()}), BrightEyes generated {_format_eur(cur.revenue_eur)} in revenue from {cur.units_sold} units."
    )

    bits.append(
        "Revenue changed " + _pct(revenue_wow) + " week-over-week."
        if revenue_wow is not None
        else "Revenue week-over-week change is not comparable due to a zero baseline last week."
    )

    bits.append(
        f"Top-of-funnel activity: {cur.new_leads} new leads ({_pct(leads_wow)} WoW) and {cur.demo_requests} demo requests."
        if leads_wow is not None
        else f"Top-of-funnel activity: {cur.new_leads} new leads and {cur.demo_requests} demo requests (WoW not comparable due to a zero baseline)."
    )

    if wr_cur is not None:
        wr_text = f"{wr_cur*100:.1f}%"
        bits.append(
            f"Sales execution: win rate was {wr_text} ({_pct(wr_wow)} WoW) on {cur.proposals_sent} proposals sent."
            if wr_wow is not None
            else f"Sales execution: win rate was {wr_text} on {cur.proposals_sent} proposals sent."
        )
    else:
        bits.append(f"Sales execution: {cur.proposals_won} wins on {cur.proposals_sent} proposals sent (win rate n/a).")

    bits.append(
        f"Customer health: CSAT was {cur.csat_score:.1f}/5 ({_pct(csat_wow)} WoW) with {cur.support_tickets_open} tickets open."
        if csat_wow is not None
        else f"Customer health: CSAT was {cur.csat_score:.1f}/5 with {cur.support_tickets_open} tickets open."
    )

    bits.append(
        f"Support workload moved {_pct(tickets_wow)} WoW; average resolution time was {cur.avg_resolution_hours:.0f} hours."
        if tickets_wow is not None
        else f"Average resolution time was {cur.avg_resolution_hours:.0f} hours."
    )

    return " ".join(bits)


def build_action_items(cur: WeeklyRow, prev: WeeklyRow) -> List[Dict[str, str]]:
    actions: List[Dict[str, str]] = []

    # Revenue / sales
    rev_wow = wow_change(cur.revenue_eur, prev.revenue_eur)
    wr_cur = win_rate(cur)
    wr_prev = win_rate(prev)
    wr_wow = wow_change(wr_cur, wr_prev) if (wr_cur is not None and wr_prev is not None) else None

    if rev_wow is not None and rev_wow <= -0.20:
        actions.append(
            {
                "priority": "High",
                "owner": "CEO",
                "action": "Run a 30-minute revenue recovery review: top 10 active opportunities, stuck stages, and next-step commitments per rep for the next 2 weeks.",
            }
        )

    if wr_wow is not None and wr_wow <= -0.20:
        actions.append(
            {
                "priority": "High",
                "owner": "Sales",
                "action": "Audit the last 10 proposals for pricing/spec gaps; introduce a stricter deal qualification checklist before proposals are sent.",
            }
        )

    # Funnel / marketing
    leads_wow = wow_change(cur.new_leads, prev.new_leads)
    visits_wow = wow_change(cur.website_visits, prev.website_visits)
    spend_wow = wow_change(cur.marketing_spend_eur, prev.marketing_spend_eur)

    if leads_wow is not None and leads_wow <= -0.20:
        actions.append(
            {
                "priority": "Medium",
                "owner": "Marketing",
                "action": "Reallocate next week’s spend toward the two highest-converting channels and refresh the demo-request landing page CTA to recover lead volume.",
            }
        )

    if spend_wow is not None and spend_wow >= 0.20 and (leads_wow is not None and leads_wow <= 0):
        actions.append(
            {
                "priority": "Medium",
                "owner": "Marketing",
                "action": "Investigate why marketing spend rose without lead lift; pause lowest-performing campaigns and report CAC and lead quality by channel.",
            }
        )

    if visits_wow is not None and visits_wow <= -0.20:
        actions.append(
            {
                "priority": "Medium",
                "owner": "Marketing",
                "action": "Run an SEO + email push for existing lists this week to restore website traffic and demo requests.",
            }
        )

    # Support / CSAT
    tickets_wow = wow_change(cur.support_tickets_open, prev.support_tickets_open)
    res_wow = wow_change(cur.avg_resolution_hours, prev.avg_resolution_hours)
    csat_wow = wow_change(cur.csat_score, prev.csat_score)

    if (tickets_wow is not None and tickets_wow >= 0.20) or (res_wow is not None and res_wow >= 0.20):
        actions.append(
            {
                "priority": "High",
                "owner": "Support Lead",
                "action": "Launch a ticket triage sprint: tag top 3 issue categories, assign daily owners, and publish a same-day response SLA for new tickets.",
            }
        )

    if csat_wow is not None and csat_wow <= -0.20:
        actions.append(
            {
                "priority": "High",
                "owner": "Support Lead",
                "action": "Contact the 5 lowest-CSAT accounts from this week, capture root causes, and align fixes with R&D/Operations where needed.",
            }
        )

    # Operations / installations
    installs_wow = wow_change(cur.installations_completed, prev.installations_completed)
    if installs_wow is not None and installs_wow <= -0.20:
        actions.append(
            {
                "priority": "Medium",
                "owner": "Operations",
                "action": "Confirm next 2 weeks of installation capacity and pre-stage shipments for scheduled installs to avoid slippage.",
            }
        )

    if not actions:
        actions.append(
            {
                "priority": "Medium",
                "owner": "CEO",
                "action": "No critical anomalies detected. Maintain focus on pipeline creation, proposal quality, and support responsiveness; re-check trends next Monday.",
            }
        )

    return actions[:8]


# -----------------------------
# Alerts + report generation
# -----------------------------


def compute_alerts(cur: WeeklyRow, prev: WeeklyRow) -> List[Dict[str, str]]:
    alerts: List[Dict[str, str]] = []

    metrics: List[Tuple[str, float, float]] = [
        ("revenue_eur", cur.revenue_eur, prev.revenue_eur),
        ("units_sold", float(cur.units_sold), float(prev.units_sold)),
        ("new_leads", float(cur.new_leads), float(prev.new_leads)),
        ("proposals_sent", float(cur.proposals_sent), float(prev.proposals_sent)),
        ("proposals_won", float(cur.proposals_won), float(prev.proposals_won)),
        ("installations_completed", float(cur.installations_completed), float(prev.installations_completed)),
        ("support_tickets_open", float(cur.support_tickets_open), float(prev.support_tickets_open)),
        ("avg_resolution_hours", cur.avg_resolution_hours, prev.avg_resolution_hours),
        ("csat_score", cur.csat_score, prev.csat_score),
        ("website_visits", float(cur.website_visits), float(prev.website_visits)),
        ("demo_requests", float(cur.demo_requests), float(prev.demo_requests)),
    ]

    wr_cur = win_rate(cur)
    wr_prev = win_rate(prev)
    if wr_cur is not None and wr_prev is not None:
        metrics.append(("win_rate", wr_cur, wr_prev))

    mroi_cur = marketing_roi_revenue_per_eur_spend(cur)
    mroi_prev = marketing_roi_revenue_per_eur_spend(prev)
    if mroi_cur is not None and mroi_prev is not None:
        metrics.append(("marketing_roi", mroi_cur, mroi_prev))

    for name, cur_v, prev_v in metrics:
        wow = wow_change(cur_v, prev_v)
        bad = is_bad_move(name, wow, cur_v, prev_v)
        if bad is True:
            alerts.append({"metric": name, "wow": _pct(wow)})

    return alerts


def generate_markdown(rows: List[WeeklyRow], generated_at: _dt.datetime) -> str:
    if len(rows) < 2:
        raise ValueError("Need at least 2 weeks of data to compute week-over-week changes.")

    cur = rows[-1]
    prev = rows[-2]
    alerts = compute_alerts(cur, prev)
    ytd = ytd_aggregates(rows)
    narrative = build_narrative(cur, prev)
    actions = build_action_items(cur, prev)

    wr_cur = win_rate(cur)
    wr_prev = win_rate(prev)
    mroi_cur = marketing_roi_revenue_per_eur_spend(cur)
    mroi_prev = marketing_roi_revenue_per_eur_spend(prev)

    def status_for(metric: str, cur_v: float, prev_v: float) -> str:
        wow = wow_change(cur_v, prev_v)
        bad = is_bad_move(metric, wow, cur_v, prev_v)
        if bad is None:
            return "—"
        return _status_emoji_label(not bad)

    lines: List[str] = []
    lines.append(f"# 📅 Weekly Business Review (WBR) — {cur.week}")
    lines.append("")
    lines.append(f"**Week starting:** {cur.week_start.isoformat()}")
    lines.append(f"**Generated:** {generated_at.strftime('%Y-%m-%d %H:%M')} by `wbr_generator.py`")
    lines.append("")

    lines.append("## 🚦 Executive status")
    lines.append("")
    lines.append(f"- **Alerts**: {'🔴 ' + str(len(alerts)) + ' flagged' if alerts else '🟢 None flagged'}")
    lines.append("")

    lines.append("## 📊 KPI snapshot (WoW)")
    lines.append("")
    lines.append("| Metric | Current week | Prior week | WoW | Good when… | Status |")
    lines.append("|---|---:|---:|---:|---|---|")
    lines.append(
        f"| 💰 revenue_eur | {_format_eur(cur.revenue_eur)} | {_format_eur(prev.revenue_eur)} | {_pct(wow_change(cur.revenue_eur, prev.revenue_eur))} | Higher | {status_for('revenue_eur', cur.revenue_eur, prev.revenue_eur)} |"
    )
    lines.append(
        f"| 📦 units_sold | {_format_int(cur.units_sold)} | {_format_int(prev.units_sold)} | {_pct(wow_change(cur.units_sold, prev.units_sold))} | Higher | {status_for('units_sold', float(cur.units_sold), float(prev.units_sold))} |"
    )
    lines.append(
        f"| 🧲 new_leads | {_format_int(cur.new_leads)} | {_format_int(prev.new_leads)} | {_pct(wow_change(cur.new_leads, prev.new_leads))} | Higher | {status_for('new_leads', float(cur.new_leads), float(prev.new_leads))} |"
    )
    lines.append(
        f"| 🎯 win_rate | {(wr_cur*100):.1f}% | {(wr_prev*100):.1f}% | {_pct(wow_change(wr_cur, wr_prev) if (wr_cur is not None and wr_prev is not None) else None)} | Higher | {status_for('win_rate', float(wr_cur or 0.0), float(wr_prev or 0.0))} |"
    )
    lines.append(
        f"| 😊 csat_score | {cur.csat_score:.1f}/5 | {prev.csat_score:.1f}/5 | {_pct(wow_change(cur.csat_score, prev.csat_score))} | Higher | {status_for('csat_score', cur.csat_score, prev.csat_score)} |"
    )
    lines.append(
        f"| ⚠️ support_tickets_open | {_format_int(cur.support_tickets_open)} | {_format_int(prev.support_tickets_open)} | {_pct(wow_change(cur.support_tickets_open, prev.support_tickets_open))} | Lower | {status_for('support_tickets_open', float(cur.support_tickets_open), float(prev.support_tickets_open))} |"
    )
    lines.append(
        f"| ⏱️ avg_resolution_hours | {cur.avg_resolution_hours:.0f}h | {prev.avg_resolution_hours:.0f}h | {_pct(wow_change(cur.avg_resolution_hours, prev.avg_resolution_hours))} | Lower | {status_for('avg_resolution_hours', cur.avg_resolution_hours, prev.avg_resolution_hours)} |"
    )
    if mroi_cur is not None and mroi_prev is not None:
        lines.append(
            f"| 📈 marketing_roi (rev/€ spend) | {mroi_cur:.2f} | {mroi_prev:.2f} | {_pct(wow_change(mroi_cur, mroi_prev))} | Higher | {status_for('marketing_roi', mroi_cur, mroi_prev)} |"
        )
    lines.append("")

    lines.append("## 📈 YTD (last 12 weeks in file)")
    lines.append("")
    lines.append(f"- **Total revenue**: {_format_eur(float(ytd['revenue_eur']))}")
    lines.append(f"- **Units sold**: {_format_int(int(ytd['units_sold']))}")
    lines.append(f"- **New leads**: {_format_int(int(ytd['new_leads']))}")
    wr_ytd = ytd.get("win_rate")
    lines.append(
        f"- **Win rate**: {(wr_ytd*100):.1f}% (wins {int(ytd['proposals_won'])} / sent {int(ytd['proposals_sent'])})"
        if wr_ytd is not None
        else "- **Win rate**: n/a"
    )
    lines.append(f"- **CSAT (avg)**: {float(ytd['csat_avg']):.2f}/5")
    lines.append(f"- **Marketing spend**: {_format_eur(float(ytd['marketing_spend_eur']))}")
    roi_ytd = ytd.get("marketing_roi")
    lines.append(f"- **Marketing ROI (rev/€ spend)**: {roi_ytd:.2f}" if roi_ytd is not None else "- **Marketing ROI**: n/a")
    lines.append(
        f"- **Support backlog (latest / avg)**: {_format_int(int(ytd['tickets_open_latest']))} / {float(ytd['tickets_open_avg']):.1f} tickets"
    )
    lines.append(f"- **Avg resolution time (avg)**: {float(ytd['avg_resolution_hours_avg']):.1f} hours")
    lines.append("")

    lines.append("## 🧠 Narrative")
    lines.append("")
    lines.append(narrative)
    lines.append("")

    lines.append("## ⚠️ Alerts (moves >20% in the wrong direction)")
    lines.append("")
    if alerts:
        for a in alerts:
            lines.append(f"- 🔴 **{a['metric']}** moved {a['wow']} in the wrong direction.")
    else:
        lines.append("- 🟢 No anomalies detected based on the 20% threshold.")
    lines.append("")

    lines.append("## ✅ Action items (owners + priority)")
    lines.append("")
    lines.append("| Priority | Owner | Action |")
    lines.append("|---|---|---|")
    for a in actions:
        lines.append(f"| {_priority_emoji(a['priority'])} | {a['owner']} | {a['action']} |")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    root = Path(__file__).resolve().parent
    csv_path = root / "data" / "weekly_metrics.csv"
    output_dir = root / "output"
    _ensure_dir(output_dir)

    print("📊 Loading weekly metrics…")
    if not csv_path.exists():
        print(f"🔴 CSV not found at: {csv_path}")
        return 2

    rows = load_weekly_metrics(csv_path)
    if len(rows) < 2:
        print(f"🔴 Need at least 2 rows; found {len(rows)}.")
        return 2

    cur = rows[-1]
    prev = rows[-2]

    print(f"📅 Current week: {cur.week} (starting {cur.week_start.isoformat()})")
    print(f"💰 Revenue: {_format_eur(cur.revenue_eur)} | Units: {cur.units_sold}")
    wr = win_rate(cur)
    wr_s = f"{wr*100:.1f}%" if wr is not None else "n/a"
    print(f"🎯 Win rate: {wr_s} (won {cur.proposals_won} / sent {cur.proposals_sent})")
    print(f"😊 CSAT: {cur.csat_score:.1f}/5")
    print(f"⚠️ Support backlog: {cur.support_tickets_open} open | Avg resolution: {cur.avg_resolution_hours:.0f}h")

    alerts = compute_alerts(cur, prev)
    if alerts:
        print(f"⚠️ Alerts flagged: {len(alerts)}")
        for a in alerts[:5]:
            print(f"🔴 {a['metric']}: {a['wow']} (wrong direction)")
    else:
        print("🟢 Alerts flagged: 0")

    generated_at = _dt.datetime.now()
    md = generate_markdown(rows, generated_at=generated_at)

    out_path = output_dir / f"WBR_{cur.week}.md"
    print(f"✅ Writing WBR to {out_path.relative_to(root)} …")
    out_path.write_text(md, encoding="utf-8")
    print("✅ Saved.")

    print("\n📌 Summary")
    print(
        f"📅 Week: {cur.week} | 💰 {_format_eur(cur.revenue_eur)} | 🎯 Win rate {wr_s} | 😊 CSAT {cur.csat_score:.1f}/5 | ⚠️ Alerts {len(alerts)}"
    )
    print("✅ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

