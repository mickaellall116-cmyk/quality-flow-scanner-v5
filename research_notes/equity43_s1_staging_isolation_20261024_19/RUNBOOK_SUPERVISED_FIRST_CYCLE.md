# Supervised first cycle — runbook (DOCUMENTATION ONLY)

QF-EQUITY43-S1-STAGING-ISOLATION-PREFLIGHT-20261024-19 r1.
This runbook authorizes nothing. It lists, in order, the gates a human
must clear before the staged S1 observer may run its first supervised
cycle. Until every gate below is cleared and recorded, the bundle's
verdict stays **PREP_READY / LAUNCH_HOLD** and processing against any
feed remains structurally unreachable in the staging namespace.

## Still-human gates (all five, in order)

1. **G4 adoption.** The G4/VBASIS data-convention question must be
   adjudicated and adopted (or the observer's qualification basis
   otherwise resolved) through the normal governance lane. The staging
   bundle carries G4 as UNADOPTED; no staging artifact waives it.
2. **Qualified prospective feed — rights + latency.** A prospective 1h
   feed must be qualified for this use: usage rights for prospective
   observation established, and live latency measured (it is currently
   UNMEASURED). The feed adapter is a separate governed build; the
   staging bundle deliberately contains no network/vendor adapter.
3. **Calendar adoption binding.** Adoption of the -18 extended session
   table must bind the exact -18 commit `19cd5aef…`, its manifest, the
   table SHA `86a1d4eaa5b838aa4138cef3c7dc5efcea99997fec40863b015075829acf6371`
   and the repin record. A newly generated table is not a substitute.
4. **Declared future T0.** A future T0 (first observation session) must
   be declared in advance, in writing, in the governance record.
5. **Explicit Mike GO + observer supervision.** Mike's explicit GO
   naming the T0, and a named supervisor for the first cycle. The GO is
   recorded as `config/LAUNCH_AUTHORITY.json` in the launch namespace
   (fields: `t0`, `mike_go_ref`, `feed_qualification`, `g4_adoption`) —
   note the staging gate still holds at LAUNCH_HOLD while the
   qualification record stands UNADOPTED/UNQUALIFIED; the launch
   record is a separate artifact of the launch lane, not of staging.

## First-cycle supervision checklist (when the gates above are cleared)

- [ ] Re-run the staging preflight against the launch namespace;
      require PREP_READY with zero STOPs and pin inventory exact
      (observer `929c1bc4…`, 14 source pins, config `87b8285a…`,
      sector `a91222c7…`, calendar `86a1d4ea…` over the adopted table).
- [ ] Confirm production is still PAUSED (harness `ce7c902c…`,
      PAUSE_NEW_ENTRIES present, RESUME_NEW_ENTRIES absent) and that
      the launch namespace is disjoint from every production path.
- [ ] Confirm the launch namespace journal/state are empty (a
      pre-populated journal is refused by design).
- [ ] Confirm the kill switch path (`<namespace>/KILL`) is known to
      the supervisor and tested once before T0.
- [ ] During the first cycle: supervisor watches the journal anchor
      chain after each session; any chain break, UNKNOWN_SESSION
      flood, poisoned-symbol quarantine, or pin drift STOPs the cycle
      and is reported before any restart.
- [ ] Restart discipline: never repair a divergent journal in place;
      resume only via the verified resume path; a refused resume ends
      the cycle pending adjudication.
- [ ] The first cycle is S1 signal-only observation: signals are
      recorded, no positions are opened, no orders exist in the
      system, and no performance figure is computed or reported.
- [ ] End of first cycle: seal the journal, write the anchor, and file
      the cycle record (journal head, record count, signal count,
      incidents) to the governance record for adjudication before any
      second cycle is scheduled.
