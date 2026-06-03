import os

pkg_dir = r"d:\mduy\source\repos\EXACT\offline_packages"

# List of packages we ABSOLUTELY want to keep
keep_keywords = [
    "transformers",
    "trl",
    "peft",
    "datasets",
    "huggingface_hub",
    "torchao"
]

if not os.path.exists(pkg_dir):
    print(f"Error: Directory {pkg_dir} does not exist.")
    exit(1)

files = os.listdir(pkg_dir)
deleted_count = 0
kept_count = 0

print("Starting cleanup of offline_packages directory...")
for f in files:
    f_lower = f.lower()
    # Check if the filename contains any of the keep keywords as a package name
    # e.g., "transformers-5.9.0-py3-none-any.whl" starts with "transformers"
    should_keep = False
    for kw in keep_keywords:
        if f_lower.startswith(kw):
            should_keep = True
            break
            
    if should_keep:
        print(f"[KEEP] {f}")
        kept_count += 1
    else:
        file_path = os.path.join(pkg_dir, f)
        try:
            os.remove(file_path)
            print(f"[DELETE] {f}")
            deleted_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to delete {f}: {e}")

print("\n" + "="*40)
print(f"Cleanup finished!")
print(f"Kept: {kept_count} packages")
print(f"Deleted: {deleted_count} packages")
print("="*40)
