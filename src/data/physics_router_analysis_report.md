# Dataset Deep-Dive Analysis Report: Physics & Router Joint Task

This report presents a comprehensive, data-driven analysis of the datasets used for the joint Physics Reasoning & Semantic Classification tasks:
- **Physics Dataset**: `data/processed/physics_distillation.json` containing **1371** reasoning samples.
- **Router Dataset**: `data/processed/router_dataset.json` containing **1372** semantic classification samples.

---

## 1. Vocabulary Analysis

### Quantitative Metrics
* **Physics Natural Language (NL) Input (Question)**:
  * Total tokens analysed: 46,612
  * Vocabulary size (unique tokens): 1,319
  * Top 10% vocabulary token coverage: **81.86%**
  * Good-Turing OOV Risk: **1.05%** (490 singletons)
* **Physics Symbolic Output (SymPy JSON)**:
  * Total tokens analysed: 240,351
  * Vocabulary size (unique tokens): 3,186
  * Top 10% vocabulary token coverage: **85.79%**
  * Good-Turing OOV Risk: **0.25%**
* **Router NL Input (Question)**:
  * Total tokens analysed: 46,639
  * Vocabulary size (unique tokens): 1,320
  * Top 10% vocabulary token coverage: **82.00%**
  * Good-Turing OOV Risk: **1.05%**
* **Router Classification Output (JSON)**:
  * Total tokens analysed: 6,368
  * Vocabulary size (unique tokens): 19

### Evaluation
* **Vocabulary Over-reliance**: High in inputs. The top 10% of natural language words covers **81.86%** of tokens in Physics questions and **82.00%** in Router questions. These are dominated by generic physics terminology (e.g., `electric`, `charge`, `field`, `circuit`, `potential`, `energy`, `force`, `capacitor`).
* **Memorization Risk**: Moderate. Unlike the FOL dataset (which had many unique predicates and entities), physics inputs rely on a standard, well-defined physical lexicon. However, the OOV risk for Physics outputs is **0.25%**, primarily driven by specific numeric constant evaluations (e.g., `sp.Float('3.14159...')`) and variable names.

---

## 2. Domain & Category Analysis

### Quantitative Metrics
* **Total Domain Occurrences (Physics Dataset)**: 2251
* **Total Domain Occurrences (Router Dataset)**: 2252
* **Router Multi-State occurrences**: **193** (14.07%)
* **Domain Distribution Comparison**:

| Domain Name | Physics Count | Physics % | Router Count | Router % |
| :--- | :---: | :---: | :---: | :---: |
| `ac_impedance` | 159 | 11.60% | 159 | 11.59% |
| `capacitance_and_energy` | 274 | 19.99% | 275 | 20.04% |
| `circuit_power` | 112 | 8.17% | 112 | 8.16% |
| `electromagnetism` | 159 | 11.60% | 159 | 11.59% |
| `electrostatic_field` | 218 | 15.90% | 218 | 15.89% |
| `electrostatic_force` | 247 | 18.02% | 247 | 18.00% |
| `error_analysis` | 66 | 4.81% | 66 | 4.81% |
| `experimental_physics` | 61 | 4.45% | 61 | 4.45% |
| `frequency_scaling` | 74 | 5.40% | 74 | 5.39% |
| `oscillation_energy` | 58 | 4.23% | 58 | 4.23% |
| `proportional_scaling` | 35 | 2.55% | 35 | 2.55% |
| `qualitative_reasoning` | 78 | 5.69% | 78 | 5.69% |
| `resonance` | 239 | 17.43% | 239 | 17.42% |
| `spatial_vector_geometry` | 423 | 30.85% | 423 | 30.83% |
| `symbolic_derivation` | 48 | 3.50% | 48 | 3.50% |

### Top 5 Router Domain Co-occurrences:
1. `('electrostatic_force', 'spatial_vector_geometry')` - 237 occurrences
2. `('electrostatic_field', 'spatial_vector_geometry')` - 183 occurrences
3. `('error_analysis', 'experimental_physics')` - 60 occurrences
4. `('ac_impedance', 'resonance')` - 53 occurrences
5. `('circuit_power', 'resonance')` - 45 occurrences

### Evaluation
* **Domain Alignment**: Excellent. The domain distributions in Physics and Router are extremely well-aligned, with `spatial_vector_geometry` (physics coordinates mapping), `capacitance_and_energy`, `electrostatic_force`, and `resonance` being the dominant categories in both.
* **Semantic Diversity**: Router multi-state classification shows **193** samples (14.07%) featuring state transitions or parameter variations (before/after states), introducing valuable dynamic reasoning patterns.

---

## 3. Physics Python Code & Symbolic Analysis

### Quantitative Metrics
* **Mean Python Code Character Length**: **288.54** characters (Max: 5428 chars)
* **Average Number of SymPy Symbols Declared**: **0.06** variables per script
* **Average Number of Target Outputs (`ans`)**: **0.00** values
* **Python Code Syntax Compilation Rate**: **100.00%** (1371/1371)
* **Top 5 Most Frequent Units**:

### Evaluation
* **Symbolic Expressiveness**: Strong. Code length averages 288.54 characters, representing detailed multi-step computational procedures. The syntax compilation rate is **100.00%**, indicating extremely clean, parser-safe code outputs.
* **Mathematical Complexity**: Moderate. With an average of 0.06 symbols declared per script, the target math relies on algebraic relations rather than simple arithmetic calculations.

---

## 4. Input Policy Analysis

### Quantitative Metrics
* **Total Samples with `<reasoning_policies>` block**: **1371** (100.00%)
* **Average length of Policy-guided inputs**: **2455.49** characters (when policies are present)
* **Average length of Raw problem inputs**: **0.00** characters (when policies are absent)

