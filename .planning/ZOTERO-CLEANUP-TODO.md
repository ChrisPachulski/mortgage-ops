# Zotero Cleanup TODO (manual GUI fixes)

> Quality-audit findings 2026-05-16. Five items ingested via the 2026-05-16
> expansion run have suboptimal source URLs. Content is genuine but provenance
> can be upgraded. Fix manually in the Zotero desktop GUI; the CLI doesn't
> expose an item-update endpoint.
>
> These don't affect decision math — they affect citation provenance only.

## Action: open each item in Zotero, edit the `URL` field

### 1. Freddie Mac Bulletin 2022-22

- **Current URL:** `https://www.tenaco.com/wp-content/uploads/2022/11/Freddie-Mac-Guide-Bulletin-2022-22-10-31-22.pdf`
- **Better URL:** `https://guide.freddiemac.com/app/guide/bulletin/2022-22`
- Source: Mortgage industry consultant mirror → official Freddie Selling Guide archive
- Collection: Regulatory and Compliance

### 2. Freddie Mac Bulletin 2023-1

- **Current URL:** `https://www.tenaco.com/freddie-mac-issues-bulletin-2023-1-credit-fee-updates/`
- **Better URL:** `https://guide.freddiemac.com/app/guide/bulletin/2023-1`
- Source: Industry blog summary → official Freddie source
- Collection: Regulatory and Compliance

### 3. FHA HECM Reverse Mortgage Servicing Handbook Revisions (2024)

- **Current URL:** `https://www.financialservicesperspectives.com/2024/05/impact-of-revised-fha-handbook-on-reverse-mortgage-servicers/`
- **Better URL:** `https://www.hud.gov/sites/dfiles/OCHCO/documents/40001HSGH.pdf` (Handbook 4000.1 — Section III for HECM servicing)
- Source: Mayer Brown LLP law-firm blog → official HUD Handbook
- Collection: Regulatory and Compliance

### 4. NWMLS 2024 Annual Market Report

- **Current URL:** `https://seattleagentmagazine.com/2025/01/21/nwmls-2024-in-review/`
- **Better URL:** `https://www.nwmls.com/market-reports/annual/2024` (or current NWMLS market-statistics archive)
- Source: Trade journalism summary → direct NWMLS data
- Collection: Market and Macro

### 5. NWMLS 2025 Annual Market Report

- **Current URL:** `https://seattleagentmagazine.com/2026/01/20/nwmls-2025-annual-housing-market-report/`
- **Better URL:** `https://www.nwmls.com/market-reports/annual/2025` (or current NWMLS market-statistics archive)
- Source: Trade journalism summary → direct NWMLS data
- Collection: Market and Macro

## Optional: cleanup test item

There may also be a residual TEST item titled "TEST: Optimal Mortgage Refinancing..." in Foundational Texts tagged `TEST-DELETE-ME`. I deleted it via SQLite earlier — verify in GUI; if it reappears (sync conflict), right-click → Move to Trash → Empty Trash.

## Verifying after fixes

Run: `cli-anything-zotero --json collection items <KEY>` and confirm none of the 5 URLs above appear.

---

*Cleanup is cosmetic / provenance-quality. Content is correct in all 5 cases — they're real Freddie Bulletins, a real HUD Handbook section, and real NWMLS data, just mediated through suboptimal hosts.*
