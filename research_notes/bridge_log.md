# Research bridge — incident & reliability log

Append-only. Newest at the bottom.

## 2026-09-25 — bridge watcher first-cycle miss (resolved)
ChatGPT's first review reply arrived via AgentMail but the watcher missed it.
Two bugs found and fixed live: (1) Gmail subject-phrase query didn't match
"Re:"-prefixed replies — broadened to
`{from:quality-flow-research@agentmail.to subject:"AGENT RESEARCH BRIDGE"}`;
(2) the script assumed triage returns a bare list — it returns
`{"messages": [...]}`. Verified the fixed watcher detects + extracts reply
bodies. Lesson: always send bridge replies with `+reply --message-id` so
threading stays in the one standing thread (`+send` with a "Re:" subject
spawns a stray thread).

## 2026-09-25 — ChatGPT outbound reply blocked by AgentMail safety checks (resolved via fallback)
ChatGPT's TYPE: REVIEW RESPONSE on the 08:22 EDT BRAINSTORM (decision: PASS;
priority reproducibility infra → synthetic edge-case hardening → fresh
architecture; five stricter audit controls) was blocked by the mail system's
outbound safety checks. Nothing reached the Muse mailbox — confirmed by
Gmail search (no bounce, no message; last thread message before the block
was Muse's own BRAINSTORM, id 1a0d884b938adfe3). Mike relayed the review
verbatim to Muse in main chat. Muse recorded the decision, began
implementing priorities (1)+(2) in `new_system/timing_audit/`, and replied
in-thread (id 1a0d8bb98a18c5aa) confirming receipt + the new fallback rule,
asking ChatGPT to confirm briefly (re-tests their outbound path).

Fallback rule added to the bridge protocol (research_mandate.md):
(a) blocked reply → retry once as plain text <2,000 chars, no
links/attachments/tables; (b) still blocked → review stands as relayed via
Mike (authoritative), Muse confirms receipt in-thread; (c) bridge replies
short plain-text by default; long artifacts on GitHub.
What this does NOT fix: AgentMail's outbound filters are outside Muse's
control and can block again. The fallback makes a block non-fatal — no
review can be stranded silently.

## 2026-09-25 ~12:30 EDT — ChatGPT outbound blocked AGAIN; plain-text retry also blocked (fallback partially failed)
ChatGPT reports (via Mike relay) that both its normal reply AND the agreed
plain-text retry (<2,000 chars, no links/tables) were blocked by AgentMail's
outbound safety checks. The fallback protocol's step (a) did not get through.
Per fallback step (b), the review stands as relayed via Mike (authoritative):
- Intrinio/Zacks feed still the blocker (trial = ~6 months history, gate needs 8 years).
- Decision remains PASS, ranked: reproducibility infra → audit-harness edge
  cases → fresh architecture research.
- New requirement: synthetic red-team suite for the timing gate (DST, early
  closes, exact-close timestamps, revisions, ticker changes/delistings,
  missing timestamps, duplicates, vendor/primary-source conflicts); 50-event
  sample hash + scorer version frozen before real data; sampled failures not
  replaced; no returns in the audit. V5.4 and ERD remain frozen.
- Muse implemented the new requirement same day: C5 scorer-version freeze
  (SCORER_VERSION=1.0.0, embedded in sample/sheet/score; cross-version
  artifacts refused) + C6 duplicate/revision handling (dedupe before
  stratification, detect_vendor_revisions() for pull-vs-pull restatements)
  + no-returns gate-scope guard. Suite now 46 tests, all passing; published
  to main as 05852cf (harness), 3f6b375 (tests), b014032 (README).
Lesson: the plain-text retry is not a reliable unblock. When step (a)
fails, skip straight to (b) — Mike's relay is authoritative, Muse confirms
receipt in main chat and executes; no further bridge round-trips spent on
unblocking. A future fix would need AgentMail filter allowlisting, which is
outside Muse's control.

## 2026-09-25 ~12:45 EDT — ChatGPT relayed review of 05852cfb: PASS WITH ONE REQUIRED HARDENING (implemented same day)
Via Mike's relay (authoritative per protocol): ChatGPT found one issue in the
current duplicate logic worth fixing before real Intrinio data touches the
harness — (1) same ticker+date rows with DIFFERING timing fields were silently
collapsed to the first row, hiding a vendor disagreement; (2) revision
matching keyed on ticker+date would turn a ticker change between historical
pulls into an apparent removed+added event instead of a revision. Judgment:
exact duplicates may collapse, conflicting duplicates must fail/flag;
revision matching should use a stable security/company identifier where the
feed provides one, with ticker/date as documented fallback. Reviewer verdict
after this: harness ready for the Intrinio gate. No change to ERD, sample
thresholds, or V5.4.
Muse implementation same day: dedupe_records() now splits rows into unique /
exact-duplicate (collapsed, counted, reported) / conflicting-duplicate
(flagged; draw_sample REFUSES the whole draw while any exist — one event
never takes zero ambiguity into the sample); revision matching via new
_revision_key() preferring security.id, ticker+date as documented fallback
(key_type recorded on changed entries). Suite now 50 tests (46 existing +
4 new: conflicting-dup flagged, draw refuses conflicts, exact-dups still
tolerate, stable-id match across ticker change, ticker fallback). Verified
end-to-end on synthetic data: CLI sample/sheet/score run clean with exact
duplicates collapsed+reported; conflicted pool refused with exit 1 and a
named vendor-disagreement message. Published to main as 3cd810c (tests),
535d674 (harness), 8ca17f1 (README).
Status: timing audit harness is READY FOR THE INTRINIO GATE; still gated on
the same blocker — human Intrinio specialist reply on Enterprise Zacks EPS
Surprises access. No purchase, no trial, no performance data.

## 2026-09-25 ~18:40 EDT — root cause found for AgentMail outbound blocks (fix requires ChatGPT's side)
Third block: ChatGPT's MAYBE review (multiple-testing candidate-family ledger proposal) blocked again on AgentMail outbound; relayed via Mike. New diagnosis (AgentMail docs + community skill notes): AgentMail auto-adds an org-level send-block entry after a bounce/rejection — 403 "Recipient(s) blocked" that refuses the send before mail leaves, regardless of content. This fits the evidence: the first review reply arrived fine; every send after that failed, including the <2,000-char plain-text retry with no links/tables — content shaping cannot fix recipient-level suppression. This revises the earlier "outside Muse's control" note: the block is fixable, but only by the AgentMail account holder (ChatGPT's side) via the Lists API: GET /v0/lists/send/block/mickaellall116@gmail.com → DELETE the entry (expect 204; 409 read_only = do not loop) → resend. Fix instructions passed to Mike for ChatGPT. Until confirmed fixed, Mike's relay stays authoritative.

## 2026-09-25 ~18:55 EDT — bridge moved to GitHub (Mike's decision)
Per ChatGPT's proposal (relayed via Mike) and Mike's "Yes": standing issue
#1 "Quality Flow Research Bridge" is now the primary channel; email/AgentMail
is fallback only. Setup: issue created with protocol body; Muse's side posts
via commits to research_notes/bridge_thread.md (commit 6972ce3) because its
GitHub token returns 403 "Resource not accessible by personal access token"
on issue comments and issue edits — create + read work, comment/edit do not
(scope limit). ChatGPT replies as issue comments; bridge_watcher.py now polls
issue #1 comments AND the Gmail fallback thread every 10 min. Mandate updated
(commit 10939e1). If Mike reconnects the GitHub connector with a broader
token, Muse can post comments directly and bridge_thread.md becomes redundant.

## 2026-09-25 ~19:20 EDT — ChatGPT (via Mike): process fixed, underlying block not
ChatGPT confirmed the process fix is complete (relay authoritative, GitHub
records decisions, no blind retries) but its AgentMail outbound suppression is
not removable from its connector — endorsing the GitHub bridge as the fix that
removes email delivery from the workflow. Recorded in bridge_thread.md
(862e2be). Email stays fallback only.

## 2026-09-25 ~19:20 EDT — bridge VERIFIED end-to-end
ChatGPT's PASS comment (5840969127) confirmed readable via API. Live path:
Muse → bridge_thread.md → ChatGPT → Issue #1 comment → 10-min watcher.
GitHub primary, email fallback. Frozen state re-acknowledged.

## 2026-09-26 ~00:40 EDT — 3H hybrid forward baseline done (Mike-authorized research)
Per Mike's 2026-09-26 authorization to investigate the 3H paper-only idea
(research only — not approved, not deployed): re-ran the frozen 3H plain
Hybrid spec (pine_2h3h_backtest, canonical pine_backtest.py unmodified, 25bps
costs, 14 tickers) on 1H data through 2026-09-25 15:30 ET. Full-window
reproduction matches the historical study exactly (371 trades, +0.158R @25bps,
50.7% win, PF 1.24) — pipeline faithful. Forward window (entry >= 2026-09-15):
n = 0 trades; last 3H signal fired 2026-09-14 (HOOD, stopped). Verdict: the
+0.15R gate cannot be evaluated on forward data yet — neither pass nor fail;
historical +0.158R stands unreplicated and unrefuted. Live arbiter needs
weeks-to-months of paper sidecar; re-check at the ~50-signal checkpoint (late
Oct 2026) alongside the other arbiters. Nothing for Claude to independently
confirm (no forward trades). Report: research_notes/3h_hybrid_forward_baseline_2026-09-26.md
(committed 668282c). Intrinio: inbox checked 2026-09-26 ~00:33 EDT — still no
human specialist reply; access remains the blocker, no purchase, no trial.
