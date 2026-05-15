# Type 2 — Physics Problems — Changelog

File: `Physics_Problems_Text_Only.zip`
Rows: 1,352

---

| Date       | Sample(s)                       | Bug                                                                                                                                                                                                                                                                           | Fix                                                                                                                                                           |
| ---------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-05-15 | 401 rows with `id` prefix `QA*` | Empty `answer` and `unit`. The question text is often truncated or asks no specific quantity; the CoT itself notes it (e.g. "_The question text is incomplete_", "_No specific physics quantity is asked_"). Cannot be auto-graded.                                           | Drop all 401 rows.                                                                                                                                            |
| 2026-05-15 | 2 rows                          | Empty `cot` field — no chain-of-thought to learn from / evaluate.                                                                                                                                                                                                             | Drop both rows.                                                                                                                                               |
| 2026-05-15 | CH377, TD357                    | The `question` field starts with translation meta-text such as _"Here are a few ways to translate that question…"_ followed by several paraphrased options, instead of a single clean problem statement.                                                                      | Rewrite each question as a single clean statement (the meaning of the original options).                                                                      |
| 2026-05-15 | LD021                           | The `question` describes the setup but never actually asks anything — no question or imperative.                                                                                                                                                                              | Append _"Calculate the magnitude of the net electric force acting on q."_ (which matches the existing `answer = 2.98 N`).                                     |
| 2026-05-15 | LD002                           | Question says "right-angled triangle ABC" without specifying which vertex carries the right angle. The provided answer (24.45×10⁻³ N) only follows if the right angle is at A.                                                                                                | Add "(right-angled at A)" to the problem statement.                                                                                                           |
| 2026-05-15 | LD053, LD054, LD056, LD057      | Each question asks for **two** separate quantities (electric field strength _E_ and electric force _F_), but `answer` / `unit` only holds one of the two — making the problem unanswerable in the expected single-value format.                                               | Trim each question to ask for the single quantity that matches the existing answer (LD053 / LD056 keep the _E_ part; LD054 / LD057 keep the _F_ part).        |
| 2026-05-15 | TD051, TD054, TD057, TD087      | "Step 2" of the chain-of-thought writes the **voltage** value into the **capacitance** variable, e.g. TD051 (C = 4.68 pF, V = 199.6 V) reads "_Convert the capacitance to SI units: C = 199.6 × 10⁻¹² F_". The final answer is correct but the intermediate reasoning is not. | Replace the wrong number in Step 2 of each record with the correct capacitance from the question (TD051 → 4.68, TD054 → 60.70, TD057 → 31.89, TD087 → 27.63). |
| 2026-05-15 | TD371, LD020                    | Mixed-language unit labels — `"lần"` (TD371) and `"Độ"` (LD020) are Vietnamese, the rest of the corpus is English.                                                                                                                                                            | Normalize to `"times"` and `"degree"` respectively.                                                                                                           |
| 2026-05-15 | TD179                           | Typo in the question: _"…rounded to onedecimal places."_ (missing space).                                                                                                                                                                                                     | Fix to _"one decimal places"_.                                                                                                                                |
| 2026-05-15 | TD401                           | Magnitude / unit-conversion error in `answer`. CoT correctly applies `E = ½ × C × U²` with `C = 100 µF = 1 × 10⁻⁴ F`, `U = 30 V` → `0.045 J`, but the `answer` field was `45` (off by 10³).                                                                                   | Set `answer = 0.045` (unit `J` unchanged).                                                                                                                    |
| 2026-05-15 | TD179                           | Propagated rounding error in `answer`. Direct calculation `½ × 36.53 × 10⁻¹² × 124.5²` = 283.11… nJ → rounds to **283.1 nJ**; the CoT itself states `≈ 283.1 nJ`, but the `answer` field was `283.2`.                                                                          | Set `answer = 283.1`.                                                                                                                                         |
| 2026-05-15 | TD181                           | Hidden unrounded value in `answer`. Direct calculation from the question text `22.30 × 10⁻¹² × 65.2` = 1.45396 nC → rounds to **1.45 nC**; the CoT itself states `≈ 1.45 nC`, but the `answer` field was `1.46` (derived by reusing an unrounded `C` from TD180).              | Set `answer = 1.45`.                                                                                                                                          |
| 2026-05-15 | 914 cot fields, 15 questions    | Multiplication symbol used inconsistently across the corpus: `*`, `·` (U+00B7) and `×` all appear in roughly comparable counts.                                                                                                                                               | Normalize all multiplication operators in `question` and `cot` to `×`.                                                                                        |

Examples of the QA pattern (last 4 before drop):

| id    | Question (truncated)                                                                             | CoT excerpt                                                       |
| ----- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| QA663 | "A vehicle with a mass of 20 kg moves up a slope of length 5 m."                                 | "Step 3: The question text is incomplete, ending with 'ng...'..." |
| QA675 | "Perform Young's double-slit experiment using a source... λ1..."                                 | "Step 3: No values are provided for λ1..."                        |
| QA691 | "A bullet of mass m=1kg, moving horizontally at v1=300m/s, penetrates a 5cm thick wooden board." | "Step 4: No specific physics quantity is asked."                  |
| QA703 | "Write an algebraic expression representing the distance traveled by a vehicle after x hours."   | "Step 3: The speed of the vehicle is not given..."                |

---

## Final state

- 1,352 rows. 0 empty `answer` / `unit` / `cot`.
- Net change vs. the 2026-05-09 release: 1,755 → 1,352 (−403).

### id-prefix distribution

```
LD     397
CH     290
NL     190
TD     177
DDT    130
THCB    80
DT      68
CHLT    20
------------
Total 1,352
```
