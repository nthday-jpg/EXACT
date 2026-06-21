import os
import subprocess
import zipfile
from pathlib import Path

def main():
    # Define repository root and target zip path
    repo_root = Path(__file__).resolve().parent.parent
    zip_output_path = repo_root / "data" / "submission" / "source_code.zip"
    
    print(f"Repository Root: {repo_root}")
    print(f"Target Zip Path: {zip_output_path}")
    
    # Run git ls-files to get all tracked and untracked (but not ignored) files
    try:
        result = subprocess.run(
            ["git", "ls-files", "-c", "-o", "--exclude-standard"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error running git ls-files: {e}")
        print(e.stderr)
        return

    # Ensure output directory exists
    zip_output_path.parent.mkdir(parents=True, exist_ok=True)

    # Filter out the output zip file itself to prevent self-inclusion
    relative_zip_path = zip_output_path.relative_to(repo_root).as_posix()
    files_to_zip = [f for f in files if f != relative_zip_path]

    print(f"Found {len(files_to_zip)} files to zip.")

    # Write files to zip
    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_rel_path in files_to_zip:
            abs_path = repo_root / file_rel_path
            if abs_path.is_file():
                # Write file with relative path inside the zip
                zipf.write(abs_path, file_rel_path)
            else:
                print(f"Warning: {file_rel_path} listed by git but is not a file.")

    print(f"Successfully zipped {len(files_to_zip)} files to {zip_output_path}")
    print(f"Zip file size: {zip_output_path.stat().st_size / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
