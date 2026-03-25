#!/usr/bin/env python3
"""
Supplier negotiation prep — Demo 3 (3C Card)

Goal
-----
Analyze BrightEyes purchase history (CSV) and generate a negotiation brief with:
- supplier scorecards (spend, quality, delivery, issues, price trends)
- deep dives per supplier + specific negotiation talking points
- savings target (5% on trailing-12-month spend)

Constraints
-----------
- Rule-based analysis only (no external APIs).
- All output in English.
- Use emojis in terminal output and the report for scannability.
"""

from __future__ import annotations

import csv
import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional, Tuple


# -----------------------------
# Data models
# -----------------------------


@dataclass(frozen=True)
class PurchaseRow:
    order_id: str
    date: _dt.date
    supplier: str
    component: str
    quantity: int
    unit_price_eur: float
    total_eur: float
    delivery_days: int
    quality_rating: float
    notes: str


@dataclass
class SupplierStats:
    supplier: str
    orders: List[PurchaseRow] = field(default_factory=list)

    @property
    def total_spend_eur(self) -> float:
        return sum(r.total_eur for r in self.orders)

    @property
    def avg_quality(self) -> float:
        vals = [r.quality_rating for r in self.orders]
        return float(mean(vals)) if vals else 0.0

    @property
    def avg_delivery_days(self) -> float:
        vals = [r.delivery_days for r in self.orders]
        return float(mean(vals)) if vals else 0.0

    @property
    def issue_count(self) -> int:
        return sum(1 for r in self.orders if detect_issue(r.notes))

    @property
    def late_count(self) -> int:
        return sum(1 for r in self.orders if detect_late(r.notes))

    @property
    def defective_units_estimate(self) -> int:
        return sum(extract_defective_units(r.notes) for r in self.orders)


# -----------------------------
# Small utilities
# -----------------------------


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _format_eur(amount: float) -> str:
    return f"€{amount:,.0f}"


def _pct(delta: float) -> str:
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta*100:.1f}%"


def _safe_div(n: float, d: float) -> Optional[float]:
    if d == 0:
        return None
    return n / d


# -----------------------------
# Company context parsing (lightweight)
# -----------------------------


def parse_key_suppliers(company_md: str) -> Dict[str, str]:
    """
    Returns supplier -> supplied component category (as described in company context).
    """
    def normalize_supplier_name(name: str) -> str:
        # Company context uses "Supplier (Country)" while the CSV uses "Supplier".
        # Example: "OptiLens GmbH (Germany)" -> "OptiLens GmbH"
        return re.sub(r"\s*\([^)]*\)\s*$", "", name or "").strip()

    out: Dict[str, str] = {}
    in_section = False
    for ln in company_md.splitlines():
        if ln.strip().lower() == "## key suppliers":
            in_section = True
            continue
        if in_section and ln.startswith("## "):
            break
        if not in_section:
            continue
        ln = ln.strip()
        if not ln.startswith("- "):
            continue
        # "- OptiLens GmbH (Germany): CMOS sensors"
        m = re.match(r"-\s*([^:]+):\s*(.+)\s*$", ln)
        if not m:
            continue
        supplier_name = normalize_supplier_name(m.group(1).strip())
        supplied = m.group(2).strip()
        out[supplier_name] = supplied
    return out


# -----------------------------
# CSV loading
# -----------------------------


def parse_date_yyyy_mm_dd(s: str) -> _dt.date:
    return _dt.datetime.strptime(s.strip(), "%Y-%m-%d").date()


def load_purchase_history(csv_path: Path) -> List[PurchaseRow]:
    rows: List[PurchaseRow] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {
            "order_id",
            "date",
            "supplier",
            "component",
            "quantity",
            "unit_price_eur",
            "total_eur",
            "delivery_days",
            "quality_rating",
            "notes",
        }
        if not reader.fieldnames or any(k not in reader.fieldnames for k in required):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

        for r in reader:
            try:
                rows.append(
                    PurchaseRow(
                        order_id=(r["order_id"] or "").strip(),
                        date=parse_date_yyyy_mm_dd(r["date"] or ""),
                        supplier=(r["supplier"] or "").strip(),
                        component=(r["component"] or "").strip(),
                        quantity=int(float(r["quantity"] or 0)),
                        unit_price_eur=float(r["unit_price_eur"] or 0.0),
                        total_eur=float(r["total_eur"] or 0.0),
                        delivery_days=int(float(r["delivery_days"] or 0)),
                        quality_rating=float(r["quality_rating"] or 0.0),
                        notes=(r["notes"] or "").strip(),
                    )
                )
            except Exception as e:
                raise ValueError(f"Failed parsing row {r!r}: {e}") from e
    rows.sort(key=lambda x: x.date)
    return rows


