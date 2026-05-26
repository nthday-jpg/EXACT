from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.agents.exploration.runner import run_exploration


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run physics exploration and collect failures.")
    parser.add_argument("--csv", default="data/processed/physics.csv", help="Path to physics CSV")
    parser.add_argument("--output", default="runs/physics_failures.json", help="Failure output JSON")
    parser.add_argument("--num-samples", type=int, default=-1, help="Sample size (-1 for full)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    parser.add_argument("--model", default=None, help="Override model name")
    parser.add_argument(
        "--no-verbose",
        action="store_true",
        help="Disable progress output",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    load_dotenv()
    api_key = os.getenv("HF_API_KEY")
    model = args.model or os.getenv("PHYSICS_MODEL", "Qwen/Qwen3-8B:featherless-ai")

    operating = Path("src/physics/instructions/operating.md").read_text("utf-8")
    heuristic = Path("src/physics/instructions/heuristic.md").read_text("utf-8")

    failures = run_exploration(
        csv_path=args.csv,
        output_path=args.output,
        model_name=model,
        api_key=api_key,
        system_prompt=operating,
        heuristic_prompt=heuristic,
        num_samples=args.num_samples,
        seed=args.seed,
        temperature=0.1,
        verbose=not args.no_verbose,
    )

    print(f"Failures: {len(failures)}")


if __name__ == "__main__":
    main()
