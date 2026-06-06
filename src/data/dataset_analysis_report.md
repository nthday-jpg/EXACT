# Dataset Deep-Dive Analysis Report: FOL Translation & Reasoning

This report presents a comprehensive, data-driven analysis of the dataset located at `data/processed/logic_merged_valid.json` containing **1,812** logic reasoning samples. The analysis highlights key architectural weaknesses, vocabulary biases, logic gaps, and fine-tuning risks to guide data augmentation and model training strategies.

---

## 1. Vocabulary Analysis

### Quantitative Metrics
* **Total Vocabulary Size**:
  * **Natural Language (NL) Vocabulary**: 5,545 unique tokens (from 207,760 total tokens).
  * **Predicate Vocabulary**: 3,907 unique predicates (from 12,448 total predicate occurrences).
  * **Entity Vocabulary**: 853 unique entities (from 2,758 total entity occurrences).
* **Token Frequency Distribution (NL)**:
  * Cumulative frequency of the top **10%** of NL tokens: **79.09%**.
  * This indicates a highly skewed Zipfian distribution, where a small subset of structural and domain-specific words dominates the dataset text.
* **Out-Of-Vocabulary (OOV) Risk Estimation** (using Good-Turing singleton ratio $N_1 / N$):
  * **NL OOV Risk**: **0.20%** (2,036 singletons / 207,760 tokens).
  * **Predicate OOV Risk**: **3.22%** (401 singletons / 12,448 occurrences).
  * **Entity OOV Risk**: **1.78%** (49 singletons / 2,758 occurrences).

### Evaluation
* **Vocabulary Over-reliance**: Yes, the dataset's NL text is heavily reliant on a small group of words (top 10% covers 79.09% of tokens). These are mostly structural words (`all`, `if`, `then`, `no`, `some`, `either`, `or`, `and`) and highly repeated names/nouns.
* **Memorization Risk**: High. The predicate vocabulary has a high singleton ratio (3.22% OOV risk), meaning many predicates appear only once or twice in the entire dataset. This prevents the model from learning to generalize across predicate names, leading to a high risk of memorizing specific vocabulary-label correlations.

---

## 2. Entity Analysis

### Quantitative Metrics
* **Total Entity Count**: 2,758 occurrences.
* **Unique Entity Count**: 853 unique constants.
* **Entity Repetition Rate**: Only **7.74%** of entities appear in more than one story.
* **Average Story Span**: **1.15** stories per entity.
  * $92.26\%$ of entities are restricted to a single story ID.
* **Top 10 Most Frequent Entities**:
  1. `james` (44 occurrences)
  2. `john` (26)
  3. `jack` (24)
  4. `John` (17)
  5. `mary` (16)
  6. `sam` (15)
  7. `x_` (12)
  8. `_x` (12)
  9. `europe` (11)
  10. `peter` (10)

### Evaluation
* **Entity Dependency**: The dataset has extreme story-specificity. Entities do not recur across stories, meaning their naming is highly tied to individual logic problems.
* **Need for Entity Anonymization**: **Critical**. Because entities are unique to their stories, a model fine-tuned on this dataset can easily use entity names as shortcuts to memorize logical outcomes rather than performing logical deduction.
* **Memorization Risk**: High. The lack of entity sharing across stories creates a structural risk where the model associates specific names (e.g. `james` or `candace`) with specific reasoning outputs.

---

## 3. Predicate Analysis

### Quantitative Metrics
* **Total Predicate Count**: 12,448 occurrences.
* **Unique Predicate Count**: 3,907 unique predicates.
* **Predicate Entropy**: **11.48 bits** (very close to the maximum possible entropy of $\log_2(3907) \approx 11.93$ bits).
  * This indicates an extremely uniform, long-tailed distribution of predicate names across the dataset.
* **Top 10 Predicate Co-occurrence Pairs**:
  1. `("Research", "Thesis")` (24 occurrences)
  2. `("Quantum", "Research")` (24)
  3. `("Student", "Teacher")` (22)
  4. `("Qualified", "Student")` (22)
  5. `("Research", "Scholarship")` (22)
  6. `("Philosophy", "Quantum")` (22)
  7. `("Philosophy", "Research")` (22)
  8. `("Quantum", "Thesis")` (22)
  9. `("Philosophy", "Thesis")` (20)
  10. `("Quantum", "Scholarship")` (20)

