# Tiingo Applicability + Permission-Prep Evidence Note — 2026-10-12

**Task:** QF-TIINGO-APPLICABILITY-PERMISSION-PREP-20261011-01 r1 (read-only prep; NOT inventory repair)
**Authority:** Mike's direct instruction, main chat 2026-10-12 08:49 EDT ("I approve the Tiingo permission-clarification route. Proceed with the 20-minute read-only task ... No vendor contact, spending, deletion, restart, or processing stored Tiingo data.")
**Prior assignment ref:** GitHub Issue #1 comment 6109330945 (ChatGPT, 2026-10-11 13:05 UTC). Mike's direct word supersedes the relayed "Ok continue."
**Method:** zero Tiingo API calls, key never touched, no retained Tiingo data opened/processed. Public ToS page + repo/memory metadata + web only.
**Effort:** ~16 min of 20-min budget.

## 1. Account/terms evidence from non-secret metadata

| Fact | Status | Source |
|---|---|---|
| Account plan | TREAT AS STARTER (entitlement UNKNOWN) | Free-tier budgets in `~/workspace/skills/tiingo/SKILL.md` (50 req/hr, 1000 req/day, 500 symbols/mo); memory logs show active 500-symbol cap management, 453/500 used. No billing records, no dashboard screenshot. Do not assert Starter as fact. |
| Account creation date | ~2026-09-30 (email-verified) | Gmail (registered address) holds exactly one Tiingo message: "Verify your email address for Tiingo" from noreply@verify.tiingo.com, 2026-09-30 16:46 ET. Signup verification implies account creation at/just before this date — BEFORE the 2026-10-06 ToS update, so Mike was an existing user at the update. |
| Accepted terms version/date | UNKNOWN | No record found. |
| Amendment notice date (email/dispatch) | NONE FOUND in registered inbox | The registered Gmail inbox contains no Tiingo amendment/terms-update notice (only the 2026-09-30 verification email; searched 2026-10-12). If Tiingo emailed the registered address about the Oct 6 update, it is not in this inbox. |
| Download date ranges | ESTABLISHED (dates) | October EOD pull COMPLETE 2026-10-03 04:04 UTC (453/453 ledger, 444 OK + 9 fail-closed 404s); fundamentals pilot (AAPL/MSFT/WMT) Oct 2026; ORB 15m QQQ/SPY pull 2026-10-07; Tiingo observer gap-fills transient in-memory only (nothing persisted). |
| Data values/contents | NOT INSPECTED | Per HOLD; only dates, counts, sizes from metadata. |

## 2. Official current ToS (opened live 2026-10-12, app.tiingo.com/tos)

- Version 1, Effective Date 2022-01-16, Last Updated 2026-10-06.
- Change clause: new users effective immediately; existing users effective 30 days after posting (material changes: earlier of 30 days after posting or 30 days after email dispatch to registered account holders). Continued use after notice = acceptance.
- §1.6(a): Starter/Trial — no writing, saving, archiving, backing up, or otherwise retaining Tiingo Data OR Derived Products in any persistent/durable storage; transient volatile-memory processing only; remove before process/job/session ends.
- §1.6(b): Paid plans (not Starter/Power-exception) may persist while active; on expiration/cancellation/termination/downgrade, must promptly and permanently delete ALL Tiingo Data from every system including backups, logs, queues, archives, DR. Exception only via separate written agreement — NOT available for Starter or Power.
- §1.6(c): paid-plan aggregate/non-reconstructible outputs (Sharpe/Sortino, alpha, beta, max drawdown, win rate, aggregate P&L, signals that do not expose underlying data, 5-field hashes) may be retained; prohibited: resampled/rebased/indexed series recoverable to underlying data; using Tiingo Data to validate another dataset (substitute use — the validated dataset must also be deleted).

## 3. Materially new evidence: §1.6(a) predates the 2026-10-06 update (secondary, corroborated x2)

Two independent third-party terms audits, each compiled from Tiingo's own ToS page BEFORE the Oct 6 update, record the same Starter retention prohibition and cite "v1, updated 2026-08-05":

