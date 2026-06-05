#!/usr/bin/env python3
import os
import re
import sys
import json
import time
from pathlib import Path

# Add project root directory to sys.path to enable top-level imports from 'src'
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

try:
    from src.llm import LLMClient
    from src.llm.prompts import REPAIR_PLAN_SYSTEM_PROMPT, REPAIR_PLAN_USER_TEMPLATE
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please make sure you are running this script inside the project virtual environment.")
    sys.exit(1)


def main():
    print("=" * 80)
    print("LOGIC FAILURE TROUBLESHOOTING & REPAIR STRATEGY GENERATOR")
    print("Generates a comprehensive diagnostic report for all remaining invalid samples.")
    print("=" * 80)

    data_dir = root_dir / "data" / "processed"
    invalid_path = data_dir / "merged_invalid.json"
    report_path = data_dir / "repair_strategies.md"

    if not invalid_path.exists():
        print(f"Error: {invalid_path} does not exist. Run validation first.")
        sys.exit(1)

    # Load invalid samples
    with open(invalid_path, "r", encoding="utf-8") as f:
        invalid_samples = json.load(f)

    if not invalid_samples:
        print("No invalid samples found to analyze!")
        sys.exit(0)

    print(f"Found {len(invalid_samples)} invalid samples to analyze.")

    # Initialize LLMClient with bypassed local tokenizer to force chat completions with together provider
    print("Initializing Qwen3-235B-A22B-Instruct-2507 client on Hugging Face router...")
    try:
        llm_client = LLMClient(
            model_name="Qwen/Qwen3-235B-A22B-Instruct-2507",
            extra_body={"provider": "together"},
            temperature=0.1
        )
        llm_client.tokenizer = None  # Force chat completions and correct provider routing
    except Exception as e:
        print(f"Failed to initialize LLMClient: {e}")
        sys.exit(1)

    reports = []
    batch_size = 3
    total_samples = len(invalid_samples)

    for i in range(0, total_samples, batch_size):
        batch = invalid_samples[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_samples + batch_size - 1) // batch_size

        print(f"\nProcessing Batch {batch_num}/{total_batches} ({len(batch)} samples)...")
        for sample in batch:
            print(f"  - ID: {sample['example_id']} | Source: {sample['dataset_source']} | Error: {sample['validation_error']}")

        # Format user prompt
        # We only pass keys relevant to analysis to avoid cluttering tokens
        prompt_payload = []
        for s in batch:
            prompt_payload.append({
                "example_id": s["example_id"],
                "dataset_source": s["dataset_source"],
                "premises-NL": s["premises-NL"],
                "premises-FOL": s["premises-FOL"],
                "question": s["question"],
                "answer": s["answer"],
                "validation_error": s.get("validation_error")
            })

        user_prompt = REPAIR_PLAN_USER_TEMPLATE.format(
            invalid_samples_json=json.dumps(prompt_payload, indent=2, ensure_ascii=False)
        )

        try:
            response_text = llm_client.generate_text(user_prompt, system_prompt=REPAIR_PLAN_SYSTEM_PROMPT, max_new_tokens=4096)
        except Exception as e:
            print(f"Error during LLM text generation in Batch {batch_num}: {e}")
            continue

        # Extract and parse JSON
        json_str = ""
        match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            start = response_text.find("[")
            end = response_text.rfind("]")
            if start != -1 and end != -1:
                json_str = response_text[start:end+1].strip()
            else:
                json_str = response_text.strip()

        try:
            batch_reports = json.loads(json_str)
            if isinstance(batch_reports, list):
                # Associate the original story information
                id_to_sample = {s["example_id"]: s for s in batch}
                for r in batch_reports:
                    ex_id = r.get("example_id")
                    if ex_id in id_to_sample:
                        r["premises-NL"] = id_to_sample[ex_id]["premises-NL"]
                        r["original-FOL"] = id_to_sample[ex_id]["premises-FOL"]
                        r["question"] = id_to_sample[ex_id]["question"]
                        r["answer"] = id_to_sample[ex_id]["answer"]
                        r["dataset_source"] = id_to_sample[ex_id]["dataset_source"]
                        reports.append(r)
                        print(f"  [OK] Successfully analyzed {ex_id}")
            else:
                print(f"  [ERROR] Model response was not a JSON list in Batch {batch_num}")
        except Exception as e:
            print(f"  [ERROR] Failed to parse JSON in Batch {batch_num}: {e}")
            # Write failed output to temp file
            temp_fail = data_dir / f"fail_analysis_batch_{batch_num}.txt"
            with open(temp_fail, "w", encoding="utf-8") as f_fail:
                f_fail.write(response_text)

        # Politeness delay
        time.sleep(2)

    # Compile the final report in Markdown
    print(f"\nGenerating Markdown Report at {report_path}...")
    
    md_content = f"""# Logic Failure Troubleshooting & Repair Strategy Report

This report contains automated diagnostics, root-cause analyses, and step-by-step repair recommendations for the remaining **{len(reports)}** invalid logical samples in the dataset. These analyses were generated using the `Qwen3-235B` model, acting as a Senior Logical Architect to identify syntactic and sort mismatches under Z3 SMT solver constraints.

## Executive Summary

The majority of remaining validation failures fall into four main categories:
1. **Sort Collisions in Quantifiers**: Variables (like `h` or `t`) that are used both as uninterpreted elements of sort `U` inside quantifiers/arguments, and also compared to integers/real numbers (e.g. `h >= 500` or `t/S`).
2. **String Constant Mismatches**: Constants (like grades `'a+'`, `'b+'` or programming languages `'c++'`) being enclosed in single quotes. Z3 parses single-quoted values as `String` sort, creating a sort mismatch when compared with uninterpreted domain terms.
3. **Implicit Arity & Domain Violations**: Functions/predicates with differing numbers of arguments, or arguments containing complex operators rather than nested formulas.
4. **Formula vs Term Connectives**: Treating terms/scalars (like numbers or exponents) as boolean formulas using logical connectives (e.g., `Retention = e AND (-t/S)`).

---

## Detailed Sample Diagnostics
"""

    for r in reports:
        ex_id = r.get("example_id")
        source = r.get("dataset_source", "unknown")
        err = r.get("validation_error", "unknown")
        root_cause = r.get("root_cause_analysis", "N/A")
        steps = r.get("repair_steps", "N/A")
        repaired_fol = r.get("repaired_premises_fol", [])
        original_fol = r.get("original-FOL", [])
        premises_nl = r.get("premises-NL", [])
        question = r.get("question", "")
        answer = r.get("answer", "")

        md_content += f"""
### Sample `{ex_id}` ({source})

- **Z3 Validation Error**: `{err}`

#### 1. Context
**Natural Language Premises**:
"""
        for idx, nl in enumerate(premises_nl, start=1):
            md_content += f"{idx}. {nl}\n"
            
        md_content += f"""
**Question/Options**:
```text
{question}
```
**Correct Answer**: `{answer}`

#### 2. Comparison: Original vs Recommended FOL

| # | Original Formula | Recommended/Repaired Formula |
|---|------------------|------------------------------|
"""
        for idx, (orig, rep) in enumerate(zip(original_fol, repaired_fol), start=1):
            md_content += f"| {idx} | `{orig}` | `{rep}` |\n"

        md_content += f"""
#### 3. Diagnostic & Repair Plan

> **Root Cause Analysis**
> {root_cause}

> **Actionable Repair Steps**
> {steps}

---
"""

    with open(report_path, "w", encoding="utf-8") as f_out:
        f_out.write(md_content)

    print(f"Diagnostics complete! Wrote report to: {report_path.name}")
    print("=" * 80)


if __name__ == "__main__":
    main()