### Evaluation
* **Predicate Dominance**: No individual predicate dominates the dataset. The predicate space is highly uniform, with most predicates appearing only in their own localized story context.
* **Predicate Space Coverage**: Extremely sparse. Since the average predicate appears only $\approx 3.18$ times in the entire dataset, there is minimal overlap in predicates between stories. This sparsity forces the model to process vocabulary-rich contexts but limits its ability to learn abstract predicate schemas.

---

## 4. Logical Structure Diversity

To evaluate logical diversity independently of vocabulary, all predicates were standardized to $P_1, P_2, \dots$ and entities to $c_1, c_2, \dots$ in order of appearance.

### Quantitative Metrics
* **Unique Abstract Logical Structures**: **679** unique structures out of 1,812 examples.
* **Structure Frequency Distribution**:
  * **1 occurrence**: 46 structures (6.77% of unique structures)
  * **2-5 occurrences**: 603 structures (88.81%)
  * **6-10 occurrences**: 25 structures (3.68%)
  * **11+ occurrences**: 5 structures (0.74%)
* **Top 3 Repeated Logical Structures**:
  1. `ForAll(v1, (P1(v1) -> NOT P2(v1))) ; ForAll(v1, (P1(v1) -> P2(v1))) ; ForAll(v1, (P1(v1) -> P2(v1))) ; ForAll(v1, (P1(v1) -> P2(v1))) ; P1(c1) OR P2(c1)` (27 occurrences)
  2. `ForAll(v1, (P1(v1) -> NOT P2(v1))) ; ForAll(v1, (P1(v1) -> P2(v1))) ; ForAll(v1, (P1(v1) -> P2(v1))) ; ForAll(v1, (P1(v1) -> P2(v1))) ; NOT(P1(c1) OR P2(c1))` (14 occurrences)
  3. `ForAll(v1, (P1(v1) -> NOT P2(v1))) ; ForAll(v1, (P1(v1) -> NOT P2(v1))) ; ForAll(v1, (P1(v1) -> P2(v1))) ; ForAll(v1, (P1(v1) -> P2(v1))) ; ForAll(v1, (P1(v1) OR P2(v1))) ; P1(c1) OR P2(c1)` (12 occurrences)

### Evaluation
* **Logic vs. Vocabulary Diversity**: The dataset exhibits a **high vocabulary diversity but low logical diversity**. While there are thousands of unique predicates and entities, they are mapped onto only 679 abstract logical templates. The dataset is structurally redundant, relying on a small set of FOLIO templates that are repeatedly populated with different words.

---

## 5. Quantifier Analysis

### Quantitative Metrics
* **Total Quantifier Occurrences**:
  * **ForAll ($\forall$)**: 11,251 occurrences (84.9%)
  * **Exists ($\exists$)**: 2,002 occurrences (15.1%)
* **Quantifier Entropy**: **0.612 bits** (max possible is 1.0, showing significant universal bias).
* **Quantifier Transition Matrix** (sequential occurrences within individual formulas):
  * `ForAll -> ForAll`: 1,078
  * `ForAll -> Exists`: 274
  * `Exists -> ForAll`: 183
  * `Exists -> Exists`: 141

### Evaluation
* **Missing Patterns**: Mixed-quantifier nesting (e.g. $\exists x \forall y$ or $\forall x \exists y \forall z$) is extremely rare.
* **Dominant Patterns**: Linear universal quantifier transitions (`ForAll -> ForAll`) dominate the dataset. The model receives insufficient training signals for existential instantiation and scope resolution when mixed with universal operators.

---

## 6. Reasoning Complexity Analysis

For each sample, a directed predicate dependency graph was built where an edge $P \rightarrow Q$ represents an implication rules linking predicate $P$ to $Q$.

### Quantitative Metrics
* **Implication Chain Length (Graph Depth) Distribution**:
  * **Mean Depth**: **2.44** steps
  * **Max Depth**: 10 steps
  * **Min Depth**: 0 steps
  * **Depth distribution table**:
    * Depth 0: 127 examples (7.0%)
    * Depth 1: 438 examples (24.2%)
    * Depth 2: 439 examples (24.2%)
    * Depth 3: 391 examples (21.6%)
    * Depth 4: 216 examples (11.9%)
    * Depth 5: 167 examples (9.2%)
    * Depth 6: 22 examples (1.2%)
    * Depth 7: 2 examples (0.1%)
    * Depth 8: 6 examples (0.3%)
    * Depth 10: 4 examples (0.2%)
