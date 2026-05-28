# 🎓 EXACT: Neurosymbolic QA System for STEM & Logic Challenges

EXACT is a high-performance, lightweight, and explainable QA workspace designed for educational and STEM-based reasoning datasets. It combines the cognitive power of **Open-Source Large Language Models (8B or smaller)** with the rigorous correctness of the **Z3 SMT Solver** to deliver correct answers backed by mathematically sound, hallucination-free explanations.

---

## 📐 Unified System Architecture

Our architecture bridges neural models with symbolic solvers, dividing the reasoning workloads into two modular pipelines for Logic and Physics problems:

```mermaid
graph TD
    %% Dataset Type 1: Logic
    subgraph Logic Pipeline (Neurosymbolic Reasoning)
        A1["Natural Language Premises & Question"] --> B1["Stage 1: Glossary Generation (LLM)"]
        B1 -->|"Unified Predicates & Entities"| C1["Stage 2: Constrained FOL Translation (LLM)"]
        C1 --> D1["Immediate Normalization (normalize_logic_fol_entry)"]
        D1 --> E1["Syntactic Validation (try_parse_fol)"]
        E1 -->|Mismatches / Errors| F1["Syntax & Semantic Repair Loop (LLM)"]
        E1 -->|Valid FOL| G1["Z3 SMT Solver Verification"]
        F1 --> D1
        G1 -->|"UNSAT (Entailed) + Proof Tree"| H1["Proof-Tree Guided CoT Explainer (LLM)"]
        G1 -->|"SAT (Consistent) + Counterexample"| I1["Counterexample-Guided Explainer (LLM)"]
        G1 -->|"No Entailment found"| J1["MCQ Process of Elimination Heuristic"]
        J1 -->|"Filter Consistent Options"| H1
    end

    %% Dataset Type 2: Physics
    subgraph Physics Pipeline (Code-Execution Reasoning)
        A2["Physics Numerical Question"] --> B2["Prompt Builder & Context Retrieval"]
        B2 --> C2["LLM Solver (Generates Executable Python)"]
        C2 --> D2["Safe Python Sandbox Execution"]
        D2 -->|"Output: ans, unit"| E2["Physics Evaluator"]
        D2 -->|Execution Fail / Exception| F2["Physics Self-Correction LLM Loop"]
        F2 --> D2
    end

    H1 --> K["API Response: answer, explanation, cot, fol, confidence"]
    I1 --> K
    E2 --> L["API Response: answer, explanation, cot, unit"]
```

---

## 📂 Repository Structure

```
EXACT/
├── data/
│   ├── logic_based.json        # Logic dataset (Type 1): NL premises, questions, answers
│   └── physic.csv             # Physics dataset (Type 2): circuits & electromagnetism
├── src/
│   ├── logic/                 # Neurosymbolic logic framework
│   │   ├── translation/       # Compiles NL premises/conclusions into FOL
│   │   ├── reasoning/         # Feeds FOL to Z3 solver, extracts proofs, generates CoT
│   │   ├── pipeline.py        # End-to-end LogicalReasoningPipeline orchestrator
│   │   └── logic.md           # Technical documentation of the logical system
│   ├── physics/               # Safe sandbox code-execution solver for numeric STEM
│   │   ├── solver.py          # Solves physics questions via LLM-sandbox code flow
│   │   ├── runner.py          # Sync/async/batch runners with self-correction
│   │   └── README.md          # Technical documentation of the physics pipeline
│   ├── llm/                   # Centralized model clients and prompts
│   │   ├── llm_client.py      # Nf4 quantized local model / API client wrapper
│   │   └── prompts.py         # Consolidated LLM prompt configuration file
│   └── utils/                 # Data cleansing & text normalization
│       ├── normalization.py   # Normalizes logic tokens, unicode, times, and physics terms
│       └── normalization.md   # Logic/Physics normalization technical details
├── tests/                     # Comprehensive testing suite
│   ├── test_z3_parser.py      # Validates FOL lexer/parser and entailment
│   ├── normalization.py       # Tests logic premise, FOL, and physics normalizers
│   ├── test_arithmetic_temporal.py # Validates SMT arithmetic, scheduling, & proof extraction
│   └── test_actual_pipeline.py# Integration test running the actual logic pipeline end-to-end
├── pyproject.toml             # Python dependencies and tooling configuration
└── context.md                 # Original EXACT challenge objectives & constraints
```

---

## 🌟 Key Features & Logic Upgrades

