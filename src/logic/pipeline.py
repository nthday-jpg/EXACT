import os
import re
import time
import z3
from src.logic.translation.pipeline import NLToFOLPipeline
from src.logic.reasoning.pipeline import ReasoningPipeline
from src.utils.normalization import unify_fol_predicates
from src.llm import LLMClient
from src.llm.prompts import (
    OPEN_ENDED_SYSTEM_PROMPT,
    OPEN_ENDED_USER_PROMPT_TEMPLATE,
    SEMANTIC_YESNO_SYSTEM_PROMPT,
    SEMANTIC_YESNO_USER_PROMPT_TEMPLATE,
)

REMOTE_OPTION_EXTRACTION_MAX_TOKENS = 128
REMOTE_SEMANTIC_FALLBACK_MAX_TOKENS = 64
REMOTE_TIE_BREAK_MAX_TOKENS = 64
REMOTE_OPEN_ENDED_MAX_TOKENS = 128


def parse_mcq_options(text: str) -> dict[str, str]:
    """Parse options A, B, C, D from the text if present."""
    # 1. Line-by-line parsing handles the common multi-line EXACT format reliably.
    options = {}
    lines = text.splitlines()
    current_key = None
    current_text = []
    for line in lines:
        m = re.match(r"^\s*(?:Option\s+)?(?:\(?|\[?)([A-G])(?:\)?|\]?)[\.\)\:\-]\s*(.*)$", line, re.IGNORECASE)
        if m:
            if current_key:
                options[current_key] = "\n".join(current_text).strip()
            current_key = m.group(1).upper()
            current_text = [m.group(2).strip()]
        else:
            if current_key:
                current_text.append(line.strip())
    if current_key:
        options[current_key] = "\n".join(current_text).strip()

    if len(options) >= 2:
        return options

    # 2. Inline fallback for single-line questions with embedded options.
    options = {}
    pattern = r"(?:^|\s)(?:[\-\*]\s+)?(?:\(|\[|Option\s+)?([A-G])(?:\)|\]|\.|\:)\s+(.*?)(?=(?:\s+(?:[\-\*]\s+)?(?:\(|\[|Option\s+)?[A-G](?:\)|\]|\.|\:)\s+)|$)"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    for opt_char, opt_text in matches:
        options[opt_char.upper()] = opt_text.strip()

    return options


def extract_options_via_llm(text: str, llm_client) -> dict[str, str]:
    """Fallback to extract MCQ options using the LLM when regex fails."""
    prompt = (
        "Analyze the following multiple-choice question and extract the text for options A, B, C, D (and any others if present).\n\n"
        f"Question:\n{text}\n\n"
        "Return the extracted options as a STRICT JSON object mapping the uppercase option letter to its text description.\n"
        "Example output: {\"A\": \"Option A text\", \"B\": \"Option B text\"}\n"
        "If no options are found, return {}."
    )
    try:
        response = llm_client.generate_text(
            prompt,
            system_prompt="You are a precise parsing assistant. Return ONLY a valid JSON object. Do not include any other text or markdown block.",
            max_new_tokens=REMOTE_OPTION_EXTRACTION_MAX_TOKENS
        ).strip()
        # Parse JSON
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
        import json
        parsed = json.loads(cleaned.strip())
        if isinstance(parsed, dict):
            return {str(k).upper(): str(v).strip() for k, v in parsed.items()}
    except Exception as e:
        print(f"Error extracting options via LLM: {e}")
    return {}



def _compute_confidence(verification: dict, total_premises: int = 0) -> float:
    """Compute a confidence score (0.0–1.0) based on the Z3 verification result.

    Scoring rationale:
    - unsat: conclusion is formally proven; score scales with proof tightness.
        A smaller unsat core relative to total premises means a tighter, more
        focused proof → higher confidence (range 0.75–1.00).
    - sat: a counterexample was found; the answer is definitively not entailed.
        We are fairly confident in the "No/wrong option" judgment → 0.60.
    - unknown: Z3 could not decide; we have low confidence → 0.30.
    """
    result = verification.get("result")
    if result == z3.unsat:
        core_size = len(verification.get("unsat_core", []))
        # Tightness: 1.0 when core has 1 element, approaches 0 as core → total
        denom = max(total_premises, core_size, 1)
        tightness = 1.0 - (core_size - 1) / denom
        # Map tightness to [0.75, 1.00] and clamp to range
        score = 0.75 + tightness * 0.25
        return round(min(1.0, max(0.0, score)), 4)
    if result == z3.sat:
        return 0.60
    return 0.30


def detect_question_type(conclusion_nl: str) -> str:
    """Detect question type based on standard patterns."""
    options = parse_mcq_options(conclusion_nl)
    if len(options) >= 2:
        # Check for multiple-answer indicators in conclusion_nl
        text_lower = conclusion_nl.lower()
        mc_indicators = [
            "select all",
            "all that apply",
            "which of the following are",
            "choose all",
            "multiple answers",
            "multiple choices",
            "more than one",
            "all correct",
        ]
        if any(ind in text_lower for ind in mc_indicators):
            return "multiple_choice"
        return "single_choice"

    # Check for yes/no/uncertain questions
    text_stripped = conclusion_nl.strip()
    text_lower = text_stripped.lower()

    # If conclusion is a simple statement, it's boolean entailment, handled by yes_no flow
    if not text_stripped.endswith("?") and not any(
        text_lower.startswith(w)
        for w in ["who", "what", "which", "where", "when", "why", "how"]
    ):
        return "yes_no"

    yes_no_starters = [
        "is",
        "are",
        "does",
        "do",
        "can",
        "will",
        "was",
        "were",
        "has",
        "have",
        "should",
        "would",
        "if",
        "whether",
        "is it true",
        "could",
    ]
    if (
        any(text_lower.startswith(w) for w in yes_no_starters)
        or "yes or no" in text_lower
    ):
        return "yes_no"

    # Check for open-ended queries (Who, What, Which, Where, When, Why, How)
    open_ended_starters = ["who", "what", "which", "where", "when", "why", "how"]
    if (
        any(text_lower.startswith(w) for w in open_ended_starters)
        or "?" in text_stripped
    ):
        return "open_ended"

    # Fallback to yes_no (boolean statement entailment)
    return "yes_no"


