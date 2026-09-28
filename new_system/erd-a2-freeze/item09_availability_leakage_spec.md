# Item 9 — Availability/leakage spec (frozen, §1.6(e) quoted verbatim from Amendment 2 rev 4)

- (e) ZERO-TOLERANCE categories — immediate FAIL on ANY demonstrated
      instance, regardless of the 48/50 floor. The leakage category uses
      the canonical decision-time inequality:
      `available_at + LATENCY_BUFFER ≤ decision_time`,
      where `available_at` = the provider's versioned availability
      timestamp for the event's timing fields (never the event/report
      time), `LATENCY_BUFFER` = **15 minutes** (frozen literal), and
      `decision_time` = 09:30 ET on session S (the regular-session open of
      the reaction session derived under Amendment 1 §1). A record whose
      availability timestamp is missing or unversioned fails the
      availability claim for that event (UNVERIFIABLE/FAIL under (a));
      systematic absence of versioned availability = PIT status
      FAIL/UNVERIFIED under (c). Other zero-tolerance classes: systematic
      timestamp imputation; permanent-ID crossing (one ID spanning two
      distinct operating companies, or vice versa); survivorship
      substitution/redraw; decision-clock override (provider bucket
      contradicting its own exact-time field under Amendment 1 §1 rules);
      any revision/backfill mechanism capable of contaminating historical
      availability. These are not "two free errors."
