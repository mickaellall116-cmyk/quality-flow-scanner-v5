# ERD v0.1 Amendment 2 — PROPOSED freeze manifest (pre-data contract)

**Status: PROPOSED — not frozen.** Prepared 2026-09-28 per ChatGPT's REVIEW
(PASS TO MATERIALIZE PRE-DATA CONTRACT / NOT YET FREEZE-READY, issue #1,
2026-09-28T17:42Z). Posted for one final mechanical verification. Nothing is
frozen until: Mike's explicit approval + ChatGPT adversarial sign-off on the
exact rev 4 text + all READY items hashed on main + issue #3 annotated.

Amendment text: `new_system/erd-v0.1-preregistration-amendment-2-DRAFT-rev4.md`
(rev 4 supersedes rev 3 on exactly two wording points: §1.2 data-independence
rule; Authority freeze language).

| # | Artifact | Path | SHA-256 | Status |
|---|----------|------|---------|--------|
| 1 | Amendment rev 4 exact text | `new_system/erd-v0.1-preregistration-amendment-2-DRAFT-rev4.md` | `e8f1e010a1599497c7080fa85da342dc959f179e6bb0f4967c857b2232d1fb25` | READY |
| 2 | Sampling frame | — | — | **PENDING-DATA** (see note) |
| 3 | Exact 50-event list | — | — | **PENDING-DATA** (see note) |
| 4 | Sampler code + config | `new_system/erd-a2-freeze/item04_sampler.py` / `item04_sampler_config.json` | `082e9c5e07416f635cf0d710524553fca1828a0ccb41ceb648cbe2311ee837e5` / `8b322ef2c342dfddd54cb45df79a471a7bba4d3aeefd0c14624eaec742e6c83b` | READY — determinism self-check PASS on synthetic frame (`item04_determinism_check.log`, `c2e0d8a4d963b2ac8304d5a1f793e9e5c0cf1cbeffff6950d6c07971f8a1d3b3`): byte-for-byte reproduction, quotas met, transition draw deterministic |
| 5 | Manual verification procedure | `new_system/erd-a2-freeze/item05_manual_verification_procedure.md` | `3f5f83d34960f9e313a9a6c7fbe7c5719cf76c2ed47295f88fa1590d61cbb6fe` | READY (§1.4 + §1.5 + §1.6 + §1.7 quoted verbatim from rev 4) |
| 6 | Calendar/timezone/environment versions | `new_system/erd-a2-freeze/item06_environment_versions.json` | `75da5a6966131e69c0b7f96a5cff69f4fdd90a2b65aac7ff0f500208b7ee1c05` | READY — Python 3.12.3, system tzdata 2026c; NYSE calendar source NOT YET PINNED (no in-repo NYSE calendar dependency; pinned at freeze) |
| 7 | PIT/revision test spec | `new_system/erd-a2-freeze/item07_pit_test_spec.md` | `af2c997c0d18337ed2a22ab7c0fdbcd5fa62dfd380c70a3ae785616711ddecc2` | READY (§1.6(c) quoted verbatim) |
| 8 | Provider-selection rule | `new_system/erd-a2-freeze/item08_provider_selection_rule.md` | `a8ce7d13ae1541c2d9e5b9a7b706c64a173470abceaefcc7614b005b06cefdb2` | READY (§2.2 quoted verbatim) |
| 9 | Availability/leakage spec | `new_system/erd-a2-freeze/item09_availability_leakage_spec.md` | `8627d49de41b6198fa524caa5e647c5a56bac0a63f6426152834d6358df39e1a` | READY (§1.6(e) quoted verbatim) |
| 10 | Issue #3 supersession annotation | `new_system/erd-a2-freeze/item10_issue3_annotation.txt` | `a8144261d045e0644ef71db6c7eaecd411c4428116d26f93f1004de03222b4d4` | READY (§6 text, to be posted at freeze) |
| 11 | Independent archival equivalent | `new_system/erd-a2-freeze/item11_archival_equivalent.txt` | `541a72d1ede0e4334da7d343d3c36be5f8ccedd1bda1e6a790b3511fddde82b4` | READY — frozen value: `none` |

## PENDING-DATA note (items 2–3)

The sampling frame (item 2) requires the licensed data build: securities
master with permanent security IDs + price history 2012→present per
Amendment 1 §§7–8 (Norgate first choice / Intrinio EOD fallback), including
delisted names and ticker-change history. No provider access or purchase is
authorized (standing rule; Mike's ~$1,500 budget vs Intrinio's $950/mo
Zacks minimum). Building a frame from free/current-only sources would
introduce survivorship bias and violate the frozen frame definition, so
items 2–3 are honestly marked pending rather than materialized from
inadequate data. The 50-event list (item 3) is derived from the frame via
the frozen sampler (item 4) and cannot exist before it.

**No candidate-provider data pull before final freeze. No ERD performance
work before the amended gate passes.**
