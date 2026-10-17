#!/usr/bin/env python3
"""Read-only probe of the sanctioned credential-helper path (-08 step 1).

Surface inspection only: existence, SHA-256, import-for-inspection and
signature. The helper callable is NEVER invoked; no credential material
is resolved, read or printed. Run under `unshare -n` (network denied).
"""
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import credential_resolver as R  # noqa: E402

OTHER_COPY = "/opt/hatch/workflow-skills/custom-connector-setup/bin/dynamic_credentials.py"


def main():
    rec = {"task": "QF-TD-CREDENTIAL-HELPER-PATH-BINDING-20261017-08",
           "probe": "read_only_surface_inspection_no_invocation"}
    rec["sanctioned_dir_exists"] = os.path.isdir(R.SANCTIONED_DIR)
    rec["sanctioned"] = R.probe_surface(R.SANCTIONED_PATH)
    rec["sanctioned_pin_matches"] = rec["sanctioned"].get("sha256") == R.PIN_SHA256
    # the -06 fact, restated precisely: absent from the DEFAULT sys.path
    try:
        importlib.import_module("dynamic_credentials")
        rec["default_syspath_import"] = "IMPORTABLE"
    except Exception as e:  # noqa: BLE001
        rec["default_syspath_import"] = "NOT_IMPORTABLE:" + type(e).__name__
    # a second byte-identical copy exists elsewhere on the platform: it is
    # NOT the sanctioned origin and the resolver route never uses it.
    other = R.probe_surface(OTHER_COPY)
    rec["other_platform_copy"] = {"path": other["path"], "exists": other["exists"],
                                  "sha256": other["sha256"],
                                  "classification": other["classification"],
                                  "identical_bytes_to_sanctioned":
                                      other["sha256"] == rec["sanctioned"].get("sha256"),
                                  "is_sanctioned_origin": False}
    handle = None
    try:
        handle = R.resolve()
        rec["resolver_against_sanctioned"] = {
            "resolved": True, "origin": handle.path,
            "origin_is_sanctioned_path": handle.path == os.path.abspath(R.SANCTIONED_PATH),
            "sha256": handle.sha256, "reverify": handle.reverify(),
            "callable_present": callable(handle.callable)}
    except R.HelperRefusal as e:
        rec["resolver_against_sanctioned"] = {"resolved": False, "refusal": e.code}
    print(json.dumps(rec, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
