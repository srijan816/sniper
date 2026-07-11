#!/usr/bin/env python3
"""
Agent/dev research loop — polls AI-Q pipeline queue until idle.

Usage:
  cd backend && python scripts/research_loop.py
  cd backend && python scripts/research_loop.py --adopt vision-ensemble 2c9a3a4f-...
  cd backend && python scripts/research_loop.py --seed --once

Runs one tick per interval (default 90s). Safe to leave running alongside Celery beat.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.research_queue import adopt_external_job, enqueue_defaults, queue_status
from app.workers.research import research_queue_tick, seed_research_queue


def main():
    parser = argparse.ArgumentParser(description="SniperIP research poll loop")
    parser.add_argument("--interval", type=int, default=90, help="Seconds between ticks")
    parser.add_argument("--once", action="store_true", help="Run one tick and exit")
    parser.add_argument("--seed", action="store_true", help="Seed default topic queue first")
    parser.add_argument("--adopt", nargs=2, metavar=("TOPIC", "JOB_ID"), help="Adopt running AI-Q job")
    parser.add_argument("--status", action="store_true", help="Print queue status and exit")
    args = parser.parse_args()

    if args.adopt:
        topic, job_id = args.adopt
        adopt_external_job(topic, job_id)
        print(json.dumps({"adopted": topic, "job_id": job_id}, indent=2))
        if args.once:
            return

    if args.seed:
        result = seed_research_queue()
        print(json.dumps(result, indent=2))

    if args.status:
        print(json.dumps(queue_status(), indent=2))
        return

    print("SniperIP research loop started (Ctrl+C to stop)", flush=True)
    while True:
        try:
            result = research_queue_tick()
            status = queue_status()
            print(
                json.dumps(
                    {
                        "tick": result,
                        "active": status.get("active"),
                        "queued": status.get("queued"),
                        "completed_topics": list((status.get("completed") or {}).keys()),
                    },
                    indent=2,
                ),
                flush=True,
            )
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), flush=True)

        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
