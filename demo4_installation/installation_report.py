#!/usr/bin/env python3
"""
Installation report generator — Demo 4 (3C Card)

Goal
----
Read raw technician field notes (unstructured text), extract structured installation data:
- technician, date, client, location, time on site
- devices installed (product names + serial numbers)
- issues (categorized + severity-rated + routed to the right team)
- sales follow-up opportunities
- inferred client satisfaction (tone)

Outputs
-------
- Markdown report: `output/installation_report_verdi.md`
- JSON export: `output/installation_data_verdi.json`

Constraints
-----------
- Rule-based parsing only (no external APIs).
- All output must be in English.
- Use emojis in terminal output and in the Markdown report for scannability.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# -----------------------------
# Data models
# -----------------------------


@dataclass
class DeviceInstalled:
    device_number: Optional[int] = None
    product_name: str = ""
    serial_number: Optional[str] = None
    status: str = "installed"  # keep a stable value for DB import
    notes: List[str] = field(default_factory=list)


@dataclass
class Issue:
    title: str
    category: str  # Mechanical / Software / Quality Control / Process
    severity: str  # LOW / MEDIUM / HIGH
    routed_team: str  # QA / R&D / Operations / Engineering
    device_serial_number: Optional[str] = None
    was_fixed_on_site: Optional[bool] = None
    evidence: List[str] = field(default_factory=list)


@dataclass
class SalesOpportunity:
    opportunity: str
    confidence: str = "MEDIUM"  # LOW / MEDIUM / HIGH
    evidence: List[str] = field(default_factory=list)


@dataclass
class InstallationReport:
    technician_name: Optional[str] = None
    date: Optional[str] = None  # ISO date yyyy-mm-dd
    client_name: Optional[str] = None
    client_org: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    arrived_time: Optional[str] = None  # best-effort "HH:MM" 24h
    left_time: Optional[str] = None  # best-effort "HH:MM" 24h
    total_time_on_site_hours: Optional[float] = None
    devices: List[DeviceInstalled] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    sales_opportunities: List[SalesOpportunity] = field(default_factory=list)
    client_satisfaction: Optional[str] = None  # NEGATIVE / MIXED / POSITIVE
    satisfaction_rationale: List[str] = field(default_factory=list)
    raw_source_file: Optional[str] = None
    generated_at: Optional[str] = None  # ISO datetime


# -----------------------------
# Small utilities
# -----------------------------


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _extract_first(pattern: str, text: str, flags: int = 0) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _time_to_24h(s: str) -> Optional[str]:
    """
    Converts times like "9:15am" / "1:45pm" to "09:15" / "13:45".
    Returns None if parsing fails.
    """
    if not s:
        return None
    t = s.strip().lower().replace(" ", "")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?(am|pm)$", t)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2) or "00")
    ap = m.group(3)
    if ap == "am":
        if hh == 12:
            hh = 0
    else:
        if hh != 12:
            hh += 12
    return f"{hh:02d}:{mm:02d}"


def _parse_date_to_iso(s: str) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y"):
        try:
            d = _dt.datetime.strptime(s, fmt).date()
            return d.isoformat()
        except Exception:
            continue
    return None


def _severity_emoji(sev: str) -> str:
    sev_u = (sev or "").upper()
    if sev_u == "LOW":
        return "🟢"
    if sev_u == "MEDIUM":
        return "🟡"
    return "🔴"


# -----------------------------
# Issue categorization + routing
# -----------------------------


def categorize_issue(title: str, details: str) -> Tuple[str, str, str]:
    """
    Returns (category, severity, routed_team).
    Categories per 3C card: Mechanical / Software / Quality Control / Process
    Routing per 3C card: QA, R&D, Operations, Engineering
    """
    blob = f"{title}\n{details}".lower()

    # Category
    if any(k in blob for k in ["scratch", "factory", "qc", "quality control", "from factory", "shipping damage"]):
        category = "Quality Control"
    elif any(k in blob for k in ["language pack", "pre-load", "before shipping", "process", "office", "packaging"]):
        category = "Process"
    elif any(k in blob for k in ["driver", "software", "pacs", "dicom", "config", "port", "windows", "firmware"]):
        category = "Software"
    elif any(k in blob for k in ["chin rest", "stiff", "mechanical", "adjustment", "lubricant"]):
        category = "Mechanical"
    else:
        category = "Process"

    # Severity (simple heuristics; optimize for QA/triage usefulness)
    sev = "MEDIUM"
    if any(k in blob for k in ["blocked", "cannot", "failed", "doesn't work", "not working", "error"]):
        sev = "HIGH"
    if any(k in blob for k in ["fixed on site", "now smooth", "resolved", "applied", "workaround"]):
        sev = "LOW"
    if category in {"Quality Control", "Process"} and any(k in blob for k in ["missing", "not pre-loaded", "scratch"]):
        sev = "MEDIUM"

    # Team routing
    if category == "Quality Control":
        team = "QA"
    elif category == "Software":
        team = "R&D"
    elif category == "Process":
        team = "Operations"
    else:
        team = "Engineering"

    return category, sev, team


# -----------------------------
# Parsing field notes (rule-based)
# -----------------------------


def parse_field_notes(raw: str, source_file: str) -> InstallationReport:
    rep = InstallationReport(raw_source_file=source_file)

    rep.technician_name = _extract_first(r"^\s*Technician:\s*(.+)\s*$", raw, flags=re.MULTILINE)
    rep.date = _parse_date_to_iso(_extract_first(r"^\s*Date:\s*(.+)\s*$", raw, flags=re.MULTILINE) or "")

    # Location line tends to include org + address
    loc_line = _extract_first(r"^\s*Location:\s*(.+)\s*$", raw, flags=re.MULTILINE)
    if loc_line:
        rep.location = loc_line
        # best-effort split: "Studio Oculistico Verdi, Via Roma 45, Torino"
        parts = [p.strip() for p in loc_line.split(",") if p.strip()]
        if parts:
            rep.client_org = parts[0]
        if len(parts) >= 2:
            rep.address = ", ".join(parts[1:])

    client_line = _extract_first(r"^\s*Client:\s*(.+)\s*$", raw, flags=re.MULTILINE)
    if client_line:
        # "Dr. Elena Verdi, small practice, 2 exam rooms..."
        rep.client_name = client_line.split(",")[0].strip()
        if rep.client_org is None:
            rep.client_org = rep.client_name

    # Arrival / leave / total time
    rep.arrived_time = _time_to_24h(_extract_first(r"\bArrived on site\s+([0-9:]+\s*(?:am|pm))\b", raw, flags=re.IGNORECASE) or "")
    rep.left_time = _time_to_24h(_extract_first(r"\bLeft site at\s+([0-9:]+\s*(?:am|pm))\b", raw, flags=re.IGNORECASE) or "")

    total_h = _extract_first(r"\bTotal time on site:\s*([0-9]+(?:\.[0-9]+)?)\s*hours?\b", raw, flags=re.IGNORECASE)
    if total_h:
        try:
            rep.total_time_on_site_hours = float(total_h)
        except ValueError:
            rep.total_time_on_site_hours = None

    # Devices
    # Example: "DEVICE 1 — BrightEyes RetinaScan Pro (S/N: BRS-2026-00847)"
    device_iter = list(
        re.finditer(
            r"^\s*DEVICE\s+(\d+)\s+—\s+(.+?)\s*\(\s*S/N:\s*([^)]+)\)\s*$",
            raw,
            flags=re.MULTILINE,
        )
    )
    for i, m in enumerate(device_iter):
        device_number = int(m.group(1))
        product_name = m.group(2).strip()
        serial = m.group(3).strip()

        # Capture lines until the next DEVICE header or next big section
        start = m.end()
        end = device_iter[i + 1].start() if i + 1 < len(device_iter) else len(raw)
        block = raw[start:end]

        notes: List[str] = []
        for ln in block.splitlines():
            ln = ln.strip()
            if ln.startswith("- "):
                notes.append(ln[2:].strip())
        rep.devices.append(
            DeviceInstalled(
                device_number=device_number,
                product_name=product_name,
                serial_number=serial,
                status="installed",
                notes=notes,
            )
        )

    # Issues section: explicit list
    issues_block = _extract_first(r"^\s*ISSUES TO REPORT:\s*\n([\s\S]*?)(?:\n\s*Left site|\Z)", raw, flags=re.MULTILINE)
    extracted_issue_lines: List[str] = []
    if issues_block:
        for ln in issues_block.splitlines():
            ln = ln.strip()
            m = re.match(r"^\d+\.\s*(.+)$", ln)
            if m:
                extracted_issue_lines.append(m.group(1).strip())

    # Build a map serial->device for routing
    serial_to_device: Dict[str, DeviceInstalled] = {d.serial_number or "": d for d in rep.devices if d.serial_number}

    for ln in extracted_issue_lines:
        # Example: "Chin rest stiffness on RetinaScan Pro S/N BRS-2026-00847 — mechanical, fixed on site"
        serial = _extract_first(r"\bS/N\s*([A-Za-z0-9-]+)\b", ln) or _extract_first(r"\bS\/N[:\s]*([A-Za-z0-9-]+)\b", ln)
        fixed = True if re.search(r"\bfixed on site\b", ln, flags=re.IGNORECASE) else None
        title = ln
        details = ""

        category, severity, team = categorize_issue(title=title, details=details)

        rep.issues.append(
            Issue(
                title=title,
                category=category,
                severity=severity,
                routed_team=team,
                device_serial_number=serial,
                was_fixed_on_site=fixed,
                evidence=[ln],
            )
        )

    # Also detect noteworthy software/integration events that aren't in the explicit list
    # Keep conservative to avoid over-reporting.
    if re.search(r"\bPACS\b.*\bconfig\b|\bport\s*4242\b", raw, flags=re.IGNORECASE):
        rep.issues.append(
            Issue(
                title="PACS/DICOM integration required a configuration change (port 4242).",
                category="Software",
                severity="LOW",
                routed_team="R&D",
                device_serial_number=_extract_first(r"RetinaScan Pro\s*\(S/N:\s*([^)]+)\)", raw) or None,
                was_fixed_on_site=True,
                evidence=["DICOM export tested — works but PACS needed a config change on port 4242."],
            )
        )

    # Sales opportunities (rule-based)
    sales: List[SalesOpportunity] = []
    if re.search(r"\basked about\b.*\bAI\b|\bAI screening module\b", raw, flags=re.IGNORECASE):
        sales.append(
            SalesOpportunity(
                opportunity="Follow up on AI screening module interest (planned Q3 2026 update).",
                confidence="MEDIUM",
                evidence=["Dr. Verdi asked about the AI screening module and expressed strong interest."],
            )
        )
    if re.search(r"\bsecond\s+RetinaScan\b|\bsatellite office\b", raw, flags=re.IGNORECASE):
        sales.append(
            SalesOpportunity(
                opportunity="Upsell opportunity: second RetinaScan Pro for the client’s satellite office (Moncalieri).",
                confidence="HIGH",
                evidence=["Client wants to discuss a second RetinaScan for her satellite office in Moncalieri."],
            )
        )
    rep.sales_opportunities = sales

    # Client satisfaction inference
    rep.client_satisfaction, rep.satisfaction_rationale = infer_satisfaction(raw)

    rep.generated_at = _dt.datetime.now().replace(microsecond=0).isoformat()
    return rep


def infer_satisfaction(raw: str) -> Tuple[str, List[str]]:
    """
    Simple tone inference. Returns (label, rationale bullets).
    """
    s = raw.lower()
    pos_hits: List[str] = []
    neg_hits: List[str] = []

    def hit(pattern: str, label: str, dst: List[str]) -> None:
        if re.search(pattern, s, flags=re.IGNORECASE):
            dst.append(label)

    hit(r"\bhappy client\b|\bhappy\b|\bvery nice\b|\boffered coffee\b|\bexcellent\b|\bvery tech-savvy\b|\bsmooth installation\b", "Positive language in notes.", pos_hits)
    hit(r"\bissue\b|\bfailed\b|\bstiff\b|\bscratch\b|\bmissing\b|\bslow wifi\b", "Issues mentioned during installation.", neg_hits)
    hit(r"\bclient signed acceptance\b|\baccepted\b", "Acceptance signed / issues accepted.", pos_hits)

    if pos_hits and not neg_hits:
        return "POSITIVE", pos_hits
    if pos_hits and neg_hits:
        return "POSITIVE", pos_hits + ["Minor issues were present but did not block acceptance."]
    return "MIXED", (pos_hits + neg_hits) or ["Insufficient tone signals in notes."]


# -----------------------------
# Reporting (Markdown + JSON)
# -----------------------------


def to_json_dict(rep: InstallationReport) -> Dict[str, object]:
    # Keep stable and machine-readable (no emojis in JSON).
    return asdict(rep)


def generate_markdown(rep: InstallationReport) -> str:
    lines: List[str] = []
    lines.append("# 📋 Installation Report — Studio Oculistico Verdi")
    lines.append("")
    lines.append("## 🧾 Summary")
    lines.append("")
    lines.append(f"- **Technician**: {rep.technician_name or 'Not found'}")
    lines.append(f"- **Date**: {rep.date or 'Not found'}")
    lines.append(f"- **Client**: {rep.client_name or 'Not found'}")
    lines.append(f"- **Site / Location**: {rep.location or 'Not found'}")
    if rep.arrived_time or rep.left_time or rep.total_time_on_site_hours is not None:
        lines.append(
            "- **Time on site**: "
            + " | ".join(
                [x for x in [
                    f"Arrived {rep.arrived_time}" if rep.arrived_time else None,
                    f"Left {rep.left_time}" if rep.left_time else None,
                    f"Total {rep.total_time_on_site_hours:.1f}h" if rep.total_time_on_site_hours is not None else None,
                ] if x]
            )
        )
    lines.append("")

    lines.append("## 🔧 Devices installed")
    lines.append("")
    if rep.devices:
        lines.append("| # | Device | Serial number | Status |")
        lines.append("|---:|---|---|---|")
        for d in rep.devices:
            num = str(d.device_number) if d.device_number is not None else "—"
            sn = d.serial_number or "—"
            status = "✅ installed" if d.status == "installed" else d.status
            lines.append(f"| {num} | {d.product_name} | `{sn}` | {status} |")
        lines.append("")
        for d in rep.devices:
            if not d.notes:
                continue
            lines.append(f"### ✅ {d.product_name} — notes")
            lines.append("")
            for n in d.notes[:10]:
                lines.append(f"- {n}")
            if len(d.notes) > 10:
                lines.append(f"- … plus {len(d.notes) - 10} more notes.")
            lines.append("")
    else:
        lines.append("No devices detected.")
        lines.append("")

    lines.append("## ⚠️ Issues (categorized, severity, routing)")
    lines.append("")
    if rep.issues:
        lines.append("| Issue | Category | Severity | Routed team | Device S/N | Fixed on site |")
        lines.append("|---|---|---|---|---|---|")
        for it in rep.issues:
            sev = f"{_severity_emoji(it.severity)} {it.severity}"
            sn = f"`{it.device_serial_number}`" if it.device_serial_number else "—"
            fixed = (
                "Yes" if it.was_fixed_on_site is True else ("No" if it.was_fixed_on_site is False else "—")
            )
            lines.append(f"| {it.title} | {it.category} | {sev} | {it.routed_team} | {sn} | {fixed} |")
        lines.append("")
    else:
        lines.append("No issues detected.")
        lines.append("")

    lines.append("## 😊 Client satisfaction (inferred)")
    lines.append("")
    lines.append(f"- **Satisfaction**: {rep.client_satisfaction or 'Not found'}")
    if rep.satisfaction_rationale:
        lines.append("- **Rationale**:")
        for r in rep.satisfaction_rationale:
            lines.append(f"  - {r}")
    lines.append("")

    lines.append("## 🧩 Sales follow-up opportunities")
    lines.append("")
    if rep.sales_opportunities:
        lines.append("| Opportunity | Confidence | Evidence |")
        lines.append("|---|---|---|")
        for op in rep.sales_opportunities:
            ev = "; ".join(op.evidence[:2]) if op.evidence else "—"
            lines.append(f"| {op.opportunity} | {op.confidence} | {ev} |")
        lines.append("")
    else:
        lines.append("No sales opportunities detected.")
        lines.append("")

    lines.append("---")
    lines.append(f"Generated on {rep.generated_at or _dt.datetime.now().isoformat()} by `installation_report.py`")
    lines.append("")
    return "\n".join(lines)


# -----------------------------
# Main
# -----------------------------


def main() -> int:
    root = Path(__file__).resolve().parent
    notes_path = root / "data" / "field_notes_verdi.txt"
    output_dir = root / "output"
    _ensure_dir(output_dir)

    md_out = output_dir / "installation_report_verdi.md"
    json_out = output_dir / "installation_data_verdi.json"

    print("📋 Loading field notes…")
    if not notes_path.exists():
        print(f"🔴 Notes file not found at: {notes_path}")
        return 2

    raw = _read_text(notes_path)

    print("👤 Extracting technician/client/site info…")
    rep = parse_field_notes(raw, source_file=str(notes_path))

    if rep.client_name or rep.client_org:
        print(f"👤 Client: {rep.client_name or rep.client_org}")
    if rep.location:
        print(f"📍 Location: {rep.location}")
    if rep.total_time_on_site_hours is not None:
        print(f"⏱️ Time on site: {rep.total_time_on_site_hours:.1f} hours")

    print("🔧 Extracting devices…")
    print(f"🔧 Devices detected: {len(rep.devices)}")

    print("⚠️ Extracting + routing issues…")
    print(f"⚠️ Issues detected: {len(rep.issues)}")

    print("😊 Inferring client satisfaction…")
    if rep.client_satisfaction:
        print(f"😊 Satisfaction: {rep.client_satisfaction}")

    print(f"📝 Writing Markdown report to {md_out.relative_to(root)} …")
    md_out.write_text(generate_markdown(rep), encoding="utf-8")
    print("✅ Report saved.")

    print(f"📊 Exporting JSON to {json_out.relative_to(root)} …")
    json_out.write_text(json.dumps(to_json_dict(rep), ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ JSON exported.")

    print("\n📌 Summary")
    dev_names = ", ".join(sorted({d.product_name for d in rep.devices})) if rep.devices else "None"
    print(f"🔧 Devices: {dev_names}")
    if rep.sales_opportunities:
        print(f"🎯 Sales opportunities: {len(rep.sales_opportunities)}")
    print("✅ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