* **Predicate Dependency Graph Branching Factor**:
  * **Mean Branching Factor**: **1.51**
  * **Max Branching Factor**: 13.5
  * **Min Branching Factor**: 0.0

### Evaluation
* **Average Reasoning Difficulty**: Low. **77%** of the dataset requires a reasoning depth of $\le 3$ steps.
* **Reasoning Depth Coverage**: Extremely thin for deep reasoning. Implication chains of depth $\ge 5$ constitute only $11\%$ of the dataset, and depth $\ge 6$ is under $2$. The model is under-trained on complex multi-hop logical deductions.

---

## 7. Dataset Coverage Analysis

### Coverage Matrix
The table below lists the frequency and example-level coverage of logical operators:

| Operator / Connective | Total Count | % of Examples Containing Operator |
| :--- | :--- | :--- |
| **ForAll ($\forall$)** | 11,251 | 93.38% |
| **Implication ($\rightarrow$)** | 10,957 | 93.71% |
| **NOT ($\neg$)** | 5,807 | 69.59% |
| **AND ($\land$)** | 3,180 | 52.10% |
| **Exists ($\exists$)** | 2,002 | 45.25% |
| **OR ($\lor$)** | 1,038 | 33.22% |
| **Biconditional ($\leftrightarrow$)** | 77 | 2.43% |

### Evaluation
* **Underrepresented Logic**: Biconditional operators ($\leftrightarrow$) are practically missing (only 2.43% coverage). Disjunction ($\lor$) is also highly underrepresented.
* **Overrepresented Logic**: Universal implication ($\forall x (P(x) \rightarrow Q(x))$) dominates the entire dataset (present in over 93% of samples), creating a strong structural bias.

---

## 8. Sample Similarity Analysis

### Quantitative Metrics
* **Pairwise NL Jaccard Similarity > 0.9**: 1,033 pairs.
* **Pairwise Exact Logical Similarity** (identical standardized FOL): 2,535 pairs.
* **Both NL > 0.9 and FOL identical (Near-Duplicates)**: 1,011 pairs.
* **Effective Dataset Size**:
  * The dataset contains **751 unique story IDs** for **1,812 examples**.
  * The average story is reused **2.41** times with different questions or labels.
  * **Effective size = 751 independent logical scenarios**.

### Evaluation
* **Redundancy**: The dataset has high redundancy (over 58% of examples are variants of existing stories).
* **Data Leakage Risk**: **Critical**. Since stories are reused, a standard random train/validation split will result in severe data leakage. 58% of the stories in the validation set will have their premises seen during training, artificially inflating evaluation scores. Splitting MUST be grouped by `story_id`.

---

## 9. Difficulty Distribution

Samples were classified into four difficulty levels based on: reasoning depth ($D$), quantifier nesting ($Q$), connective complexity ($C$), and premise count ($P$).

### Quantitative Metrics
* **Easy**: 10 examples (0.6%)
* **Medium**: 38 examples (2.1%)
* **Hard**: 449 examples (24.8%)
* **Very Hard**: 1,315 examples (72.6%)

### Evaluation
* **Syntactic Bloating**: The distribution is heavily skewed toward "Very Hard". This is primarily driven by high premise counts (mean 6.0) and high connective counts (mean 11.4), which trigger structural complexity thresholds.
* **Semantic Simplicity**: While the texts are syntactically long and complex, their actual reasoning depths are shallow (mean 2.44). The dataset represents a "syntactically bloated, semantically shallow" complexity profile.

---

## 10. Augmentation Opportunity Analysis

* **Logic Gaps**:
  * **Biconditionals ($\leftrightarrow$)**: Need targeting to bridge the 2.43% gap.
  * **Existential quantifiers ($\exists$)**: Must be balanced against universals to reduce the 5.6x universal bias.
  * **Disjunctions ($\lor$)**: Need additional coverage to improve disjunctive reasoning.
* **Reasoning Gaps**:
  * **Deep chain lengths**: Augmenting samples with implication chain depths between 4 and 8 is critical to prevent performance degradation on complex problems.
