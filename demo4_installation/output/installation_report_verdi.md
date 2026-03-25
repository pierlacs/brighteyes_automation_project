# 📋 Installation Report — Studio Oculistico Verdi

## 🧾 Summary

- **Technician**: Marco Bianchi
- **Date**: 2026-03-18
- **Client**: Dr. Elena Verdi
- **Site / Location**: Studio Oculistico Verdi, Via Roma 45, Torino
- **Time on site**: Arrived 09:15 | Left 13:45 | Total 4.5h

## 🔧 Devices installed

| # | Device | Serial number | Status |
|---:|---|---|---|
| 1 | BrightEyes RetinaScan Pro | `BRS-2026-00847` | ✅ installed |
| 2 | BrightEyes AutoRef 500 | `BAR-2026-01203` | ✅ installed |

### ✅ BrightEyes RetinaScan Pro — notes

- Unpacked, no visible shipping damage
- Installed in exam room 1, had to move the old slit lamp to make space
- Power connection fine, using the wall socket behind the desk
- Calibration: ran auto-calibration 3 times, first 2 failed because room was too bright. Closed the blinds, third attempt OK.
- Connected to their PC via USB-C, driver installed automatically on Windows 11
- DICOM export tested — works but their PACS system (OphthaPACS v3.2) needed a config change on port 4242
- Patient test capture: Dr. Verdi tested on her assistant, image quality rated "excellent" by the doctor
- One issue: the chin rest height adjustment is a bit stiff. Applied silicone lubricant, now smooth. Noted for QA.

### ✅ BrightEyes AutoRef 500 — notes

- Installed in exam room 2
- Setup straightforward, took about 30 mins
- Connected to same PC network
- Italian language pack was not pre-loaded! Had to download it on site, took 15 min on their slow wifi. NOTE TO OFFICE: please pre-load Italian language pack before shipping to Italian clients!!!
- Measurement accuracy test: compared 5 readings with their existing manual refractometer, all within ±0.25D. Dr. Verdi happy.
- Small scratch on the device base — was there from factory, not shipping. Took photo. Client accepted it but noted for future QA.
- Spent 45 mins training Dr. Verdi and her assistant Maria on both devices
- They picked it up quickly, very tech-savvy
- Left the quick-start guide (Italian version)
- Dr. Verdi asked about the AI screening module — told her it's coming in Q3 2026 update. She's very interested.

## ⚠️ Issues (categorized, severity, routing)

| Issue | Category | Severity | Routed team | Device S/N | Fixed on site |
|---|---|---|---|---|---|
| Chin rest stiffness on RetinaScan Pro S/N BRS-2026-00847 — mechanical, fixed on site | Mechanical | 🟢 LOW | Engineering | `BRS-2026-00847` | Yes |
| Missing Italian language pack on AutoRef 500 — process issue | Process | 🟡 MEDIUM | Operations | — | — |
| Scratch on AutoRef 500 base S/N BAR-2026-01203 — factory QC issue | Quality Control | 🟡 MEDIUM | QA | `BAR-2026-01203` | — |
| PACS/DICOM integration required a configuration change (port 4242). | Software | 🟢 LOW | R&D | `BRS-2026-00847` | Yes |

## 😊 Client satisfaction (inferred)

- **Satisfaction**: POSITIVE
- **Rationale**:
  - Positive language in notes.
  - Acceptance signed / issues accepted.
  - Minor issues were present but did not block acceptance.

## 🧩 Sales follow-up opportunities

| Opportunity | Confidence | Evidence |
|---|---|---|
| Follow up on AI screening module interest (planned Q3 2026 update). | MEDIUM | Dr. Verdi asked about the AI screening module and expressed strong interest. |
| Upsell opportunity: second RetinaScan Pro for the client’s satellite office (Moncalieri). | HIGH | Client wants to discuss a second RetinaScan for her satellite office in Moncalieri. |

---
Generated on 2026-03-25T18:07:32 by `installation_report.py`
