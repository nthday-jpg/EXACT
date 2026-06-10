import json
import os
import re

# 1. Load the router system prompt
with open(r"src/physics/instructions/router.md", "r", encoding="utf-8") as f:
    router_system_prompt = f.read().strip()

# 2. Load the original fol_and_physics notebook
with open(r"src/llm/tuning/fol_and_physics.ipynb", "r", encoding="utf-8") as f:
    notebook = json.load(f)

cells = notebook["cells"]

# --- CELL 1: TRAINING HYPERPARAMETERS ---
hyper_cell = cells[1]
hyper_source = "".join(hyper_cell["source"])

# Replace MAX_LENGTH
hyper_source = re.sub(r"MAX_LENGTH\s*=\s*\d+", "MAX_LENGTH = 1500", hyper_source)
hyper_cell["source"] = [line + "\n" for line in hyper_source.splitlines()]

# --- CELL 2: DATA LOADING ---
data_cell = cells[2]

# Escape backslashes and double quotes safely
escaped_router_prompt = router_system_prompt.replace('\\', '\\\\').replace('"', '\\"')

new_data_source = """# 3. Load NL -> FOL translation datasets, Router dataset, and Router Prompt
import os
import json

merged_path = "/kaggle/input/datasets/mduy2911/folc-train/logic_merged_valid_augmented.json"
router_path = "/kaggle/input/datasets/mduy2911/folc-train/router_dataset.json"

def load_translation_dataset(path):
    samples = []
    seen_premises = set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        nl_list = item.get("premises-NL", [])
        fol_list = item.get("premises-FOL", [])
        if not nl_list or not fol_list or len(nl_list) != len(fol_list):
            continue
        nl_serialized = "\\n".join(nl_list)
        if nl_serialized in seen_premises:
            continue
        seen_premises.add(nl_serialized)
        
        sample_dict = {
            "premises-NL": nl_list, 
            "premises-FOL": fol_list,
            "example_id": item.get("example_id", ""),
            "dataset_source": item.get("dataset_source", ""),
            "question": item.get("question", ""),
            "answer": item.get("answer", "")
        }
        if "split" in item:
            sample_dict["split"] = item["split"]
        samples.append(sample_dict)
        
    print(f"Loaded {len(samples)} unique translation samples from {os.path.basename(path)}")
    return samples

def load_router_dataset(path):
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        inp = item.get("input", "")
        out = item.get("output", "")
        if inp and out:
            samples.append({"input": inp, "output": out})
    print(f"Loaded {len(samples)} router samples from {os.path.basename(path)}")
    return samples

raw_samples = load_translation_dataset(merged_path)
router_samples = load_router_dataset(router_path)

router_system_prompt = \"\"\"""" + escaped_router_prompt + """\"\"\".strip()
"""

data_cell["source"] = [line + "\n" for line in new_data_source.splitlines()]

# --- CELL 4: DATASET PREP ---
prep_cell = cells[4]
new_prep_source = """# 5. Format Dataset (Chat Template) and split Train/Val
import os
import json
import random
from datasets import Dataset

# Define prompt templates for flat JSON list output with strict count constraint
system_prompt_template = (
    "You convert natural-language premises into parser-safe first-order logic formulas.\\n\\n"
    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\\n"
    "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\\n\\n"
    "ALLOWED OPERATORS:\\n"
    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\\n\\n"
    "QUANTIFIER RULES:\\n"
    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\\n\\n"
    "NUMERICAL ATTRIBUTES & COMPARISONS:\\n"
    "Represent numerical attributes (e.g., age, score, GPA, duration, credits) as functions mapping to a number, and compare using operators (=, !=, >=, <=, >, <).\\n"
    "E.g., \\\"John has a GPA of 3.8\\\" -> GPA(john) = 3.8\\n"
    "E.g., \\\"GPA is at least 3.5\\\" -> ForAll(x, GPA(x) >= 3.5 -> ...)\\n"
    "Do NOT use binary predicates like GPA(john, 3.8).\\n\\n"
    "DOMAIN RESTRICTION RULE:\\n"
    "Restrict the domain of quantified variables to the relevant category.\\n"
    "E.g., \\\"All students are happy\\\" -> ForAll(x, Student(x) -> Happy(x))\\n"
    "Do NOT write ForAll(x, Happy(x)).\\n\\n"
    "Return JSON only."
)

user_prompt_template = (
    "Convert the following {num_premises} premises into canonical first-order logic.\\n\\n"
    "Premises:\\n"
    "{premises}\\n\\n"
    "Return a JSON list of exactly {num_premises} strings containing the formulas, in the exact same order."
)

# --- Split FOL dataset before augmentation to prevent data leakage ---
has_presplit = all("split" in sample for sample in raw_samples)
if has_presplit:
    train_fol = [s for s in raw_samples if s.get("split") == "train"]
    val_fol = [s for s in raw_samples if s.get("split") == "val"]
    train_orig_fol = [s for s in train_fol if "augmented" not in str(s.get("dataset_source", ""))]
    val_orig_fol = val_fol
    train_augmented_fol = [s for s in train_fol if "augmented" in str(s.get("dataset_source", ""))]
else:
    original_fol = []
    augmented_fol = []
    for sample in raw_samples:
        ds = str(sample.get("dataset_source", ""))
        if "augmented" in ds:
            augmented_fol.append(sample)
        else:
            original_fol.append(sample)

    # Shuffle original FOL samples deterministically
    random.Random(42).shuffle(original_fol)
    split_idx_fol = int(len(original_fol) * 0.9)
    train_orig_fol = original_fol[:split_idx_fol]
    val_orig_fol = original_fol[split_idx_fol:]

    # Map augmented samples back to train split
    train_orig_ids = set(x["example_id"] for x in train_orig_fol)

    def get_original_id(example_id):
        for suffix in ["_aug_var", "_perm_var", "_neg_var"]:
            if suffix in example_id:
                return example_id.split(suffix)[0]
        return example_id

    train_augmented_fol = []
    for sample in augmented_fol:
        base_id = get_original_id(sample["example_id"])
        if base_id in train_orig_ids:
            train_augmented_fol.append(sample)

    # Combine splits
    train_fol = train_orig_fol + train_augmented_fol
    val_fol = val_orig_fol

# --- Split Router dataset deterministically ---
random.Random(42).shuffle(router_samples)
split_idx_router = int(len(router_samples) * 0.9)
train_router = router_samples[:split_idx_router]
val_router = router_samples[split_idx_router:]

# --- Format training and validation samples ---
def format_samples(fol_list, router_list, balance_oversample=False):
    fol_samples = []
    # Format FOL translation samples
    for item in fol_list:
        nl_list = item["premises-NL"]
        fol_list_item = item["premises-FOL"]
        
        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\\n"
            
        user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())
        assistant_response = json.dumps(fol_list_item, indent=2)
        
        fol_samples.append({
            "messages": [
                {"role": "system", "content": system_prompt_template},
                {"role": "user", "content": user_prompt.strip()},
                {"role": "assistant", "content": assistant_response.strip()}
            ]
        })
        
    router_samples_formatted = []
    # Format Router samples
    for item in router_list:
        router_input = item["input"]
        router_output = item["output"]
        
        router_samples_formatted.append({
            "messages": [
                {"role": "system", "content": router_system_prompt},
                {"role": "user", "content": f"<QUESTION>\\n{router_input.strip()}\\n</QUESTION>"},
                {"role": "assistant", "content": router_output.strip()}
            ]
        })
        
    if balance_oversample:
        target_len = max(len(fol_samples), len(router_samples_formatted))
        print(f"Balancing datasets via oversampling: target size = {target_len}")
        
        if len(fol_samples) < target_len:
            extra_needed = target_len - len(fol_samples)
            fol_samples += random.Random(42).choices(fol_samples, k=extra_needed)
        if len(router_samples_formatted) < target_len:
            extra_needed = target_len - len(router_samples_formatted)
            router_samples_formatted += random.Random(42).choices(router_samples_formatted, k=extra_needed)
            
    formatted = fol_samples + router_samples_formatted
    return formatted

def apply_template(batch):
    texts = []
    for messages in batch["messages"]:
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return {"text": texts}

# --- PREPARE VAL DATASET (Common for both phases) ---
formatted_val = format_samples(val_fol, val_router, balance_oversample=False)
val_dataset = Dataset.from_list(formatted_val)
val_dataset = val_dataset.map(apply_template, batched=True, remove_columns=["messages"])
val_dataset = val_dataset.shuffle(seed=42)

# --- PREPARE DATASETS FOR PHASE 1 ---
# FOL: 100%, Router: 20%
num_router_p1 = int(len(train_router) * 0.20)
train_router_p1 = train_router[:num_router_p1]

formatted_train_p1 = format_samples(train_fol, train_router_p1, balance_oversample=False)
train_dataset_p1 = Dataset.from_list(formatted_train_p1)
train_dataset_p1 = train_dataset_p1.map(apply_template, batched=True, remove_columns=["messages"])
train_dataset_p1 = train_dataset_p1.shuffle(seed=42)

# --- PREPARE DATASETS FOR PHASE 2 ---
# Router: 100%, FOL: 50%
num_fol_p2 = int(len(train_fol) * 0.50)
train_fol_p2 = random.Random(42).sample(train_fol, num_fol_p2)

formatted_train_p2 = format_samples(train_fol_p2, train_router, balance_oversample=False)
train_dataset_p2 = Dataset.from_list(formatted_train_p2)
train_dataset_p2 = train_dataset_p2.map(apply_template, batched=True, remove_columns=["messages"])
train_dataset_p2 = train_dataset_p2.shuffle(seed=42)

print(f"FOL Train/Val Split: original train={len(train_orig_fol)}, original val={len(val_orig_fol)}")
print(f"FOL Augmented added to Train: {len(train_augmented_fol)}")
print(f"Router Train/Val Split: train={len(train_router)}, val={len(val_router)}")
print(f"Common Validation size: {len(val_dataset)}")
print(f"Phase 1 - Train size (100% FOL : 20% Router): {len(train_dataset_p1)}")
print(f"Phase 2 - Train size (100% Router : 50% FOL): {len(train_dataset_p2)}")
"""
prep_cell["source"] = [line + "\n" for line in new_prep_source.splitlines()]