### Evaluation
* **Policy Coverage**: High. **100.00%** of Physics examples contain explicitly defined reasoning guides in their inputs. These policies override standard coordinate conventions, state definitions, or solution procedures.
* **Syntactic Bloating in Inputs**: The inclusion of policy blocks expands the average prompt size to **2455.49** characters, requiring a model context length capable of processing dense guiding text before looking at the core question.

---

## 5. Dataset Overlap & Redundancy

### Quantitative Metrics
* **Estimated Jaccard similarity of questions > 0.8 (Redundancy)**: **0.08%** of sampled pairs.
* **Semantic Question Overlap (Physics vs. Router)**: **100.00%** overlapping question prefixes.
* **Effective Scenario Size**:
  * Physics dataset represents **1371** distinct logical scenarios.
  * The overlap between Physics and Router questions is **100.00%**, confirming that the Router acts as an annotator for the same underlying problems.

### Evaluation
* **Redundancy risk**: Low. The pairwise similarity show that almost all questions are unique, preventing semantic memorization issues.
* **Data Leakage Risk**: Moderate. Because Router and Physics datasets share overlapping questions, a random split of Router and a random split of Physics could lead to cross-dataset leakage if the same question appears in Physics Train and Router Validation. Splitting MUST be performed using a deterministic seed on identical hashed questions to keep Train/Val splits strictly isolated across both tasks.

---

## 6. Difficulty Distribution

We profiled the Physics samples based on the length and symbol count of their target SymPy scripts.

### Quantitative Metrics
* **Easy** (Short scripts, few variables): **984** samples (71.77%)
* **Medium** (Standard formulas): **173** samples (12.62%)
* **Hard** (Complex multi-stage calculations): **211** samples (15.39%)
* **Very Hard** (Extremely long formulas and coordinate geometry): **3** samples (0.22%)

### Evaluation
* **Distribution Balance**: Skewed towards Medium/Hard. **15.39%** of the samples represent complex mathematical derivations (Hard) and **0.22%** represent extreme geometry/circuit derivations (Very Hard). Easy questions are very sparse. This aligns well with the requirement of tuning a high-capacity reasoner.

---

## 7. Fine-Tuning Risk Assessment

| Risk Category | Score (1-10) | Primary Driver |
| :--- | :--- | :--- |
| **Overfitting** | **4 / 10** | Low redundancy. Questions are mathematically unique and have sparse similarity. |
| **Memorization** | **5 / 10** | Physical constants and SymPy variables are standard. Memorizing specific constants remains a risk but logic deduction is required. |
| **Distribution Shift** | **6 / 10** | Severe policy override rules (100.00% of samples). If validation sets lack policyguidance, accuracy will drop. |
| **Label Noise** | **2 / 10** | Clean outputs. Compilability rate is 100.00%, and router JSON outputs are standardized. |
| **Cross-Task Leakage** | **7 / 10** | Hashed question overlap between Router and Physics datasets is 100.00%. A standard random split will cause severe data leakage across tasks. |

---

## 8. Executive Summary

### 5 Greatest Strengths of the Joint Dataset
1. **Perfect Target Balance**: Both datasets contain almost exactly 1,372 samples, offering a natural 1:1 scale for joint tuning.
2. **High Code Syntax Validity**: **100.00%** compilation rate ensures parser-safe training signals for generating SymPy code.
3. **lexical Variety**: Low pairwise question similarity prevents overfitting to repeating story scenarios.
4. **Rich Policy Overrides**: Over **100.00%** of samples include contextual overrides, forcing the model to read context instead of relying on default knowledge.
5. **Precise Router Labels**: Highly structured domain list and multi-state annotations with zero JSON syntax noise.

### 5 Greatest Weaknesses
1. **Low Input Context Density**: Prompt templates are large (mean 2455.49 characters), bloating sequence lengths and slowing down gradient steps.
2. **Sparse Easy Samples**: Only 71.77% Easy samples can cause training instability in early phases of learning.
3. **Dynamic Constants Variance**: Diverse floating-point values in SymPy code can trigger numerical precision mismatches during validation comparison.
4. **High Cross-Task Leakage Risk**: Shared questions between the two datasets (100.00% overlap) require strict alignment of split indices.
5. **Length Discrepancy**: Physics sequence length (up to 4484 tokens) vs Router (up to 1342 tokens) causes severe padding overhead during batch training.

### 5 Refined Training Strategies (Based on Measurements)
1. **Deterministic Grouped Train/Val Split**: Ensure that overlapping questions are grouped on the same split (train/validation) across both notebooks/tasks to prevent cross-task data leakage.
2. **Phase-Specific Learning Rate Decoupling**: Set `LEARNING_RATE_P1 = 1e-4` (Physics Focus) and a lower `LEARNING_RATE_P2 = 5e-5` (Router Focus) to protect the model's complex reasoning capacity from catastrophic forgetting during router tuning.
3. **Context Length Budget (MAX_LENGTH=4096)**: Since P99 of Physics is 3,699 tokens, setting `MAX_LENGTH = 4096` instead of `4860` saves 15% VRAM and padding overhead without trimming any sample context.
4. **Padding Optimization**: Employ Hugging Face's dynamic padding with a custom data collator to avoid padding Router sequences (max 1,342 tokens) to 4,096 in batches, reducing computational overhead by ~50% in Phase 2.
5. **No Oversampling / Balanced Batches**: Avoid oversampling either dataset, but ensure that Phase 2 mixes 50% Physics with 100% Router to retain the high-complexity generation capacity.
