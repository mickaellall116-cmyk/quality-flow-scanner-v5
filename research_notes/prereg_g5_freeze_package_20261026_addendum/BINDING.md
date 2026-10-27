# G5 Addendum — Binding of the signable decision text to the reviewed package

**Purpose.** ChatGPT's independent review of the G5 freeze package
(Issue #1 comment `6434458722`) verified the package (6/6 manifest
entries reconcile) and closed with two narrow holds. Hold 1: the
signable decision text must be bound to the exact reviewed bytes —
the package commit plus the package's own manifest hash — otherwise
the package documents (`OPEN_ITEMS_CHECKLIST.md`, `O4_PROCEDURE.md`,
`MECHANICAL_CHECKS.md`) can drift after review and a signature would
adopt text nobody reviewed. This document is that binding. It lives
**outside** the reviewed package, in this sibling addendum directory,
so the reviewed bytes are not mutated.

## The pins

- **Package:** `research_notes/prereg_g5_freeze_package_20261026/`
- **Package commit:** `503731183b4d9385059b83e1996b5bc3989ebe8d`
- **Package manifest:** `SHA256_MANIFEST.txt` in that directory at
  that commit.
  - Byte-exact SHA-256 of the manifest blob as committed:
    `81b881b3574fba5156107bcac0e53e27472dfc9c8fa8217e7f6de17f91b8975e`
    (computed from the git blob at the package commit; verified by
    Muse at addendum build).
  - Internal check: all 6 manifest entries verify against the
    committed blobs at the package commit (6/6) —
    `FREEZE_MANIFEST.md` `0c64a2e3…`, `G5_DECISION_TEXT.md`
    `9f6c9441…`, `OPEN_ITEMS_CHECKLIST.md` `467b4bd8…`,
    `O4_PROCEDURE.md` `3d98be8e…`, `MECHANICAL_CHECKS.md`
    `bde388d6…`, `VERIFY_MANIFEST.py` `a5d74023…`.
  - **Reconciliation with the review's cited value:** comment
    `6434458722` cites the manifest SHA as
    `2930ac9080fbf6ff866df7823ddf458d5c3472135d385ecdd023f043a30a90bd`.
    That value is exactly `sha256(manifest blob bytes + one
    additional trailing newline)` — an extraction artifact (one
    extra `"\n"`), not different content. Both values are recorded
    here so the two sides reconcile byte-for-byte. The authoritative
    pin for this binding is the byte-exact blob hash above, because
    the committed bytes are what a signature must identify. Flagged
    for ChatGPT's concurrence.

## What is bound

The signable text is `G5_DECISION_TEXT.md` at the package commit
(blob SHA-256
`9f6c9441aba0bdd3608818cafd438b0f393fe8be558820603311b0fa1ff8afb4`).
Its operative sentence:

> I freeze Quality Flow Edge Validation Pre-Registration **v1.0**,
> as amended by **v1.0.1** and **v1.0.2** and closed out by the
> 2026-10-26 closure addendum — the Frozen Protocol — exactly as
> enumerated in `FREEZE_MANIFEST.md` in
> `research_notes/prereg_g5_freeze_package_20261026/`, whose SHA-256
> hashes are the identity of the frozen set: `PREREG_V10.md`
> `29a0477a13e52ff4467193f69df7ef107048a8801f64c61f43de28d40d2850c6`
> (bootstrap seed `2999475941474119668`), amendments at commits
> `247a1c742c8d10c7a9ef9bb82abbfee5d5747e8a` and
> `4b45a3e48b82064880db28ce8c82079d0655d3e3`, closure addendum at
> `c31c61391c62b09dbfd008bc2cf91e7c511bc1f0`.

(The full verbatim text — including the B2 ECONOMICS-FIRST contract,
the §9 PARTLY CONTAMINATED readings, the Tier 3 11-name list, and the
"authorizes no run" clause — is the file at the pin above. The
quotation here is an identifier, not a substitute.)

## Effect of signature

Mike's signature or verbatim adoption adopts the decision text
**exactly as pinned** at the package commit and manifest hash above —
no other version. The package documents (`FREEZE_MANIFEST.md`,
`G5_DECISION_TEXT.md`, `OPEN_ITEMS_CHECKLIST.md`, `O4_PROCEDURE.md`,
`MECHANICAL_CHECKS.md`, `VERIFY_MANIFEST.py`,
`SHA256_MANIFEST.txt`) are FROZEN at those pins from this binding
forward.

## Drift rule

Any later edit to any package document — however small — voids this
binding for the edited document: edited bytes are not the reviewed
bytes and are not adopted by a signature under this binding.
Restoring validity requires a new package commit, a new manifest,
and a new binding (a new addendum), followed by a fresh signature. A
signature obtained while this binding stands covers only the pinned
bytes.

## Status

Prepared by Muse, 2026-10-27. This is not a signature request; G5
remains open until Mike adopts the pinned text. O4 remains
separately gated (see `O4_BASIS_PIN.md` in this addendum).

— Muse
