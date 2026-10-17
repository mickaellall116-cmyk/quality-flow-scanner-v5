#!/usr/bin/env python3
"""Shared origin-verified credential-helper resolver.

QF-TD-CREDENTIAL-HELPER-PATH-BINDING-20261017-08.

One resolution route for BOTH the pre-arm dispatch gate and the armed
driver: the Twelve Data credential helper is loaded ONLY from the exact
sanctioned platform path, ONLY when its bytes hash to the pinned
SHA-256, and ONLY after its surface (named callable + allowed-host
binding) verifies by inspection. The helper callable is NEVER invoked
by this resolver: resolution is import + inspect, nothing more. No
credential material is resolved, read, logged or returned - the handle
carries origin metadata and the uninvoked callable only.

Fail-closed refusals (HelperRefusal.code):
  CREDENTIAL_HELPER_PATH_ABSENT        file (or its directory) missing
  CREDENTIAL_HELPER_TAMPERED           bytes != pinned SHA-256
  CREDENTIAL_HELPER_UNAVAILABLE        import of the exact file failed
  CREDENTIAL_HELPER_ORIGIN_MISMATCH    loaded module origin != exact path
  CREDENTIAL_HELPER_CALLABLE_MISSING   named callable absent / not callable
  CREDENTIAL_HELPER_BINDING_MISMATCH   signature lacks the allowed-host binding
  CREDENTIAL_HELPER_SWAPPED_POST_GATE  reverify(): bytes changed after issue
  CREDENTIAL_HELPER_SHADOW_INSTALLED   a foreign module already occupies the
                                       helper's import name at handoff time

The resolver never consults sys.path and never accepts a same-named
module from anywhere else: the load is bound to the exact file path via
importlib.util.spec_from_file_location under a private module name.
"""
import hashlib
import importlib.util
import inspect
import os
import sys

SANCTIONED_DIR = "/opt/hatch/skills/skill-creator/bin"
SANCTIONED_PATH = os.path.join(SANCTIONED_DIR, "dynamic_credentials.py")
# sha256 of the sanctioned platform helper, probed read-only 2026-10-17
# (7675 bytes; the Stage-0 runner imported it from this exact directory
# and completed two HTTP-200 requests).
PIN_SHA256 = "8b1f42e80a76710edf0ff2abf8a51b0cde35b06474af865de108a7ca27d6728d"
MODULE_NAME = "dynamic_credentials"
CALLABLE_NAME = "url_with_surrogate_query_param"
_PRIVATE_LOAD_NAME = "qf_verified_dynamic_credentials"


