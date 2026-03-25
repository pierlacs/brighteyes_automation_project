#!/usr/bin/env python3
"""
Customer proposal generator — Demo 2 (3C Card)

Goal
-----
Read messy sales call notes (Markdown) plus the BrightEyes company context (Markdown),
extract client needs (products, budget, timeline, requests), match to our product catalog,
apply bundle discounts, compute a 36-month leasing estimate, and generate a polished
commercial proposal as Markdown in `output/`.

Constraints
-----------
- Rule-based parsing only (no external APIs).
- All output in English.
- Use emojis in terminal output for scannability.
- All prices in EUR.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# -----------------------------
# Data models (simple + explicit)
# -----------------------------


@dataclass
class Product:
    name: str
    list_price_eur: Optional[int] = None
    specs: Dict[str, str] = field(default_factory=dict)


@dataclass
class CompanyProfile:
    name: str = "BrightEyes"
    products: Dict[str, Product] = field(default_factory=dict)


@dataclass
class ClientInfo:
    contact_name: Optional[str] = None
    clinic_name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    clinic_size: Optional[str] = None
    weekly_patients: Optional[int] = None


@dataclass
class Request:
    key: str
    value: str


@dataclass
class LineItem:
    product: Product
    quantity: int = 1
    is_optional: bool = False
    notes: List[str] = field(default_factory=list)

    @property
    def total_list_price_eur(self) -> int:
        unit = int(self.product.list_price_eur or 0)
        return unit * int(self.quantity)


@dataclass
class ProposalInputs:
    client: ClientInfo
    items: List[LineItem]
    budget_eur: Optional[int] = None
    deadline_text: Optional[str] = None
    sentiment: Optional[str] = None
    requests: List[Request] = field(default_factory=list)
    throughput_context: Optional[str] = None
    reference_clinic_suggestion: Optional[str] = None


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


def _format_eur(amount: float) -> str:
    return f"€{amount:,.0f}"


def _slugify_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "proposal"


def _parse_company_context(md_text: str) -> CompanyProfile:
    """
    Reuses the same simple product extraction strategy as Demo 1:
    - "### Product name" blocks with bullets and a "**List price: €xx,xxx**" line.
    """
    company = CompanyProfile()
    blocks = re.split(r"\n###\s+", md_text)
    for block in blocks[1:]:
        lines = block.splitlines()
        name = lines[0].strip()
        body = "\n".join(lines[1:])

        price_s = _extract_first(r"\*\*List price:\s*€\s*([0-9,]+)\*\*", body)
        price: Optional[int] = None
        if price_s:
            try:
                price = int(price_s.replace(",", ""))
            except ValueError:
                price = None

        specs: Dict[str, str] = {}
        for ln in body.splitlines():
            ln = ln.strip()
            if not ln.startswith("- "):
                continue
            bullet = ln[2:].strip()
            if bullet.lower().startswith("**list price"):
                # Avoid echoing the list price inside "specs" bullets.
                continue
            if ":" in bullet:
                k, v = bullet.split(":", 1)
                specs[k.strip()] = v.strip()
            else:
                specs[bullet] = "yes"

        company.products[name] = Product(name=name, list_price_eur=price, specs=specs)
    return company


# -----------------------------
# Parsing call notes (rule-based)
# -----------------------------


def _money_to_int_eur(text: str) -> Optional[int]:
    """
    Best-effort parse of budget strings like:
    - "around 150k"
    - "€150,000"
    """
    if not text:
        return None
    s = text.lower().replace(",", "").replace("€", "").replace("eur", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*k\b", s)
    if m:
        try:
            return int(float(m.group(1)) * 1000)
        except ValueError:
            return None
    m2 = re.search(r"\b(\d{2,6})\b", s)
    if m2:
        try:
            return int(m2.group(1))
        except ValueError:
            return None
    return None


def parse_call_notes(md_text: str, company: CompanyProfile) -> ProposalInputs:
    client = ClientInfo()

    # Header lines
    client.contact_name = _extract_first(r"\*\*Client:\*\*\s*([^,]+)", md_text)
    client.clinic_name = _extract_first(r"\*\*Client:\*\*\s*[^,]+,\s*([^\n]+)", md_text)
    if client.clinic_name and "milano" in client.clinic_name.lower():
        client.city = "Milan"
        client.country = "Italy"

    # Clinic size and volume
    size = _extract_first(r"clinic.*?with\s+([^\n.]+)\.", md_text, flags=re.IGNORECASE)
    if size:
        client.clinic_size = size
    pts = _extract_first(r"see around\s+(\d+)\s+patients/week", md_text, flags=re.IGNORECASE)
    if pts and pts.isdigit():
        client.weekly_patients = int(pts)

    # Budget + timeline
    budget_line = _extract_first(r"Budget:\s*([^\n]+)", md_text, flags=re.IGNORECASE)
    budget_eur = _money_to_int_eur(budget_line or "")

    timeline_line = _extract_first(r"Timeline:\s*([^\n]+)", md_text, flags=re.IGNORECASE)
    deadline_text = timeline_line

    # Products of interest (keep it robust to "retinograph"/"retinal camera")
    interest_block = _extract_first(r"He's interested in:\s*\n([\s\S]*?)\n\s*Budget:", md_text, flags=re.IGNORECASE)
    interest_lines: List[str] = []
    if interest_block:
        for ln in interest_block.splitlines():
            ln = ln.strip()
            if ln.startswith("- "):
                interest_lines.append(ln[2:].strip())

    def pick_product(keyword: str) -> Optional[Product]:
        for name, p in company.products.items():
            if keyword.lower() in name.lower():
                return p
        return None

    retina = pick_product("retinascan") or pick_product("retina")
    octp = pick_product("oct")
    autoref = pick_product("autoref")

    items: List[LineItem] = []
    for ln in interest_lines:
        ln_l = ln.lower()
        if "retinograph" in ln_l or "retinograph" in ln_l or "retinal" in ln_l:
            if retina:
                item = LineItem(product=retina, quantity=1)
                if "autofocus" in ln_l:
                    item.notes.append("Autofocus requested (highlighted in configuration and training).")
                items.append(item)
        elif "oct" in ln_l:
            if octp:
                item = LineItem(product=octp, quantity=1)
                if "ai" in ln_l or "layer" in ln_l:
                    item.notes.append("Client asked specifically about AI-assisted retinal layer analysis (beta).")
                items.append(item)
        elif "autorefractor" in ln_l or "autorefractors" in ln_l or "refractor" in ln_l:
            if autoref:
                qty = 1
                mqty = re.search(r"\b(\d+)\b", ln_l)
                if mqty:
                    try:
                        qty = int(mqty.group(1))
                    except ValueError:
                        qty = 1
                # Treat "maybe" as optional
                optional = "maybe" in ln_l
                items.append(LineItem(product=autoref, quantity=qty, is_optional=optional))

    # Special requests
    requests: List[Request] = []
    if re.search(r"training.*italian", md_text, flags=re.IGNORECASE):
        requests.append(Request(key="Training language", value="Italian (on-site, hands-on)."))
    integration = _extract_first(r"Integration with their software\s*\(([^)]+)\)", md_text, flags=re.IGNORECASE)
    if integration:
        requests.append(Request(key="Integration", value=f"Client software mentioned: {integration} (to be confirmed)."))
    if re.search(r"prefer leasing|leasing", md_text, flags=re.IGNORECASE):
        requests.append(Request(key="Financing preference", value="Leasing preferred over outright purchase."))
    warranty = _extract_first(r"Warranty:\s*([^\n]+)", md_text, flags=re.IGNORECASE)
    if warranty:
        requests.append(Request(key="Warranty expectation", value=warranty))

    # Sentiment / vibe
    vibe = _extract_first(r"Vibe:\s*([^\n]+)", md_text, flags=re.IGNORECASE)
    sentiment = "Very positive" if vibe and "positive" in vibe.lower() else (vibe or None)

    # Throughput comparison: build from context present in notes
    throughput_context = (
        "Current OCT is described as slow, contributing to patient waiting times. "
        "Proposal will emphasize faster OCT scanning and streamlined workflow to increase patient throughput."
    )

    # Reference clinic suggestion
    ref = _extract_first(r"suggest\s+([^.?\n]+)", md_text, flags=re.IGNORECASE)
    reference_clinic_suggestion = ref.strip() if ref else "Clinica Bianchi (Turin) — suggested reference visit"

    return ProposalInputs(
        client=client,
        items=items,
        budget_eur=budget_eur,
        deadline_text=deadline_text,
        sentiment=sentiment,
        requests=requests,
        throughput_context=throughput_context,
        reference_clinic_suggestion=reference_clinic_suggestion,
    )


# -----------------------------
# Pricing, discounts, leasing
# -----------------------------


def bundle_discount_rate(distinct_products_count: int) -> float:
    if distinct_products_count >= 3:
        return 0.08
    if distinct_products_count == 2:
        return 0.05
    return 0.0


def compute_totals(items: List[LineItem]) -> Tuple[int, float, int]:
    """
    Returns: (subtotal_list_eur, discount_rate, total_after_discount_eur)
    Discount is based on distinct products included (not optional items).
    """
    included = [it for it in items if not it.is_optional]
    subtotal = sum(it.total_list_price_eur for it in included)
    distinct = len({it.product.name for it in included})
    rate = bundle_discount_rate(distinct)
    total = int(round(subtotal * (1.0 - rate)))
    return subtotal, rate, total


def estimate_monthly_lease_payment(principal_eur: int, months: int = 36, apr: float = 0.06) -> float:
    """
    Standard amortized payment estimate:
      r = APR/12
      payment = P * r / (1 - (1+r)^-n)
    This is only an estimate; actual leasing terms depend on financier, credit, and fees.
    """
    if principal_eur <= 0:
        return 0.0
    r = apr / 12.0
    n = float(months)
    if r <= 0:
        return principal_eur / n
    return principal_eur * (r / (1.0 - (1.0 + r) ** (-n)))


# -----------------------------
# Proposal Markdown generation
# -----------------------------


def _product_specs_bullets(p: Product, max_items: int = 7) -> List[str]:
    """
    Formats a small, client-friendly spec list from the catalog keys/values.
    """
    bullets: List[str] = []
    for k, v in p.specs.items():
        if len(bullets) >= max_items:
            break
        if v == "yes":
            bullets.append(k)
        else:
            bullets.append(f"{k}: {v}")
    return bullets


def generate_proposal_markdown(
    company: CompanyProfile,
    inputs: ProposalInputs,
    generated_at: _dt.datetime,
) -> str:
    client = inputs.client
    clinic_name = client.clinic_name or "Client"
    contact = client.contact_name or "Client Contact"

    included_items = [it for it in inputs.items if not it.is_optional]
    optional_items = [it for it in inputs.items if it.is_optional]

    subtotal, discount_rate, total = compute_totals(inputs.items)
    monthly = estimate_monthly_lease_payment(total, months=36, apr=0.06)

    # Alternative: include optional items as a second scenario (if any)
    total_with_optional: Optional[int] = None
    monthly_with_optional: Optional[float] = None
    discount_rate_with_optional: Optional[float] = None
    subtotal_with_optional: Optional[int] = None
    if optional_items:
        all_items = included_items + optional_items
        subtotal_with_optional = sum(it.total_list_price_eur for it in all_items)
        distinct_all = len({it.product.name for it in all_items})
        discount_rate_with_optional = bundle_discount_rate(distinct_all)
        total_with_optional = int(round(subtotal_with_optional * (1.0 - discount_rate_with_optional)))
        monthly_with_optional = estimate_monthly_lease_payment(total_with_optional, months=36, apr=0.06)

    lines: List[str] = []
    lines.append(f"# 📄 Commercial Proposal — {clinic_name}")
    lines.append("")
    lines.append(f"**Prepared for:** {contact} — {clinic_name}")
    if client.city or client.country:
        loc = ", ".join([x for x in [client.city, client.country] if x])
        lines.append(f"**Location:** {loc}")
    lines.append(f"**Prepared by:** {company.name}")
    lines.append(f"**Date:** {generated_at.strftime('%d %B %Y')}")
    lines.append("")

    lines.append("## 🧾 Executive Summary")
    lines.append("")
    lines.append(
        "Thank you for your time. Based on our conversation, we propose a modern diagnostic bundle that improves patient flow by reducing imaging time, streamlining data export, and enabling consistent, high-quality acquisition."
    )
    if inputs.sentiment:
        lines.append(f"- **Call sentiment:** {inputs.sentiment}")
    if inputs.budget_eur:
        lines.append(f"- **Indicative budget discussed:** {_format_eur(inputs.budget_eur)} (flexible with ROI justification)")
    if inputs.deadline_text:
        lines.append(f"- **Target timeline:** {inputs.deadline_text}")
    lines.append("")

    lines.append("## 👤 Client Snapshot (from call notes)")
    lines.append("")
    if client.clinic_size:
        lines.append(f"- **Clinic profile:** Private ophthalmology clinic; {client.clinic_size}")
    if client.weekly_patients is not None:
        lines.append(f"- **Patient volume:** ~{client.weekly_patients} patients/week")
    lines.append("- **Current situation:** Aging retinal camera and a slower OCT leading to longer patient waiting times.")
    lines.append("")

    lines.append("## 🎯 Objectives & Special Requests")
    lines.append("")
    lines.append("- **Primary objective:** Improve throughput and reduce patient waiting times (especially for OCT exams).")
    if inputs.requests:
        for r in inputs.requests:
            lines.append(f"- **{r.key}:** {r.value}")
    lines.append("")

    lines.append("## 📦 Proposed Configuration")
    lines.append("")
    if included_items:
        for it in included_items:
            lines.append(f"### ✅ {it.product.name} (x{it.quantity})")
            lines.append("")
            if it.product.list_price_eur:
                lines.append(f"- **List price (unit):** {_format_eur(it.product.list_price_eur)}")
            bullets = _product_specs_bullets(it.product)
            if bullets:
                lines.append("- **Key specifications:**")
                for b in bullets:
                    lines.append(f"  - {b}")
            if it.notes:
                lines.append("- **Notes for your clinic:**")
                for n in it.notes:
                    lines.append(f"  - {n}")
            lines.append("")
    else:
        lines.append("No products were detected in the call notes. Please confirm the requested configuration.")
        lines.append("")

    if optional_items:
        lines.append("### ➕ Optional items")
        lines.append("")
        for it in optional_items:
            lines.append(f"- **{it.product.name} (x{it.quantity})** — optional based on final budget and workflow design")
        lines.append("")

    lines.append("## 💰 Pricing (EUR)")
    lines.append("")
    lines.append("All prices are in **EUR** and exclude VAT (if applicable).")
    lines.append("")

    # Scenario A (base)
    lines.append("### Scenario A — Core bundle")
    lines.append("")
    lines.append("| Item | Qty | Unit price | Line total |")
    lines.append("|---|---:|---:|---:|")
    for it in included_items:
        unit = int(it.product.list_price_eur or 0)
        lines.append(f"| {it.product.name} | {it.quantity} | {_format_eur(unit)} | {_format_eur(it.total_list_price_eur)} |")
    lines.append(f"| **Subtotal (list)** |  |  | **{_format_eur(subtotal)}** |")
    if discount_rate > 0:
        lines.append(f"| **Bundle discount** |  |  | **-{discount_rate*100:.0f}%** |")
    lines.append(f"| **Total (after discount)** |  |  | **{_format_eur(total)}** |")
    lines.append("")

    # Scenario B (optional)
    if optional_items and total_with_optional is not None and subtotal_with_optional is not None and discount_rate_with_optional is not None:
        lines.append("### Scenario B — Full bundle (including optional items)")
        lines.append("")
        lines.append("| Item | Qty | Unit price | Line total |")
        lines.append("|---|---:|---:|---:|")
        for it in included_items + optional_items:
            unit = int(it.product.list_price_eur or 0)
            lines.append(f"| {it.product.name} | {it.quantity} | {_format_eur(unit)} | {_format_eur(it.total_list_price_eur)} |")
        lines.append(f"| **Subtotal (list)** |  |  | **{_format_eur(subtotal_with_optional)}** |")
        if discount_rate_with_optional > 0:
            lines.append(f"| **Bundle discount** |  |  | **-{discount_rate_with_optional*100:.0f}%** |")
        lines.append(f"| **Total (after discount)** |  |  | **{_format_eur(total_with_optional)}** |")
        lines.append("")

    lines.append("## 🧾 Financing Options (Leasing)")
    lines.append("")
    lines.append(
        "Below is an **estimate** for a 36-month leasing-style payment schedule (subject to financier approval; excludes fees and VAT)."
    )
    lines.append("")
    lines.append(f"- **Scenario A — 36 months (est.)**: ~{_format_eur(monthly)}/month (assumes ~6% APR equivalent)")
    if optional_items and monthly_with_optional is not None:
        lines.append(
            f"- **Scenario B — 36 months (est.)**: ~{_format_eur(monthly_with_optional)}/month (assumes ~6% APR equivalent)"
        )
    lines.append("")

    lines.append("## 🗓️ Implementation Timeline (targeting before September)")
    lines.append("")
    lines.append("- **Week 0:** Purchase order / leasing approval + final configuration confirmation")
    lines.append("- **Weeks 1–6:** Production allocation + logistics planning + integration scoping call")
    lines.append("- **Weeks 6–8:** Delivery to clinic, on-site installation, and acceptance testing")
    lines.append("- **Week 8:** On-site training in **Italian** for doctors and optometrists (hands-on workflows)")
    lines.append("- **Go-live:** Immediately after training, with remote follow-up session in the first 2 weeks")
    lines.append("")

    lines.append("## 🛡️ Warranty & Support")
    lines.append("")
    lines.append("- **Warranty:** 36 months (meets the requested minimum of 3 years).")
    lines.append("- **Support:** Remote first-response + on-site intervention scheduling as needed.")
    lines.append("- **Preventive maintenance:** Annual check recommended; can be included as a service add-on.")
    lines.append("")

    lines.append("## 📈 Expected Throughput Impact (qualitative)")
    lines.append("")
    lines.append(inputs.throughput_context or "We expect measurable reductions in exam time and waiting time based on faster capture and smoother workflow.")
    lines.append("")
    lines.append("We can include a short appendix comparing:")
    lines.append("- Current workflow duration (your current OCT and retinal camera)")
    lines.append("- Proposed workflow duration (BrightEyes devices)")
    lines.append("- Impact on daily capacity and estimated ROI")
    lines.append("")

    lines.append("## ✅ Next Steps")
    lines.append("")
    lines.append("- Confirm final configuration (including whether to include the optional autorefractors).")
    lines.append("- Share the clinic software name/version for integration validation (DICOM export / interoperability checks).")
    lines.append("- Schedule a **reference visit**: " + (inputs.reference_clinic_suggestion or "a nearby reference clinic installation") + ".")
    lines.append("- Align on commercial terms and initiate leasing approval if preferred.")
    lines.append("")

    lines.append("---")
    lines.append("**Validity:** 30 days from the date of this proposal.")
    lines.append(f"Generated on {generated_at.strftime('%Y-%m-%d %H:%M')} by `proposal_generator.py`")
    lines.append("")

    return "\n".join(lines)


# -----------------------------
# Main entrypoint
# -----------------------------


def main() -> int:
    root = Path(__file__).resolve().parent
    notes_path = root / "data" / "call_notes_rossi.md"
    company_path = root.parent / "company_context.md"
    output_dir = root / "output"
    _ensure_dir(output_dir)

    print("📝 Loading call notes…")
    if not notes_path.exists():
        print(f"🔴 Notes file not found at: {notes_path}")
        return 2
    print("🏢 Loading company context…")
    if not company_path.exists():
        print(f"🔴 Company context file not found at: {company_path}")
        return 2

    notes_md = _read_text(notes_path)
    company_md = _read_text(company_path)

    print("📦 Building product catalog…")
    company = _parse_company_context(company_md)
    print("👤 Parsing client info and needs…")
    inputs = parse_call_notes(notes_md, company)

    clinic_name = inputs.client.clinic_name or "Client"
    print(f"👤 Client: {inputs.client.contact_name or 'Unknown'} — {clinic_name}")
    if inputs.budget_eur:
        print(f"💰 Budget (heard): {_format_eur(inputs.budget_eur)}")
    if inputs.deadline_text:
        print(f"📅 Timeline: {inputs.deadline_text}")
    if inputs.items:
        print(f"📦 Products detected: {', '.join(sorted({it.product.name for it in inputs.items}))}")

    generated_at = _dt.datetime.now()
    proposal_md = generate_proposal_markdown(company, inputs, generated_at=generated_at)

    out_name = _slugify_filename(f"proposal_{clinic_name}") + ".md"
    out_path = output_dir / out_name

    print(f"✅ Saving proposal to {out_path.relative_to(root)} …")
    out_path.write_text(proposal_md, encoding="utf-8")
    print("✅ Saved.")

    # Ensure exact required output name as per 3C card
    required_name = "proposal_Clinica_Oculistica_Milano.md"
    required_path = output_dir / required_name
    if required_path.name != out_path.name:
        required_path.write_text(proposal_md, encoding="utf-8")

    print("\n📌 Summary")
    included_items = [it for it in inputs.items if not it.is_optional]
    subtotal, rate, total = compute_totals(inputs.items)
    print(f"📦 Core items: {len(included_items)} | Discount: {rate*100:.0f}% | Total: {_format_eur(total)}")
    print("✅ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

