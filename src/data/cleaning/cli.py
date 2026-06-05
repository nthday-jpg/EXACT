import argparse
import sys
from pathlib import Path
from src.data import LogicalDatasetPipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Logical Dataset Validation and Automated Repair Pipeline"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the input JSON dataset file"
    )
    parser.add_argument(
        "--output-valid", "-v",
        required=True,
        help="Path to write the valid JSON samples to"
    )
    parser.add_argument(
        "--output-invalid", "-x",
        required=True,
        help="Path to write the invalid/unrepaired JSON samples to"
    )
    parser.add_argument(
        "--no-repair",
        action="store_true",
        help="Disable automated LLM-assisted repair, only perform Z3 validation filtering"
    )
    parser.add_argument(
        "--model", "-m",
        default="Qwen/Qwen3-235B-A22B-Instruct-2507",
        help="LLM model name to use for logical repair"
    )
    parser.add_argument(
        "--provider", "-p",
        default="together",
        help="Provider for API routing (e.g. together, huggingface)"
    )
    parser.add_argument(
        "--retries", "-r",
        type=int,
        default=3,
        help="Maximum self-correction repair dialogue turns per sample"
    )

    args = parser.parse_args()

    # Validate file path existence
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("LOGICAL DATASET PIPELINE CLI")
    print("=" * 80)
    print(f"Input:          {input_path.resolve()}")
    print(f"Output Valid:   {Path(args.output_valid).resolve()}")
    print(f"Output Invalid: {Path(args.output_invalid).resolve()}")
    print(f"Auto-Repair:    {not args.no_repair}")
    if not args.no_repair:
        print(f"Model:          {args.model} (via {args.provider})")
        print(f"Max Retries:    {args.retries}")
    print("=" * 80)

    try:
        pipeline = LogicalDatasetPipeline(
            model_name=args.model,
            extra_body={"provider": args.provider} if args.provider else None
        )
        
        pipeline.run_pipeline(
            input_path=str(input_path),
            output_valid_path=args.output_valid,
            output_invalid_path=args.output_invalid,
            auto_repair=not args.no_repair,
            max_retries=args.retries
        )
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL ERROR] Pipeline execution failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
