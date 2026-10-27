# Credits headroom — remaining pilot sessions (Option B successor)

Computed from the live journal (`state/pilot_state.json`, read-only) at
build time; raw census in `headroom_census.json`. Caps (frozen):
**149 calls per execution day, 800 total**. Calls used so far:
**0** (`desk_calls = 0`; the Oct-26 session was missed under the hold).

Worst case = no bar is ever sighted at an early ladder rung, so all
three rungs (+60/+180/+420s) fire for every bar — the maximum the
frozen schedule can generate. The 148 TD-kind actions of the missed
Oct-26 session (105 ladder, 35 finalization, 5 revision, 3 usage) are
stale-marked at clearance and **never execute**, so they consume no
budget. (The 149th Oct-26 action, the archive push, is not a TD call.)

| Execution day (ET) | Worst-case TD calls | Composition | vs 149/day cap |
|---|---|---|---|
| Tue 2026-10-27 | 144 | usage 4, ladder 105, finalization 35 | 5 spare |
| Wed 2026-10-28 | 149 | usage 4, revision 5, ladder 105, finalization 35 | at cap |
| Thu 2026-10-29 | 149 | usage 4, revision 5, ladder 105, finalization 35 | at cap |
| Fri 2026-10-30 | 149 | usage 4, revision 5, ladder 105, finalization 35 | at cap |
| Mon 2026-11-02 | 7 | usage 2, revision 5 | 142 spare |
| **Total remaining** | **598** | | |

- **Total headroom: 800 − 598 − 0 used = 202 calls.**
- Revision days (Wed–Fri) exactly saturate the 149/day cap in the
  worst case — that is the frozen design point, not an overrun: the
  schedule contains no 150th call on those days, and `cap_check`
  refuses any call once the day counter reaches 149. Realized counts
  will be lower whenever a bar is sighted before its last rung (the
  ladder stops at first sighting).
- The continuity fixture's simulated Oct-27 realized the full worst
  case for that day (144 calls) with the pilot never stopping and both
  caps respected.
