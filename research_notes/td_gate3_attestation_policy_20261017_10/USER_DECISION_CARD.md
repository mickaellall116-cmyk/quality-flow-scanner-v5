# DECISION CARD — for Mike (from QF-TD-GATE3-ATTESTATION-POLICY-20261017-10 r1)

**The question: approve 52 credits for the Twelve Data screen day instead of 51?**

What we found, in plain terms:

- Before the 51-request data screen can run, the safety gate has to check the
  account: right plan, enough credits left today. The only account-check
  endpoint Twelve Data documents is `GET /api_usage`.
- That check is **not free**. Twelve Data's own docs price it at **1 API
  credit** — the same credit pool the screen spends from. Your standing
  authorization covers a 51-credit screen. The check would make the day's
  total **52 credits** (still $0 — these are free-tier daily credits,
  52 out of the 800/day the plan allows).
- There is no way to keep the total at 51 and still run the full screen:
  at 51 total, only 50 data requests fit, and the qualification needs all
  51 requests — a 50-request run would not count as the full-manifest
  screen. Checking the account a day early doesn't work either (the
  evidence has to be fresh, and credits are counted per day).

**What changes if you say yes:** on the screen day only, the gate is
allowed to spend 1 credit on the account check plus the unchanged 51
credits on the data screen — 52 total, $0, same one-attempt / fail-closed
rules, same frozen 51-request list, nothing else changes.

**What stays the same either way:** no screen runs until you decide. The
ledger adoption, the dispatch token, and the screen itself each still
need their own reviewed step. Saying no parks the Twelve Data screen at
this gate — everything built so far stays valid and published.

**The ask: GO for a 52-credit ceiling (1 status + 51 data) on the screen
day, or NO (screen stays parked)?**