* **Label Noise and Normalization**:
  * The dataset contains inconsistent validation labels (`True`, `False`, `Unknown` mixed with `Yes`, `No`, `A`, `B`, `C`, `D`, and raw texts). Normalizing labels is required before fine-tuning.

---

## 11. Fine-Tuning Risk Assessment

| Risk Category | Score (1-10) | Primary Driver |
| :--- | :--- | :--- |
| **Overfitting** | **8 / 10** | High redundancy of abstract logic templates (only 679 templates for 1,812 examples) and low effective dataset size (751 unique stories). |
| **Memorization** | **9 / 10** | Entities (92%) and predicates are highly story-specific (average story span of 1.15). The model will memorize specific vocabulary tokens as shortcuts to logic outcomes. |
| **Distribution Shift** | **9 / 10** | Low coverage of deep implication chains (depth $\ge 5$ is only 11%) and biconditionals. The model will fail on multi-hop logical deductions at test time. |
| **Label Noise** | **7 / 10** | Inconsistent labels in the validation set (`Yes`/`No`/`A`/`B`/`C`/`D`) will corrupt the output alignment if not normalized. |
| **Shortcut Learning** | **8 / 10** | High overlap of identical premises across multiple examples allows the model to map text templates directly to answers without parsing logical steps. |

---

## 12. Executive Summary

### 5 Greatest Strengths of the Dataset
1. **High Vocabulary Diversity**: 3,907 unique predicates and 853 unique entities provide a rich lexical context representing realistic domain variety.
2. **Detailed Annotations**: Dual alignment between Natural Language (`premises-NL`) and First-Order Logic (`premises-FOL`) allows for training translation models.
3. **High Syntactic Complexity**: A large number of premises and logical connectives train models to handle long, complex input contexts.
4. **Structured Metadata**: The inclusion of `story_id` and `dataset_source` metadata enables proper grouping to prevent training leakage.
5. **No Exact Semantic Duplicates**: Almost all duplicate logical structures are instantiated with different domain vocabularies, ensuring lexical variety.

### 5 Greatest Weaknesses of the Dataset
1. **Logic Template Redundancy**: Heavy reuse of a small set of logical templates (679 structures for 1,812 examples), causing models to overfit structural patterns.
2. **Extreme Story-Specificity of Entities**: 92% of entities appear in exactly one story. The model will easily map entity names to logical targets (memorization shortcut).
3. **Severe Quantifier Imbalance**: Universal quantifiers outnumber existential quantifiers by 5.6x, leaving the model under-trained on existential logic.
4. **Shallow Reasoning Depth**: Mean implication depth is only 2.44 steps. 77% of the dataset requires $\le 3$ steps, leaving deep multi-hop reasoning untested.
5. **Inconsistent Answer Formats**: Inconsistent labels (`True`/`Yes`/`A` and raw text strings) introduce label noise into training.

### 5 Largest Data Gaps
1. **Biconditional Logic ($\leftrightarrow$)**: Present in only 2.43% of examples.
2. **Disjunctive Logic ($\lor$)**: Present in only 33.22% of examples.
3. **Deep Implication Chains**: Chains of depth $\ge 5$ represent only 11% of the dataset.
4. **Mixed Quantifier Transitions**: Sequences like $\exists x \forall y$ are virtually absent.
5. **Multi-argument Predicate Generalization**: Most predicates are unary, leaving n-ary predicate relations underrepresented.

### 5 Next Measurements to Perform Before Augmentation
1. **Rule-Level Semantic Consistency**: Check if the FOL rules are mathematically consistent (solvable by Z3) to prevent training on logical contradictions.
2. **Story-Level Lexical Overlap**: Measure the Jaccard overlap of NL vocabulary between different stories to identify if the dataset shares common context domains.
3. **Question-Premise Entity Overlap**: Quantify the percentage of entities in the question that are present in the premises to diagnose query-matching shortcuts.
4. **FOL Syntax Validity**: Run standard FOL parsers across all samples to ensure no syntax errors exist in the target training labels.
5. **Label-Story Correlation**: Check if specific story templates or sources are highly correlated with a single label (e.g. all FOLIO-train stories always yielding `True`), which would introduce shortcut learning.