# -----------------------------
# Issue / late detection (rule-based)
# -----------------------------


_ISSUE_PATTERNS = [
    r"\bdefect",
    r"\bdoa\b",
    r"\bscratch",
    r"\breturn",
    r"\breplace",
    r"\bquality\b.*\bdeclin",
]

_LATE_PATTERNS = [
    r"\blate\b",
    r"\bdays?\s+late\b",
    r"\bcustoms\b",
    r"\bdelay\b",
]


def detect_issue(notes: str) -> bool:
    s = (notes or "").lower()
    if not s:
        return False
    return any(re.search(p, s) for p in _ISSUE_PATTERNS)


def detect_late(notes: str) -> bool:
    s = (notes or "").lower()
    if not s:
        return False
    return any(re.search(p, s) for p in _LATE_PATTERNS)


def extract_defective_units(notes: str) -> int:
    """
    Best-effort extraction from notes like:
    - "5 units defective"
    - "12 defective units returned"
    - "1 board DOA replaced"
    """
    s = (notes or "").lower()
    if not s:
        return 0

    m = re.search(r"\b(\d+)\s+units?\s+defect", s)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d+)\s+defect(?:ive)?\s+units?", s)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d+)\s+\w+\s+doa\b", s)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d+)\s+board[s]?\s+doa\b", s)
    if m:
        return int(m.group(1))
    return 0


# -----------------------------
# Trend calculations
# -----------------------------


def trailing_12_months(rows: Iterable[PurchaseRow]) -> List[PurchaseRow]:
    rows_list = list(rows)
    if not rows_list:
        return []
    max_date = max(r.date for r in rows_list)
    cutoff = max_date - _dt.timedelta(days=365)
    return [r for r in rows_list if r.date >= cutoff]


def price_trend_percent(orders: List[PurchaseRow]) -> Optional[float]:
    """
    Computes a robust-ish trend using first-3 vs last-3 average unit prices.
    Returns percent change as a fraction (e.g., +0.05 for +5%).
    """
    if len(orders) < 2:
        return None
    by_date = sorted(orders, key=lambda r: r.date)
    k = min(3, len(by_date))
    first_avg = mean([r.unit_price_eur for r in by_date[:k]])
    last_avg = mean([r.unit_price_eur for r in by_date[-k:]])
    div = _safe_div(last_avg - first_avg, first_avg)
    return div


def price_change_first_last_percent(orders: List[PurchaseRow]) -> Optional[float]:
    if len(orders) < 2:
        return None
    by_date = sorted(orders, key=lambda r: r.date)
    first = by_date[0].unit_price_eur
    last = by_date[-1].unit_price_eur
    div = _safe_div(last - first, first)
    return div


# -----------------------------
# Risk scoring (per 3C card)
# -----------------------------


def risk_level(avg_quality: float, issues: int) -> Tuple[str, str]:
    """
    Returns (emoji, label) where label in {LOW, MEDIUM, HIGH}.
    Risk levels:
    - HIGH if quality < 3.5/5
    - MEDIUM if quality < 4.0 OR > 2 issues
    - LOW otherwise
    """
    if avg_quality < 3.5:
        return ("🔴", "HIGH")
    if avg_quality < 4.0 or issues > 2:
        return ("🟡", "MEDIUM")
    return ("🟢", "LOW")


# -----------------------------
# Negotiation talking points (specific, data-driven)
# -----------------------------


