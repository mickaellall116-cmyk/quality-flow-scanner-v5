# QF-CH1-CORE-HOURS-EVIDENCE-20261021-90 — IN-ERA 2023 CORE-HOURS EVIDENCE

**Proposed verdict: `CH-1 RETIRED` — in-era primary evidence found.**
(This package PROPOSES the status. CH-1's status in the -87 packet / -88
freeze record changes only via later adjudication; nothing in the freeze is
edited here.)

**Authority:** Mike, chat 2026-10-21 22:01 ET: "Preserve CH-1 explicitly;
pursue its supporting historical documentation without blocking downstream
work." Research only; zero vendor calls, zero spend, zero credits.

## 1. The gap, exactly as recorded

From the -81 re-audit (`research_notes/nyse_calendar_2023_evidence_20261021_81/
REAUDIT_MEMO.md`, §"Core-hours sub-gap"), restated as assumption **CH-1** in
-87 Gate 1 and carried into the adopted calendar by the -88 freeze (commit
`a126ce5`):

> The -81 artifact states early closings on named dates but nowhere states
> 09:30–16:00 core hours for 2023. The only core-hours proof in the record
> was the -33 chain (NYSE Rule 1.1(d) text, SEC filing Jun 2025; RM-24-12
> dated 2024-09-13) — documents dated at/after the window, not back-projected.
> The evidence class "in-era dated core-hours proof for 2023" was absent.

## 2. What was found — three NYSE-issued documents, all dated 2023

All three are live official PDFs on `nyse.com` (source priority 1,
OFFICIAL_LIVE — the same priority -81 used; no Wayback or distribution copy
was needed). Bytes archived in private `qf-data-archive`,
`captures/ch1_core_hours_evidence_20261021_90/`, commits `f47823b` (base)
+ `4f6d470` (addendum), verified by fresh re-fetch: `sha256sum -c` 7/7 OK
(base SHA256SUMS) and 4/4 OK (SHA256SUMS_ADDENDUM). Quotations below were
verified against the captured bytes (pdftotext extractions archived
alongside the PDFs).

### 2.1 NYSE 2023 Annual Guidance Letter — NYSE Regulation, January 17, 2023

`NYSE_2023_Annual_Guidance_Letter.pdf`, 260,323 B,
sha256 `81a16c40d26aff312b05f21795153f8b27be6ee9fddf2b4d5916b5d4e30d0df7`.
NYSE Regulation's annual guidance memo to NYSE listed companies, "DATE:
January 17, 2023". The Exchange's own words:

- "Companies are required to call the Exchange's Market Watch Group … when
  intending to release material news between 7:00 a.m. ET and **the end of
  the NYSE trading session (4:00 p.m. ET)**."
- "Outside of the hours 7:00 a.m. ET and **the end of the NYSE trading
  session (4:00 p.m. ET)**, companies are generally not required to call the
  Exchange in advance…"
- "**Between the hours of 9:25 a.m. and 4:00 p.m. ET**, it is the Exchange's
  practice to institute a trading halt pending dissemination of news…"
  (contrasted in the next bullet with 7:00–9:25 a.m., when a halt is set only
  at the company's request — the 9:25 boundary is the pre-open edge of the
  trading day).
- "…price discrepancies between trading prices on other markets after **the
  NYSE official closing time, which is generally 4:00 p.m. ET**…"

### 2.2 NYSE Regulatory Bulletin RB-23-043 — April 28 / May 3, 2023

`NYSE_RB-23-043.pdf`, 141,827 B,
sha256 `7d94f9c7521a14cb2c7991dddf0476e766557c619a64bf6beb3d0f9cb090bdb1`.
Joint bulletin (NYSE Arca RB-23-043 / **NYSE RB-23-043** / NYSE American
RB-23-043 / NYSE National RB-23-043 / NYSE Chicago RB-23-043), cover dated
May 3, 2023, page footers April 28, 2023, addressed among others to "NEW
YORK STOCK EXCHANGE LLC ("NYSE") MEMBERS AND MEMBER ORGANIZATIONS".
"Trading Hours" section:

- "The shares will trade on **the NYSE from 7:00 a.m. ET until 4:00 p.m. ET
  on every business day in accordance with NYSE Rule 7.34**."

"Extended Hours Trading" section:

