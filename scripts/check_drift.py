#!/usr/bin/env python3
"""
Drift Check Script

Runs drift analysis on the inference log and prints a summary.

Usage:
    python scripts/check_drift.py
    python scripts/check_drift.py --log-path data/monitoring/inference_log.csv
    python scripts/check_drift.py --ref-days 30 --cur-days 7
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run drift analysis")
    parser.add_argument(
        "--log-path",
        type=str,
        default=None,
        help="Path to inference_log.csv",
    )
    parser.add_argument(
        "--ref-days",
        type=int,
        default=30,
        help="Reference window size in days (default: 30)",
    )
    parser.add_argument(
        "--cur-days",
        type=int,
        default=7,
        help="Current window size in days (default: 7)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON",
    )
    args = parser.parse_args()

    from src.monitoring.drift_monitor import DriftMonitor

    monitor = DriftMonitor(
        inference_log_path=args.log_path,
        reference_window_days=args.ref_days,
        current_window_days=args.cur_days,
    )

    report = monitor.run_drift_analysis()

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("")
        print("=" * 60)
        print("  DRIFT ANALYSIS REPORT")
        print("=" * 60)
        print(f"  Status           : {report['status']}")
        print(f"  Severity         : {report['severity']}")
        print(f"  Drift detected   : {report['drift_detected']}")
        print(f"  Overall score    : {report['overall_drift_score']:.4f}")
        print(f"  Data drift (PSI) : {report['data_drift_score']:.4f}")
        print(f"  Pred drift (PSI) : {report['prediction_drift_score']:.4f}")
        print(f"  Perf drift       : {report['performance_drift_score']:.4f}")
        print(f"  Reference samples: {report['reference_samples']}")
        print(f"  Current samples  : {report['current_samples']}")
        if report.get("message"):
            print(f"  Message          : {report['message']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