### 1. Glossary-Constrained Translation (Two-Stage)
Prevents naming mismatches across premises (e.g., `well_structured(c)` in Premise 1 vs `practical_exercises(c)` in Premise 2).
*   **Stage 1**: Extracts a unified JSON Glossary of predicates and constants from all input premises.
*   **Stage 2**: Translates statements to FOL under strict constraints of the Glossary.

### 2. Automatic FOL Normalization & Repair Loop
*   **Zero-Overhead Normalization**: Extracted FOL strings are automatically normalized (e.g., `forall` $\rightarrow$ `ForAll`, Unicode logic operators $\rightarrow$ ASCII equivalents) to repair syntax issues instantly.
*   **LLM Repair Loop**: Formulas failing syntax checks are sent back to the LLM with the exact Z3 parser error for automated repair (up to 2 retries).

### 3. MCQ Process of Elimination (Heuristic)
If Z3 cannot find a direct proof (`unsat` core) for any option:
*   Instead of defaulting to Option A, it performs a **Process of Elimination** by checking consistency (`negate_conclusion=False` returns `sat`).
*   Direct contradictions are eliminated, and consistent options are ranked, improving accuracy under incomplete premises.

### 4. Arithmetic & Temporal Reasoning
*   **Pre-scanning & Sort-Upgrading**: Identifies constants/functions involved in numeric comparisons (`=`, `<`, `>=`, etc.) and upgrades their Z3 Sort from the default universe `U` to `IntSort()`, eliminating Z3 sort mismatches.
*   **Temporal Constants**: Maps time strings (e.g., `Time830AM` $\rightarrow$ `IntVal(510)`) and durations (e.g., `Duration4Hours` $\rightarrow$ `IntVal(240)`) into integer minutes since midnight, allowing native SMT inequality and scheduling reasoning.

### 5. Neurosymbolic Proof-Guided Chain-of-Thought (CoT)
*   **Tree-Traversal**: Post-order traverses Z3's proof tree recursively, extracting asserted leaf premises and intermediate logical resolutions (e.g., `mp`, `unit-resolution`).
*   **Hallucination-Free Explanations**: Passes the derived mathematical skeleton to the LLM to guide its natural language reasoning, ensuring explanations are 100% grounded in symbolic proofs.

### 6. Resource-Constrained Thinking Model Optimization
*   Sets local thinking-model limits automatically (allocating a `max_tokens=4096` budget when `enable_thinking=True` is active) to prevent reasoning blocks (`<think>`) from truncating JSON outputs.

---

## 🚀 Installation & Quick Start

### 1. Clone the repository and navigate to the project directory:
```bash
git clone <repository_url> EXACT
cd EXACT
```

### 2. Install dependencies (Requires Python >= 3.12, `< 3.13`):
Using the standard package manager `uv` (recommended):
```bash
uv sync
```
Using standard `pip`:
```bash
pip install -e .
```

### 3. Configure API Credentials:
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your_remote_llm_api_key
OPENAI_BASE_URL=https://api.yourprovider.com/v1
```

---

## 🧪 Running Verification and Test Suites

Verify all features are working and that there are no regressions by running the test suite:

### 1. Run Z3 Core Parser & Entailment Tests
Checks custom FOL-to-SMT compilation and basic proof resolution:
```bash
.venv\Scripts\python.exe tests/test_z3_parser.py
```

### 2. Run Punctuation & Normalization Tests
Validates logic, temporal parsing, and physics string normalization:
```bash
.venv\Scripts\python.exe tests/normalization.py
```

### 3. Run SMT Arithmetic, Scheduling, & Proof-Traversal Tests
Validates numeric pre-scanning, temporal math, and Z3 post-order proof extraction:
```bash
.venv\Scripts\python.exe tests/test_arithmetic_temporal.py
```

### 4. Run End-to-End Integration Pipeline Test
Executes the full pipeline (Glossary $\rightarrow$ Translation $\rightarrow$ Normalization $\rightarrow$ Z3 Proof $\rightarrow$ Proof-Guided CoT) on a sample logic query:
```bash
.venv\Scripts\python.exe tests/test_actual_pipeline.py
```

---

## 📝 Submission & Evaluation Compliance

Our system satisfies all challenge constraints:
*   **Model Restrictions**: Fully compatible with open-source models with $\le 8\text{B}$ parameters (e.g., `Qwen/Qwen3-8B` fine-tuned variants).
*   **Explainability (P2, P3)**: Returns full mathematical proofs, structured CoT, used premises, and natural language explanations.
*   **Format Compliance**: Output dictionary perfectly aligns with the required API JSON schema.

> [!TIP]
> For detailed developer guidelines and deep architectural details, see [src/logic/logic.md](file:///d:/mduy/source/repos/EXACT/src/logic/logic.md).