- "Shares of the Fund will trade on **NYSE Arca, NYSE, NYSE American, NYSE
  National and NYSE Chicago from 9:30 a.m. ET until 4:00 p.m. ET (the "Core
  Trading Session")**."

### 2.3 NYSE Regulatory Bulletin RB-23-116 — November 2, 2023

`NYSE_RB-23-116.pdf`, 133,292 B,
sha256 `e1dec9117f42bfdf1d6840e5ce0493c82bcde11cb924e52f6824a8d8b02f2b73`.
Joint bulletin of the same series, dated **November 2, 2023** — inside the
adopted calendar's 2023 segment (2023-10-19 → 2023-12-31) itself. Identical
session language:

- "The Shares will trade on **the NYSE from 7:00 a.m. ET until 4:00 p.m. ET
  on every business day in accordance with NYSE Rule 7.34**."
- "The Shares will trade on **NYSE Arca, NYSE, NYSE American, NYSE National
  and NYSE Chicago from 9:30 a.m. ET until 4:00 p.m. ET (the "Core Trading
  Session")**."

## 3. Why this retires CH-1 (proposed)

- **In-era:** all three documents are dated within calendar 2023
  (Jan 17; Apr 28/May 3; Nov 2). One is dated *inside* the adopted
  calendar's 2023 segment. This is precisely the evidence class -81
  recorded as absent — not a back-projection of later documents.
- **Primary and NYSE-specific:** the issuers are NYSE Regulation and the
  NYSE joint-bulletin series; the language states the sessions of the NYSE
  itself, under NYSE Rule 7.34 — not a sibling exchange's definition (the
  -33 discipline excluded sibling definitions; none is relied on here).
- **Both bounds stated:** the bulletins state the Core Trading Session on
  NYSE as 9:30 a.m. ET → 4:00 p.m. ET verbatim; the guidance letter
  independently states the 4:00 p.m. ET end of "the NYSE trading session"
  three times and brackets the open with its 9:25 a.m. halt-practice
  boundary.
- **Consistent with the rest of the record:** identical bounds to the Rule
  1.1(d) definition quoted in the -33 chain ("the hours of 9:30 a.m.
  Eastern Time through 4:00 p.m. Eastern Time"), to RM-24-12's operative use
  (2024-09-13), and to the qualified -35 calendar's session definition for
  2024-09-16 onward. No document found anywhere in this search states
  different 2023 hours, and no 2023 rule change altering core hours
  surfaced.
- **No calendar bytes change:** the evidence confirms the content of the
  CH-1 assumption. If adjudicated RETIRED, the only effect is that readouts
  spanning 2023 no longer carry the CH-1 assumption statement.

## 4. Scope disclosures (stated, not buried)

- The two bulletins are ETP-listing bulletins (subjects: Breakwave Tanker
  Shipping ETF, BWET; JPMorgan Healthcare Leaders ETF, JDOC). Their
  "Trading Hours" / "Extended Hours Trading" sections are the series'
  standard session boilerplate, restating each exchange's sessions as a
  general matter — including NYSE's, under NYSE Rule 7.34 — and are quoted
  exactly as written. The guidance letter's statements are about "the NYSE
  trading session" generally, in NYSE Regulation's own annual issuer
  guidance for 2023.
- The guidance letter does not contain the literal string "9:30"; its
  open-side evidence is the 9:25 a.m. halt-practice boundary. The explicit
  9:30 a.m. open statement is the bulletins'. The package does not overstate
  either document.

## 5. Search trail (the negative space)

- Read firsthand before searching: -79 audit memo, -81 capture memo + re-
  audit memo, the -33 core-hours proof memo — so nothing already held was
  re-captured (the Dec-21-2022 ICE release, the -31 hours-page captures and
  the -33 artifacts were NOT duplicated).
- Located and deliberately NOT relied on (sibling-exchange material, per
  the -33 discipline): the Dec 7, 2022 Federal Register NYSE Chicago notice
  (87 FR, doc 2022-26541) whose footnote 14 quotes Rule 7.34(a)(2)/Rule 1.1
  session language for NYSE Chicago's mirror rules; the Apr 2, 2024 NYSE
  Arca reverse-split halt filing (doc 2024-06887) referencing Arca's Core
  Trading Session at 9:30 a.m.; NYSE American/Arca Rule 1.1-series
  definitions in 2024–2025 filings.
- Reviewed, not used as primary: SR-NYSE-2022 (filed Aug 5, 2022; FR doc
  2022-17749), NYSE LLC's Off-Hours Trading Facility filing — it frames
  off-hours trading as beginning at 4:00 p.m. but does not state the 9:30
  open; superseded for this purpose by the 2023 documents above.
- Wayback Machine: not needed. As with -81, priority (1) OFFICIAL_LIVE was
  available for every document, so no archive fallback was used. No
  paywalled or credentialed source was touched; public unauthenticated GETs
  only.

## 6. Archive record

- Repo: private `mickaellall116-cmyk/qf-data-archive`, path
  `captures/ch1_core_hours_evidence_20261021_90/`.
- Commits: `f47823b` (RB-23-043 + guidance letter + extractions + header
  records + capture_manifest.json + SHA256SUMS); `4f6d470` (addendum:
  RB-23-116 + extraction + header record + capture_manifest_addendum.json +
  SHA256SUMS_ADDENDUM). Base files untouched by the addendum (write-once).
- Verification: after push, a fresh clone re-ran `sha256sum -c` — SHA256SUMS
  7/7 OK, SHA256SUMS_ADDENDUM 4/4 OK; both PDFs byte-identical to the
  captured originals.

## 7. Effect and limits of this package

- Proposes `CH-1 RETIRED` for adjudication (ChatGPT/Claude review, Mike's
  record). Until adjudicated, CH-1 stands exactly as frozen.
- No production or pinned file was edited; no calendar artifact changes;
  nothing was adopted or pinned by this package. Single-dispatch check
  before any file operation: no -90 stage, package, or commit existed —
  proceeded clean.

— Muse (task QF-CH1-CORE-HOURS-EVIDENCE-20261021-90)
