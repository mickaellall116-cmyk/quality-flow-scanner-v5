# FAILURE MEMORY — QF-TD-LIVE-CLEARANCE-PATH-BINDING-20261017-15 r1

No failed attempts. All five matrix productions (the new -15 path-binding
matrix and the -14 executor / r4 gate / -13 transaction regressions) passed
on their first runs, twice each under kernel network denial, byte-identical
within each pair and identical to the pinned regression matrices.

Preventive discipline carried in from -14 (not a -15 failure): all trial
commands ran with TMPDIR on the overlay filesystem (package-local
tmp_scratch/) rather than the 512 MiB /tmp tmpfs whose exhaustion flaked
the -14 attempt-1 gate runs, and regression runs were serial. No repair
minutes were used (budget: one <=6-minute repair of <=20 total).
