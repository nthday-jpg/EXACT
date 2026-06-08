import json
import re
from pathlib import Path

notebook_paths = [
    Path("src/llm/tuning/fol.ipynb"),
    Path("src/llm/tuning/fol_and_physics.ipynb")
]

for path in notebook_paths:
    if not path.exists():
        print(f"Skipping {path} (not found)")
        continue
        
    print(f"Patching {path}...")
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    patched = False
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            source = "".join(cell["source"])
            if "def check_sample_with_z3" in source and "def parse_formulas" in source:
                # 1. Inject lowercase_constants_and_variables helper before parse_formulas
                helper_code = """
def lowercase_constants_and_variables(formula: str) -> str:
    reserved = {"ForAll", "Exists", "AND", "OR", "NOT", "In", "implies", "BICOND", "IMPLIES"}
    def repl(match):
        word = match.group(1)
        if word in reserved or word.isdigit():
            return word
        return word.lower()
    return re.sub(r"\\b([A-Za-z_][A-Za-z0-9_]*)\\b(?!\\s*\\()", repl, formula)
"""
                # 2. Modify parse_formulas to apply lowercase normalization to formulas
                old_parse_formulas = """    def parse_formulas(formulas: list[str], sort_name="U") -> tuple[Z3Symbols, list[BoolRef]]:
        numeric_symbols = set()"""
                
                new_parse_formulas = """    def parse_formulas(formulas: list[str], sort_name="U") -> tuple[Z3Symbols, list[BoolRef]]:
        # Standardize and lowercase constants/variables in formulas
        normalized_formulas = []
        for f in formulas:
            f_clean = f.strip()
            f_clean = f_clean.replace("¬", "NOT ").replace("∧", " AND ").replace("∨", " OR ").replace("→", " -> ").replace("↔", " <-> ")
            open_count = f_clean.count("(")
            close_count = f_clean.count(")")
            if close_count < open_count:
                f_clean = f_clean + ")" * (open_count - close_count)
            f_clean = lowercase_constants_and_variables(f_clean)
            normalized_formulas.append(f_clean)
        formulas = normalized_formulas

        numeric_symbols = set()"""
                
                # 3. Update translate_sentences and translate_single_sentence signatures to support glossary_str
                old_translate_sentences = """def translate_sentences(model, tokenizer, sentences: list[str]) -> list[str]:"""
                new_translate_sentences = """def translate_sentences(model, tokenizer, sentences: list[str], glossary_str=None) -> list[str]:"""
                
                old_translate_single_sentence = """def translate_single_sentence(model, tokenizer, s: str) -> str:"""
                new_translate_single_sentence = """def translate_single_sentence(model, tokenizer, s: str, glossary_str=None) -> str:"""
                
                # 4. Inject glossary prompt logic into translate_sentences and translate_single_sentence
                old_messages_setup = """    messages = [
        {"role": "system", "content": system_prompt_template},
        {"role": "user", "content": user_prompt.strip()}
    ]"""
                
                new_messages_setup = """    sys_prompt = system_prompt_template
    if glossary_str:
        sys_prompt = (
            "You convert natural-language premises into parser-safe first-order logic formulas.\\n\\n"
            "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\\n"
            "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\\n\\n"
            "ALLOWED OPERATORS:\\n"
            "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\\n\\n"
            "QUANTIFIER RULES:\\n"
            "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\\n\\n"
            "GLOSSARY CONSTRAINTS:\\n"
            "You MUST strictly align your translation with the predicates and constants used in the premises:\\n"
            f"{glossary_str}\\n\\n"
            "Return JSON only."
        )
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt.strip()}
    ]"""
                
                # 5. Update check_sample_with_z3 to extract glossary from predicted premises and pass it
                old_check_sample = """def check_sample_with_z3(predicted_premises_fol, question, model, tokenizer, premises_nl=None):
    from z3 import unsat, sat
    options = parse_mcq_options(question)
    
    if len(options) >= 2:"""
                
                new_check_sample = """def check_sample_with_z3(predicted_premises_fol, question, model, tokenizer, premises_nl=None):
    from z3 import unsat, sat
    options = parse_mcq_options(question)
    
    # Extract glossary from predicted premises
    predicates = set()
    constants = set()
    reserved = {"ForAll", "Exists", "AND", "OR", "NOT", "In", "implies", "BICOND", "IMPLIES"}
    for formula in predicted_premises_fol:
        if not formula:
            continue
        calls = re.findall(r"\\b([A-Za-z_][A-Za-z0-9_]*)\\s*\\(([^()]*)\\)", formula)
        for name, args_str in calls:
            if name in reserved:
                continue
            args = [a.strip() for a in args_str.split(",") if a.strip()]
            arity = len(args)
            predicates.add(f"{name}({', '.join(['x']*arity)})")
            for arg in args:
                if arg not in {"x", "y", "z", "w", "u", "v", "a", "b", "c"} and not arg.isdigit():
                    constants.add(arg)
        comp_matches = re.findall(r"(=|!=|>=|<=|>|<)\\s*([A-Za-z0-9_']+)", formula)
        for op, val in comp_matches:
            val = val.strip().strip("'")
            if val and not val.isdigit() and val not in {"x", "y", "z", "w", "u", "v", "a", "b", "c"}:
                constants.add(val)
    pred_str = ", ".join(sorted(list(predicates)))
    const_str = ", ".join(sorted(list(constants)))
    glossary_str = f"Predicates: {pred_str}\\nConstants: {const_str}"
    
    if len(options) >= 2:"""
                
                # Update option/conclusion translations in check_sample_with_z3 to pass glossary_str
                old_opt_fol_call = """        options_fol = translate_sentences(model, tokenizer, opt_texts)
        if len(options_fol) != len(opt_keys):
            options_fol = []
            for opt_text in opt_texts:
                options_fol.append(translate_single_sentence(model, tokenizer, opt_text))"""
                
                new_opt_fol_call = """        options_fol = translate_sentences(model, tokenizer, opt_texts, glossary_str=glossary_str)
        if len(options_fol) != len(opt_keys):
            options_fol = []
            for opt_text in opt_texts:
                options_fol.append(translate_single_sentence(model, tokenizer, opt_text, glossary_str=glossary_str))"""
                
                old_conc_fol_call = """        conclusion_text = strip_question_framing(question)
        conclusion_fol_list = translate_sentences(model, tokenizer, [conclusion_text])"""
                
                new_conc_fol_call = """        conclusion_text = strip_question_framing(question)
        conclusion_fol_list = translate_sentences(model, tokenizer, [conclusion_text], glossary_str=glossary_str)"""
                
                # Perform the modifications
                new_source = source
                if helper_code not in new_source:
                    new_source = new_source.replace("class Z3Symbols:", helper_code + "\nclass Z3Symbols:")
                new_source = new_source.replace(old_parse_formulas, new_parse_formulas)
                new_source = new_source.replace(old_translate_sentences, new_translate_sentences)
                new_source = new_source.replace(old_translate_single_sentence, new_translate_single_sentence)
                new_source = new_source.replace(old_messages_setup, new_messages_setup)
                new_source = new_source.replace(old_check_sample, new_check_sample)
                new_source = new_source.replace(old_opt_fol_call, new_opt_fol_call)
                new_source = new_source.replace(old_conc_fol_call, new_conc_fol_call)
                
                cell["source"] = [line + "\n" if idx < len(new_source.split("\n"))-1 else line for idx, line in enumerate(new_source.split("\n"))]
                patched = True
                
    if patched:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Successfully patched {path}")
    else:
        print(f"Could not find or match Z3 logic block in {path}")
