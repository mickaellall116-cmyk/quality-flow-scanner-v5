"""Frozen pin set for the shadow closeout candidate
(shadow_closeout_20261022).

This module is the candidate's EXPECTED_PINS: the exact values
the launch manifest must carry, verified at every startup by
shadow_signal_core (manifest digest recompute + pin-set
equality + on-disk module hash recompute). Values were frozen
at package build time, 2026-10-22:

  candidate_commit — the repair-lineage commit this closeout
    successor is cut from (4130e74, shadow successor V5/V8
    repair). Binding the successor's own commit is impossible
    (self-reference); per ChatGPT's verdict the launch-day
    re-pin replaces this with the then-current candidate
    commit. The package's own git commit + SHA256_MANIFEST
    pin these bytes at rest.
  stack_pins — the six live-stack module pins, carried
    unchanged from the successor/repair lineage (the runner's
    PINNED_STACK; verify_pins() enforces them on the live
    path before any adapter use).
  module_hashes — sha256 of THIS package's candidate module
    files as shipped. This pins module itself is excluded
    (self-reference); its bytes are pinned by the package
    SHA256_MANIFEST and git.
  universe — the frozen 250 cohort (UX51 51 + X2 199, ordered
    as hybrid_exit_test.UNIVERSE_X + v54_universe_x2.
    UNIVERSE_X2): count, ordered digest (sha256 of the
    LF-joined ordered symbols + trailing LF, UTF-8), and the
    sha256 of the shipped universe.json artifact (ordered list
    + symbol classes: 25 crypto *-USD pairs, 225 equity).
  calendar — the adopted calendar of record: 751-session XNYS
    union (three-gate freeze a126ce5), version string, the
    sha256 of the shipped session_table.json artifact, and
    the session count.
  rule_version — the frozen V5.4 rule version string carried
    by every production signal row (v54_rule_version).
  authorization — the launch authorization slot: artifact
    name, digest None, state NOT_AUTHORIZED. No authorization
    artifact exists; this package creates none. At a future
    launch GO the artifact's digest is bound here by the
    launch-day re-pin, never before.
"""

SESSION_TABLE_FILENAME = "session_table.json"
UNIVERSE_FILENAME = "universe.json"

EXPECTED_PINS = {
    "candidate_commit":
        "4130e74ef2433bf4f491edb6e3a886419063d968",
    "candidate_lineage":
        "798de18 successor -> 4130e74 repair -> closeout v3",
    "stack_pins": {
        "v54_engine.py":
            "bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb",
        "v54_rules.py":
            "1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a",
        "scanner_rules.py":
            "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
        "masterscanner_api.py":
            "c3e95b25b114a50c4129360f24f4fd27471b000a7749fe750abf038f1abf0a21",
        "v54_universe_x2.py":
            "44b0d8ba5a7ea6415652fdfa1e89a0f9bb57d191bfb0d66c578f9d7a3f5880c9",
        "hybrid_exit_test.py":
            "9140504f6449cafe62e1647ccbacaa384427a56ff111cab8c6e9298a220cf45b",
    },
    "module_hashes": {
        "shadow_signal_core.py":
            "71244848d245858af0df1b34c1418a7581e709c0454178847a3410d4310be294",
        "shadow_signal_runner.py":
            "409a79a1d938386323c13feabf259ddf5327ffe241fbd930bea7eb1bb32ff3f9",
    },
    "universe": {
        "count": 250,
        "ordered_digest":
            "77381fe4f82b2722474e20f43ddd87da99c37b921fe5c608d6abfb2eb0f7c6ea",
        "file_sha256":
            "63ed21e858ce9dde2f8c2fdcb3f22dac01cca771ec2c33adf6dbf291ef4b62ac",
        "crypto_count": 25,
        "equity_count": 225,
    },
    "calendar": {
        "version": "XNYS-751-UNION-20261021",
        "session_table_sha256":
            "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f",
        "sessions": 751,
    },
    "rule_version": "2026-09-15-v54",
    "authorization": {
        "artifact": "LAUNCH_AUTHORIZED.json",
        "artifact_sha256": None,
        "state": "NOT_AUTHORIZED",
    },
}
