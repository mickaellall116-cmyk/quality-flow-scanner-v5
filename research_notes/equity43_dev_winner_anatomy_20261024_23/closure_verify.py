#!/usr/bin/env python3
"""Fail-closed verifier for the -23 supplement path-census provenance closure.

Recomputes the census chain end-to-end from the committed derived record:
  1. committed input_inventory.json / census_output.json must match the
     package SHA256_MANIFEST.txt entries (output-hash check);
  2. every private raw input named in the inventory must exist, hash-match,
     and match its recorded row count + first/last timestamps;
  3. the analysis ledger (local witness copy) must hash-match the inventory;
  4. the committed deep2.py must hash-match the inventory, is re-run, and its
     derived census (counts + breach keys) must equal census_output.json
     exactly — no missing, duplicate, or drifted keys.
Any failure prints STOP:<reason> and exits nonzero. Success prints PASS lines
and exits 0. Derived-only: no OHLCV values are printed or persisted here
(only datetimes/counts/hashes are read from the raw captures)."""
import json, os, sys, hashlib, subprocess, tempfile

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()

def stop(reason):
    print(f'STOP: {reason}')
    sys.exit(2)

def main():
    ap = {'--pkg': os.path.dirname(os.path.abspath(__file__)),
          '--base': os.path.expanduser('~/workspace/qf_td13_stage/archive_clone/captures'),
          '--ledger': '/tmp/anat/trade_ledger.json',
          '--work': '/tmp/anat'}
    args = sys.argv[1:]
    for i in range(0, len(args) - 1, 2):
        if args[i] in ap: ap[args[i]] = args[i + 1]
    pkg, base, ledger_path, work = ap['--pkg'], ap['--base'], ap['--ledger'], ap['--work']

    inv_p = os.path.join(pkg, 'input_inventory.json')
    cen_p = os.path.join(pkg, 'census_output.json')
    man_p = os.path.join(pkg, 'SHA256_MANIFEST.txt')
    for p in (inv_p, cen_p, man_p):
        if not os.path.exists(p): stop(f'missing committed file: {os.path.basename(p)}')

    # 1. committed outputs vs package manifest (output-hash integrity)
    manifest = {}
    for line in open(man_p):
        parts = line.split()
        if len(parts) == 2: manifest[parts[1]] = parts[0]
    for name, p in (('input_inventory.json', inv_p), ('census_output.json', cen_p)):
        want = manifest.get(name)
        if want is None: stop(f'{name} absent from SHA256_MANIFEST.txt')
        got = sha256_file(p)
        if got != want: stop(f'output-hash mismatch: {name} sha256 {got} != manifest {want}')
    print('CHECK manifest: input_inventory.json + census_output.json hashes match SHA256_MANIFEST.txt')

    inv = json.load(open(inv_p)); cen = json.load(open(cen_p))
    if cen.get('input_inventory_sha256') != sha256_file(inv_p):
        stop('census_output.json input_inventory_sha256 does not match the committed inventory file')

    # 2. private inputs: existence, hash, rows, first/last timestamps
    n = 0
    for e in inv['symbols']:
        p = os.path.join(base, e['namespace'], 'raw', f"{e['symbol']}__DEV.json")
        if not os.path.exists(p): stop(f"missing input: {e['symbol']} ({e['namespace']})")
        got = sha256_file(p)
        if got != e['raw_sha256']: stop(f"input-hash drift: {e['symbol']} {got} != {e['raw_sha256']}")
        vals = json.load(open(p))['values']
        if len(vals) != e['row_count']: stop(f"row-count drift: {e['symbol']} {len(vals)} != {e['row_count']}")
        if vals[0]['datetime'] != e['first_timestamp'] or vals[-1]['datetime'] != e['last_timestamp']:
            stop(f"timestamp drift: {e['symbol']}")
        n += 1
    print(f'CHECK inputs: {n} symbol captures exist, hash-match, row counts + first/last timestamps match')

    # 3. ledger witness
    if not os.path.exists(ledger_path): stop(f'missing ledger witness: {ledger_path}')
    if sha256_file(ledger_path) != inv['ledger_input']['sha256']:
        stop('ledger-hash drift vs inventory')

    # 4. derivation code + deterministic re-run of the census
    code_p = os.path.join(pkg, 'deep2.py')
    if not os.path.exists(code_p): stop('missing deep2.py in package')
    if sha256_file(code_p) != inv['derivation_code']['sha256']:
        stop('deep2.py hash drift vs inventory')
    out_json = os.path.join(work, 'intrabar.json')
    before = sha256_file(out_json) if os.path.exists(out_json) else None
    r = subprocess.run([sys.executable, code_p], capture_output=True, text=True)
    if r.returncode != 0: stop(f'deep2.py re-run exit {r.returncode}: {r.stderr.strip()[-200:]}')
    eoline = [ln for ln in r.stdout.splitlines() if ln.startswith('ENTRY-OPEN verification:')]
    if eoline != ['ENTRY-OPEN verification: 191 match / 0 mismatch of 191']:
        stop(f'entry-open verification line drift: {eoline}')
    ib = json.load(open(out_json))
    keys = sorted([list(x) for x in ib['pre_breach']])
    if len(keys) != len(set(tuple(x) for x in keys)): stop('duplicate breach keys in re-run census')
    if keys != cen['breach_keys']: stop('breach-key set drift vs committed census_output.json')
    checks = [
        ('closed_trades_walked', ib['counts']['trades_walked']),
        ('intrabar_stop_breach_pre_tp1', ib['counts']['intrabar_stop_breach_pre_tp1']),
        ('dual_touch_same_4h_bar', len(ib['dual4h'])),
        ('dual_undetermined_1h', len(ib['und1h'])),
        ('sim_tp1_and_exit_same_bar', len(ib['sim_samebar'])),
    ]
    for name, got in checks:
        if cen[name] != got: stop(f'count drift: {name} committed {cen[name]} != recomputed {got}')
    lab_p = os.path.join(pkg, 'ordering_labels.json')
    if sha256_file(lab_p) != cen['ordering_labels_file_sha256']:
        stop('ordering_labels.json hash drift vs census_output.json')
    lab = json.load(open(lab_p))
    if dict(lab['census']) != cen['ordering_label_census']: stop('ordering label census drift')
    sf = sorted([[t['symbol'], str(t['entry_time'])[:16].replace('T', ' ')]
                 for t in lab['trades'] if t['label'] == 'CONFIRMED_STOP_FIRST'])
    if sf != keys: stop('CONFIRMED_STOP_FIRST keys != breach keys')
    print('CHECK census: re-run reproduces committed counts, breach keys (87, no duplicates), label census 87/85/15/0/0')
    print(f'PASS: provenance closure verified (intrabar witness sha256 {sha256_file(out_json)}, prior {before})')
    return 0

if __name__ == '__main__':
    sys.exit(main())
