# Blind Review Packet — delivery manifest

Packet built 2026-10-24 (America/New_York) at the request of ChatGPT
(Slack #qualityflowscaner TS 1792896517.514959) for an independent Claude
blind review of the Quality Flow DEV record. Contents carry data artifacts,
configuration, and source code only — no analysis memos, findings, or
conclusions from Muse or ChatGPT.

## Download

- File: `QF_DEV_blind_review_packet.zip` (in this directory)
- Direct download (pinned to the delivery commit):
  https://raw.githubusercontent.com/mickaellall116-cmyk/quality-flow-scanner-v5/57cb065819813b396da074782381a7e397bfbdb0/research_notes/blind_review_packet_20261024/QF_DEV_blind_review_packet.zip
- ZIP SHA-256: `2ef1e8c38310ceec506bc26507627abcbe405ffd332bdc20ec943d76fb940027`
- ZIP size: 147,332 bytes
- Delivery commit: `57cb065819813b396da074782381a7e397bfbdb0` (verified
  ancestor of origin/main; the downloaded bytes were re-hashed and match
  the ZIP SHA-256 above)

## Source pin

Every file inside the ZIP was extracted from pinned commit
`555ebb1f13586460b07b4e39e5e48bdfa83a0287` of this repository. The ZIP's
internal `MANIFEST.json` lists each file's packet path, repository source
path, byte size, and SHA-256; the ZIP's internal `README.md` is neutral
(facts, definitions, provenance, known missing fields, frozen governance).
The frozen experiment configuration's canonical pin is
`87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706`
(recorded in `results.json`).

## Contents (15 files)

- `data/trade_ledger.json` — 590 candidate records (-13), sha256
  `267e794c284a409d7d9b6d8e1056c452976b59746062e9e6e18c5664b74c003b`
- `data/results.json` — DEV run results (-13), sha256
  `42b05ce32ce545e95b919692ad3736316f8f42d9f603b1db42005342be413956`
- `data/register_lifecycle66.json` — 66-loss evidence register (-25),
  sha256 `767e7fc27b8799fd520a7ff8f109d2f6d48a23edbf7503400968feffcc2288a4`
- `config/experiment_config.json`, `config/universe43.json` — frozen
  configuration and the pinned 43-symbol universe
- `source/run_study13.py` — the -13 run driver, verbatim as committed
- `source/engine/` — successor simulator + strategy source at committed
  pins: `pine_backtest.py` `874d2a9b…`, `pine_stack/pine_stack.py`
  `8d4a964f…`, `asof_benchmark.py` `f0f4582c…`, `scanner_rules.py`
  `62aa743a…`, `pine_ranking/pine_ranking.py` `77afae0d…`,
  `pine_signal_quality/pine_signal_quality.py` `b1b39ee8…`,
  `pine_exposure/pine_exposure.py` `9f646161…`
- `README.md`, `MANIFEST.json` — written for this packet

## Verification performed

- Every extracted file's SHA-256 matches its committed pin/manifest value.
- Fresh-extract of the finished ZIP: all 14 manifested files re-hash to the
  manifest values; the only unmanifested file is `MANIFEST.json` itself.
- Exclusion scans, run before packaging and again on the finished ZIP's
  full content stream: zero hits for credential/token/private-key patterns,
  zero references to the private data archive or credential files, zero
  2023 dates and zero 2024-01-01 to 2024-09-15 dates in any data or source
  file (the only occurrences of the holdout window dates are the README's
  governance lines naming the sealed window, as required). All timestamps
  in the data files fall inside the DEV window (2024-09-16 to 2026-10-16).
- Completeness against the request: every requested item is included;
  nothing requested is missing. By the request's own exclusion, no raw
  market bars are included, so the simulators cannot be re-executed from
  the packet alone; the packet supports independent analysis of the
  ledger/records and a full source audit.
