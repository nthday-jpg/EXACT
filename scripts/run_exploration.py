from __future__ import annotations

import argparse
import asyncio
import os

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
    default_model = os.getenv("DEFAULT_MODEL", "Qwen/Qwen3-8B:featherless-ai")
    model = args.model or os.getenv("PHYSICS_MODEL") or default_model
    router_model = args.router_model or os.getenv("ROUTER_MODEL") or default_model
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