def build_talking_points(stats: SupplierStats) -> List[str]:
    pts: List[str] = []

    avg_q = stats.avg_quality
    issues = stats.issue_count
    late = stats.late_count
    defects = stats.defective_units_estimate
    trend = price_trend_percent(stats.orders)
    first_last = price_change_first_last_percent(stats.orders)

    # Pricing
    if trend is not None and trend > 0.01:
        pts.append(
            f"Unit pricing has increased by about {_pct(trend)} over the period (first-3 vs last-3 orders). Ask for a step-down price or tiered volume rebate tied to annual quantities."
        )
    elif trend is not None and trend < -0.01:
        pts.append(
            f"Unit pricing improved by about {_pct(trend)} over the period. Lock this in with a 12-month price hold and pre-agreed volume tiers."
        )
    else:
        pts.append("Request a 12-month price hold and an explicit volume-break schedule to prevent mid-year price drift.")

    if first_last is not None and abs(first_last) >= 0.03:
        pts.append(
            f"Anchor negotiation on first vs last unit price change ({_pct(first_last)}). Ask for a correction if the change is not justified by material/index shifts."
        )

    # Quality
    if avg_q < 4.0 or issues > 0:
        if defects > 0:
            pts.append(
                f"Quality has caused tangible waste: estimated {defects} defective units mentioned in notes. Request improved incoming QC, root-cause analysis (8D), and credit/replacement SLA."
            )
        else:
            pts.append(
                "Quality signals in notes suggest issues (scratches/DOA/returns). Ask for a corrective action plan and tighter outgoing inspection with documented test results per batch."
            )

        if avg_q < 3.5:
            pts.append(
                "Given sub-3.5 average quality, propose adding penalty/chargeback terms for defects and requiring pre-shipment QC reports until quality stabilizes."
            )

    # Delivery reliability
    if late > 0:
        pts.append(
            f"Delivery reliability: {late} late shipments noted. Ask for a committed lead time with on-time KPI and escalation path; propose partial expedited shipping at supplier cost when late."
        )
    else:
        pts.append("Delivery reliability has been acceptable in notes; still request a committed lead time and proactive shipment tracking updates.")

    # Commercial leverage
    pts.append(
        f"Use spend leverage: total spend with supplier is {_format_eur(stats.total_spend_eur)}; position BrightEyes as a growing account and request preferred-customer terms (allocation priority, stable pricing, faster lead times)."
    )

    return pts


# -----------------------------
# Markdown report generation
# -----------------------------


def generate_markdown_report(
    all_rows: List[PurchaseRow],
    supplier_map: Dict[str, str],
    generated_at: _dt.datetime,
) -> str:
    # Aggregate
    suppliers: Dict[str, SupplierStats] = {}
    for r in all_rows:
        suppliers.setdefault(r.supplier, SupplierStats(supplier=r.supplier)).orders.append(r)

    supplier_list = sorted(suppliers.values(), key=lambda s: s.total_spend_eur, reverse=True)
    t12 = trailing_12_months(all_rows)
    t12_total = sum(r.total_eur for r in t12)
    savings_target_total = t12_total * 0.05

    lines: List[str] = []
    lines.append("# 🏭 Supplier Negotiation Brief — BrightEyes")
    lines.append("")
    lines.append(f"**Generated:** {generated_at.strftime('%Y-%m-%d %H:%M')} by `supplier_analysis.py`")
    lines.append("")

    lines.append("## 🎯 Objectives")
    lines.append("")
    lines.append("- Prepare for supplier negotiations with a data-driven scorecard and supplier-specific talking points.")
    lines.append(f"- **Savings target:** {_format_eur(savings_target_total)} (5% of trailing-12-month spend: {_format_eur(t12_total)}).")
    lines.append("")

    if supplier_map:
        lines.append("## 🧩 Supplier landscape (from company context)")
        lines.append("")
        for name, supplied in supplier_map.items():
            lines.append(f"- **{name}** — {supplied}")
        lines.append("")

    # Scorecard table
    lines.append("## 🧾 Supplier scorecard (sorted by total spend)")
    lines.append("")
    lines.append("| Supplier | Category | Total spend | Avg quality | Avg delivery (days) | Issues | Price trend | Risk |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")

    for s in supplier_list:
        emoji, lvl = risk_level(s.avg_quality, s.issue_count)
        trend = price_trend_percent(s.orders)
        trend_s = _pct(trend) if trend is not None else "n/a"
        category = supplier_map.get(s.supplier, "—")
        lines.append(
            f"| {s.supplier} | {category} | {_format_eur(s.total_spend_eur)} | {s.avg_quality:.2f}/5 | {s.avg_delivery_days:.1f} | {s.issue_count} | {trend_s} | {emoji} {lvl} |"
        )
    lines.append("")

    # Deep dives
    lines.append("## 🔎 Supplier deep dives")
    lines.append("")

    for s in supplier_list:
        emoji, lvl = risk_level(s.avg_quality, s.issue_count)
        category = supplier_map.get(s.supplier, "—")
        trend = price_trend_percent(s.orders)
        first_last = price_change_first_last_percent(s.orders)

        lines.append(f"### {emoji} {s.supplier} — Risk: {lvl}")
        lines.append("")
        lines.append(f"- **Category**: {category}")
        lines.append(f"- **Total spend**: {_format_eur(s.total_spend_eur)}")
        lines.append(f"- **Average quality**: {s.avg_quality:.2f}/5")
        lines.append(f"- **Average delivery time**: {s.avg_delivery_days:.1f} days")
        lines.append(f"- **Issues noted**: {s.issue_count} (late shipments: {s.late_count}; estimated defective units mentioned: {s.defective_units_estimate})")
        if trend is not None:
            lines.append(f"- **Price trend (first-3 vs last-3 avg unit price)**: {_pct(trend)}")
        else:
            lines.append("- **Price trend**: n/a (insufficient data)")
        if first_last is not None:
            lines.append(f"- **First vs last unit price change**: {_pct(first_last)}")
        lines.append("")

        # Evidence snippets (keep short)
        issue_examples = [r for r in s.orders if detect_issue(r.notes) or detect_late(r.notes)]
        if issue_examples:
            lines.append("#### 🧾 Evidence from order notes")
            lines.append("")
            for r in issue_examples[:4]:
                lines.append(f"- `{r.order_id}` ({r.date.isoformat()}): {r.notes}")
            if len(issue_examples) > 4:
                lines.append(f"- … plus {len(issue_examples) - 4} more note entries.")
            lines.append("")

        # Talking points
        lines.append("#### 🗣️ Negotiation talking points (specific)")
        lines.append("")
        for tp in build_talking_points(s):
            lines.append(f"- {tp}")
        lines.append("")

        # Savings potential (5% on trailing 12 months for this supplier)
        t12_supplier_spend = sum(r.total_eur for r in trailing_12_months(s.orders))
        if t12_supplier_spend > 0:
            lines.append("#### 💰 Savings target")
            lines.append("")
            lines.append(
                f"- Trailing-12-month spend with {s.supplier}: {_format_eur(t12_supplier_spend)} → **5% target: {_format_eur(t12_supplier_spend * 0.05)}**"
            )
            lines.append("")

    lines.append("---")
    lines.append("### Notes on methodology")
    lines.append("")
    lines.append("- **Issues** are inferred from the `notes` column (keywords like *defective*, *DOA*, *scratches*, *returned/replaced*, *quality declining*).")
    lines.append("- **Late shipments** are inferred from `notes` mentions (*late*, *delay*, *customs*).")
    lines.append("- **Price trend** uses first-3 vs last-3 average unit price to avoid overreacting to one-off orders.")
    lines.append("")

    return "\n".join(lines)


