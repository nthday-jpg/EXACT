import sys
import subprocess
from pathlib import Path

def main():
    # Resolve project root directory
    root_dir = Path(__file__).resolve().parents[1]
    
    # Path to local virtualenv python and the evaluation runner script
    python_bin = root_dir / ".venv" / "Scripts" / "python.exe"
    eval_script = root_dir / "tests" / "evaluate_200_samples.py"
    
    if not python_bin.exists():
        python_bin = "python"  # Fallback to system python if venv isn't in default path
        
    cmd = [str(python_bin), "-u", str(eval_script), "--local"] + sys.argv[1:]
    
    print("=" * 70)
    print("STARTING LOCAL GPU LOGICAL REASONING EVALUATION")
    print("Enforces sequential runs (--jobs 1) to prevent VRAM memory overflow.")
    print(f"Executing: {' '.join(cmd)}")
    print("=" * 70)
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nEvaluation failed with exit code: {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
