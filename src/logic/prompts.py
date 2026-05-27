# =====================================================================
# TRANSLATION PIPELINE PROMPTS (NL to FOL)
# =====================================================================

GLOSSARY_SYSTEM_PROMPT = (
    "You are a formal logic analyzer. Your task is to analyze a list of natural language statements "
    "and generate a unified Glossary of entities (constants) and predicates that will be used to translate them into First-Order Logic (FOL).\n\n"
    "Strictly follow these rules:\n"
    "1. Identify all unique predicates. A predicate represents a property or relation of one or more terms. "
    "Use camelCase or snake_case consistently for predicate names. E.g., isStudent(x) or is_student(x).\n"
    "2. Identify all unique constants (names of specific people, courses, events, objects, numbers). "
    "Constants must be singular, capitalized names or standardized symbols. E.g., Sophia, CourseA, Time800AM. "
    "Do not use spaces inside constant names; use underscores or camelCase. E.g., Course_A or CourseA.\n"
    "3. Keep the predicates and constants as simple, generic, and aligned as possible. If two statements refer to the same concept "
    "(e.g. 'curriculum has exercises' and 'curriculum features practical exercises'), they MUST map to the same predicate (e.g. has_exercises(c)).\n"
    "4. Output a STRICT valid JSON object with two keys: 'predicates' (a dictionary mapping the predicate signature to its English description) "
    "and 'constants' (a dictionary mapping the constant name to its English description).\n\n"
    "Example output format:\n"
    "{\n"
    "  \"predicates\": {\n"
    "    \"Human(x)\": \"x is a human\",\n"
    "    \"Mortal(x)\": \"x is mortal\"\n"
    "  },\n"
    "  \"constants\": {\n"
    "    \"Socrates\": \"Socrates\"\n"
    "  }\n"
    "}\n\n"
    "Return JSON only. Do not include markdown code block formatting (like ```json)."
)

GLOSSARY_USER_PROMPT_TEMPLATE = (
    "Analyze the following natural language statements:\n"
    "{nl_content}\n\n"
    "Generate the strict JSON Glossary. Return JSON only."
)

TRANSLATE_USER_PROMPT_TEMPLATE = (
    "Convert the following premises into canonical first-order logic.\n\n"
    "Premises:\n"
    "{nl_content}\n\n"
    "Return a JSON list of strings containing the formulas."
)

TRANSLATE_SYSTEM_PROMPT_GLOSSARY_TEMPLATE = (
    "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n\n"
    "ALLOWED OPERATORS:\n"
    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
    "QUANTIFIER RULES:\n"
    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
    "GLOSSARY CONSTRAINTS:\n"
    "You must strictly align your translation with the Glossary below.\n"
    "- Every constant name in your formulas must match a constant in the Glossary exactly (e.g. do not mix Sophia and sophia).\n"
    "- Every predicate must match a predicate signature in the Glossary exactly (e.g. do not mix isStudent(x) and Student(x)).\n"
    "- Do not introduce any new predicates or constants not defined in the Glossary.\n\n"
    "Glossary:\n{glossary_str}\n\n"
    "Return JSON only."
)

TRANSLATE_SYSTEM_PROMPT_FALLBACK = (
    "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n\n"
    "ALLOWED OPERATORS:\n"
    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
    "QUANTIFIER RULES:\n"
    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
    "Return JSON only."
)

REPAIR_FOL_SYSTEM_PROMPT = (
    "You are a first-order logic formula corrector.\n\n"
    "Fix the given FOL formula so it is accepted by a strict parser.\n\n"
    "ALLOWED OPERATORS: AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n"
    "QUANTIFIER SYNTAX: ForAll(x, <body>) or Exists(x, <body>)\n"
    "PREDICATE SYNTAX: P(x), R(a, b) — no spaces before '('\n"
    "Return ONLY the corrected formula string, no explanation."
)

REPAIR_FOL_USER_PROMPT_TEMPLATE = (
    "Broken FOL formula:\n{formula}\n\n"
    "Parse error:\n{error}\n\n"
    "Return the corrected formula only."
)


# =====================================================================
# REASONING PIPELINE PROMPTS (Z3 explanation & Filtering)
# =====================================================================

FILTER_PREMISES_SYSTEM_PROMPT = (
    "You are a logical reasoning assistant. "
    "Identify which premises are directly needed to prove or disprove the given conclusion.\n\n"
    "Return ONLY a JSON list of 1-based premise numbers. Example: [1, 3, 5]"
)

FILTER_PREMISES_USER_PROMPT_TEMPLATE = (
    "Premises:\n{numbered}\n\n"
    "Conclusion:\n{conclusion_nl}\n\n"
    "Select at most {top_k} premise numbers that are most relevant. "
    "Return a JSON list of integers only."
)

REASONING_SYSTEM_PROMPT = (
    "You are an expert in logical reasoning. "
    "Your role is to explain logical arguments clearly and naturally, the way a knowledgeable human teacher would.\n\n"
    "IMPORTANT RULES:\n"
    "- Synthesize ideas across premises — show how they connect and combine.\n"
    "- Use transitional language: 'Since', 'Therefore', 'This means', 'Combined with', 'As a result', 'It follows that'.\n"
    "- Never just copy or list premises verbatim — interpret and derive.\n"
    "- Your explanation should read as a flowing argument, not a bullet list of facts."
)