class HelperRefusal(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _signature_ok(fn):
    """Same binding rule the r2 gate used: >=2 positional parameters and
    an explicit allowed_hosts parameter (or **kwargs to carry it)."""
    try:
        params = inspect.signature(fn).parameters
    except Exception:
        return False
    positional = [p for p in params.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    has_kwargs = any(p.kind == p.VAR_KEYWORD for p in params.values())
    return len(positional) >= 2 and ("allowed_hosts" in params or has_kwargs)


class VerifiedHelper:
    """An issued handle: origin path + verified hash + the loaded module
    and its uninvoked callable. reverify() re-hashes the file so any
    post-issuance swap/tamper is caught before use."""

    def __init__(self, path, sha256, module, fn):
        self.path = path
        self.sha256 = sha256
        self.module = module
        self.callable = fn

    def reverify(self):
        try:
            now = _sha256_file(self.path)
        except Exception:
            raise HelperRefusal("CREDENTIAL_HELPER_SWAPPED_POST_GATE")
        if now != self.sha256:
            raise HelperRefusal("CREDENTIAL_HELPER_SWAPPED_POST_GATE")
        return True


def resolve(path=SANCTIONED_PATH, expected_sha256=PIN_SHA256):
    """Load + verify the helper from the exact path. Raises HelperRefusal.
    Never invokes the callable; never touches credential material."""
    apath = os.path.abspath(path)
    if not os.path.isfile(apath):
        raise HelperRefusal("CREDENTIAL_HELPER_PATH_ABSENT")
    try:
        digest = _sha256_file(apath)
    except Exception:
        raise HelperRefusal("CREDENTIAL_HELPER_PATH_ABSENT")
    if digest != expected_sha256:
        raise HelperRefusal("CREDENTIAL_HELPER_TAMPERED")
    spec = importlib.util.spec_from_file_location(_PRIVATE_LOAD_NAME, apath)
    if spec is None or spec.loader is None:
        raise HelperRefusal("CREDENTIAL_HELPER_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        raise HelperRefusal("CREDENTIAL_HELPER_UNAVAILABLE")
    if os.path.abspath(getattr(mod, "__file__", "")) != apath:
        raise HelperRefusal("CREDENTIAL_HELPER_ORIGIN_MISMATCH")
    fn = getattr(mod, CALLABLE_NAME, None)
    if fn is None or not callable(fn):
        raise HelperRefusal("CREDENTIAL_HELPER_CALLABLE_MISSING")
    if not _signature_ok(fn):
        raise HelperRefusal("CREDENTIAL_HELPER_BINDING_MISMATCH")
    return VerifiedHelper(apath, digest, mod, fn)


def same_verified_origin(module, handle):
    """True iff an already-installed module is the same verified origin
    as the handle (same exact file, same current bytes) - e.g. installed
    by an earlier handoff of this same verified helper."""
    try:
        mfile = os.path.abspath(getattr(module, "__file__", "") or "")
    except Exception:
        return False
    if mfile != handle.path:
        return False
    try:
        return _sha256_file(mfile) == handle.sha256
    except Exception:
        return False


def check_handoff_slot(handle):
    """Pre-arm handoff check for the pinned driver's import route: the
    helper's import name must be either free or already occupied by this
    same verified origin. A foreign occupant is a shadow -> refuse."""
    existing = sys.modules.get(MODULE_NAME)
    if existing is not None and not same_verified_origin(existing, handle):
        raise HelperRefusal("CREDENTIAL_HELPER_SHADOW_INSTALLED")
    return True


def install_handoff(handle):
    """Hand the verified module to the driver's by-name import. Call
    only after check_handoff_slot() passed in the same flow."""
    sys.modules[MODULE_NAME] = handle.module
    return handle.module


def probe_surface(path):
    """Read-only surface taxonomy for one candidate path (spec step 1).
    Distinguishes: PATH_ABSENT / IMPORT_ERROR / CALLABLE_ABSENT /
    BINDING_MISMATCH / SURFACE_PASS. Imports for inspection only; the
    callable is never invoked."""
    apath = os.path.abspath(path)
    out = {"path": apath, "exists": os.path.isfile(apath), "sha256": None,
           "classification": None}
    if not out["exists"]:
        out["classification"] = "PATH_ABSENT"
        return out
    try:
        out["sha256"] = _sha256_file(apath)
    except Exception:
        out["classification"] = "PATH_ABSENT"
        return out
    spec = importlib.util.spec_from_file_location(_PRIVATE_LOAD_NAME + "_probe", apath)
    if spec is None or spec.loader is None:
        out["classification"] = "IMPORT_ERROR"
        return out
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001 - taxonomy record
        out["classification"] = "IMPORT_ERROR"
        out["import_error"] = type(e).__name__
        return out
    fn = getattr(mod, CALLABLE_NAME, None)
    if fn is None or not callable(fn):
        out["classification"] = "CALLABLE_ABSENT"
        return out
    if not _signature_ok(fn):
        out["classification"] = "BINDING_MISMATCH"
        return out
    out["classification"] = "SURFACE_PASS"
    out["callable"] = CALLABLE_NAME
    out["signature"] = str(inspect.signature(fn))
    return out
