import json
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
problematic_json_path = root_dir / "scratch" / "problematic_tuning_samples.json"
report_path = root_dir / "scratch" / "problematic_tuning_samples_report.md"

with open(problematic_json_path, "r", encoding="utf-8") as f:
    problems = json.load(f)

print(f"Generating report for {len(problems)} problematic samples...")

with open(report_path, "w", encoding="utf-8") as f:
    f.write("# 🔍 Logic Tuning Dataset Problematic Samples Report\n\n")
    f.write(f"This report lists all **{len(problems)}** problematic samples detected in the model tuning dataset (`logic_merged_valid_augmented.json`) during the Z3 syntactic and semantic validation scan.\n\n")
    
    f.write("## 📊 Summary of Issues\n\n")
    f.write("- **Total problematic samples**: " + str(len(problems)) + "\n")
    f.write("- **Primary cause**: Contradictory premises (UNSAT). The premises themselves contain logical contradictions, rendering downstream reasoning trivial or invalid.\n")
    f.write("- **Impact**: These samples can harm the model's ability to learn valid logical structures and should be repaired or filtered out before fine-tuning.\n\n")
    
    f.write("## ❌ Problematic Samples List\n\n")
    
    for idx, sample in enumerate(problems, 1):
        f.write(f"### {idx}. Sample ID: `{sample.get('example_id')}`\n")
        f.write(f"- **Dataset Source**: `{sample.get('dataset_source')}`\n")
        f.write(f"- **Story ID**: `{sample.get('story_id')}`\n")
        f.write(f"- **Scan Index**: `{sample.get('scan_index')}`\n")
        f.write(f"- **Split**: `{sample.get('split')}`\n")
        f.write(f"- **Validation Error**: `{sample.get('validation_error')}`\n\n")
        
        f.write("#### Natural Language Premises\n")
        for nl in sample.get("premises-NL", []):
            f.write(f"- {nl}\n")
        f.write("\n")
        
        f.write("#### First-Order Logic (FOL) Formulas\n")
        f.write("```json\n")
        f.write(json.dumps(sample.get("premises-FOL", []), indent=2) + "\n")
        f.write("```\n")
        
        f.write(f"#### Question & Target Answer\n")
        f.write(f"- **Question**: {sample.get('question')}\n")
        f.write(f"- **Ground Truth Answer**: `{sample.get('answer')}`\n\n")
        f.write("---\n\n")

print(f"Report generated successfully at: {report_path}")