# --- CELL 5: SFT TRAINING SETUP AND CALLBACKS ---
training_cell = cells[5]

new_training_source = """# 6. SFT Training Setup and Callbacks
import os
import glob
import torch
import torch.nn as nn
import json
import random
import re
from trl import SFTTrainer, SFTConfig
from transformers import TrainerCallback, DataCollatorForLanguageModeling
from typing import Dict, Union, Any, Optional, List, Tuple

class LossLoggingCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs is not None:
            if "loss" in logs:
                print(f"Step {state.global_step}: training_loss = {logs['loss']:.6f}")
            if "eval_loss" in logs:
                print(f"Step {state.global_step}: validation_loss = {logs['eval_loss']:.6f}")

class CustomDataCollator(DataCollatorForLanguageModeling):
    def __init__(self, response_template, tokenizer, *args, **kwargs):
        super().__init__(tokenizer=tokenizer, mlm=False, *args, **kwargs)
        self.response_template = response_template
        self.response_token_ids = self.tokenizer.encode(self.response_template, add_special_tokens=False)
        
    def __call__(self, examples):
        batch = super().__call__(examples)
        labels = batch["labels"]
        for i in range(labels.size(0)):
            input_ids = batch["input_ids"][i].tolist()
            response_idx = -1
            n_template = len(self.response_token_ids)
            for j in range(len(input_ids) - n_template + 1):
                if input_ids[j:j+n_template] == self.response_token_ids:
                    response_idx = j + n_template
                    break
            
            if response_idx != -1:
                labels[i, :response_idx] = -100
                
        return batch

def clean_json_response(response: str) -> str:
    response = response.strip()
    if response.startswith("```"):
        match = re.search(r"```(?:json)?\\s*(.*?)\\s*```", response, re.DOTALL)
        if match:
            response = match.group(1).strip()
            
    first_brace = response.find("{")
    first_bracket = response.find("[")
    
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        obj_match = re.search(r"(\\{.*\\})", response, re.DOTALL)
        if obj_match:
            response = obj_match.group(1).strip()
        else:
            obj_match_open = re.search(r"(\\{.*)", response, re.DOTALL)
            if obj_match_open:
                response = obj_match_open.group(1).strip()
    elif first_bracket != -1:
        array_match = re.search(r"(\\[.*\\])", response, re.DOTALL)
        if array_match:
            response = array_match.group(1).strip()
        else:
            array_match_open = re.search(r"(\\[.*)", response, re.DOTALL)
            if array_match_open:
                response = array_match_open.group(1).strip()
                
    in_quote = False
    escape = False
    stack = []
    i = 0
    while i < len(response):
        char = response[i]
        if escape:
            escape = False
        elif char == '\\\\':
            escape = True
        elif char == '\"':
            in_quote = not in_quote
        elif not in_quote:
            if char in ('{', '['):
                stack.append(char)
            elif char in ('}', ']'):
                if stack and ((char == '}' and stack[-1] == '{') or (char == ']' and stack[-1] == '[')):
                    stack.pop()
        i += 1
        
    if in_quote:
        response += '\"'
    while stack:
        top = stack.pop()
        if top == '{':
            response += '}'
        elif top == '[':
            response += ']'
            
    return response

# --- OFFLINE FOL PARSER (HARDCODED FROM src/logic/reasoning/parser.py) ---
try:
    import z3
    from z3 import (
        And,
        BoolSort,
        Const,
        DeclareSort,
        Exists,
        ForAll,
        Function,
        IntSort,
        IntVal,
        Not,
        Or,
        RealSort,
        RealVal,
        StringVal,
        BoolRef,
        ExprRef,
    )
    import threading
    from typing import Dict, Iterable, List, Optional, Tuple
    
    _TOKEN_RE = re.compile(
        r"\\s*(->|<->|AND|OR|NOT|IN|ForAll|Exists|>=|<=|!=|=|>|<|\\(|\\)|,|\\+|-|\\d+\\.\\d+|\\d+|'[^']*'|[^\\W\\d][\\w-]*)"
    )
    
    def lowercase_constants_and_variables(formula: str) -> str:
        reserved = {"ForAll", "Exists", "AND", "OR", "NOT", "In", "implies", "BICOND", "IMPLIES"}
        def repl(match):
            word = match.group(1)
            if word in reserved or word.isdigit():
                return word
            return word.lower()
        return re.sub(r"\\b([A-Za-z_][A-Za-z0-9_]*)\\b(?!\\s*\\()", repl, formula)

    class Z3Symbols:
        def __init__(self, sort: ExprRef) -> None:
            self.sort = sort
            self.consts: Dict[str, ExprRef] = {}
            self.preds: Dict[Tuple[str, int], ExprRef] = {}
            self.funcs: Dict[Tuple[str, int], ExprRef] = {}
            self.numeric_symbols: set[str] = set()
    
        def get_const(self, name: str, sort: Optional[ExprRef] = None) -> ExprRef:
            if name in self.consts:
                return self.consts[name]
            use_sort = sort
            if use_sort is None:
                use_sort = RealSort() if name in self.numeric_symbols else self.sort
            const = Const(name, use_sort)
            self.consts[name] = const
            return const
    
        def get_pred(self, name: str, arity: int) -> ExprRef:
            key = (name, arity)
            if key in self.preds:
                return self.preds[key]
            if name in self.numeric_symbols:
                return self.get_func(name, arity, RealSort())
            pred = Function(name, *([self.sort] * arity), BoolSort())
            self.preds[key] = pred
            return pred
    
        def get_func(self, name: str, arity: int, sort: Optional[ExprRef] = None) -> ExprRef:
            key = (name, arity)
            if key in self.funcs:
                return self.funcs[key]
            use_sort = sort
            if use_sort is None:
                use_sort = RealSort() if name in self.numeric_symbols else self.sort
            func = Function(name, *([self.sort] * arity), use_sort)
            self.funcs[key] = func
            return func
            
    class TokenStream:
        def __init__(self, text: str) -> None:
            self.tokens = [t for t in _TOKEN_RE.findall(text) if t.strip()]
            self.index = 0
    
        def peek(self) -> Optional[str]:
            if self.index >= len(self.tokens):
                return None
            return self.tokens[self.index]
    
        def peek_offset(self, offset: int) -> Optional[str]:
            idx = self.index + offset
            if idx >= len(self.tokens):
                return None
            return self.tokens[idx]
    
        def next(self) -> Optional[str]:
            tok = self.peek()
            if tok is not None:
                self.index += 1
            return tok
    
        def expect(self, value: str) -> None:
            tok = self.next()
            if tok != value:
                raise ValueError(f"Expected '{value}', got '{tok}'")
                
    class FolParser:
        def __init__(self, symbols: Z3Symbols) -> None:
            self.symbols = symbols
            self.var_stack: List[Dict[str, ExprRef]] = []
    
        def parse(self, text: str) -> BoolRef:
            stream = TokenStream(text)
            expr = self._parse_implication(stream)
            return expr
    
        def _parse_implication(self, stream: TokenStream) -> BoolRef:
            left = self._parse_or(stream)
            tok = stream.peek()
            if tok == "->":
                stream.next()
                right = self._parse_implication(stream)
                return Or(Not(left), right)
            if tok == "<->":
                stream.next()
                right = self._parse_implication(stream)
                return And(Or(Not(left), right), Or(Not(right), left))
            return left
    
        def _parse_or(self, stream: TokenStream) -> BoolRef:
            left = self._parse_and(stream)
            while stream.peek() == "OR":
                stream.next()
                right = self._parse_and(stream)
                left = Or(left, right)
            return left
    
        def _parse_and(self, stream: TokenStream) -> BoolRef:
            left = self._parse_not(stream)
            while stream.peek() == "AND":
                stream.next()
                right = self._parse_not(stream)
                left = And(left, right)
            return left
    
        def _parse_not(self, stream: TokenStream) -> BoolRef:
            if stream.peek() == "NOT":
                stream.next()
                return Not(self._parse_not(stream))
            return self._parse_atom(stream)
    
        def _parse_atom(self, stream: TokenStream) -> BoolRef:
            tok = stream.peek()
            if tok is None:
                raise ValueError("Unexpected end of input")
            if tok == "(":
                stream.next()
                expr = self._parse_implication(stream)
                stream.expect(")")
                return expr
            if tok in ("ForAll", "Exists"):
                return self._parse_quantifier(stream)
            start_index = stream.index
            term = self._parse_term(stream)
            comp = stream.peek()
            if comp == "IN":
                stream.next()
                right = self._parse_term(stream)
                pred = self.symbols.get_pred("In", 2)
                return pred(term, right)
            if comp in ("=", "!=", ">=", "<=", ">", "<"):
                numeric = comp in (">=", "<=", ">", "<")
                if comp in ("=", "!="):
                    next_tok = stream.peek_offset(1)
                    if next_tok is not None and re.fullmatch(r"\\d+(?:\\.\\d+)?", next_tok):
                        numeric = True
                if numeric and isinstance(term, BoolRef):
                    stream.index = start_index
                    term = self._parse_term(stream, prefer_numeric=True)
                    comp = stream.peek()
                stream.next()
                right = self._parse_term(stream, prefer_numeric=numeric)
                return self._build_comparison(comp, term, right)
            if not isinstance(term, BoolRef):
                raise ValueError("Predicate expected, got term")
            return term
    
        def _parse_quantifier(self, stream: TokenStream) -> BoolRef:
            quant = stream.next()
            stream.expect("(")
            var_name = stream.next()
            if var_name is None:
                raise ValueError("Missing quantified variable")
            stream.expect(",")
            var = Const(var_name, self.symbols.sort)
            self.var_stack.append({var_name: var})
            body = self._parse_implication(stream)
            self.var_stack.pop()
            stream.expect(")")
            if quant == "ForAll":
                return ForAll([var], body)
            return Exists([var], body)
    
        def _parse_term(self, stream: TokenStream, prefer_numeric: bool = False) -> ExprRef:
            left = self._parse_simple_term(stream, prefer_numeric=prefer_numeric)
            while stream.peek() in ("+", "-"):
                op = stream.next()
                right = self._parse_simple_term(stream, prefer_numeric=True)
                if op == "+":
                    left = left + right
                else:
                    left = left - right
            return left
    
        def _parse_simple_term(self, stream: TokenStream, prefer_numeric: bool = False) -> ExprRef:
            tok = stream.next()
            if tok is None:
                raise ValueError("Unexpected end of input")
            if tok == "(":
                expr = self._parse_term(stream, prefer_numeric=prefer_numeric)
                stream.expect(")")
                return expr
            if tok.startswith("'") and tok.endswith("'"):
                return StringVal(tok[1:-1])
    
            time_match = re.match(r"^Time(\\d{1,2})(\\d{2})?(AM|PM)$", tok, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                ampm = time_match.group(3).upper()
                if ampm == "PM" and hour < 12:
                    hour += 12
                elif ampm == "AM" and hour == 12:
                    hour = 0
                minutes = hour * 60 + minute
                return IntVal(minutes)
    
            duration_match = re.match(r"^Duration(\\d+(?:\\.\\d+)?)(Hours|Minutes|Days)$", tok, re.IGNORECASE)
            if duration_match:
                value = float(duration_match.group(1))
                unit = duration_match.group(2).lower()
                if unit == "hours":
                    minutes = int(value * 60)
                elif unit == "days":
                    minutes = int(value * 1440)
                else:
                    minutes = int(value)
                return IntVal(minutes)
    
            if tok.replace(".", "", 1).isdigit():
                if "." in tok:
                    return RealVal(tok)
                return IntVal(tok)

            # Constant lookup inside quantifier variables stack
            for var_dict in reversed(self.var_stack):
                if tok in var_dict:
                    return var_dict[tok]

            if stream.peek() == "(":
                stream.next()
                args = []
                if stream.peek() != ")":
                    while True:
                        args.append(self._parse_term(stream, prefer_numeric=prefer_numeric))
                        if stream.peek() == ",":
                            stream.next()
                            continue
                        break
                stream.expect(")")
                if prefer_numeric:
                    func = self.symbols.get_func(tok, len(args), RealSort())
                    return func(*args)
                pred = self.symbols.get_pred(tok, len(args))
                return pred(*args)

            # Default to real/uninterpreted constant
            return self.symbols.get_const(tok, sort=RealSort() if prefer_numeric else None)
    
        def _build_comparison(self, op: str, left: ExprRef, right: ExprRef) -> BoolRef:
            if op == "=":
                return left == right
            if op == "!=":
                return left != right
            if op == ">=":
                return left >= right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            if op == "<":
                return left < right
            raise ValueError(f"Unknown comparison operator '{op}'")
            
    def parse_formulas(formulas: list[str], sort_name="U") -> tuple[Z3Symbols, list[BoolRef]]:
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

        numeric_symbols = set()
        for f in formulas:
            f_temp = re.sub(r"'[^']*'", "", f)
            # Find comparison variables
            comp_matches = re.finditer(r"\\b([A-Za-z_][A-Za-z0-9_-]*)\\s*(?:>=|<=|>|<)\\s*(?:\\d+(?:\\.\\d+)?|Time\\d+[A-Za-z]+|Duration\\d+[A-Z]+)\\b", f_temp)
            for m in comp_matches:
                name = m.group(1)
                if name not in ("ForAll", "Exists", "AND", "OR", "NOT", "IN", "BICOND", "IMPLIES"):
                    numeric_symbols.add(name)
                    
            eq_matches = re.finditer(r"\\b([A-Za-z_][A-Za-z0-9_-]*)\\s*(?:=|!=)\\s*(?:\\d+(?:\\.\\d+)?|Time\\d+[A-Za-z]+|Duration\\d+[A-Z]+)\\b", f_temp)
            for m in eq_matches:
                name = m.group(1)
                if name not in ("ForAll", "Exists", "AND", "OR", "NOT", "IN", "BICOND", "IMPLIES"):
                    numeric_symbols.add(name)
                    
            eq_rev_matches = re.finditer(r"\\b(?:\\d+(?:\\.\\d+)?|Time\\d+[A-Za-z]+|Duration\\d+[A-Z]+)\\s*(?:=|!=)\\s*([A-Za-z_][A-Za-z0-9_-]*)\\b", f_temp)
            for m in eq_rev_matches:
                name = m.group(1)
                if name not in ("ForAll", "Exists", "AND", "OR", "NOT", "IN", "BICOND", "IMPLIES"):
                    numeric_symbols.add(name)
    
        symbols = Z3Symbols(sort=DeclareSort(sort_name))
        symbols.numeric_symbols = numeric_symbols
        
        parser = FolParser(symbols)
        formula_exprs = [parser.parse(f) for f in formulas]
        return symbols, formula_exprs

    _z3_lock = threading.Lock()
    
    def try_parse_fol(formula: str) -> tuple[bool, str]:
        with _z3_lock:
            try:
                parse_formulas([formula])
                return True, ""
            except Exception as exc:
                return False, str(exc)
                
    fol_parser_available = True
    print("Offline Z3 logic parser successfully initialized.")
except ImportError:
    fol_parser_available = False
    print("Warning: Z3 or logic parser not available. Using basic syntax checking (parentheses/operators).")
    
    def try_parse_fol(formula: str) -> tuple[bool, str]:
        return False, "Z3 solver library not installed."

# --- ACCURACY EVALUATION HELPERS ---
def basic_validate_fol(formula: str) -> bool:
    if formula.count("(") != formula.count(")"):
        return False
    for bad in [" and ", " or ", " not "]:
        if bad in formula:
            return False
    for bad_q in ["forall(", "exists("]:
        if bad_q in formula.lower() and not (bad_q.capitalize() in formula or "ForAll" in formula or "Exists" in formula):
            return False
    return True

# --- Z3 DOWNSTREAM QA EVALUATION HELPERS ---
def parse_mcq_options(text: str) -> dict[str, str]:
    options = {}
    pattern = r'(?:\\s+|^)([A-D])[\\.\\)]\\s+(.*?)(?=\\s+[A-D][\\.\\)]\\s+|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    for opt_char, opt_text in matches:
        options[opt_char] = opt_text.strip()
    return options

def strip_question_framing(text: str) -> str:
    stripped = text.strip()
    patterns = [
        r"^(?:does it follow that|is it true that|can we conclude that|is it the case that"
        r"|do the premises imply that|does the passage imply that"
        r"|does it follow from the premises that)\\s*",
    ]
    for pat in patterns:
        m = re.match(pat, stripped, re.IGNORECASE)
        if m:
            stripped = stripped[m.end():]
            break
    stripped = stripped.rstrip("?").strip()
    if stripped:
        stripped = stripped[0].upper() + stripped[1:]
    return stripped

def verify_with_z3(premises_fol: list[str], conclusion_fol: str, negate_conclusion: bool = True) -> dict:
    negated_conclusion_fol = f"NOT ({conclusion_fol})" if negate_conclusion else conclusion_fol
    all_formulas = premises_fol + [negated_conclusion_fol]
    
    try:
        symbols, exprs = parse_formulas(all_formulas)
    except Exception as parse_err:
        try:
            standardized_formulas = []
            for f_str in all_formulas:
                f_clean = f_str.replace("¬", "NOT ").replace("∧", " AND ").replace("∨", " OR ").replace("→", " -> ").replace("↔", " <-> ")
                open_count = f_clean.count("(")
                close_count = f_clean.count(")")
                if close_count < open_count:
                    f_clean = f_clean + ")" * (open_count - close_count)
                standardized_formulas.append(f_clean)
            symbols, exprs = parse_formulas(standardized_formulas)
        except Exception as parse_err_inner:
            return {"result": z3.unknown, "error": str(parse_err_inner)}
            
    premise_exprs = exprs[:-1]
    negated_conclusion_expr = exprs[-1]
    
    solver = z3.Solver()
    solver.set("timeout", 10000)
    
    for expr in premise_exprs:
        solver.add(expr)
    solver.add(negated_conclusion_expr)
    
    try:
        result = solver.check()
        return {"result": result}
    except Exception as z3_err:
        return {"result": z3.unknown, "error": str(z3_err)}

def check_answers_match(predicted, ground_truth):
    p_lower = str(predicted).strip().lower()
    gt_lower = str(ground_truth).strip().lower()
    
    yes_true = {"yes", "true"}
    no_false = {"no", "false"}
    unknown_uncertain = {"unknown", "uncertain"}
    
    if p_lower in yes_true and gt_lower in yes_true:
        return True
    if p_lower in no_false and gt_lower in no_false:
        return True
    if p_lower in unknown_uncertain and gt_lower in unknown_uncertain:
        return True
    return p_lower == gt_lower

def translate_sentences(model, tokenizer, sentences: list[str], glossary_str=None) -> list[str]:
    if not sentences:
        return []
        
    nl_content = ""
    for i, nl in enumerate(sentences, start=1):
        nl_content += f"{i}. {nl}\\n"
        
    user_prompt = user_prompt_template.format(num_premises=len(sentences), premises=nl_content.strip())
    sys_prompt = system_prompt_template
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
    ]
    
    prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
        
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    cleaned_response = clean_json_response(response)
    
    try:
        fol_list = json.loads(cleaned_response)
        if isinstance(fol_list, list) and len(fol_list) == len(sentences):
            return [str(x).strip() for x in fol_list]
    except Exception:
        pass
        
    fallback_fol = []
    for s in sentences:
        fallback_fol.append(translate_single_sentence(model, tokenizer, s, glossary_str=glossary_str))
    return fallback_fol

def translate_single_sentence(model, tokenizer, s: str, glossary_str=None) -> str:
    user_prompt = user_prompt_template.format(num_premises=1, premises=f"1. {s}")
    sys_prompt = system_prompt_template
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
    ]
    
    prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
        
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    cleaned_response = clean_json_response(response)
    
    try:
        fol_list = json.loads(cleaned_response)
        if isinstance(fol_list, list) and len(fol_list) > 0:
            return str(fol_list[0]).strip()
    except Exception:
        pass
    return cleaned_response

GENERIC_WORDS = {
    'project', 'projects', 'python', 'code', 'standard', 'standards',
    'rule', 'rules', 'requirement', 'requirements', 'practice', 'practices',
    'convention', 'conventions', 'protocol', 'protocols', 'specification', 'specifications',
    'constraint', 'constraints', 'condition', 'conditions', 'regulation', 'regulations',
    'policy', 'policies', 'guideline', 'guidelines', 'recommendation', 'recommendations',
    'system', 'systems', 'application', 'applications', 'program', 'programs'
}

RESERVED_WORDS = {'ForAll', 'Exists', 'AND', 'OR', 'NOT', 'implies', 'IN'}

def split_camel_snake(s: str) -> list[str]:
    parts = s.split('_')
    words = []
    for part in parts:
        camel_parts = re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\\b)', part)
        if camel_parts:
            words.extend(camel_parts)
        else:
            words.append(part)
    return words

def clean_repetitive_name(name: str) -> str:
    if len(name) <= 50:
        return name
    for length in range(4, 40):
        for i in range(len(name) - 2 * length):
            sub = name[i:i+length]
            j = i + length
            count = 1
            while name[j:j+length] == sub:
                count += 1
                j += length
            if count >= 2:
                repeated_part = sub * count
                name = name.replace(repeated_part, sub)
                return clean_repetitive_name(name)
    if len(name) > 50:
        name = name[:47] + "Trunc"
    return name

def unify_fol_predicates(formulas: list[str]) -> list[str]:
    if not formulas:
        return formulas
    predicate_pattern = r'\\b([A-Za-z_][A-Za-z0-9_]*)\\s*\\('
    predicates = set()
    for f in formulas:
        matches = re.findall(predicate_pattern, f)
        for m in matches:
            if m not in RESERVED_WORDS:
                predicates.add(m)
    mapping = {}
    for p in predicates:
        words = split_camel_snake(p)
        core = [w for w in words if w.lower() not in GENERIC_WORDS]
        if not core:
            core = words
        canonical = "".join(w[0].upper() + w[1:] if len(w) > 0 else w for w in core)
        canonical = clean_repetitive_name(canonical)
        mapping[p] = canonical
    unified_formulas = []
    for f in formulas:
        new_f = f
        for name in sorted(mapping.keys(), key=len, reverse=True):
            canonical = mapping[name]
            if name != canonical:
                new_f = re.sub(rf'\\b{name}\\b', canonical, new_f)
        unified_formulas.append(new_f)
    return unified_formulas

# --- SEMANTIC FALLBACK PROMPTS & HELPERS ---
SEMANTIC_YESNO_SYSTEM_PROMPT = (
    "You are a logical reasoning assistant. "
    "Given a set of premises and a conclusion, determine whether the conclusion logically follows from the premises.\\n\\n"
    "STRICT RULES:\\n"
    "- Answer ONLY with one of: Yes, No, or Uncertain.\\n"
    "- 'Yes' means the conclusion is a logical consequence of the premises.\\n"
    "- 'No' means the conclusion contradicts or is inconsistent with the premises.\\n"
    "- 'Uncertain' means the premises do not provide enough information to determine the conclusion.\\n"
    "- Do NOT add any explanation, punctuation, or extra text."
)

SEMANTIC_YESNO_USER_PROMPT_TEMPLATE = (
    "Premises:\\n{premises_text}\\n\\n"
    "Conclusion:\\n{conclusion_nl}\\n\\n"
    "Does the conclusion logically follow from the premises? Answer Yes, No, or Uncertain only."
)

SEMANTIC_MCQ_SYSTEM_PROMPT = (
    "You are a logical reasoning assistant. "
    "Given a set of premises and a multiple-choice question, select the single best answer that logically follows from the premises.\\n\\n"
    "STRICT RULES:\\n"
    "- Answer ONLY with the capital letter of your chosen option (A, B, C, or D).\\n"
    "- Do NOT add any explanation or extra text."
)

SEMANTIC_MCQ_USER_PROMPT_TEMPLATE = (
    "Premises:\\n{premises_text}\\n\\n"
    "Question:\\n{question_nl}\\n\\n"
    "Select the single best answer: respond with ONLY the letter (A, B, C, or D)."
)

def llm_generate_text(model, tokenizer, prompt, system_prompt="", max_new_tokens=15):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

def check_sample_with_z3(predicted_premises_fol, question, model, tokenizer, premises_nl=None):
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
    
    if len(options) >= 2:
        opt_keys = sorted(options.keys())
        opt_texts = [options[k] for k in opt_keys]
        options_fol = translate_sentences(model, tokenizer, opt_texts, glossary_str=glossary_str)
        if len(options_fol) != len(opt_keys):
            options_fol = []
            for opt_text in opt_texts:
                options_fol.append(translate_single_sentence(model, tokenizer, opt_text, glossary_str=glossary_str))
            
        all_fol = predicted_premises_fol + options_fol
        unified_fol = unify_fol_predicates(all_fol)
        unified_premises_fol = unified_fol[:len(predicted_premises_fol)]
        unified_options_fol = unified_fol[len(predicted_premises_fol):]
        
        entailed_options = []
        consistent_options = []
        
        for idx, k in enumerate(opt_keys):
            opt_fol = unified_options_fol[idx] if idx < len(unified_options_fol) else ""
            if not opt_fol:
                continue
            res = verify_with_z3(unified_premises_fol, opt_fol, negate_conclusion=True)
            if res.get("result") == unsat:
                entailed_options.append(k)
            elif res.get("result") == sat:
                res_neg = verify_with_z3(unified_premises_fol, opt_fol, negate_conclusion=False)
                if res_neg.get("result") != unsat:
                    consistent_options.append(k)
                    
        if len(entailed_options) == 1:
            return entailed_options[0]
        elif len(entailed_options) > 1:
            choices_list = []
            for k in entailed_options:
                choices_list.append(f"{k}. {options[k]}")
            choices_str = "\\n".join(choices_list)
            premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
            prompt = (
                f"You are a logical reasoning assistant.\\n"
                f"Given the premises and the question:\\n\\n"
                f"Premises:\\n{premises_text}\\n\\n"
                f"Question: {question}\\n\\n"
                f"Our formal symbolic prover has verified that the following options are mathematically valid conclusions:\\n"
                f"{choices_str}\\n\\n"
                f"Select the single most appropriate and intended conclusion from the verified options above.\\n"
                f"Respond with ONLY the capital letter (A, B, C, or D) of your choice."
            )
            try:
                best_opt = llm_generate_text(model, tokenizer, prompt, max_new_tokens=5).strip()
                match = re.search(r"\\b([A-D])\\b", best_opt)
                if match and match.group(1) in entailed_options:
                    return match.group(1)
            except Exception:
                pass
            return entailed_options[0]
        elif len(consistent_options) >= 1:
            if len(consistent_options) == 1:
                return consistent_options[0]
            else:
                choices_str = "\\n".join(f"{k}. {options[k]}" for k in consistent_options)
                premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
                prompt = (
                    f"You are a logical reasoning assistant.\\n"
                    f"Given the premises and the question:\\n\\n"
                    f"Premises:\\n{premises_text}\\n\\n"
                    f"Question: {question}\\n\\n"
                    f"Our formal symbolic prover has verified that the following options are consistent (not contradicted by the premises):\\n"
                    f"{choices_str}\\n\\n"
                    f"Select the single most appropriate and intended conclusion from the consistent options above.\\n"
                    f"Respond with ONLY the capital letter (A, B, C, or D) of your choice."
                )
                try:
                    best_opt = llm_generate_text(model, tokenizer, prompt, max_new_tokens=5).strip()
                    match = re.search(r"\\b([A-D])\\b", best_opt)
                    if match and match.group(1) in consistent_options:
                        return match.group(1)
                except Exception:
                    pass
                return consistent_options[0]
        else:
            premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
            sem_prompt = SEMANTIC_MCQ_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text,
                question_nl=question
            )
            try:
                sem_resp = llm_generate_text(model, tokenizer, sem_prompt, system_prompt=SEMANTIC_MCQ_SYSTEM_PROMPT, max_new_tokens=10).strip()
                sem_clean = sem_resp.strip("., ")
                if "unknown" in sem_clean.lower():
                    return "Unknown"
                match = re.search(r"\\b([A-D])\\b", sem_clean)
                if match:
                    return match.group(1)
            except Exception:
                pass
            return "Unknown"
            
    else:
        conclusion_text = strip_question_framing(question)
        conclusion_fol_list = translate_sentences(model, tokenizer, [conclusion_text], glossary_str=glossary_str)
        conclusion_fol = conclusion_fol_list[0] if conclusion_fol_list else ""
        
        if not conclusion_fol:
            premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
            sem_prompt = SEMANTIC_YESNO_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text,
                conclusion_nl=question
            )
            try:
                sem_resp = llm_generate_text(model, tokenizer, sem_prompt, system_prompt=SEMANTIC_YESNO_SYSTEM_PROMPT, max_new_tokens=10).strip()
                sem_lower = sem_resp.lower().strip("., ")
                if sem_lower.startswith("yes"):
                    return "Yes"
                elif sem_lower.startswith("no"):
                    return "No"
            except Exception:
                pass
            return "Unknown"
            
        all_fol = predicted_premises_fol + [conclusion_fol]
        unified_fol = unify_fol_predicates(all_fol)
        unified_premises_fol = unified_fol[:-1]
        unified_conclusion_fol = unified_fol[-1]
        
        res = verify_with_z3(unified_premises_fol, unified_conclusion_fol, negate_conclusion=True)
        if res.get("result") == unsat:
            return "Yes"
            
        res_neg = verify_with_z3(unified_premises_fol, unified_conclusion_fol, negate_conclusion=False)
        if res_neg.get("result") == unsat:
            return "No"
            
        premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
        sem_prompt = SEMANTIC_YESNO_USER_PROMPT_TEMPLATE.format(
            premises_text=premises_text,
            conclusion_nl=question
        )
        try:
            sem_resp = llm_generate_text(model, tokenizer, sem_prompt, system_prompt=SEMANTIC_YESNO_SYSTEM_PROMPT, max_new_tokens=10).strip()
            sem_lower = sem_resp.lower().strip("., ")
            if sem_lower.startswith("yes"):
                return "Yes"
            elif sem_lower.startswith("no"):
                return "No"
        except Exception:
            pass
            
        return "Unknown"

def evaluate_fol_accuracy(model, tokenizer, val_samples, limit=None):
    eval_limit = limit if limit is not None else len(val_samples)
    print(f"Evaluating FOL Accuracy on {eval_limit} samples...")
    correct_count = 0
    total_count = 0
    valid_json_count = 0
    syntax_valid_count = 0
    formula_correct = 0
    formula_total = 0
    
    z3_correct_count = 0
    z3_total_count = 0
    
    if limit is not None:
        eval_subset = random.Random(42).sample(val_samples, min(len(val_samples), limit))
    else:
        eval_subset = val_samples
    
    for item in eval_subset:
        nl_list = item["premises-NL"]
        fol_list_gt = item["premises-FOL"]
        
        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\\n"
            
        user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())
        messages = [
            {"role": "system", "content": system_prompt_template},
            {"role": "user", "content": user_prompt.strip()}
        ]
        
        prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        
        cleaned_response = ""
        try:
            cleaned_response = clean_json_response(response)
        except Exception as e:
            cleaned_response = response
            
        predicted_premises_fol = []
        is_json_valid = False
        is_syntax_valid = False
        
        try:
            parsed_response = json.loads(cleaned_response)
            valid_json_count += 1
            is_json_valid = True
            if isinstance(parsed_response, list):
                predicted_premises_fol = [str(x).strip() for x in parsed_response]
                all_formulas_valid = True
                for formula in parsed_response:
                    if fol_parser_available:
                        try:
                            is_valid, _ = try_parse_fol(str(formula))
                            if not is_valid:
                                all_formulas_valid = False
                                break
                        except Exception:
                            if not basic_validate_fol(str(formula)):
                                all_formulas_valid = False
                                break
                    else:
                        if not basic_validate_fol(str(formula)):
                            all_formulas_valid = False
                            break
                if all_formulas_valid:
                    syntax_valid_count += 1
                    is_syntax_valid = True
                
                if isinstance(fol_list_gt, list):
                    if [str(x).strip() for x in parsed_response] == [str(x).strip() for x in fol_list_gt]:
                        correct_count += 1
                    
                    matched_formulas = 0
                    for p_f, g_f in zip(parsed_response, fol_list_gt):
                        if str(p_f).strip() == str(g_f).strip():
                            matched_formulas += 1
                    formula_correct += matched_formulas
                    formula_total += len(fol_list_gt)
        except Exception:
            pass
            
        question = item.get("question", "")
        gt_answer = item.get("answer", "")
        pred_ans = "N/A"
        is_qa_correct = False
        
        if question and gt_answer and predicted_premises_fol:
            z3_total_count += 1
            try:
                pred_ans = check_sample_with_z3(predicted_premises_fol, question, model, tokenizer, premises_nl=nl_list)
                if check_answers_match(pred_ans, gt_answer):
                    z3_correct_count += 1
                    is_qa_correct = True
            except Exception as z3_err:
                pass
                    
        total_count += 1
        
    em_acc = (correct_count / total_count) * 100 if total_count > 0 else 0
    formula_acc = (formula_correct / formula_total) * 100 if formula_total > 0 else 0
    json_rate = (valid_json_count / total_count) * 100 if total_count > 0 else 0
    syntax_rate = (syntax_valid_count / total_count) * 100 if total_count > 0 else 0
    z3_acc = (z3_correct_count / z3_total_count) * 100 if z3_total_count > 0 else 0
    
    print("\\n=== FOL Evaluation Metrics ===")
    print(f"FOL Exact Match Accuracy (Sample Level): {em_acc:.2f}% ({correct_count}/{total_count})")
    print(f"FOL Formula Level Match Accuracy: {formula_acc:.2f}% ({formula_correct}/{formula_total})")
    print(f"FOL Syntax Validity Rate: {syntax_rate:.2f}% ({syntax_valid_count}/{total_count})")
    print(f"FOL JSON Validity Rate: {json_rate:.2f}% ({valid_json_count}/{total_count})")
    print(f"FOL Z3 Downstream QA Accuracy: {z3_acc:.2f}% ({z3_correct_count}/{z3_total_count})")
    return em_acc, json_rate, syntax_rate

def evaluate_router_accuracy(model, tokenizer, val_samples, limit=None):
    eval_limit = limit if limit is not None else len(val_samples)
    print(f"Evaluating Router Accuracy on {eval_limit} samples...")
    correct_count = 0
    total_count = 0
    valid_json_count = 0
    domain_exact_match_count = 0
    multi_state_correct_count = 0
    
    if limit is not None:
        eval_subset = random.Random(42).sample(val_samples, min(len(val_samples), limit))
    else:
        eval_subset = val_samples
        
    for item in eval_subset:
        inp = item["input"]
        gt_output_str = item["output"]
        
        messages = [
            {"role": "system", "content": router_system_prompt},
            {"role": "user", "content": f"<QUESTION>\\n{inp.strip()}\\n</QUESTION>"}
        ]
        
        prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        cleaned_response = clean_json_response(response)
        
        try:
            parsed_response = json.loads(cleaned_response)
            valid_json_count += 1
            
            # Ground truth
            gt_parsed = json.loads(gt_output_str)
            
            pred_domains = parsed_response.get("domains", [])
            gt_domains = gt_parsed.get("domains", [])
            
            pred_multi_state = parsed_response.get("multi_state", False)
            gt_multi_state = gt_parsed.get("multi_state", False)
            
            domain_exact_match = sorted(pred_domains) == sorted(gt_domains)
            if domain_exact_match:
                domain_exact_match_count += 1
                
            multi_state_correct = bool(pred_multi_state) == bool(gt_multi_state)
            if multi_state_correct:
                multi_state_correct_count += 1
                
            if domain_exact_match and multi_state_correct:
                correct_count += 1
        except Exception:
            pass
            
        total_count += 1
        
    acc = (correct_count / total_count) * 100 if total_count > 0 else 0
    json_rate = (valid_json_count / total_count) * 100 if total_count > 0 else 0
    domain_acc = (domain_exact_match_count / total_count) * 100 if total_count > 0 else 0
    multi_state_acc = (multi_state_correct_count / total_count) * 100 if total_count > 0 else 0
    
    print("\\n=== Router Evaluation Metrics ===")
    print(f"Router Exact Match Accuracy: {acc:.2f}% ({correct_count}/{total_count})")
    print(f"Router JSON Validity Rate: {json_rate:.2f}% ({valid_json_count}/{total_count})")
    print(f"Router Domain Exact Match Rate: {domain_acc:.2f}% ({domain_exact_match_count}/{total_count})")
    print(f"Router Multi-State Accuracy: {multi_state_acc:.2f}% ({multi_state_correct_count}/{total_count})")
    return acc, json_rate, domain_acc, multi_state_acc

class CustomSFTTrainer(SFTTrainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        if "labels" not in inputs:
            return super().compute_loss(model, inputs, return_outputs, **kwargs)
            
        labels = inputs["labels"]
        input_ids = inputs["input_ids"]
        outputs = model(**inputs)
        logits = outputs.get("logits")
        
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        loss_fct = nn.CrossEntropyLoss(reduction="none")
        
        vocab_size = shift_logits.size(-1)
        flat_logits = shift_logits.view(-1, vocab_size)
        flat_labels = shift_labels.view(-1)
        
        token_losses = loss_fct(flat_logits, flat_labels)
        token_losses = token_losses.view(shift_labels.size())
        
        weighted_losses = []
        for i in range(input_ids.size(0)):
            seq_input_ids = input_ids[i].tolist()
            seq_losses = token_losses[i]
            seq_labels = shift_labels[i]
            
            is_fol = False
            for idx in range(len(seq_input_ids) - 5):
                if idx > 20:
                    break
                if seq_input_ids[idx] == 2610 and seq_input_ids[idx+1] == 5508:
                    is_fol = True
                    break
            
            valid_mask = (seq_labels != -100)
            active_losses = seq_losses[valid_mask]
            
            if len(active_losses) > 0:
                mean_loss = active_losses.mean()
                weight = 2.0 if is_fol else 1.0
                weighted_losses.append(mean_loss * weight)
            else:
                weighted_losses.append(torch.tensor(0.0, device=logits.device, dtype=logits.dtype))
                
        loss = torch.stack(weighted_losses).mean()
        return (loss, outputs) if return_outputs else loss

def train_model(train_dataset, val_dataset, output_dir, epochs=2, learning_rate=1e-4, resume_from_dir=None):
    clean_memory()
    
    num_samples = len(train_dataset)
    effective_batch_size = BATCH_SIZE * GRADIENT_ACCUMULATION
    steps_per_epoch = num_samples // effective_batch_size
    if num_samples % effective_batch_size != 0:
        steps_per_epoch += 1
    total_steps = steps_per_epoch * epochs
    
    warmup_steps = max(1, int(total_steps * 0.05))
    print(f"Training on {num_samples} samples. Steps per epoch: {steps_per_epoch}. Total steps: {total_steps}. Dynamic warmup steps: {warmup_steps}")
    
    base_model = load_base_model()
    
    load_dir = resume_from_dir if resume_from_dir else output_dir
    adapter_config_path = os.path.join(load_dir, "adapter_config.json")
    if os.path.exists(adapter_config_path):
        print(f"Loading PEFT adapter weights from {load_dir}...")
        model = PeftModel.from_pretrained(base_model, load_dir, is_trainable=True)
    else:
        print("Initializing a new PEFT adapter...")
        model = get_peft_model(base_model, peft_config)
        
    model.print_trainable_parameters()
    
    sft_config = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        warmup_steps=warmup_steps,
        fp16=use_fp16,
        bf16=use_bf16,
        logging_steps=1,
        logging_first_step=True,
        optim="adamw_torch_fused",
        gradient_checkpointing=GRADIENT_CHECKPOINTING,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        per_device_eval_batch_size=BATCH_SIZE,
        report_to="none",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=2,
        dataset_text_field="text",
        max_length=MAX_LENGTH,
        neftune_noise_alpha=None,
        dataloader_num_workers=2,
        dataloader_pin_memory=True
    )

    response_template = "<|im_start|>assistant\\n"
    collator = CustomDataCollator(
        response_template=response_template, 
        tokenizer=tokenizer
    )
    
    trainer = CustomSFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        args=sft_config,
        data_collator=collator,
        callbacks=[LossLoggingCallback()]
    )

    checkpoints = glob.glob(os.path.join(output_dir, "checkpoint-*"))
    resume_path = None
    if checkpoints:
        checkpoints.sort(key=lambda x: int(x.split("-")[-1]))
        resume_path = checkpoints[-1]
        print(f"Found checkpoints. Resuming training from: {resume_path}")
        
    trainer.train(resume_from_checkpoint=resume_path)
    
    print(f"Saving best validation adapter weights and tokenizer to {output_dir}...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("Training completed successfully!")
    
    try:
        print("\\n=== Starting Post-Training Accuracy Evaluation ===")
        model.eval()
        evaluate_fol_accuracy(model, tokenizer, val_fol, limit=None)
        evaluate_router_accuracy(model, tokenizer, val_router, limit=None)
    except Exception as e:
        print(f"Error during post-training evaluation: {e}")
    
    del trainer
    del model
    del base_model
    clean_memory()
"""
training_cell["source"] = [line + "\n" for line in new_training_source.splitlines()]

# --- CELL 6: START TRAINING (Phase 1 & Phase 2) ---
run_cell = cells[6]
new_run_source = """# 7. Start Training and Post-Training Evaluation (2-Phase Strategy)
print("=== STARTING PHASE 1 (FOL focus: 100% FOL : 20% Router) ===")
train_model(
    train_dataset=train_dataset_p1,
    val_dataset=val_dataset,
    output_dir=OUTPUT_DIR_P1,
    epochs=EPOCHS_P1,
    learning_rate=LEARNING_RATE_P1,
    resume_from_dir=None
)

print("\\n=== STARTING PHASE 2 (Router focus: 100% Router : 50% FOL) ===")
train_model(
    train_dataset=train_dataset_p2,
    val_dataset=val_dataset,
    output_dir=OUTPUT_DIR_P2,
    epochs=EPOCHS_P2,
    learning_rate=LEARNING_RATE_P2,
    resume_from_dir=OUTPUT_DIR_P1
)
"""
run_cell["source"] = [line + "\n" for line in new_run_source.splitlines()]

# 3. Write out to the new notebook file
output_nb_path = r"src/llm/tuning/fol_and_router.ipynb"
with open(output_nb_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"Successfully generated new notebook: {os.path.abspath(output_nb_path)}")