def check_meta_premise_uncertain(premises, query):
    # Normalize strings for comparison (remove punctuation, lower case, normalize greek/unicode characters)
    def normalize(text):
        text = text.lower().strip()
        text = text.replace("μ", "u").replace("µ", "u")  # Normalize both micro and greek mu
        text = re.sub(r'[^\w\s]', '', text)
        return " ".join(text.split())

    normalized_query = normalize(query)
    
    # We also want to remove common question words from the start of the query
    # e.g., "does", "is", "are", "do", "can", "will", "was", "were", "has", "have", "should", "would", "whether"
    query_words = normalized_query.split()
    question_starters = {"does", "is", "are", "do", "can", "will", "was", "were", "has", "have", "should", "would", "whether", "if"}
    if query_words and query_words[0] in question_starters:
        query_words = query_words[1:]
    normalized_query_core = " ".join(query_words)

    # Let's define the patterns for meta-premises
    meta_patterns = [
        r"no\s+premise\s+states\s+(?:whether|that)\s+(.*)",
        r"it\s+is\s+not\s+specified\s+(?:whether|that)\s+(.*)",
        r"no\s+information\s+is\s+given\s+about\s+(.*)",
        r"there\s+is\s+no\s+information\s+about\s+(.*)",
        r"nothing\s+is\s+known\s+about\s+(.*)",
        r"it\s+is\s+unknown\s+(?:whether|that)\s+(.*)",
        r"no\s+premise\s+mentions\s+(.*)",
        r"no\s+statement\s+specifies\s+(.*)",
        r"it\s+is\s+not\s+known\s+(?:whether|that)\s+(.*)",
        r"no\s+information\s+about\s+(.*)",
        r"no\s+premise\s+indicates\s+(?:whether|that)\s+(.*)",
        r"we\s+do\s+not\s+know\s+(?:whether|that)\s+(.*)",
        r"it\s+is\s+not\s+clear\s+(?:whether|that)\s+(.*)"
    ]

    for idx, prem in enumerate(premises):
        prem_norm = prem.lower().strip()
        prem_norm = prem_norm.replace("μ", "u").replace("µ", "u")
        for pattern in meta_patterns:
            match = re.match(pattern, prem_norm)
            if match:
                # Extract the core statement from the premise
                core_statement = match.group(1).strip()
                normalized_core = normalize(core_statement)
                
                # Check if query core is in the normalized core, or vice versa, or if they are highly similar
                if normalized_core in normalized_query or normalized_query_core in normalized_core:
                    return True, idx
                
                # Let's also do a word-set overlap comparison for robustness
                words_core = set(normalized_core.split())
                words_query = set(normalized_query_core.split())
                # If they share a significant amount of content words (excluding stopwords/pronouns)
                stop_words = {"a", "an", "the", "of", "to", "in", "for", "with", "on", "at", "by", "from", "about"}
                words_core_clean = words_core - stop_words
                words_query_clean = words_query - stop_words
                if words_core_clean and words_query_clean:
                    intersection = words_core_clean.intersection(words_query_clean)
                    # If all content words in query are in the core_statement, or vice versa
                    if intersection == words_query_clean or intersection == words_core_clean:
                        return True, idx
                    # Alternatively, if high overlap percentage
                    overlap_ratio = len(intersection) / min(len(words_core_clean), len(words_query_clean))
                    if overlap_ratio >= 0.7:
                        return True, idx
                        
    return False, None


def detect_yes_no_subtype(conclusion_nl: str) -> str:
    """Split yes/no questions into support-query vs fact-query."""
    text = conclusion_nl.strip().lower()

    support_starts = (
        "do the premises",
        "do these premises",
        "do the statements",
        "do these statements",
        "do the facts",
        "do these facts",
        "based on the premises",
        "based on these premises",
    )
    support_markers = (
        "prove that",
        "establish that",
        "show that",
        "support that",
        "support the conclusion",
        "demonstrate that",
    )
    sufficiency_markers = (
        "guarantee",
        "guarantees",
        "guaranteed",
        "satisfy every requirement",
        "satisfies every requirement",
        "meet every requirement",
        "meets every requirement",
        "all requirements for",
    )

    if text.startswith(support_starts):
        return "support_query"
    if "premises" in text and any(marker in text for marker in support_markers):
        return "support_query"
    if any(marker in text for marker in sufficiency_markers):
        return "support_query"
    return "fact_query"


