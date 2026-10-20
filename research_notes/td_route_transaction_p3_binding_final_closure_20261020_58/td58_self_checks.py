#!/usr/bin/env python3
"""-58 pre-execution self-checks (static + synthetic; executes NO
proof step). Verifies: the v10 derivation from EXECUTED v9 is
confined to the spec-6303549678 sanctioned changes (identity/lease
+ v9 hash gate + pilot-stage token + the SS.3 _c4h_mod binding
correction); the corrected P2 digest checker (reused from v9) still
passes its positive and rejects its negative on the pinned
supplement bytes; the binding guard predicate fails closed on
synthetic entrypoint/module mismatches (absent _c4h_mod, non-module
_c4h_mod, _c4h_mod whose file/sha is a different module)."""
import ast, hashlib, importlib.util, json, sys, types
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent
PKG57 = NOTES / "td_route_transaction_digest_p3_closure_20261020_57"
PKG56 = NOTES / "td_route_transaction_collision_safe_remainder_20261020_56"
PKG49 = NOTES / "td_route_transaction_offline_proof_cli_closure_20261020_49"
PKG48 = NOTES / "td_route_adoption_transaction_prep_20261020_48"

V9_PIN = "c96ef6dc9c81cb718431dbbfe4688ddb8467bc844b8535bc8d638240666aacbe"
SUPP_PIN = "55ad6f40509ac77f0634b8ab4208bf39017219ae065e240af852ac581c1acca5"
EXPECTED = "6b030c62fdaf3cd738001a438b6f6a562b381b93b29dd8b299753de6aebe4fa5"
ORIG_PROOF = "36bc3a89bd266b9d7478d7f6082addd7b764a824bac45afdcbe534eb1d37f21a"
CAND_SHA = "3f432e7e30d3d962b36cb0c82cae9658cf269c3214beb918402f8645a3fe0ad1"

def H(b): return hashlib.sha256(b).hexdigest()
def HF(p): return H(Path(p).read_bytes())

checks = []
def ck(name, cond, detail=""):
    checks.append({"check": name, "pass": bool(cond), "detail": str(detail)})

v9p = PKG57 / "proof_driver_v9.py"
v10p = HERE / "proof_driver_v10.py"
ck("v9_base_pin", HF(v9p) == V9_PIN, HF(v9p))
v9, v10 = v9p.read_text(), v10p.read_text()

def fn_sources(src):
    tree = ast.parse(src)
    return {n.name: ast.get_source_segment(src, n)
            for n in tree.body if isinstance(n, ast.FunctionDef)}
f9, f10 = fn_sources(v9), fn_sources(v10)
ck("v10_no_new_functions", set(f10) - set(f9) == set(),
   str(sorted(set(f10) - set(f9))))
ck("v10_no_functions_removed", set(f9) - set(f10) == set(),
   str(sorted(set(f9) - set(f10))))
SANCTIONED = {"hash_gates", "build_shadow_gitaware", "p3"}
ident = [n for n in f9 if n not in SANCTIONED and f9[n] == f10.get(n)]
ck("unsanctioned_functions_byte_identical",
   len(ident) == len(f9) - len(SANCTIONED & set(f9)),
   f"{len(ident)}/{len(f9) - len(SANCTIONED & set(f9))} identical")
# build_shadow diff confined to the pilot-stage token
ck("build_shadow_token_only",
   f10["build_shadow_gitaware"].replace("td58_pilot_stage", "td57_pilot_stage")
   == f9["build_shadow_gitaware"])
# p3: evidence sourced from _c4h_mod; fail-closed guard BEFORE the
# first dereference (HF(cmod.__file__) / cmod.construct_4h)
p3s = f10["p3"]
ck("p3_sources_c4h_mod", 'getattr(v7, "_c4h_mod", None)' in p3s)
ck("p3_no_sysmodules_evidence",
   'cmod = sys.modules.get("construct_4h_v3_cliguard")' not in p3s)
gi = p3s.index('fail("P3_BINDING", p)')
ck("p3_guard_before_deref",
   gi < p3s.index("HF(cmod.__file__)") and gi < p3s.index("cmod.construct_4h"))
