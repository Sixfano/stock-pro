"""Apply the evidence-layer upgrade to an existing A-stock checkout.

Usage:
    python apply_upgrade.py /path/to/A-stock
"""
from __future__ import annotations
from pathlib import Path
import shutil
import sys

FILES = [
    "factors/evidence.py",
    "factors/cyq.py",
    "factors/leader_feedback.py",
    "factors/competition.py",
    "factors/theme_reflow.py",
    "data/providers/akshare_provider.py",
    "data/providers/router.py",
    "reports/evidence_report.py",
    "reports/market_context.py",
    "scripts/run_screen.py",
    "tests/test_evidence.py",
    "tests/test_evidence_v2.py",
    "config/evidence_policy.yaml",
    "docs/limitup_evidence_layer.md",
    "README.md",
]

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python apply_upgrade.py /path/to/A-stock")
    source = Path(__file__).resolve().parent
    target = Path(sys.argv[1]).resolve()
    if not (target / "strategies").exists():
        raise SystemExit("target does not look like the A-stock repository")
    for rel in FILES:
        src = source / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"updated {rel}")
    print("Core strategy files were not modified.")

if __name__ == "__main__":
    main()
