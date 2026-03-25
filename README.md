# BrightEyes — Enterprise AI Demos
## Group E: Unlocking Enterprise AI — Final Project

### The Story
Your team has been hired by **BrightEyes**, a Paris-based startup selling ophthalmic diagnostic devices (retinal cameras, OCTs, autorefractors) to hospitals and clinics across Europe.

You are running a **sharing session** for BrightEyes staff to show them how AI can transform their daily workflows — from sales to procurement to operations to the CEO's Monday morning meeting.

---

## 5 Demos — One Per Team Member

| # | Demo | Role it helps | Input → Output |
|---|------|--------------|----------------|
| 1 | **Tender Parser** | Sales / BD | Tender PDF → Eligibility check + response strategy |
| 2 | **Proposal Generator** | Sales Rep | Messy call notes → Polished client proposal |
| 3 | **Supplier Negotiation Prep** | Procurement | Purchase history CSV → Negotiation brief with scorecards |
| 4 | **Installation Report** | Field Technician / QA | Raw field notes → Structured report + JSON export |
| 5 | **WBR Dashboard** | CEO | Weekly metrics CSV → Executive summary with alerts |

---

## How to Run Each Demo

Each demo is a standalone Python script. No external APIs needed. No pip installs required (uses only Python standard library).

```bash
# Demo 1 — Tender Parser
python3 demo1_tender/tender_parser.py

# Demo 2 — Proposal Generator
python3 demo2_proposal/proposal_generator.py

# Demo 3 — Supplier Negotiation Prep
python3 demo3_supplier/supplier_analysis.py

# Demo 4 — Installation Report
python3 demo4_installation/installation_report.py

# Demo 5 — WBR Dashboard
python3 demo5_wbr/wbr_generator.py
```

Each script reads from its `data/` folder and outputs to its `output/` folder.

---

## Bingo Card Coverage

Below is which bingo squares each demo naturally hits when built in Cursor:

| Bingo Task | Demo 1 | Demo 2 | Demo 3 | Demo 4 | Demo 5 |
|-----------|--------|--------|--------|--------|--------|
| Run code in the terminal | ✅ | ✅ | ✅ | ✅ | ✅ |
| Use a 3C card to build a task | ✅ | ✅ | ✅ | ✅ | ✅ |
| Use a CER card to debug a task | ✅ | ✅ | ✅ | ✅ | ✅ |
| Extract structured data from unstructured doc | ✅ | ✅ | | ✅ | |
| Read / export an excel file | | | ✅ | | ✅ |
| Inspect a CSV / JSON file and summarize patterns | | | ✅ | ✅ | ✅ |
| Read and export .docx file | ✅ | ✅ | | | |
| Generate a README from existing files | ✅ (this file) | | | | |
| Turn rough notes into clean Markdown | | | | ✅ | |
| Use browser / visual checks to verify output | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manually edit a .mdc rules file | once | | | | |
| Update a .mdc rules file from a prompt | once | | | | |
| Use comment-oriented programming | ✅ | ✅ | ✅ | ✅ | ✅ |
| Use @file to give a file as context | ✅ | ✅ | ✅ | ✅ | ✅ |
| Use @folder to provide folder as context | ✅ | | | | |
| Use objective-oriented programming | | | ✅ | | ✅ |
| Ask Cursor to explain an unfamiliar code file | any | any | any | any | any |
| Ask Cursor to summarize a folder / codebase | ✅ | | | | |
| Perform a data analytics or data science workflow | | | ✅ | | ✅ |
| Use Cursor Plan mode | any | any | any | any | any |

**Total achievable: 20-22 out of 25** (the 4 red tasks — Open WebUI, Ollama, GitHub, Google Slide export — are optional stretch goals)

---

## Presentation Structure (10 minutes)

| Time | Section | Who |
|------|---------|-----|
| 0:00–1:30 | **Intro**: "We're hired by BrightEyes. Here's the company, here's the problem: every role wastes hours on manual work that AI can automate." | Team lead |
| 1:30–3:00 | **Demo 1**: Tender Parser — drop a tender doc, get a go/no-go in seconds | Person 1 |
| 3:00–4:30 | **Demo 2**: Proposal Generator — call notes in, polished proposal out | Person 2 |
| 4:30–6:00 | **Demo 3**: Supplier Analysis — CSV in, negotiation brief out | Person 3 |
| 6:00–7:30 | **Demo 4**: Installation Report — messy field notes → structured report + JSON | Person 4 |
| 7:30–9:00 | **Demo 5**: WBR Generator — metrics CSV → executive summary with alerts | Person 5 |
| 9:00–10:00 | **Wrap-up**: What changed? Org impact. From "hours of manual work" to "seconds with AI". Trade-offs (hallucination risk, need for human review). | Team lead |

**Tips:**
- Each demo: show the messy INPUT on screen, run the script, show the clean OUTPUT. 3 steps, 90 seconds.
- Keep slides minimal. The terminal IS the presentation.
- If something breaks live, use the CER card to fix it — that's actually impressive, not embarrassing.

---

## File Structure

```
brighteyes/
├── README.md                    ← You are here
├── company_context.md           ← Company profile (shared across demos)
├── 3C_PROMPTS_ALL.md            ← All 5 prompts ready for Cursor
├── demo1_tender/
│   ├── 3C_PROMPT.md
│   ├── tender_parser.py
│   └── data/tender_hospital_milan.md
├── demo2_proposal/
│   ├── proposal_generator.py
│   └── data/call_notes_rossi.md
├── demo3_supplier/
│   ├── supplier_analysis.py
│   └── data/purchase_history.csv
├── demo4_installation/
│   ├── installation_report.py
│   └── data/field_notes_verdi.txt
└── demo5_wbr/
    ├── wbr_generator.py
    └── data/weekly_metrics.csv
```
