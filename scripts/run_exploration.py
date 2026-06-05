from __future__ import annotations

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

from src.agents.exploration.runner import run_exploration


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run physics exploration and collect failures.")
    parser.add_argument("--csv", default="data/processed/physics.csv", help="Path to physics CSV")
    parser.add_argument("--output", default="runs/physics_failures.json", help="Failure output JSON")
    parser.add_argument("--num-samples", type=int, default=-1, help="Sample size (-1 for full)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    parser.add_argument("--model", default=None, help="Override model name")
    parser.add_argument("--router-model", default=None, help="Override router model name")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    load_dotenv()
    api_key = os.getenv("HF_API_KEY")
    if not api_key:
        print("[physics-explore] HF_API_KEY not set; model calls may fail.", file=sys.stderr)
    default_model = os.getenv("DEFAULT_MODEL", "Qwen/Qwen3-8B:featherless-ai")
    physics_model_env = os.getenv("PHYSICS_MODEL")
    model = args.model or physics_model_env or default_model
    if not args.model and not physics_model_env:
        print(f"[physics-explore] PHYSICS_MODEL not set; using DEFAULT_MODEL={default_model}.", file=sys.stderr)
    router_model_env = os.getenv("ROUTER_MODEL")
    router_model = args.router_model or router_model_env or default_model
    if not args.router_model and not router_model_env:
        print(f"[physics-explore] ROUTER_MODEL not set; using DEFAULT_MODEL={default_model}.", file=sys.stderr)
    failures = asyncio.run(
        run_exploration(
            csv_path=args.csv,
            output_path=args.output,
            model_name=model,
            api_key=api_key,
            router_model_name=router_model,
            num_samples=args.num_samples,
            seed=args.seed,
            temperature=0.1,
        )
    )

    print(f"Failures: {len(failures)}")


if __name__ == "__main__":
    main()
