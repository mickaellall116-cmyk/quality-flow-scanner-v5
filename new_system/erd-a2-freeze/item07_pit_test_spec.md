# Item 7 — PIT/revision test spec (frozen, §1.6(c) quoted verbatim from Amendment 2 rev 4)

- (c) PIT/revision gate (mechanically decidable; detection AND evidence).
      Two time-separated pulls of the candidate's historical record (pull A
      at T1, pull B at T2, T2 − T1 ≥ **45 days**, frozen literal).
      Comparison uses the frozen timing-audit harness semantics (exact
      duplicates collapse and are counted; conflicting duplicates =
      vendor disagreement, investigated fail-closed, never silently
      resolved; revision matching prefers permanent security ID,
      ticker/date as documented fallback). Fixed transition sample:
      **N = 20** events, drawn by Fisher–Yates seeded shuffle of the
      frozen 50 with frozen literal seed **20260929**, first 20 taken —
      no revision-prone weighting, no judgmental oversampling.
      Pass requires ALL of: (i) ZERO unversioned historical changes to
      date/time/bucket fields between pulls in the transition sample —
      any unversioned change = backfill evidence = FAIL; (ii) the provider
      supplies versioned revision records carrying availability timestamps
      for the transition sample's timing fields, with record-version
      semantics documented in the build log BEFORE the gate runs —
      undocumented or contradicted version semantics = FAIL; (iii) the
      availability claim is corroborated by versioned provider evidence
      OR by an explicitly frozen independent archival equivalent (named
      and frozen before the gate; ad-hoc archives do not count) —
      otherwise provider PIT status is FAIL/UNVERIFIED. The two-pull test
      is a backfill tripwire: passing it alone NEVER establishes
      historical as-seen correctness. No current-state snapshot may
      establish historical PIT correctness.
