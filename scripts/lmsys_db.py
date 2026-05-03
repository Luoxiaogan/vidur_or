#!/usr/bin/env python3
"""Initialize or inspect the LMSYS reproduction SQLite database."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vidur_or_experiments.lmsys.config import DEFAULT_DB_PATH
from vidur_or_experiments.lmsys.database import initialize_database


def print_summary(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        raw_table_exists = False
        for name in ["reproduction_configs", "real_data_provenance_runs"]:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name = ?",
                (name,),
            ).fetchone()
            if not exists:
                print(f"{name}: missing")
                continue
            if name == "real_data_provenance_runs":
                raw_table_exists = True
            count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"{name}: {count}")
        if not raw_table_exists:
            return
        view_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='view' AND name='lmsys_best_wcp_vs_baseline'"
        ).fetchone()
        if view_exists:
            rows = conn.execute(
                """
                SELECT qps, config_name, ROUND(wcp_latency, 4), ROUND(best_baseline_latency, 4),
                       ROUND(win_pct, 2), total_limit, chunk_size, m
                FROM lmsys_best_wcp_vs_baseline
                ORDER BY qps
                """
            ).fetchall()
            for row in rows:
                print(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    initialize_database(args.db_path)
    if args.summary:
        print_summary(args.db_path)
    else:
        print(f"initialized {args.db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