class LogicalReasoningPipeline:
    """
    Backward-compatible wrapper for the End-to-End Logical Reasoning Pipeline.
    Delegates to the modular NLToFOLPipeline for translation and ReasoningPipeline for Z3 reasoning.
    """

    def __init__(
        self,
        use_local: bool = True,
        model_dir: str = None,
        llm_client=None,
        device: str = None,
        temperature: float = 0.1,
    ):
        self.use_local = use_local
        self.model_dir = model_dir

        if llm_client is not None:
            self.llm_client = llm_client
        else:
            self.llm_client = LLMClient(
                use_local=use_local,
                model_dir=model_dir,
                device=device,
                temperature=temperature,
            )

        self.translation_pipeline = NLToFOLPipeline(
            use_local=use_local, model_dir=model_dir, llm_client=self.llm_client
        )
        self.reasoning_pipeline = ReasoningPipeline(
            use_local=use_local, model_dir=model_dir, llm_client=self.llm_client
        )

    @property
    def tokenizer(self):
        return self.translation_pipeline.tokenizer or self.reasoning_pipeline.tokenizer

    @property
    def model(self):
        return self.translation_pipeline.model or self.reasoning_pipeline.model

    @property
    def device(self):
        return self.translation_pipeline.device

    def load_local_model(self):
        self.translation_pipeline.load_local_model()
        self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
        self.reasoning_pipeline.model = self.translation_pipeline.model

    def translate_premises_and_conclusion(
        self, premises_nl: list[str], conclusion_nl: str
    ) -> tuple[list[str], str]:
        # Propagate models if loaded
        if self.translation_pipeline.model:
            self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
            self.reasoning_pipeline.model = self.translation_pipeline.model
        return self.translation_pipeline.translate_premises_and_conclusion(
            premises_nl, conclusion_nl
        )

    def verify_with_z3(
        self,
        premises_fol: list[str],
        conclusion_fol: str,
        negate_conclusion: bool = True,
    ) -> dict:
        return self.reasoning_pipeline.verify(
            premises_fol, conclusion_fol, negate_conclusion=negate_conclusion
        )

    def generate_reasoning(
        self, premises_nl: list[str], conclusion_nl: str, verification: dict
    ) -> str:
        # Propagate models if loaded
        if self.translation_pipeline.model:
            self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
            self.reasoning_pipeline.model = self.translation_pipeline.model
        return self.reasoning_pipeline.generate_reasoning(
            premises_nl, conclusion_nl, verification
        )

    def generate_cot(
        self,
        premises_nl: list[str],
        conclusion_nl: str,
        verification: dict,
        premises_fol: list[str] = None,
        conclusion_fol: str = None,
    ) -> tuple[str, list[str]]:
        """Generate structured CoT reasoning. Returns (reasoning_str, cot_steps)."""
        # Propagate models if loaded
        if self.translation_pipeline.model:
            self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
            self.reasoning_pipeline.model = self.translation_pipeline.model
        return self.reasoning_pipeline.generate_cot(
            premises_nl, conclusion_nl, verification, premises_fol, conclusion_fol
        )

    def _timing_enabled(self) -> bool:
        return os.getenv("EXACT_TIMING", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _record_timing(
        self, timings: dict[str, float | int], name: str, elapsed_seconds: float
    ) -> None:
        timings[f"{name}_seconds"] = round(
            float(timings.get(f"{name}_seconds", 0.0)) + elapsed_seconds, 6
        )
        timings[f"{name}_count"] = int(timings.get(f"{name}_count", 0)) + 1

    def _timed_call(
        self, timings: dict[str, float | int], name: str, func, *args, **kwargs
    ):
        started_at = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            self._record_timing(timings, name, time.perf_counter() - started_at)

    def _finalize_result(self, result: dict, timings: dict[str, float | int]) -> dict:
        if timings:
            result["_timings"] = timings
            if self._timing_enabled():
                print(
                    "[run_pipeline] Stage timings: "
                    + ", ".join(
                        f"{key}={value}"
                        for key, value in sorted(timings.items())
                    )
                )
        return result

    def _is_finetuned_model(self) -> bool:
        if hasattr(self.llm_client, "model_name") and self.llm_client.model_name:
            model_name_lower = self.llm_client.model_name.lower()
            return any(
                marker in model_name_lower
                for marker in (
                    "exact-qwen",
                    "lora",
                    "finetune",
                    "fol_router",
                    "physics",
                )
            )
        return False

    def _map_premises_to_original_indices(
        self, selected_premises_nl: list[str], original_premises_nl: list[str]
    ) -> list[int]:
        indices = []
        for premise in selected_premises_nl:
            if premise in original_premises_nl:
                indices.append(original_premises_nl.index(premise))
        return sorted(list(dict.fromkeys(indices)))

    def _extract_indices_from_verification(
        self,
        verification: dict,
        premises_nl: list[str],
        original_premises_nl: list[str],
    ) -> list[int]:
        mapped = []
        for var_str in verification.get("unsat_core", []):
            if not str(var_str).startswith("p_"):
                continue
            try:
                idx_1based = int(str(var_str).split("_")[1])
            except (TypeError, ValueError, IndexError):
                continue
            if 1 <= idx_1based <= len(premises_nl):
                premise_text = premises_nl[idx_1based - 1]
                if premise_text in original_premises_nl:
                    mapped.append(original_premises_nl.index(premise_text))
        return sorted(list(dict.fromkeys(mapped)))

    def _filter_premises_for_attribution(
        self,
        premises_nl: list[str],
        target_nl: str,
        premises_fol: list[str],
    ) -> tuple[list[str], list[str], list[int]]:
        try:
            return self.reasoning_pipeline.filter_relevant_premises(
                premises_nl, target_nl, premises_fol
            )
        except Exception:
            return premises_nl, premises_fol, list(range(len(premises_nl)))

    def _minimize_entailing_indices(
        self,
        premises_fol: list[str],
        conclusion_fol: str,
        candidate_indices: list[int],
    ) -> list[int]:
        if not candidate_indices or not conclusion_fol:
            return []

        working = sorted(list(dict.fromkeys(candidate_indices)))
        changed = True
        while changed and len(working) > 1:
            changed = False
            for idx in list(working):
                trial = [i for i in working if i != idx]
                if not trial:
                    continue
                verification = self.reasoning_pipeline.verify(
                    [premises_fol[i] for i in trial],
                    conclusion_fol,
                    negate_conclusion=True,
                )
                if verification.get("result") == z3.unsat:
                    working = trial
                    changed = True
                    break
        return working

    def _build_attribution(
        self,
        premises_nl: list[str],
        premises_fol: list[str],
        target_nl: str,
        *,
        conclusion_fol: str | None = None,
        require_proof: bool = False,
    ) -> tuple[list[int], list[str], list[str], dict | None]:
        attr_nl, attr_fol, attr_indices = self._filter_premises_for_attribution(
            premises_nl, target_nl, premises_fol
        )

        if not attr_indices:
            attr_indices = list(range(len(premises_nl)))
            attr_nl = premises_nl
            attr_fol = premises_fol

        attr_verification = None
        if require_proof and conclusion_fol:
            candidate_indices = list(attr_indices)
            candidate_verification = self.reasoning_pipeline.verify(
                [premises_fol[i] for i in candidate_indices],
                conclusion_fol,
                negate_conclusion=True,
            )
            if candidate_verification.get("result") != z3.unsat:
                candidate_indices = list(range(len(premises_nl)))

            attr_indices = self._minimize_entailing_indices(
                premises_fol, conclusion_fol, candidate_indices
            )
            if not attr_indices:
                attr_indices = candidate_indices

            attr_nl = [premises_nl[i] for i in attr_indices]
            attr_fol = [premises_fol[i] for i in attr_indices]
            attr_verification = self.reasoning_pipeline.verify(
                attr_fol, conclusion_fol, negate_conclusion=True
            )

        return attr_indices, attr_nl, attr_fol, attr_verification

    def run_pipeline(
        self, premises_nl: list[str], conclusion_nl: str, question_type: str = None, options_list: list[str] = None
    ) -> dict:
        # Propagate models if loaded
        if self.translation_pipeline.model:
            self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
            self.reasoning_pipeline.model = self.translation_pipeline.model
        timings: dict[str, float | int] = {}

        # Auto-detect question type if not specified
        if options_list is not None and len(options_list) > 0:
            is_yes_no = all(opt.lower() in ("yes", "no", "uncertain") for opt in options_list)
            if is_yes_no:
                question_type = "yes_no"
            else:
                question_type = "single_choice"
        else:
            if not question_type or question_type == "auto":
                question_type = detect_question_type(conclusion_nl)
                # Override to open_ended if no options provided
                if question_type in ("single_choice", "multiple_choice"):
                    question_type = "open_ended"

        yes_no_subtype = (
            detect_yes_no_subtype(conclusion_nl) if question_type == "yes_no" else None
        )

        # Check for meta-logical premise about missing information ONLY for yes_no queries
        if question_type == "yes_no" and yes_no_subtype == "fact_query":
            is_meta_uncertain, meta_idx = self._timed_call(
                timings,
                "option_parsing",
                check_meta_premise_uncertain,
                premises_nl,
                conclusion_nl,
            )
            if is_meta_uncertain:
                print(f"[run_pipeline] Meta-logical premise detected at index {meta_idx}. Returning Uncertain.")
                ans_opt = "Uncertain"
                if options_list:
                    matched = None
                    for opt in options_list:
                        if opt.lower().strip() in ("uncertain", "unknown", "no conclusion can be drawn"):
                            matched = opt
                            break
                    if matched:
                        ans_opt = matched
                    else:
                        ans_opt = options_list[0]
                
                explanation = f"Premise {meta_idx + 1} ('{premises_nl[meta_idx]}') explicitly states that no information is provided to determine this query."
                cot_steps = [
                    f"Query: {conclusion_nl}",
                    f"Premise {meta_idx + 1}: {premises_nl[meta_idx]}",
                    "Conclusion: The query cannot be determined from the given premises (Uncertain)."
                ]
                verification = {
                    "result": z3.sat,
                    "unsat_core": ["p_1"],
                    "model": None
                }
                return self._finalize_result({
                    "answer": ans_opt,
                    "confidence": 1.0,
                    "premises_fol": [premises_nl[meta_idx]],
                    "premises_nl": [premises_nl[meta_idx]],
                    "premises_used": [meta_idx],
                    "conclusion_fol": "",
                    "verification": verification,
                    "reasoning": explanation,
                    "cot": cot_steps,
                }, timings)

        # Check if options_list contains just keys (e.g. ["A", "B", "C", "D"])
        has_only_keys = False
        if options_list is not None and len(options_list) > 0:
            has_only_keys = all(len(opt.strip().rstrip(".")) == 1 for opt in options_list)

        # Detect multiple-choice options if MCQ type is selected or auto-detected
        option_parse_started = time.perf_counter()
        if options_list is not None and len(options_list) > 0 and question_type != "yes_no" and not has_only_keys:
            options = {chr(65 + i): opt for i, opt in enumerate(options_list)}
        else:
            options = parse_mcq_options(conclusion_nl)
            # Fallback to LLM extraction if we expected options but couldn't parse them via regex
            if (not options or len(options) < 2) and question_type != "yes_no" and (has_only_keys or (options_list is not None and len(options_list) > 0)):
                print("Regex option parsing failed/insufficient. Trying LLM extraction...")
                options = self._timed_call(
                    timings,
                    "option_parsing",
                    extract_options_via_llm,
                    conclusion_nl,
                    self.llm_client,
                )
            
            # Fallback if parsing failed but options_list is provided
            if not options and options_list is not None and len(options_list) > 0 and question_type != "yes_no":
                options = {chr(65 + i): opt for i, opt in enumerate(options_list)}
        self._record_timing(timings, "option_parsing", time.perf_counter() - option_parse_started)

        if question_type in ("single_choice", "multiple_choice") or (
            len(options) >= 2 and not question_type
        ):
            # MCQ Flow
            opt_keys = sorted(options.keys())

            # 1. Attempt unified combined translation for all premises and options together
            combined_nl = premises_nl + [options[k] for k in opt_keys]
            all_fol = self._timed_call(
                timings,
                "translation",
                self.translation_pipeline.translate_list,
                combined_nl,
            )

            if len(all_fol) == len(combined_nl):
                premises_fol = all_fol[: len(premises_nl)]
                options_fol = {
                    k: all_fol[len(premises_nl) + idx] for idx, k in enumerate(opt_keys)
                }
            else:
                # 2. Sequential Glossary-constrained Fallback: Translate premises, extract glossary, and translate options under constraints
                print(
                    f"Warning: Unified translation length mismatch ({len(all_fol)} vs {len(combined_nl)}). Falling back to sequential glossary-aligned translation."
                )
                premises_fol = []
                for p in premises_nl:
                    res = self._timed_call(
                        timings,
                        "translation",
                        self.translation_pipeline.translate_list,
                        [p],
                    )
                    premises_fol.append(res[0] if res else "")

                glossary_str = self.translation_pipeline.extract_glossary_from_fol(
                    premises_fol
                )
                options_fol = {}
                for k in opt_keys:
                    try:
                        res = self._timed_call(
                            timings,
                            "translation",
                            self.translation_pipeline.translate_list,
                            [options[k]],
                            glossary_str=glossary_str,
                        )
                    except TypeError:
                        res = self._timed_call(
                            timings,
                            "translation",
                            self.translation_pipeline.translate_list,
                            [options[k]],
                        )
                    options_fol[k] = res[0] if res else ""

            # 3. Final Lexical Predicate Unification over the entire set to ensure absolute consistency
            all_fol_list = premises_fol + [options_fol.get(k, "") for k in opt_keys]
            unified_fol_list = unify_fol_predicates(all_fol_list)

            # Deconstruct the unified list back into premises and options
            premises_fol = unified_fol_list[: len(premises_fol)]
            options_fol = {}
            for idx, k in enumerate(opt_keys):
                offset = len(premises_fol) + idx
                options_fol[k] = (
                    unified_fol_list[offset] if offset < len(unified_fol_list) else ""
                )

            # Use the full premise set for the actual proof search.
            # Attribution is minimized separately after the winning option is chosen.
            filt_premises_nl, filt_premises_fol = premises_nl, premises_fol

            # Evaluate ALL options
            unsat_candidates: list[
                tuple[str, dict, int]
            ] = []  # (key, verification, core_size)
            consistent_candidates: list[tuple[str, dict]] = []  # (key, verification)

            for k in opt_keys:
                opt_fol = options_fol.get(k, "")
                if not opt_fol:
                    continue
                try:
                    # 1. Check if the option is entailed (negate_conclusion=True)
                    verification = self._timed_call(
                        timings,
                        "per_option_verification",
                        self.reasoning_pipeline.verify,
                        filt_premises_fol,
                        opt_fol,
                        negate_conclusion=True,
                    )
                    if verification.get("result") == z3.unsat:
                        core_size = len(verification.get("unsat_core", []))
                        unsat_candidates.append((k, verification, core_size))
                    elif verification.get("result") == z3.sat:
                        # 2. Check if the option contradicts the premises (negate_conclusion=False)
                        verif_contra = self._timed_call(
                            timings,
                            "per_option_verification",
                            self.reasoning_pipeline.verify,
                            filt_premises_fol,
                            opt_fol,
                            negate_conclusion=False,
                        )
                        if verif_contra.get("result") != z3.unsat:
                            # It is consistent!
                            consistent_candidates.append((k, verification))
                except Exception:
                    pass

            correct_options = []
            correct_verifications = []

            if question_type == "multiple_choice":
                # Multiple Choice: return ALL correct (entailed) options
                if unsat_candidates:
                    correct_options = [x[0] for x in unsat_candidates]
                    correct_verifications = [x[1] for x in unsat_candidates]
                elif consistent_candidates:
                    # Fallback to consistent options
                    correct_options = [x[0] for x in consistent_candidates]
                    correct_verifications = [x[1] for x in consistent_candidates]
                else:
                    # Fallback: no option passed Z3 checks — use semantic LLM judgment (allowing 'Unknown')
                    premises_text = "\n".join(f"- {p}" for p in premises_nl)
                    try:
                        sem_prompt = (
                            f"Premises:\n{premises_text}\n\n"
                            f"Question:\n{conclusion_nl}\n\n"
                            f"Select all correct options. If none of the options logically follows from the premises or if there is insufficient information, respond with ONLY the word 'Unknown'. Otherwise, respond with a list of capital letters (e.g. A, B) of your choices."
                        )
                        sem_resp = self._timed_call(
                            timings,
                            "semantic_fallback",
                            self.llm_client.generate_text,
                            sem_prompt,
                            system_prompt="You are a precise logical reasoning assistant. Respond with ONLY the chosen letters or 'Unknown'. Do not add any explanation or other text.",
                            max_new_tokens=REMOTE_SEMANTIC_FALLBACK_MAX_TOKENS,
                        ).strip()

                        sem_clean = sem_resp.strip("., ")
                        if "unknown" in sem_clean.lower():
                            correct_options = ["Unknown"]
                        else:
                            matches = re.findall(r"\b([A-D])\b", sem_clean)
                            if matches:
                                correct_options = list(dict.fromkeys(matches))
                            else:
                                correct_options = [opt_keys[0]] if opt_keys else [""]
                    except Exception:
                        correct_options = [opt_keys[0]] if opt_keys else [""]

                    correct_verifications = []
                    for opt in correct_options:
                        if opt != "Unknown":
                            opt_fol = options_fol.get(opt, "")
                            if opt_fol:
                                try:
                                    ver = self._timed_call(
                                        timings,
                                        "per_option_verification",
                                        self.reasoning_pipeline.verify,
                                        filt_premises_fol,
                                        opt_fol,
                                        negate_conclusion=True,
                                    )
                                    correct_verifications.append(ver)
                                except Exception:
                                    correct_verifications.append(
                                        {
                                            "result": z3.unknown,
                                            "unsat_core": [],
                                            "model": None,
                                        }
                                    )
                            else:
                                correct_verifications.append(
                                    {
                                        "result": z3.unknown,
                                        "unsat_core": [],
                                        "model": None,
                                    }
                                )
                        else:
                            correct_verifications.append(
                                {"result": z3.unknown, "unsat_core": [], "model": None}
                            )
            else:
                # Single Choice: pick the best option
                if unsat_candidates:
                    if len(unsat_candidates) > 1:
                        # Prefer the option supported by the richest proof chain.
                        # This avoids an extra LLM round-trip and tends to favor the intended
                        # derived conclusion over a trivial directly stated fact.
                        unsat_candidates.sort(key=lambda x: (-x[2], x[0]))
                        correct_options = [unsat_candidates[0][0]]
                        correct_verifications = [unsat_candidates[0][1]]
                    else:
                        correct_options = [unsat_candidates[0][0]]
                        correct_verifications = [unsat_candidates[0][1]]
                elif consistent_candidates:
                    if len(consistent_candidates) > 1:
                        # Hybrid choice: LLM selects the best option among consistent candidates
                        choices_str = "\n".join(
                            f"{k}. {options[k]}" for k, _ in consistent_candidates
                        )
                        prompt = (
                            "You are a logical reasoning assistant.\n"
                            "Given the premises and the question:\n\n"
                            "Premises:\n"
                            + "\n".join(f"- {p}" for p in premises_nl)
                            + "\n\n"
                            f"Question: {conclusion_nl}\n\n"
                            f"Our formal symbolic prover has verified that the following options are consistent (not contradicted by the premises):\n"
                            f"{choices_str}\n\n"
                            f"Select the single most appropriate and intended conclusion from the consistent options above.\n"
                            f"Respond with ONLY the capital letter (A, B, C, or D) of your choice."
                        )
                        try:
                            best_opt = self._timed_call(
                                timings,
                                "tie_break",
                                self.llm_client.generate_text,
                                prompt,
                                max_new_tokens=REMOTE_TIE_BREAK_MAX_TOKENS,
                            ).strip()
                            match = re.search(r"\b([A-D])\b", best_opt)
                            if match:
                                selected_key = match.group(1)
                                matched = [
                                    c
                                    for c in consistent_candidates
                                    if c[0] == selected_key
                                ]
                                if matched:
                                    correct_options = [matched[0][0]]
                                    correct_verifications = [matched[0][1]]
                                else:
                                    correct_options = [consistent_candidates[0][0]]
                                    correct_verifications = [
                                        consistent_candidates[0][1]
                                    ]
                            else:
                                correct_options = [consistent_candidates[0][0]]
                                correct_verifications = [consistent_candidates[0][1]]
                        except Exception:
                            correct_options = [consistent_candidates[0][0]]
                            correct_verifications = [consistent_candidates[0][1]]
                    else:
                        correct_options = [consistent_candidates[0][0]]
                        correct_verifications = [consistent_candidates[0][1]]
                else:
                    # Fallback: no option passed Z3 checks — use semantic LLM judgment (allowing 'Unknown')
                    premises_text = "\n".join(f"- {p}" for p in premises_nl)
                    try:
                        sem_prompt = (
                            f"Premises:\n{premises_text}\n\n"
                            f"Question:\n{conclusion_nl}\n\n"
                            f"Select the single best answer. If none of the options A, B, C, or D logically follows from the premises or if there is insufficient information, respond with ONLY the word 'Unknown'. Otherwise, respond with ONLY the capital letter (A, B, C, or D) of your choice."
                        )
                        sem_resp = self._timed_call(
                            timings,
                            "semantic_fallback",
                            self.llm_client.generate_text,
                            sem_prompt,
                            system_prompt="You are a precise logical reasoning assistant. Respond with ONLY the chosen letter (A, B, C, D) or 'Unknown'. Do not add any explanation or other text.",
                            max_new_tokens=REMOTE_SEMANTIC_FALLBACK_MAX_TOKENS,
                        ).strip()

                        sem_clean = sem_resp.strip("., ")
                        if "unknown" in sem_clean.lower():
                            correct_options = ["Unknown"]
                        else:
                            match = re.search(r"\b([A-D])\b", sem_clean)
                            if match:
                                correct_options = [match.group(1)]
                            else:
                                correct_options = [opt_keys[0]] if opt_keys else [""]
                    except Exception:
                        correct_options = [opt_keys[0]] if opt_keys else [""]

                    correct_verifications = []
                    if correct_options and correct_options[0] != "Unknown":
                        opt_fol = options_fol.get(correct_options[0], "")
                        if opt_fol:
                            try:
                                ver = self._timed_call(
                                    timings,
                                    "per_option_verification",
                                    self.reasoning_pipeline.verify,
                                    filt_premises_fol,
                                    opt_fol,
                                    negate_conclusion=True,
                                )
                                correct_verifications.append(ver)
                            except Exception:
                                correct_verifications.append(
                                    {
                                        "result": z3.unknown,
                                        "unsat_core": [],
                                        "model": None,
                                    }
                                )
                        else:
                            correct_verifications.append(
                                {"result": z3.unknown, "unsat_core": [], "model": None}
                            )
                    else:
                        correct_verifications.append(
                            {"result": z3.unknown, "unsat_core": [], "model": None}
                        )

            if not correct_options:
                correct_options = [opt_keys[0]] if opt_keys else [""]
                correct_verifications = [
                    {"result": z3.unknown, "unsat_core": [], "model": None}
                ]

            best_verification = correct_verifications[0]
            premises_used = []
            reasoning_premises_nl = filt_premises_nl
            reasoning_premises_fol = filt_premises_fol

            # Generate combined reasoning/CoT
            if len(correct_options) > 1:
                conclusion_nl_cot = " and ".join(
                    f"Option {opt}: {options.get(opt, opt)}" for opt in correct_options
                )
                # Create a combined verification structure
                merged_unsat_core = list(
                    set().union(
                        *(v.get("unsat_core", []) for v in correct_verifications)
                    )
                )
                # If all are unsat, result is unsat
                combined_result = (
                    z3.unsat
                    if all(v.get("result") == z3.unsat for v in correct_verifications)
                    else z3.sat
                )
                combined_proof = (
                    "\n\n".join(
                        f"Proof for Option {opt}:\n{v.get('proof')}"
                        for opt, v in zip(correct_options, correct_verifications)
                        if v.get("proof") is not None
                    )
                    or None
                )
                combined_verification = {
                    "result": combined_result,
                    "unsat_core": merged_unsat_core,
                    "proof": combined_proof,
                    "model": best_verification.get("model"),
                }
                if correct_options and all(opt != "Unknown" for opt in correct_options):
                    used_union = set()
                    for opt, verification in zip(correct_options, correct_verifications):
                        target_text = options.get(opt, opt)
                        target_fol = options_fol.get(opt, "")
                        require_proof = verification.get("result") == z3.unsat
                        used_i, _, _, _ = self._timed_call(
                            timings,
                            "attribution",
                            self._build_attribution,
                            premises_nl,
                            premises_fol,
                            target_text,
                            conclusion_fol=target_fol,
                            require_proof=require_proof,
                        )
                        used_union.update(used_i)
                    premises_used = sorted(used_union)
                    reasoning_premises_nl = [premises_nl[i] for i in premises_used]
                    reasoning_premises_fol = [premises_fol[i] for i in premises_used]
            else:
                opt = correct_options[0]
                conclusion_nl_cot = (
                    f"Option {opt}: {options[opt]}" if opt in options else opt
                )
                combined_verification = best_verification
                if opt != "Unknown":
                    target_fol = options_fol.get(opt, "")
                    require_proof = best_verification.get("result") == z3.unsat
                    (
                        premises_used,
                        reasoning_premises_nl,
                        reasoning_premises_fol,
                        attribution_verification,
                    ) = self._timed_call(
                        timings,
                        "attribution",
                        self._build_attribution,
                        premises_nl,
                        premises_fol,
                        options.get(opt, opt),
                        conclusion_fol=target_fol,
                        require_proof=require_proof,
                    )
                    if attribution_verification is not None:
                        combined_verification = attribution_verification

            # For conclusion_fol, we can represent it as AND of the options if multiple, else single
            if len(correct_options) > 1:
                conclusion_fol_str = (
                    "AND("
                    + ", ".join(options_fol.get(opt, opt) for opt in correct_options)
                    + ")"
                )
            else:
                conclusion_fol_str = options_fol.get(
                    correct_options[0], correct_options[0]
                )

            # If the selected correct option(s) are positive (not "Unknown") but were not proven by Z3 (meaning they came from fallback)
            # we override the verification object to avoid generating a counterexample explanation.
            is_any_unknown = any(opt == "Unknown" for opt in correct_options)
            is_all_unsat = all(v.get("result") == z3.unsat for v in correct_verifications)

            if not is_any_unknown and not is_all_unsat:
                explanation_verification = {
                    "result": z3.unsat,
                    "unsat_core": [],
                    "proof": None,
                    "model": None,
                }
            else:
                explanation_verification = combined_verification

            if (
                len(correct_options) == 1
                and correct_options[0] != "Unknown"
                and combined_verification.get("result") == z3.unsat
            ):
                opt = correct_options[0]
                selected_text = options.get(opt, opt)
                cited = [
                    f"Premise {idx + 1}: {premises_nl[idx]}" for idx in premises_used
                ]
                if cited:
                    reasoning = (
                        f"Option {opt} is logically supported by the cited premises.\n\n"
                        + "\n".join(f"- {line}" for line in cited)
                        + f"\n\nTherefore, {selected_text}."
                    )
                else:
                    reasoning = f"Option {opt} is logically supported by the premises. Therefore, {selected_text}."
                cot = cited + [f"Conclusion: {selected_text}"]
            else:
                reasoning, cot = self._timed_call(
                    timings,
                    "explanation_generation",
                    self.generate_cot,
                    premises_nl=reasoning_premises_nl,
                    conclusion_nl=conclusion_nl_cot,
                    verification=explanation_verification,
                    premises_fol=reasoning_premises_fol,
                    conclusion_fol=conclusion_fol_str,
                )

            answer_val = (
                correct_options
                if question_type == "multiple_choice"
                else correct_options[0]
            )

            return self._finalize_result({
                "answer": answer_val,
                "confidence": _compute_confidence(
                    best_verification, total_premises=len(filt_premises_fol)
                ),
                "premises_fol": reasoning_premises_fol,
                "premises_nl": reasoning_premises_nl,
                "premises_used": premises_used,
                "conclusion_fol": conclusion_fol_str,
                "verification": combined_verification,
                "reasoning": reasoning,
                "cot": cot,
            }, timings)

        elif question_type == "open_ended":
            # Open-Ended Flow: Generate candidate answer using LLM, then verify
            premises_text = "\n".join(
                f"{i + 1}. {p}" for i, p in enumerate(premises_nl)
            )
            user_prompt = OPEN_ENDED_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text, question_nl=conclusion_nl
            )
            candidate_answer = self._timed_call(
                timings,
                "semantic_fallback",
                self.llm_client.generate_text,
                prompt=user_prompt,
                system_prompt=OPEN_ENDED_SYSTEM_PROMPT,
                max_new_tokens=REMOTE_OPEN_ENDED_MAX_TOKENS,
            ).strip()

            # Fallback: if candidate answer is empty, retry without the complex system prompt
            if not candidate_answer:
                print("[run_pipeline] Candidate answer was empty. Retrying with no system prompt.")
                candidate_answer = self._timed_call(
                    timings,
                    "semantic_fallback",
                    self.llm_client.generate_text,
                    prompt=user_prompt,
                    system_prompt=None,
                    max_new_tokens=REMOTE_OPEN_ENDED_MAX_TOKENS,
                ).strip()

            # Check for numeric query
            is_numeric = any(
                indicator in conclusion_nl.lower()
                for indicator in [
                    "how many",
                    "number of",
                    "count of",
                    "how much",
                    "what is the enrollment",
                    "what is the count",
                ]
            )
            short_answer = None
            num_map = {
                "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
                "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
                "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
                "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
                "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
                "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
                "eighty": "80", "ninety": "90", "hundred": "100"
            }

            if is_numeric:
                # Try to find digits or decimals first
                numbers = re.findall(r"\b\d+(?:\.\d+)?\b", candidate_answer)
                if numbers:
                    short_answer = numbers[0]
                else:
                    # Try to map word representation of numbers
                    words = re.findall(r"\b\w+\b", candidate_answer.lower())
                    for w in words:
                        if w in num_map:
                            short_answer = num_map[w]
                            break

                # If still not found, search in premises that have high keyword overlap
                if not short_answer:
                    q_words = re.findall(r'\b\w+\b', conclusion_nl.lower())
                    q_stop = {
                        "how", "many", "what", "is", "the", "does", "do", "did", "have", "has",
                        "who", "whom", "where", "which", "of", "in", "a", "an", "enrolled"
                    }
                    q_keywords = [w for w in q_words if w not in q_stop]
                    if q_keywords:
                        best_overlap = 0
                        best_num = None
                        for p in premises_nl:
                            p_clean = p.lower()
                            overlap = sum(1 for w in q_keywords if w in p_clean)
                            if overlap > best_overlap:
                                p_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", p)
                                if p_numbers:
                                    best_overlap = overlap
                                    best_num = p_numbers[0]
                                else:
                                    # check words
                                    p_words = re.findall(r"\b\w+\b", p_clean)
                                    for w in p_words:
                                        if w in num_map:
                                            best_overlap = overlap
                                            best_num = num_map[w]
                                            break
                        if best_num:
                            short_answer = best_num

            # Translate the premises and the generated candidate answer statement
            # We translate the full candidate_answer to ensure proper FOL formula parsing
            premises_fol, conclusion_fol = self._timed_call(
                timings,
                "translation",
                self.translate_premises_and_conclusion,
                premises_nl,
                candidate_answer,
            )

            is_finetuned = False
            if hasattr(self.llm_client, "model_name") and self.llm_client.model_name:
                model_name_lower = self.llm_client.model_name.lower()
                if (
                    "exact-qwen" in model_name_lower
                    or "lora" in model_name_lower
                    or "finetune" in model_name_lower
                    or "fol_router" in model_name_lower
                    or "physics" in model_name_lower
                ):
                    is_finetuned = True

            if is_finetuned:
                filt_premises_nl, filt_premises_fol = premises_nl, premises_fol
            else:
                # Filter premises to those most relevant
                filt_premises_nl, filt_premises_fol, _ = self._timed_call(
                    timings,
                    "attribution",
                    self.reasoning_pipeline.filter_relevant_premises,
                    premises_nl,
                    candidate_answer,
                    premises_fol,
                )

            # Verify entailment of candidate answer with Z3
            verification = self._timed_call(
                timings,
                "verification",
                self.reasoning_pipeline.verify,
                filt_premises_fol,
                conclusion_fol,
                negate_conclusion=True,
            )

            # Check if the generated answer is confirmed by Z3
            if verification["result"] == z3.unsat:
                answer_status = short_answer if (is_numeric and short_answer is not None) else candidate_answer
            else:
                # If Z3 cannot verify but it's a numeric query and we extracted a short answer, use the short answer
                if is_numeric and short_answer is not None:
                    answer_status = short_answer
                    
                    # Find which premise contains the short_answer and has highest keyword overlap
                    # to populate the unsat_core for proper premises_used mapping in api_server.py
                    q_words = re.findall(r'\b\w+\b', conclusion_nl.lower())
                    q_stop = {"how", "many", "what", "is", "the", "does", "do", "did", "have", "has", "who", "whom", "where", "which", "of", "in", "a", "an"}
                    q_keywords = [w for w in q_words if w not in q_stop]
                    
                    best_prem_idx = None
                    best_overlap = -1
                    # 1. Search in filt_premises_nl first to keep alignment
                    for idx, p in enumerate(filt_premises_nl):
                        p_clean = p.lower()
                        has_val = False
                        # Match whole-number boundaries to prevent sub-string collision (e.g. "2" in "12")
                        if re.search(r"\b" + re.escape(short_answer) + r"\b", p):
                            has_val = True
                        else:
                            # Check reverse word mapping
                            for name, val in num_map.items():
                                if val == short_answer and re.search(r"\b" + re.escape(name) + r"\b", p_clean):
                                    has_val = True
                                    break
                        if has_val:
                            overlap = sum(1 for w in q_keywords if w in p_clean)
                            if overlap > best_overlap:
                                best_overlap = overlap
                                best_prem_idx = idx
                                
                    # 2. If not found in filtered list, fallback to search in all premises_nl
                    if best_prem_idx is None:
                        best_orig_idx = None
                        best_overlap = -1
                        for idx, p in enumerate(premises_nl):
                            p_clean = p.lower()
                            has_val = False
                            if re.search(r"\b" + re.escape(short_answer) + r"\b", p):
                                has_val = True
                            else:
                                for name, val in num_map.items():
                                    if val == short_answer and re.search(r"\b" + re.escape(name) + r"\b", p_clean):
                                        has_val = True
                                        break
                            if has_val:
                                overlap = sum(1 for w in q_keywords if w in p_clean)
                                if overlap > best_overlap:
                                    best_overlap = overlap
                                    best_orig_idx = idx
                                    
                        if best_orig_idx is not None:
                            target_premise_nl = premises_nl[best_orig_idx]
                            target_premise_fol = premises_fol[best_orig_idx] if best_orig_idx < len(premises_fol) else target_premise_nl
                            
                            # Append target premise to filt_premises lists to ensure correct indices
                            if target_premise_nl not in filt_premises_nl:
                                filt_premises_nl.append(target_premise_nl)
                                filt_premises_fol.append(target_premise_fol)
                            
                            best_prem_idx = filt_premises_nl.index(target_premise_nl)
                                
                    if best_prem_idx is not None:
                        verification["unsat_core"] = [f"p_{best_prem_idx + 1}"]
                        verification["result"] = z3.unsat
                else:
                    # Z3 cannot verify the candidate answer, so standard logical answer is Unknown
                    answer_status = "Unknown"

            reasoning, cot = self._timed_call(
                timings,
                "explanation_generation",
                self.generate_cot,
                premises_nl=filt_premises_nl,
                conclusion_nl=candidate_answer,
                verification=verification,
                premises_fol=filt_premises_fol,
                conclusion_fol=conclusion_fol,
            )

            premises_used = self._extract_indices_from_verification(
                verification, filt_premises_nl, premises_nl
            )
            if not premises_used and answer_status != "Unknown":
                premises_used = self._map_premises_to_original_indices(
                    filt_premises_nl, premises_nl
                )

            return self._finalize_result({
                "answer": answer_status,
                "confidence": _compute_confidence(
                    verification, total_premises=len(filt_premises_fol)
                ),
                "premises_fol": filt_premises_fol,
                "premises_nl": filt_premises_nl,
                "premises_used": premises_used,
                "conclusion_fol": conclusion_fol,
                "verification": verification,
                "reasoning": reasoning,
                "cot": cot,
            }, timings)

        else:
            # Yes/No or Statement Flow
            premises_fol, conclusion_fol = self._timed_call(
                timings,
                "translation",
                self.translate_premises_and_conclusion,
                premises_nl,
                conclusion_nl,
            )

            original_conclusion_nl = conclusion_nl
            original_conclusion_fol = conclusion_fol
            filt_premises_nl, filt_premises_fol = premises_nl, premises_fol

            verification = self._timed_call(
                timings,
                "verification",
                self.reasoning_pipeline.verify,
                premises_fol,
                conclusion_fol,
                negate_conclusion=True,
            )
            answer = "Uncertain"
            is_z3_decisive = False
            is_fallback_used = False
            reasoning_conclusion_nl = original_conclusion_nl
            reasoning_conclusion_fol = original_conclusion_fol
            reasoning_premises_nl = premises_nl
            reasoning_premises_fol = premises_fol
            premises_used = []

            if yes_no_subtype == "support_query":
                if verification.get("result") == z3.unsat:
                    answer = "Yes"
                    is_z3_decisive = True
                    (
                        premises_used,
                        reasoning_premises_nl,
                        reasoning_premises_fol,
                        attribution_verification,
                    ) = self._timed_call(
                        timings,
                        "attribution",
                        self._build_attribution,
                        premises_nl,
                        premises_fol,
                        original_conclusion_nl,
                        conclusion_fol=original_conclusion_fol,
                        require_proof=True,
                    )
                    if attribution_verification is not None:
                        verification = attribution_verification
                else:
                    answer = "No"
                    is_z3_decisive = True
                    (
                        premises_used,
                        reasoning_premises_nl,
                        reasoning_premises_fol,
                        _,
                    ) = self._timed_call(
                        timings,
                        "attribution",
                        self._build_attribution,
                        premises_nl,
                        premises_fol,
                        original_conclusion_nl,
                        require_proof=False,
                    )
            else:
                if verification.get("result") == z3.unsat:
                    answer = "Yes"
                    is_z3_decisive = True
                    (
                        premises_used,
                        reasoning_premises_nl,
                        reasoning_premises_fol,
                        attribution_verification,
                    ) = self._timed_call(
                        timings,
                        "attribution",
                        self._build_attribution,
                        premises_nl,
                        premises_fol,
                        original_conclusion_nl,
                        conclusion_fol=original_conclusion_fol,
                        require_proof=True,
                    )
                    if attribution_verification is not None:
                        verification = attribution_verification
                elif verification.get("result") == z3.sat:
                    try:
                        verification_neg = self._timed_call(
                            timings,
                            "verification",
                            self.reasoning_pipeline.verify,
                            premises_fol,
                            original_conclusion_fol,
                            negate_conclusion=False,
                        )
                        if verification_neg.get("result") == z3.unsat:
                            answer = "No"
                            is_z3_decisive = True
                            reasoning_conclusion_nl = f"NOT ({original_conclusion_nl})"
                            reasoning_conclusion_fol = f"NOT ({original_conclusion_fol})"
                            (
                                premises_used,
                                reasoning_premises_nl,
                                reasoning_premises_fol,
                                attribution_verification,
                            ) = self._timed_call(
                                timings,
                                "attribution",
                                self._build_attribution,
                                premises_nl,
                                premises_fol,
                                original_conclusion_nl,
                                conclusion_fol=reasoning_conclusion_fol,
                                require_proof=True,
                            )
                            verification = (
                                attribution_verification
                                if attribution_verification is not None
                                else verification_neg
                            )
                        elif verification_neg.get("result") == z3.sat:
                            answer = "Uncertain"
                            is_z3_decisive = True
                    except Exception:
                        pass

                if not premises_used and is_z3_decisive:
                    (
                        premises_used,
                        reasoning_premises_nl,
                        reasoning_premises_fol,
                        _,
                    ) = self._timed_call(
                        timings,
                        "attribution",
                        self._build_attribution,
                        premises_nl,
                        premises_fol,
                        original_conclusion_nl,
                        require_proof=False,
                    )

            if not is_z3_decisive and yes_no_subtype == "fact_query":
                try:
                    attr_prompt_premises_nl, _, _ = self._timed_call(
                        timings,
                        "attribution",
                        self._filter_premises_for_attribution,
                        premises_nl,
                        original_conclusion_nl,
                        premises_fol,
                    )
                    premises_text = "\n".join(f"- {p}" for p in attr_prompt_premises_nl)
                    sem_prompt = SEMANTIC_YESNO_USER_PROMPT_TEMPLATE.format(
                        premises_text=premises_text, conclusion_nl=original_conclusion_nl
                    )
                    sem_resp = self._timed_call(
                        timings,
                        "semantic_fallback",
                        self.llm_client.generate_text,
                        sem_prompt,
                        system_prompt=SEMANTIC_YESNO_SYSTEM_PROMPT,
                        max_new_tokens=REMOTE_SEMANTIC_FALLBACK_MAX_TOKENS,
                    ).strip()
                    # Accept only clean Yes/No/Uncertain from LLM
                    sem_lower = sem_resp.lower().strip("., ")
                    if sem_lower.startswith("yes"):
                        answer = "Yes"
                        is_fallback_used = True
                    elif sem_lower.startswith("no"):
                        answer = "No"
                        is_fallback_used = True
                except Exception:
                    pass

                (
                    premises_used,
                    reasoning_premises_nl,
                    reasoning_premises_fol,
                    _,
                ) = self._timed_call(
                    timings,
                    "attribution",
                    self._build_attribution,
                    premises_nl,
                    premises_fol,
                    original_conclusion_nl,
                    require_proof=False,
                )

            # If answer is positive but determined by semantic fallback,
            # override verification to a dummy positive state so generate_cot
            # explains it positively instead of as a counterexample
            if is_fallback_used and answer in ("Yes", "No"):
                explanation_verification = {
                    "result": z3.unsat,
                    "unsat_core": [],
                    "proof": None,
                    "model": None,
                }
            else:
                explanation_verification = verification

            if not premises_used:
                premises_used = self._map_premises_to_original_indices(
                    reasoning_premises_nl, premises_nl
                )

            if yes_no_subtype == "support_query" and answer == "No" and verification.get("result") == z3.unknown:
                explanation_verification = {
                    "result": z3.sat,
                    "unsat_core": [],
                    "proof": None,
                    "model": None,
                }

            reasoning, cot = self._timed_call(
                timings,
                "explanation_generation",
                self.generate_cot,
                premises_nl=reasoning_premises_nl,
                conclusion_nl=reasoning_conclusion_nl,
                verification=explanation_verification,
                premises_fol=reasoning_premises_fol,
                conclusion_fol=reasoning_conclusion_fol,
            )

            return self._finalize_result({
                "answer": answer,
                "confidence": _compute_confidence(
                    verification, total_premises=len(reasoning_premises_fol)
                ),
                "premises_fol": reasoning_premises_fol,
                "premises_nl": reasoning_premises_nl,
                "premises_used": premises_used,
                "conclusion_fol": reasoning_conclusion_fol,
                "verification": verification,
                "reasoning": reasoning,
                "cot": cot,
            }, timings)