ck("p3_checks_pin_and_identity",
   "PIN_CONSTRUCTOR_CAND" in p3s and "v7.construct_4h is cmod.construct_4h" in p3s
   and '"construct_4h" in sys.modules' in p3s)
# identity pins inside v10
ck("v10_identity", "QF-TD-ROUTE-TRANSACTION-P3-BINDING-FINAL-CLOSURE-20261020-58" in v10
   and "qf_td58_stage" in v10 and "qf_td58_wt" in v10
   and "qf_td58_owner_lease.json" in v10 and '"6303549678"' in v10)

# --- corrected digest checker reuse (import v10 in-process) ------
sys.argv = ["self_checks", "/dev/null"]
spec = importlib.util.spec_from_file_location("v10_driver", str(v10p))
drv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drv)
supp = json.loads((PKG48 / "fresh_supplement_v2_candidate.json").read_bytes())
ck("supplement_pin", HF(PKG48 / "fresh_supplement_v2_candidate.json") == SUPP_PIN)
pos = drv.proof_digest_check(supp)
ck("digest_positive", pos["ok"] is True)
neg = json.loads((PKG48 / "fresh_supplement_v2_candidate.json").read_bytes())
val = next(iter(neg["calendar_proofs"].values()))
neg["calendar_proofs"] = {ORIG_PROOF: val}
for v in neg["entries"].values():
    v["calendar_proof_digest"] = ORIG_PROOF
ck("digest_negative_rejected", drv.proof_digest_check(neg)["ok"] is False)

# --- binding guard predicate: synthetic mismatches fail closed ---
def binding_ok(v7mod, staged_ps):
    """Mirror of the v10 p3 binding predicate (guard + identity)."""
    cmod = getattr(v7mod, "_c4h_mod", None)
    if cmod is None or not isinstance(cmod, types.ModuleType):
        return False
    try:
        return (Path(cmod.__file__).resolve()
                == (staged_ps / "construct_4h_v3_cliguard.py").resolve()
                and HF(cmod.__file__) == CAND_SHA
                and v7mod.construct_4h is cmod.construct_4h)
    except Exception:
        return False

import tempfile
tmp = Path(tempfile.mkdtemp(prefix="td58_selfcheck_"))
ps = tmp / "stage"; ps.mkdir()
cand_file = ps / "construct_4h_v3_cliguard.py"
cand_file.write_bytes((PKG49 / "construct_4h_v3_cliguard.py").read_bytes())
spec2 = importlib.util.spec_from_file_location("syn_cand", str(cand_file))
good_mod = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(good_mod)
good_v7 = types.SimpleNamespace(_c4h_mod=good_mod, construct_4h=good_mod.construct_4h)
ck("binding_positive_synthetic", binding_ok(good_v7, ps) is True)
ck("binding_negative_absent",
   binding_ok(types.SimpleNamespace(construct_4h=good_mod.construct_4h), ps) is False)
ck("binding_negative_nonmodule",
   binding_ok(types.SimpleNamespace(_c4h_mod=42, construct_4h=None), ps) is False)
other = tmp / "other.py"; other.write_bytes(b"# different module\ndef construct_4h():\n    pass\n")
spec3 = importlib.util.spec_from_file_location("syn_other", str(other))
other_mod = importlib.util.module_from_spec(spec3); spec3.loader.exec_module(other_mod)
ck("binding_negative_mismatch_module",
   binding_ok(types.SimpleNamespace(_c4h_mod=other_mod,
                                    construct_4h=other_mod.construct_4h), ps) is False)
ck("binding_negative_wrong_function",
   binding_ok(types.SimpleNamespace(_c4h_mod=good_mod,
                                    construct_4h=other_mod.construct_4h), ps) is False)

out = {"task": "QF-TD-ROUTE-TRANSACTION-P3-BINDING-FINAL-CLOSURE-20261020-58",
       "checks": checks,
       "n_pass": sum(1 for c in checks if c["pass"]),
       "n_total": len(checks)}
(HERE / "td58_self_check_results.json").write_text(json.dumps(out, indent=1))
print(json.dumps({"n_pass": out["n_pass"], "n_total": out["n_total"],
                  "failed": [c["check"] for c in checks if not c["pass"]]}))