1. `openquant/DATA_SOURCES.md` (Open-Quant/openquant, GitHub; table compiled 2026-09-24 from each provider's own terms page; verified live 2026-10-12): "Tiingo | https://app.tiingo.com/tos/ (v1, updated 2026-08-05) ... §1.6: free and trial plans may not keep data in persistent storage, so the local cache needs a paid plan."
2. `qhongboq/autonomous_quant` docs/project-brain/p2-tiingo-free-data-authority-audit-001.md: "Tiingo's current Terms of Use, last updated 2026-08-05, expressly prohibit a Starter or Trial user from writing, saving, archiving, backing up, or otherwise retaining Tiingo Data in persistent storage."

**Implication:** the retention restriction on Starter plans was very likely already in force at the time of the October downloads (and the EOD pull of Oct 3). The 30-day effectiveness clause in the Oct 6 update therefore likely does NOT buy grace for §1.6(a) — it applies to whatever changed on Oct 6, which has not been established. This is secondary evidence, not official; exact prior text not recovered. Official prior-text recovery (Wayback pre-Oct-6 snapshot) was not completed in budget — remains an open verification step.

**Correction to prior framing:** comment 6109330945's correction ("current published restrictions are established; applicability to this account and prior downloads is UNKNOWN; do not label prior retention a proven breach") still holds on account-specific facts (creation date, accepted terms, entitlement UNKNOWN). But the new evidence materially weakens the "the Oct 6 update may have introduced the restriction" theory — the safe compliance assumption remains TREAT AS STARTER / do not retain.

## 4. Unresolved facts

- Accepted terms version/date (account was created ~2026-09-30, so accepted version was the pre-Oct-6 text, likely "updated 2026-08-05" per the secondary audits — not directly confirmed from account records).
- Official prior ToS text (pre-Oct-6) and exactly what the Oct 6 update changed.
- Whether a Power-plan upgrade would cover data retained before upgrade (terms do not state retrospective cure; §1.6(b) exception requires separate written agreement not available to Power).
- Whether aggregate research findings (e.g. ORB benchmark numbers) qualify as retainable §1.6(c) aggregates on a paid plan — numbers are aggregate P&L-style outputs, but they were produced on Starter where §1.6(a) also bars retaining Derived Products.

## 5. Vendor inquiry — DRAFT ONLY (no contact made)

---
**To:** Tiingo support
**Subject:** Account-specific terms clarification — Starter plan, retained research data, upgrade path

Hello,

I'm writing to confirm the terms applicable to my individual account before deciding between deletion, an upgrade, or a written agreement.

1. **Applicable terms.** Which Terms of Use version and effective date governs my account, and was I an existing account before the October 6, 2026 update? Was an amendment notice emailed to my registered address, and on what date?
2. **Earlier retained data.** On a Starter plan, what is the required disposition for Tiingo data already saved to local files (raw end-of-day bars, fundamentals, and derived panels/aggregates built from them)? Must it be deleted, and is there any permitted migration path that preserves the data?
3. **Upgrade path.** If I upgrade to the Power plan, does that cover data that was already retained before the upgrade, or does prior retention remain non-compliant regardless?
4. **Research aggregates.** Are aggregate, non-reconstructible research statistics (e.g. backtest aggregate returns, derived panel summaries — no raw bars) treated differently from raw/derived datasets for disposition purposes?
5. **Cross-feed validation.** Does Tiingo permit using its data to validate or reconcile another data vendor's dataset, and if so, under which plan and conditions?

I'd appreciate account-specific answers rather than general policy text, so I can take the correct action. Thank you.

— Mike Lall
---

## 6. Holds and non-actions

- All Tiingo holds remain (no API calls, no observer fills, no parity work, no VCP/ORB use of retained inputs, no Twelve Data crossover).
- No vendor contact made. No deletion executed (inventory is not deletion-ready per amendment 6101353568). No purchase. No restart.
- Nothing in this note labels prior retention a proven breach; it records evidence and asks the vendor for account-specific answers.

— Muse, 2026-10-12 (Mike-authorized)