# -----------------------------
# Main
# -----------------------------


def main() -> int:
    root = Path(__file__).resolve().parent
    csv_path = root / "data" / "purchase_history.csv"
    company_path = root.parent / "company_context.md"
    output_dir = root / "output"
    _ensure_dir(output_dir)

    print("📦 Loading purchase history…")
    if not csv_path.exists():
        print(f"🔴 CSV not found at: {csv_path}")
        return 2

    rows = load_purchase_history(csv_path)
    print(f"✅ Loaded {len(rows)} purchase rows.")

    print("🏢 Loading company context…")
    supplier_map: Dict[str, str] = {}
    if company_path.exists():
        supplier_map = parse_key_suppliers(_read_text(company_path))
        print(f"✅ Found {len(supplier_map)} suppliers in company context.")
    else:
        print(f"⚠️ Company context not found at: {company_path} (will continue without categories).")

    print("🏭 Aggregating suppliers…")
    suppliers = sorted({r.supplier for r in rows})
    print(f"🏭 Suppliers detected: {', '.join(suppliers)}")

    generated_at = _dt.datetime.now()
    report_md = generate_markdown_report(rows, supplier_map=supplier_map, generated_at=generated_at)

    out_path = output_dir / "supplier_negotiation_brief.md"
    print(f"📝 Writing Markdown report to {out_path.relative_to(root)} …")
    out_path.write_text(report_md, encoding="utf-8")
    print("✅ Saved.")

    # Terminal summary
    t12 = trailing_12_months(rows)
    t12_total = sum(r.total_eur for r in t12)
    savings_target_total = t12_total * 0.05
    print("\n📌 Summary")
    print(f"💰 Trailing-12-month spend: {_format_eur(t12_total)}")
    print(f"🎯 Savings target (5%): {_format_eur(savings_target_total)}")

    # Top 3 by spend with risk
    agg: Dict[str, SupplierStats] = {}
    for r in rows:
        agg.setdefault(r.supplier, SupplierStats(supplier=r.supplier)).orders.append(r)
    top = sorted(agg.values(), key=lambda s: s.total_spend_eur, reverse=True)[:3]
    for s in top:
        emoji, lvl = risk_level(s.avg_quality, s.issue_count)
        print(f"{emoji} {s.supplier}: spend {_format_eur(s.total_spend_eur)} | quality {s.avg_quality:.2f}/5 | issues {s.issue_count} | risk {lvl}")

    print("✅ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

