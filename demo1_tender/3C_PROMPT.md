# 3C Card — Demo 1: Tender Response Automation

## Context
I work at BrightEyes, a startup selling ophthalmic diagnostic devices (retinal cameras, OCTs, autorefractors) to hospitals and clinics. We regularly respond to public hospital tenders (appels d'offres). Currently, someone reads a 40-page tender PDF manually, extracts requirements, checks if we're eligible, and drafts responses. This takes 1-2 full days per tender.

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
- Use clear section headers in the output report
- Flag any eligibility criteria we do NOT meet as "RISK" items
- Include the scoring weights from the tender so the sales team knows where to focus
- Keep the code well-commented so non-developers can understand what each section does
- Do not call any external API — parse and analyze using rule-based logic (string matching, keyword extraction)
- Print a summary to the terminal when the script finishes
