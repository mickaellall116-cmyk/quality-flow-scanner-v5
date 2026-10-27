"""Reproduce every hash in FREEZE_MANIFEST.md from the repository alone.
Reads committed blobs via git show at the frozen package commits; computes
no performance quantity. Run from anywhere inside the repo.
"""
import ast, hashlib, json, subprocess, sys

REPO = subprocess.run(["git","rev-parse","--show-toplevel"], capture_output=True, text=True).stdout.strip()
def show(commit, path):
    r = subprocess.run(["git","show",f"{commit}:{path}"], cwd=REPO, capture_output=True)
    if r.returncode != 0: raise SystemExit(f"FAIL {commit}:{path}: {r.stderr.decode()[:200]}")
    return r.stdout
def sha(b): return hashlib.sha256(b).hexdigest()
def tree(commit, prefix):
    r = subprocess.run(["git","ls-tree","-r","--name-only",commit,"--",prefix], cwd=REPO, capture_output=True, text=True)
    return sorted(r.stdout.split())

PKGS = {
 "4ffb8fb": "research_notes/prereg_v10_20261026",
 "247a1c7": "research_notes/prereg_v10_1_amendment_20261026",
 "4b45a3e": "research_notes/prereg_v10_2_wording_20261026",
 "c31c613": "research_notes/prereg_closure_20261026",
}
out = {}
for commit, prefix in PKGS.items():
    files = {}
    for p in tree(commit, prefix):
        files[p] = sha(show(commit, p))
    out[commit] = files
    # cross-check the package's own manifest
    man = [p for p in files if p.endswith("SHA256_MANIFEST.txt")]
    if man:
        txt = show(commit, man[0]).decode()
        ok, bad = 0, []
        for line in txt.splitlines():
            line=line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split()
            if len(parts) < 2: continue
            h, name = parts[0], parts[-1].lstrip("*")
            full = prefix + "/" + name if not name.startswith(prefix) else name
            if full in files:
                if files[full]==h: ok+=1
                else: bad.append((full,h,files[full]))
        out.setdefault("_manifest_check",{})[commit] = {"ok":ok,"bad":bad,"manifest":man[0]}

# Reproduce C1 config canonical pin from driver source
src = show("origin/main","research_notes/equity43_dev_order_censor_20261023_13/run_study13.py").decode()
tree_ast = ast.parse(src)
cfg = None
for node in tree_ast.body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0],"id","")=="EXPERIMENT_CONFIG":
        cfg = ast.literal_eval(node.value)
canon = json.dumps(cfg, sort_keys=True, separators=(",",":")).encode()
out["_c1_config"] = {"canonical_sha256_recomputed": sha(canon),
                     "recorded_pin": "87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706",
                     "match": sha(canon)=="87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706",
                     "cost_views_in_config": cfg.get("cost_views")}

# Tier3 canonical array hashes
for commit, path in [("247a1c7","research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/tier3_list_v1_2.json"),
                     ("4b45a3e","research_notes/prereg_v10_2_wording_20261026/tier3_inputs/tier3_list_v1_2.json")]:
    d = json.loads(show(commit,path))
    arr = d["tier3_list"]
    ch = sha(json.dumps(arr, sort_keys=True, separators=(",",":")).encode())
    out.setdefault("_tier3",{})[commit] = {"container": sha(show(commit,path)), "array_canonical": ch,
        "names":[e["symbol"] for e in arr], "rank_12": d.get("rank_12"), "rank_12_status": d.get("rank_12_status")}
print(json.dumps(out, indent=1))
