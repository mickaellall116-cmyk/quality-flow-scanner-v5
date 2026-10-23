"""Dry-run CLI: runs one fixture leg through the disabled transport.
Expected behavior with the network off: FAIL_CLOSED on stdout, exit 3,
and NO receipt file created (absence is the failure signal)."""
import sys
from capture_wrapper import disabled_transport, run_leg, CaptureRefused

LEG = {"leg_id": "FIXTURE/HO", "symbol": "FIX", "window": "W_HO",
       "start_date": "2026-10-20", "end_date": "2026-10-20", "expected_rows": 7}

if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else "receipts.jsonl"
    try:
        receipt = run_leg(disabled_transport, LEG, "FIXTURE_ROOT", "GENESIS")
    except CaptureRefused as e:
        print(f"FAIL_CLOSED reason={e.reason} detail={e.detail}")
        sys.exit(3)
    with open(out_path, "a") as f:
        f.write(receipt["chain"]["receipt_hash"] + "\n")
    print("RECEIPT_EMITTED")
