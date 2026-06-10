import json
import os

def main():
    notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\fol_and_router.ipynb"
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    print(f"Original notebook cells: {len(nb['cells'])}")
    
    new_cell_source = [
        "# 8. Zip training results for downloading back to local machine\n",
        "import shutil\n",
        "import os\n",
        "\n",
        "# Set OUTPUT_DIR to Phase 2 results directory\n",
        "OUTPUT_DIR = OUTPUT_DIR_P2\n",
        "\n",
        "zip_name = \"/kaggle/working/results\"\n",
        "if os.path.exists(OUTPUT_DIR):\n",
        "    print(\"Zipping results folder...\")\n",
        "    shutil.make_archive(zip_name, 'zip', OUTPUT_DIR)\n",
        "    print(f\"Successfully zipped to: {zip_name}.zip\")\n",
        "    print(\"You can download this file from the Kaggle Output sidebar panel.\")\n",
        "else:\n",
        "    print(f\"Results directory {OUTPUT_DIR} not found. Train first!\")"
    ]
    
    new_cell = {
        "cell_type": "code",
        "execution_count": None,
        "id": "f3a8b2c4",
        "metadata": {},
        "outputs": [],
        "source": new_cell_source
    }
    
    # Check if a zip cell already exists at the end to avoid duplication
    if nb['cells'] and "Zip training results" in "".join(nb['cells'][-1].get('source', [])):
        print("A zip results cell already exists at the end of the notebook. Skipping append.")
        return
        
    nb['cells'].append(new_cell)
    print(f"Modified notebook cells: {len(nb['cells'])}")
    
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")  # Match trailing newline
    print("Successfully added zip results cell to notebook.")

if __name__ == "__main__":
    main()
