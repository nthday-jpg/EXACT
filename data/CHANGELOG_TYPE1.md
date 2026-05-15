# Type 1 — Logic-Based Educational Queries — Changelog

File: `Logic_Based_Educational_Queries_Text_Only.zip`
Records: 411 · Questions: 808

---

## 2026-05-15

> **Note on `idx`:** the `idx` field is **1-based** — values run from `1` to `n` (the number of premises). An entry `0` or `> n` is therefore invalid.

| Date       | Sample(s)                                                                                           | Bug                                                                                                                                     | Fix                                                                                               |
| ---------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 2026-05-15 | rec 57, 74, 76, 77, 79, 81, 83, 84, 85, 86, 87, 88, 89, 125, 126, 129, 334, 376, 382 (24 questions) | `idx` references out of range under the 1-based convention (uses `0`, or a value `> n`).                                                | Drop the invalid indices from the affected questions.                                             |
| 2026-05-15 | 9 questions across the corpus                                                                       | Answer label uses `Uncertain` / `True` / `False` instead of the standard `{Yes, No, Unknown}`.                                          | Normalize to `{Yes, No, Unknown}`.                                                                |
| 2026-05-15 | 103 MCQ records                                                                                     | Answer is `Unknown` although the explanation clearly names a winning option (A/B/C/D).                                                  | Replace `Unknown` with the option letter the explanation states.                                  |
| 2026-05-15 | rec 183, 381, 384, 405                                                                              | Further answer/explanation mismatches reported after the audit (e.g. rec 381 explanation concludes "(option A)" but answer was `B`).    | Flip each affected answer to match the explanation: `[A,Yes]`, `[A,Yes]`, `[D,Yes]`, `[A,Yes]`.   |
| 2026-05-15 | rec 133                                                                                             | MCQ uses a separate `choices` field instead of inlining the options into the question text — inconsistent with the rest of the dataset. | Inline options A–D into `questions[0]` and drop the `choices` field.                              |
| 2026-05-15 | rec 31 (P1, P2, P5, P8, P9, P10, P11, P14, P17, P19, P20)                                           | Premises use a free variable (`l`, `g`, `e`, `f`, `d`, `i`, `m`) without a `∀` quantifier, e.g. `play_based_learning(l) → …`.           | Add a leading `∀<v>` to each affected premise.                                                    |
| 2026-05-15 | rec 29 (P10)                                                                                        | `complete_modules(s,c1) ∧ … ∧ pass_exam(s,c4)` is bound only by `ForAll(s, …)` — `c1, c2, c3, c4` are free.                             | Wrap the body in `ForAll(c1, ForAll(c2, ForAll(c3, ForAll(c4, …))))` and balance the parentheses. |

**Known issue (not fixed):** 168 further MCQ records still answer
`Unknown`. The explanation does not contain an explicit option letter,
so we left them as-is rather than risk auto-flipping a genuinely
unknown answer.

---

## 2026-05-10

| Date       | Sample(s)                                                       | Bug                                                                                                                                            | Fix                                                                           |
| ---------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 2026-05-10 | rec 0 (P9), 209 (P6), 263 (P4), 330 (P14), 407 (P29), 410 (P12) | A leading `U+FFFD` (`�`) replacement character broke the FOL string (`�forall(x, …)`).                                                         | Strip the bad byte and rewrite as `∀x …`.                                     |
| 2026-05-10 | rec 30, 31, 32, 33, 34, 36, 39, 50                              | Ground-truth `answer` directly contradicts the verdict written in the same record's `explanation`.                                             | Flip the answer label to match the explanation.                               |
| 2026-05-10 | rec 23, 53                                                      | `premises-FOL` field was missing entirely.                                                                                                     | Wrote FOL for all 14 + 17 NL premises and re-checked with Z3 (both SAT).      |
| 2026-05-10 | rec 61, 63, 66, 72, 99, 160, 161, 372                           | Premises self-contradictory (Z3 reported UNSAT) — caused by over-strict translation of NL modal hedges.                                        | Rewrote 1–2 premises per record so the axioms are consistent (all 8 now SAT). |
| 2026-05-10 | 37 formulas across 17 records                                   | Annotation typos that broke the FOL parser (stray brackets, identifiers with `.`, set literals as bare arguments, chained inequalities, etc.). | Per-formula rewrite. Full table below.                                        |

### Formula-syntax fixes (2026-05-10)

| Bug class                                  |   # | Records affected         | Fix                                           |
| ------------------------------------------ | --: | ------------------------ | --------------------------------------------- |
| Extra trailing `)`                         |  16 | 20, 26, 29, 36, 157, 188 | Strip surplus paren                           |
| Missing trailing `)` (extra leading `(`)   |   4 | 304, 305, 306, 309       | Append paren                                  |
| Identifier with `.` (`GPA4.0`)             |   4 | 101                      | Rename → `GPA40`, `MaintainsGPA40`            |
| Time/unit literals (`9AM-5PM`, `80%`, ...) |   4 | 377, 378                 | Rename → `Time_9AM_to_5PM`, `Percent_80`, ... |
| Set literal as bare argument               |   2 | 376, 379                 | Expand `f(x, {a,b})` → `f(x,a) ∧ f(x,b)`      |
| Arithmetic-as-formula (`f(x)+f(y)=k`)      |   3 | 26, 36                   | Wrap in comparison or introduce func name     |
| Chained inequality `a ≤ x < b`             |   2 | 381, 382                 | Split into two `∧`-joined comparisons         |
| Multi-binding `∀x,v`                       |   1 | 132                      | Expand to nested `∀x ∀v`                      |
| Formula as `Count(...)` arg                |   1 | 362                      | Replace with named predicate `EnoughAGrades`  |
| `:`-ratio literal `2:1`                    |   1 | 26                       | Replace with positional args `ratio(_, 2, 1)` |

---

## Final state

- 411 records, 808 questions.
- 100% of formulas parse, 411/411 records Z3-SAT.
- Answer labels in `{Yes, No, Unknown, A, B, C, D}`; all `idx` values in `[1, n]`.
