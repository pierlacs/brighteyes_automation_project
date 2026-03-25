# 3C Card — Demo 1: Tender Response Automation

## Context
I work at BrightEyes, a startup selling ophthalmic diagnostic devices (retinal cameras, OCTs, autorefractors) to hospitals and clinics. We regularly respond to public hospital tenders. Currently, someone reads a 40-page tender PDF manually, extracts requirements, checks if we're eligible, and drafts responses. This takes 1-2 full days per tender.

Build a Python script that parses a tender document and produces a structured analysis with:
1. A go/no-go eligibility check against our company profile
2. Extracted requirements mapped to our products
3. A draft response outline

## Components
1. **Read the tender document** (Markdown or PDF) and the company context file
2. **Extract structured data**: lots (what they want to buy), eligibility criteria, evaluation criteria with weights, deadlines, budget
3. **Run eligibility check**: compare tender requirements against BrightEyes profile (years of experience, revenue, certifications, references)
4. **Product matching**: for each lot, check which BrightEyes product fits and highlight gaps
5. **Generate a structured report** as a Markdown file with: summary, eligibility verdict, lot-by-lot analysis, recommended strategy, key deadlines, and risk flags
6. **Export the report** also as a .docx file

## Criteria
- The script should work with the tender file `data/tender_hospital_milan.md` and `../company_context.md`
- Output must be saved to the `output/` folder
- ALL output must be in English, even if the source tender contains foreign language text. Translate any extracted text to English.
- Use emojis in terminal output to make it visual and scannable (e.g. 📄 for loading files, 📋 for parsing, ✅ for pass, ⚠️ for risk, 🔴 for fail, 💰 for pricing, 📅 for deadlines, 🔗 for product matching)
- Use emojis in the Markdown report too (✅ ⚠️ 🔴 🟢 for status indicators)
- Use clear section headers in the output report
- Flag any eligibility criteria we do NOT meet as "RISK" items
- Include the scoring weights from the tender so the sales team knows where to focus
- Keep the code well-commented so non-developers can understand what each section does
- Do not call any external API — parse and analyze using rule-based logic (string matching, keyword extraction)
- Print a summary to the terminal when the script finishes

---

# 3C Card — Demo 2: Customer Proposal Generator

## Context
I work at BrightEyes, a startup selling ophthalmic diagnostic devices. After a sales call, our reps take rough notes and then spend hours writing formal proposals. Build a Python script that reads messy call notes and generates a polished commercial proposal with pricing, specs, timeline, and financing options.

## Components
1. Read the call notes file (Markdown)
2. Parse client info: name, clinic, products of interest, budget, timeline, special requests
3. Match requested products to our catalog with specs and pricing
4. Calculate bundle discount (5% for 2 products, 8% for 3+)
5. Generate a professional proposal as Markdown with: exec summary, product details, pricing table, financing options, implementation timeline, warranty, next steps
6. Save to output folder

## Criteria
- Input file: `data/call_notes_rossi.md`
- Output: `output/proposal_Clinica_Oculistica_Milano.md`
- ALL output must be in English
- Use emojis in terminal output to make it visual (e.g. 📝 for loading notes, 👤 for client info, 📦 for products, 💰 for budget, 🎯 for sentiment, ✅ for saved)
- Include leasing calculation (36-month estimate)
- All prices in EUR
- Proposal should look ready to send to a client
- Well-commented code

---

# 3C Card — Demo 3: Supplier Negotiation Prep

## Context
BrightEyes procures components from 5 suppliers across Europe and Asia. Before negotiation meetings, we manually review past orders. Build a Python script that analyzes our purchase history CSV and generates a negotiation brief with supplier scorecards, pricing trends, quality ratings, and strategic recommendations.

