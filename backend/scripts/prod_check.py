#!/usr/bin/env python3
"""Production readiness check — run before deploy."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root or backend/
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.startup import run_prod_check  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="SniperIP production readiness check")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    report = run_prod_check()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        status = "OK" if report["ok"] else "FAIL"
        print(f"Production check: {status} (environment={report['environment']})")
        for err in report["errors"]:
            print(f"  ERROR: {err}")
        for warn in report["warnings"]:
            print(f"  WARN:  {warn}")
        for key, ok in sorted(report["checks"].items()):
            mark = "✓" if ok else "✗"
            print(f"  [{mark}] {key}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
