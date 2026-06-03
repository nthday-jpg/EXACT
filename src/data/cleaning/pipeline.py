import os
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from src.llm import LLMClient
from src.data.cleaning.validator import validate_sample_fol, validate_dataset
from src.data.cleaning.repairer import LogicalDatasetRepairer


class LogicalDatasetPipeline:
    """
    Exhaustive Logical Reasoning Dataset Orchestration & Auto-Repair Pipeline.
    Manages data loading, validator invocations, repair loops, and dataset merging.
    """
    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-235B-A22B-Instruct-2507",
        extra_body: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        llm_client: Optional[LLMClient] = None
    ) -> None:
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            eb = extra_body if extra_body is not None else {"provider": "together"}
            self.llm_client = LLMClient(
                model_name=model_name,
                extra_body=eb,
                temperature=temperature
            )
            # Force standard chat completions API routing for HF serverless client
            self.llm_client.tokenizer = None
        
        self.repairer = LogicalDatasetRepairer(self.llm_client)

    @staticmethod
    def standardize_fol_formula(f_str: str) -> str:
        """Wrap formatter's standardization helper for backwards compatibility."""
        from src.data.cleaning.formatter import standardize_fol_formula
        return standardize_fol_formula(f_str)

    def validate_sample_fol(self, formulas: list[str]) -> Tuple[bool, str]:
        """Wrap validator's single sample validation for backwards compatibility."""
        return validate_sample_fol(formulas)

    def validate_dataset(self, dataset: list[Dict[str, Any]]) -> Tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
        """Wrap validator's dataset split for backwards compatibility."""
        return validate_dataset(dataset)

    def repair_sample(self, sample: Dict[str, Any], max_retries: int = 3) -> Tuple[bool, Dict[str, Any]]:
        """Wrap repairer's repair_sample for backwards compatibility."""
        return self.repairer.repair_sample(sample, max_retries=max_retries)

    def run_pipeline(
        self,
        input_path: str,
        output_valid_path: str,
        output_invalid_path: str,
        auto_repair: bool = True,
        max_retries: int = 3
    ) -> Tuple[int, int]:
        """
        Runs the logical cleaning and repair pipeline.
        If auto_repair is True, it loops continuously, feeding unrepaired invalid samples 
        back into the repair engine until either:
          1. 0 invalid samples remain (100% cleanliness)
          2. No more progress can be made (no invalid samples are rescued in a complete pass)
        """
        in_p = Path(input_path)
        out_v = Path(output_valid_path)
        out_i = Path(output_invalid_path)

        if not in_p.exists():
            raise FileNotFoundError(f"Input file {input_path} does not exist.")

        print("\n" + "=" * 80)
        print("EXHAUSTIVE ITERATIVE LOGICAL DATASET PIPELINE")
        print(f"Input file: {in_p.name}")
        print("=" * 80)

        with open(in_p, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        print(f"Loaded {len(dataset)} total samples.")

        # Step 1: Initial validation split
        valid_samples, invalid_samples = self.validate_dataset(dataset)
        initial_invalid_count = len(invalid_samples)
        print(f"  - Initial Valid:   {len(valid_samples)}")
        print(f"  - Initial Invalid: {len(invalid_samples)}")

        if not auto_repair or not invalid_samples:
            os.makedirs(out_v.parent, exist_ok=True)
            with open(out_v, "w", encoding="utf-8") as f:
                json.dump(valid_samples, f, indent=2, ensure_ascii=False)
            with open(out_i, "w", encoding="utf-8") as f:
                json.dump(invalid_samples, f, indent=2, ensure_ascii=False)
            return len(valid_samples), len(invalid_samples)

        # Step 2: Auto-repair loop
        loop_pass = 1
        rescued_total = 0

        while invalid_samples:
            print("\n" + "-" * 80)
            print(f"PASS {loop_pass}: Auto-repairing {len(invalid_samples)} invalid samples...")
            print("-" * 80)

            still_invalid = []
            pass_rescued = 0

            for idx, sample in enumerate(invalid_samples, start=1):
                ex_id = sample.get("example_id", "unknown")
                print(f"  [{idx}/{len(invalid_samples)}] Repairing {ex_id}...")
                
                success, result = self.repairer.repair_sample(sample, max_retries=max_retries)
                if success:
                    print(f"    -> [SUCCESS] Rescued {ex_id}! Merging into valid database.")
                    valid_samples.append(result)
                    pass_rescued += 1
                    rescued_total += 1
                else:
                    print(f"    -> [FAILED] Could not repair {ex_id}. Moving to residual list.")
                    still_invalid.append(result)

                # Politeness API delay
                time.sleep(2)

            print(f"\nPass {loop_pass} completed: Rescued {pass_rescued} / {len(invalid_samples)} samples.")
            
            invalid_samples = still_invalid
            
            # If we made no progress in this pass, we are exhausted
            if pass_rescued == 0:
                print("\n[EXHAUSTED] No samples could be rescued in this pass. Ending loop to prevent infinite runs.")
                break

            loop_pass += 1

        # Step 3: Save results
        os.makedirs(out_v.parent, exist_ok=True)
        os.makedirs(out_i.parent, exist_ok=True)

        with open(out_v, "w", encoding="utf-8") as f:
            json.dump(valid_samples, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(valid_samples)} valid samples to: {out_v.name}")

        with open(out_i, "w", encoding="utf-8") as f:
            json.dump(invalid_samples, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(invalid_samples)} invalid samples to: {out_i.name}")

        total = len(valid_samples) + len(invalid_samples)
        rate = (len(valid_samples) / total) * 100 if total > 0 else 0
        
        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 80)
        print(f"Total processed samples:  {total}")
        print(f"Initial invalid:          {initial_invalid_count}")
        print(f"Net rescued:              {rescued_total}")
        print(f"Final valid questions:     {len(valid_samples)} ({rate:.2f}%)")
        print(f"Final invalid questions:   {len(invalid_samples)} ({100 - rate:.2f}%)")
        if len(invalid_samples) > 0:
            print(f"Warning: {len(invalid_samples)} samples remained invalid. Diagnostics written to data/processed/pipeline_diagnostics.md.")
        print("=" * 80)

        return len(valid_samples), len(invalid_samples)
