# Processed Data

This folder describes the standardized and cleaned datasets used for training and testing.

## Processed Datasets

All processed datasets are stored in `data/processed/`:

1. **`logic_merged_valid_augmented.json`**:
   - The verified logical reasoning dataset containing repaired FOL formulas and standardized labels.
   - Initial logic validation and syntax repair is handled iteratively by the repair pipeline in `src/data/cleaning/cli.py`.
   - Validation labels and explanation consistency are verified using `src/data/cleaning/clean_val_labels.py`.

2. **`physics_distillation.json`**:
   - The generated physics training dataset used to fine-tune the physics solver.

3. **`router_dataset.json`**:
   - The classification dataset used to train the query classifier (routing between Type 1/Type 2 queries and physics sub-domains).

## Data Processing & Cleaning Tools

1. **Logical Dataset Repair Pipeline** (`src/data/cleaning/cli.py`):
   - Validates natural language premises and FOL formulas against Z3 syntax.
   - Performs automated self-correction/repair dialogues using a larger LLM when Z3 syntax checks fail.
   - Can be run as:
     ```bash
     python -m src.data.cleaning.cli -i data/logic_based.json -v data/processed/logic_merged_valid.json -x data/processed/logic_merged_invalid.json
     ```

2. **Validation Label Cleaner** (`src/data/cleaning/clean_val_labels.py`):
   - Verifies the semantic correctness of candidate answers in validation splits.
   - Corrects erroneous labels and outputs consistent explanation text.
   - Can be run as:
     ```bash
     python src/data/cleaning/clean_val_labels.py
     ```
