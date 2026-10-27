# Zero-call / live-state-untouched receipt — Option B successor build

Build window: 2026-10-26 evening ET. This build made **no Twelve Data
calls** (the only transport exercised anywhere was the offline stub in
the fixtures, against a copied state in a scratch directory).

## Live stage before the build

```
63e2ccbfe836b5f81e1d8285dff7626e28f6f8936fa5ce32cbf712268dd1e8f2  pilot_runner.py
71fb1acb9d4d8e6ac307de0c1eba95f0ed9c79965fb9ab269a96855a0c44857c  state/pilot_state.json
596e9e81c7b62a2370c4caa6df8ac9149657189a4684f419784ca4914f6922db  run_manifest.json
```

Live state at build start: daemon alive (heartbeat advancing), status
`held`, `tripwire.hold = true`, `desk_calls = 0`, `stopped = null`, no
`state/tripwire_clear.json` present.

## Live stage after the build (verified at delivery)

- `sha256sum -c` on the three files above: **all OK** (byte-identical).
- `state/` still contains no `tripwire_clear.json`; hold still `true`;
  `desk_calls` still **0**.
- The fixed runner exists **only** in this package and the build
  directory — the stage `pilot_runner.py` is still the pre-fix file
  (SHA-256 `63e2ccbf…`), so the live daemon and any watchdog restart
  keep running the current code until the deployment step in
  `SUCCESSOR_README.md` is executed tomorrow.
- Sole write inside the stage: the pre-fix backup
  `work/pilot_runner.py.bak_20261026_optionB_prefix` (a copy; the daemon
  neither reads nor executes it).