## Components
1. Load purchase history from CSV
2. Aggregate per supplier: total spend, average quality, average delivery time, price trends, issue count
3. Generate a supplier scorecard table with risk levels (Green/Yellow/Red)
4. Deep dive per supplier: price change %, quality issues, delivery reliability
5. Generate negotiation talking points per supplier
6. Calculate total savings potential (5% target on annual spend)
7. Output as Markdown report

## Criteria
- Input: `data/purchase_history.csv`
- Output: `output/supplier_negotiation_brief.md`
- ALL output must be in English
- Use emojis in terminal output (e.g. 📦 for loading, 🏭 for suppliers, 🟢🟡🔴 for risk levels, 💰 for spend, 🎯 for savings target)
- Use emojis in the Markdown report for risk indicators (🟢 LOW, 🟡 MEDIUM, 🔴 HIGH)
- Risk levels: HIGH if quality < 3.5/5, MEDIUM if < 4.0 or > 2 issues, LOW otherwise
- Include specific talking points (not generic advice)
- Sort suppliers by total spend descending
- Print summary to terminal

---

# 3C Card — Demo 4: Installation Report Generator

## Context
BrightEyes field technicians write messy, unstructured notes after device installations. These need to be turned into structured reports for QA tracking, client records, and sales follow-up. Build a script that reads raw technician field notes and extracts structured data: devices installed (with serial numbers), issues found (categorized and severity-rated), and sales opportunities.

## Components
1. Read unstructured text file with field notes
2. Extract: technician name, date, client, location, time on site
3. Extract device info: product names and serial numbers
4. Extract and categorize issues: Mechanical / Software / Quality Control / Process, with severity LOW/MEDIUM/HIGH
5. Detect sales follow-up opportunities (mentions of additional purchases)
6. Generate a clean structured report (Markdown) with tables
7. Also export as JSON for database import

## Criteria
- Input: `data/field_notes_verdi.txt`
- Output: `output/installation_report_verdi.md` and `output/installation_data_verdi.json`
- ALL output must be in English
- Use emojis in terminal output (e.g. 📋 for loading, 👤 for client, 📍 for location, 🔧 for devices, ⚠️ for issues, 😊 for satisfaction, 📝 for report saved, 📊 for JSON export)
- Use emojis in the Markdown report for severity (🟢 LOW, 🟡 MEDIUM, 🔴 HIGH) and status (✅ installed)
- Issues must be routed to the correct team (QA, R&D, Operations, Engineering)
- JSON export should be machine-readable for a future tracking database
- Client satisfaction should be inferred from the tone of the notes

---

# 3C Card — Demo 5: Weekly Business Review (WBR)

## Context
As CEO of BrightEyes, I need a weekly snapshot of business performance for the Monday morning review. Currently I pull data from multiple spreadsheets manually. Build a script that reads a weekly metrics CSV and generates an executive WBR summary with alerts, trends, YTD totals, a narrative, and action items.

## Components
1. Load weekly metrics CSV (12 weeks of data)
2. Calculate week-over-week changes for all key metrics
3. Flag anomalies: alert if any metric moves > 20% in the wrong direction
4. Calculate YTD aggregates: total revenue, units, leads, win rate, CSAT, marketing ROI
5. Auto-generate a narrative paragraph explaining the week's performance
6. Generate action items based on the data (e.g., if tickets are rising, assign to support lead)
7. Output as Markdown

## Criteria
- Input: `data/weekly_metrics.csv`
- Output: `output/WBR_W12.md`
- ALL output must be in English
- Use emojis in terminal output (e.g. 📊 for loading data, 📅 for current week, 💰 for revenue, ⚠️ for alerts, ✅ for saved, 📈 for YTD, 🎯 for win rate, 😊 for CSAT)
- Use emojis in the Markdown report for alerts (🔴 ALERT, 🟢 STRONG) and action priority (🔴 High, 🟡 Medium)
- Narrative should be data-driven, not generic
- Action items should name specific owners (Sales, Marketing, Support Lead, CEO)
- Print key numbers to terminal as a quick preview