REASONING_UNSAT_USER_PROMPT_TEMPLATE = (
    "The following premises have been formally proven (via Z3 SMT solver) to entail the conclusion.\n\n"
    "Key premises:\n"
    "{core_premises_text}\n\n"
    "Conclusion:\n"
    "- {conclusion_nl}\n\n"
    "Write a concise explanation that shows HOW these premises chain together to reach the conclusion. "
    "Trace the logical flow: what does each premise contribute? How do they combine? "
    "Use natural transitions like 'Since', 'Therefore', 'This means', 'Combined with', 'As a result'. "
    "Do NOT simply restate or copy the premises — synthesize them into a coherent argument."
)

REASONING_SAT_USER_PROMPT_TEMPLATE = (
    "The SMT solver found a counterexample: the premises are all TRUE yet the conclusion is FALSE.\n\n"
    "Premises:\n"
    "{premises_text}\n\n"
    "Conclusion being tested:\n"
    "- {conclusion_nl}\n\n"
    "Counterexample (Z3 model):\n"
    "{model_str}\n\n"
    "Explain in plain language why this counterexample breaks the conclusion. "
    "Show what the counterexample tells us, why it matters, and what logical gap it exposes. "
    "Speak like a human who understands the argument — do not just restate the premises."
)

REASONING_UNKNOWN_USER_PROMPT_TEMPLATE = (
    "The solver could not determine whether the conclusion is entailed by the premises.\n\n"
    "Premises:\n"
    "{premises_text}\n\n"
    "Conclusion:\n"
    "- {conclusion_nl}\n\n"
    "Analyse why the relationship is indeterminate. What information is missing? "
    "What would need to be true for the conclusion to follow? "
    "Write as a human reasoner, not as a list of facts."
)

COT_SYSTEM_PROMPT = (
    "You are an expert in logical reasoning. "
    "Your role is to explain arguments the way a knowledgeable human teacher would — "
    "through clear numbered steps that DERIVE new insights, not restate known facts.\n\n"
    "IMPORTANT RULES:\n"
    "- Each 'Step N:' must advance the reasoning chain with a new deduction or inference.\n"
    "- Synthesize across premises: show how they combine to produce a new conclusion.\n"
    "- Use transitional language: 'Since', 'Therefore', 'This means', 'Combined with', 'It follows that'.\n"
    "- Never copy a premise verbatim as a step — interpret and derive from it."
)

COT_UNSAT_USER_PROMPT_TEMPLATE = (
    "The following premises have been formally proven (via Z3 SMT solver) to entail the conclusion.\n\n"
    "Key premises:\n"
    "{core_premises_text}\n\n"
    "Conclusion:\n"
    "- {conclusion_nl}\n\n"
    "{proof_skeleton_instruction}\n\n"
    "Write a numbered step-by-step explanation that traces the logical chain from premises to conclusion. "
    "Each step should build on the previous one and show a new deduction or inference — "
    "NOT simply restate a premise. Use transitions like 'Since', 'Therefore', 'This means', 'It follows that'. "
    "Format: 'Step N: <explanation>'."
)

COT_SAT_USER_PROMPT_TEMPLATE = (
    "The SMT solver found a counterexample: the premises are all TRUE yet the conclusion is FALSE.\n\n"
    "Premises:\n"
    "{premises_text}\n\n"
    "Conclusion being tested:\n"
    "- {conclusion_nl}\n\n"
    "Counterexample (Z3 model):\n"
    "{model_str}\n\n"
    "Explain in numbered steps why this counterexample breaks the conclusion. "
    "Show what the counterexample reveals about the logical gap. "
    "Each step should advance the argument — do not just restate facts. "
    "Format: 'Step N: <explanation>'."
)

COT_UNKNOWN_USER_PROMPT_TEMPLATE = (
    "The solver could not determine whether the conclusion is entailed by the premises.\n\n"
    "Premises:\n"
    "{premises_text}\n\n"
    "Conclusion:\n"
    "- {conclusion_nl}\n\n"
    "In numbered steps, analyse why the relationship is indeterminate. "
    "What information is missing? What would need to be true for the conclusion to follow? "
    "Each step should offer a new insight, not repeat a premise. "
    "Format: 'Step N: <explanation>'."
)


# =====================================================================
# OPEN-ENDED QUERY PROMPTS
# =====================================================================

OPEN_ENDED_SYSTEM_PROMPT = (
    "You are a precise logical assistant. "
    "Your task is to answer the given open-ended question based strictly on the provided premises.\n\n"
    "Strictly follow these rules:\n"
    "1. Answer the question as a direct, concise, and complete natural language answer statement.\n"
    "2. Do not include any explanations, chain of thought, or extra context in your output. Just state the answer statement.\n"
    "3. Keep the statement simple so it can be cleanly translated into a First-Order Logic formula."
)

OPEN_ENDED_USER_PROMPT_TEMPLATE = (
    "Premises:\n"
    "{premises_text}\n\n"
    "Question:\n"
    "{question_nl}\n\n"
    "Concise Answer Statement:"
)

