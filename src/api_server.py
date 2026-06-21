# ruff: noqa: E402
from __future__ import annotations

import os
import sys

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import time
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to sys.path to enable src imports
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Configure Z3 for stability
import z3

z3.set_param("proof", False)

# Import EXACT pipelines
from src.llm.llm_client import LLMClient
from src.logic.pipeline import LogicalReasoningPipeline
from src.physics.api import run_physics
from src.physics.types import PhysicsTask

# Initialize FastAPI App
app = FastAPI(
    title="EXACT 2026 Evaluation Endpoint",
    description="Unified API prediction server for Type 1 and Type 2 queries",
    version="1.0.0",
)

# Configuration settings (configurable via environment variables)
MODEL_NAME = os.getenv("MODEL_NAME", "fol_router")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "https://router.huggingface.co/v1")
HF_API_KEY = os.getenv("HF_API_KEY", "")

# Fallback override for development/testing when using Hugging Face router
if "router.huggingface.co" in VLLM_BASE_URL and MODEL_NAME == "fol_router":
    MODEL_NAME = "Qwen/Qwen3-8B:featherless-ai"

# Global instances of logic pipeline and physics helper
logic_pipeline: Optional[LogicalReasoningPipeline] = None
TYPE1_TIMEOUT_SECONDS = 58.0


def _timing_enabled() -> bool:
    return os.getenv("EXACT_TIMING", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@app.on_event("startup")
def startup_event():
    global logic_pipeline
    print("=" * 60)
    print("STARTING EXACT 2026 API SERVER")
    print(f"Model Name    : {MODEL_NAME}")
    print(f"vLLM Base URL : {VLLM_BASE_URL}")
    print("=" * 60)

    # Initialize client and pipelines
    client = LLMClient(
        model_name=MODEL_NAME,
        api_key=HF_API_KEY,
        base_url=VLLM_BASE_URL,
        temperature=0.1,
        use_local=False,
    )
    logic_pipeline = LogicalReasoningPipeline(use_local=False, llm_client=client)
    print("Pipelines successfully initialized.")


# Pydantic Schemas for Input/Output validation
class PredictRequest(BaseModel):
    query_id: str
    type: str  # "type1" or "type2"
    query: str
    premises: List[str] = Field(default_factory=list)
    options: List[str] = Field(default_factory=list)


class ReasoningObject(BaseModel):
    type: str  # "fol" or "cot" or "proof"
    steps: List[str]


class PredictResponseItem(BaseModel):
    query_id: str
    answer: str
    unit: str
    explanation: str
    premises_used: List[int]
    reasoning: Optional[ReasoningObject] = None


def map_pipeline_answer_to_options(pipeline_ans: Any, input_options: List[str]) -> str:
    """
    Robust mapping from logic pipeline answer format to the required exact choice string.
    """
    if not input_options:
        return str(pipeline_ans) if pipeline_ans is not None else ""

    # If it is a list of answers, handle them
    if isinstance(pipeline_ans, list):
        ans_items = [str(x).strip() for x in pipeline_ans]
    else:
        ans_items = [str(pipeline_ans).strip()]

    mapped_items = []
    for item in ans_items:
        # Check if the pipeline response matches any option directly (case-insensitive)
        matched_opt = None
        for opt in input_options:
            if opt.lower().strip() == item.lower():
                matched_opt = opt
                break
        if matched_opt:
            mapped_items.append(matched_opt)
            continue

        # If pipeline returned a letter index (A, B, C, D)
        if item in ("A", "B", "C", "D", "E", "F", "G"):
            idx = ord(item) - ord("A")
            if 0 <= idx < len(input_options):
                mapped_items.append(input_options[idx])
                continue

        # If pipeline returned numeric index string
        if item.isdigit():
            idx = int(item)
            if 0 <= idx < len(input_options):
                mapped_items.append(input_options[idx])
                continue

        # Fallback to option by index if it looks like character mapping failed
        mapped_items.append(item)

    if isinstance(pipeline_ans, list):
        return ", ".join(mapped_items)
    return mapped_items[0] if mapped_items else ""


def extract_premises_used(
    verification: Dict[str, Any],
    filt_premises_nl: List[str],
    original_premises: List[str],
) -> List[int]:
    """
    Map Z3's unsat core tracking variables (like p_1, p_2...) back to 0-based indices in the original premises.
    """
    premises_used = []
    unsat_core = verification.get("unsat_core", [])
    for var_str in unsat_core:
        if var_str.startswith("p_"):
            try:
                # p_1 is 1-based index into filt_premises_nl
                idx_1based = int(var_str.split("_")[1])
                if 1 <= idx_1based <= len(filt_premises_nl):
                    premise_text = filt_premises_nl[idx_1based - 1]
                    if premise_text in original_premises:
                        premises_used.append(original_premises.index(premise_text))
            except (ValueError, IndexError):
                pass
    return sorted(list(set(premises_used)))


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


@app.post("/predict", response_model=List[PredictResponseItem], response_class=UTF8JSONResponse)
async def predict(request: PredictRequest):
    """
    Unified prediction endpoint that routes the request to Type 1 (logic) or Type 2 (physics) pipelines.
    Returns a list with a single prediction response item.
    """
    start_time = time.time()
    print(f"\n[{request.query_id}] Received {request.type} request...")
    try:
        print(f"[{request.query_id}] Request payload: {json.dumps(request.model_dump(), ensure_ascii=False)}")
    except Exception as e:
        print(f"[{request.query_id}] Error logging request payload: {e}")

    if request.type == "type1":
        if not logic_pipeline:
            raise HTTPException(
                status_code=500, detail="Logic pipeline not initialized."
            )

        try:
            # 2. Run the Logical Reasoning Pipeline
            # We run this in a threadpool to prevent blocking the async loop
            # and wrap it in asyncio.wait_for to enforce a strict Type 1 timeout
            # that still stays below the evaluator's 60-second client timeout.
            loop = asyncio.get_running_loop()
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        logic_pipeline.run_pipeline,
                        request.premises,
                        request.query,
                        None,
                        request.options
                    ),
                    timeout=TYPE1_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                print(f"[{request.query_id}] Type 1 pipeline timed out after {TYPE1_TIMEOUT_SECONDS:.0f} seconds. Returning fallback.")
                answer = "Uncertain" if "Uncertain" in request.options else (request.options[0] if request.options else "Unknown")
                resp_items = [
                    PredictResponseItem(
                        query_id=request.query_id,
                        answer=answer,
                        unit="",
                        explanation=f"Logical reasoning execution timed out after {TYPE1_TIMEOUT_SECONDS:.0f} seconds.",
                        premises_used=[],
                        reasoning=None,
                    ).model_dump(mode="json")
                ]
                print(f"[{request.query_id}] Response payload (timeout fallback): {json.dumps(resp_items, ensure_ascii=False)}")
                return UTF8JSONResponse(content=resp_items)

            # 3. Format the final output
            answer = map_pipeline_answer_to_options(
                result.get("answer"), request.options
            )

            premises_used = result.get("premises_used")
            if not isinstance(premises_used, list):
                filt_premises_nl = result.get("premises_nl", [])
                premises_used = extract_premises_used(
                    result.get("verification", {}), filt_premises_nl, request.premises
                )

            # Reconstruct the conclusion text to generate a concise, human-like explanation
            from src.logic.pipeline import parse_mcq_options
            conclusion_nl = request.query
            try:
                options = parse_mcq_options(request.query)
                if answer in options:
                    conclusion_nl = f"Option {answer}: {options[answer]}"
                elif request.options and answer in request.options:
                    idx = request.options.index(answer)
                    opt_key = chr(65 + idx)
                    if opt_key in options:
                        conclusion_nl = f"Option {opt_key}: {options[opt_key]}"
                    else:
                        conclusion_nl = answer
            except Exception:
                pass

            explanation = ""
            if logic_pipeline and result.get("verification"):
                try:
                    from src.logic.reasoning.verifier import format_z3_model
                    verification = result.get("verification")
                    verification_result = verification.get("result")
                    
                    system_prompt = (
                        "You are an expert in logical reasoning. "
                        "Your role is to explain logical arguments clearly, concisely, and naturally, like a human thinker.\n\n"
                        "IMPORTANT RULES:\n"
                        "- Be highly concise and direct. Keep the explanation under 2-3 sentences.\n"
                        "- Do NOT include any introductory fluff (e.g. 'Based on the provided premises...', 'We can conclude...'). Start immediately with the first logical step.\n"
                        "- Synthesize ideas across premises — show how they connect and combine.\n"
                        "- Use transitional language: 'Since', 'Therefore', 'This means', 'Combined with', 'As a result', 'It follows that'.\n"
                        "- Never just copy or list premises verbatim — interpret and derive.\n"
                        "- Your explanation should read as a flowing argument, not a bullet list of facts."
                    )
                    
                    core_premises_nl = result.get("premises_nl") or request.premises
                    
                    if verification_result == z3.unsat:
                        core_indices = []
                        for var_str in verification.get("unsat_core", []):
                            if var_str.startswith("p_"):
                                try:
                                    core_indices.append(int(var_str.split("_")[1]) - 1)
                                except ValueError:
                                    pass
                        core_indices.sort()
                        
                        core_premises_text = "\n".join(
                            f"- Premise {idx + 1}: {core_premises_nl[idx]}"
                            for idx in core_indices if idx < len(core_premises_nl)
                        )
                        if not core_premises_text:
                            core_premises_text = "\n".join(f"- {p}" for p in core_premises_nl)
                            
                        user_prompt = (
                            "The following premises have been formally proven (via Z3 SMT solver) to entail the conclusion.\n\n"
                            f"Key premises:\n{core_premises_text}\n\n"
                            f"Conclusion:\n- {conclusion_nl}\n\n"
                            "Write an extremely concise explanation (2-3 sentences max) that shows HOW these premises chain together to reach the conclusion. "
                            "Start directly with the first step of reasoning, without any introductory filler. "
                            "Trace the logical flow using transitional words like 'Since', 'Therefore', 'This means', 'Combined with'."
                        )
                    elif verification_result == z3.sat:
                        premises_text = "\n".join(f"- {p}" for p in core_premises_nl)
                        model_str = format_z3_model(verification.get("model"))
                        user_prompt = (
                            "The SMT solver found a counterexample: the premises are all TRUE yet the conclusion is FALSE.\n\n"
                            f"Premises:\n{premises_text}\n\n"
                            f"Conclusion being tested:\n- {conclusion_nl}\n\n"
                            f"Counterexample (Z3 model):\n{model_str}\n\n"
                            "Explain in a very brief plain language sentence or two why this counterexample breaks the conclusion. "
                            "Start directly without introductory filler. Show what the counterexample tells us and what logical gap it exposes."
                        )
                    else:
                        premises_text = "\n".join(f"- {p}" for p in core_premises_nl)
                        user_prompt = (
                            "The solver could not determine whether the conclusion is entailed by the premises.\n\n"
                            f"Premises:\n{premises_text}\n\n"
                            f"Conclusion:\n- {conclusion_nl}\n\n"
                            "Analyse briefly (in 1-2 sentences) why the relationship is indeterminate. "
                            "Start directly. What key information is missing?"
                        )
                    
                    explanation = logic_pipeline.llm_client.generate_text(
                        user_prompt,
                        system_prompt=system_prompt,
                        max_new_tokens=256
                    ).strip()
                except Exception as e:
                    print(f"Error generating human explanation: {e}")

            if not explanation or not explanation.strip():
                explanation = result.get("reasoning") or ""

            # If the explanation is just cited premises or list of rules, let's construct/use the CoT response 
            # if it exists, as it is a more descriptive and flowing natural language explanation.
            # However, for a single/multiple choice, if Z3 was unsat and we generated a simple cited premise string:
            # "Option A is logically supported by the cited premises..."
            # we want to ensure it reads nicely. If result has "cot" and explanation starts with "Option ",
            # we can combine them or construct a flowing explanation.
            if result.get("cot") and (not explanation.strip() or explanation.strip().startswith("Option ")):
                # Filter out raw rule/fact formatting from CoT to make it natural language
                clean_steps = []
                for step in result.get("cot", []):
                    # Remove formal logic tags if present
                    s = step.replace("Rule:", "").replace("Fact:", "").replace("Conclusion:", "").strip()
                    if s:
                        clean_steps.append(s)
                if clean_steps:
                    explanation = " ".join(clean_steps)
            
            if not explanation.strip():
                explanation = "No explanation generated."

            reasoning = None
            if result.get("cot"):
                reasoning = ReasoningObject(
                    type="fol"
                    if result.get("verification", {}).get("result") == z3.unsat
                    else "cot",
                    steps=result["cot"],
                )
            elif result.get("reasoning"):
                reasoning = ReasoningObject(
                    type="cot",
                    steps=[
                        line.strip()
                        for line in result["reasoning"].splitlines()
                        if line.strip()
                    ],
                )

            elapsed = time.time() - start_time
            print(
                f"[{request.query_id}] Type 1 processed in {elapsed:.2f}s. Answer: {answer}"
            )
            if _timing_enabled() and isinstance(result.get("_timings"), dict):
                print(
                    f"[{request.query_id}] Type 1 stage timings: "
                    f"{json.dumps(result['_timings'], ensure_ascii=False, sort_keys=True)}"
                )

            resp_items = [
                PredictResponseItem(
                    query_id=request.query_id,
                    answer=answer,
                    unit="",
                    explanation=explanation,
                    premises_used=premises_used,
                    reasoning=reasoning,
                ).model_dump(mode="json")
            ]
            print(f"[{request.query_id}] Response payload: {json.dumps(resp_items, ensure_ascii=False)}")
            return UTF8JSONResponse(content=resp_items)

        except Exception as e:
            print(f"[{request.query_id}] Error in Type 1 pipeline: {str(e)}")
            import traceback

            traceback.print_exc()
            resp_items = [
                PredictResponseItem(
                    query_id=request.query_id,
                    answer="Uncertain"
                    if "Uncertain" in request.options
                    else (request.options[0] if request.options else "Unknown"),
                    unit="",
                    explanation=f"Error occurred during logical reasoning pipeline execution: {str(e)}",
                    premises_used=[],
                    reasoning=None,
                ).model_dump(mode="json")
            ]
            print(f"[{request.query_id}] Response payload (fallback): {json.dumps(resp_items, ensure_ascii=False)}")
            return UTF8JSONResponse(content=resp_items)

    elif request.type == "type2":
        try:
            # 1. Create PhysicsTask
            task = PhysicsTask(question=request.query)

            # 2. Run Physics Pipeline
            # If using multi-LoRA vLLM, we target the specific adapters.
            # Otherwise (HF Router fallback), we use the single MODEL_NAME.
            is_multilora = "router.huggingface.co" not in VLLM_BASE_URL
            physics_model = "physics" if is_multilora else MODEL_NAME
            router_model = "fol_router" if is_multilora else MODEL_NAME

            try:
                eval_res = await asyncio.wait_for(
                    run_physics(
                        task,
                        model_name=physics_model,
                        router_model_name=router_model,
                        api_key=HF_API_KEY,
                        base_url=VLLM_BASE_URL,
                    ),
                    timeout=55.0
                )
            except asyncio.TimeoutError:
                print(f"[{request.query_id}] Type 2 pipeline timed out after 55 seconds. Returning fallback.")
                resp_items = [
                    PredictResponseItem(
                        query_id=request.query_id,
                        answer="0",
                        unit="",
                        explanation="Physics reasoning execution timed out after 55 seconds.",
                        premises_used=[],
                        reasoning=None,
                    ).model_dump()
                ]
                print(f"[{request.query_id}] Response payload (timeout fallback): {json.dumps(resp_items, ensure_ascii=False)}")
                return UTF8JSONResponse(content=resp_items)

            result = eval_res.result

            # 3. Parse and extract answer and unit
            ans_str = "0"
            unit_str = ""
            if result.model_answer:
                ans_val = result.model_answer.get("ans")
                unit_val = result.model_answer.get("unit")

                if isinstance(ans_val, list):
                    ans_str = "; ".join(str(x) for x in ans_val)
                else:
                    ans_str = str(ans_val) if ans_val is not None else "0"

                def clean_unit(u):
                    u_str = str(u) if u is not None else ""
                    u_str = u_str.replace("μ", "u").replace("µ", "u").replace("Ω", "ohm").replace("Ohm", "ohm")
                    if u_str == "-":
                        u_str = ""
                    return u_str

                if isinstance(unit_val, list):
                    unit_str = "; ".join(clean_unit(u) for u in unit_val)
                else:
                    unit_str = clean_unit(unit_val)

            # 4. Form explanation and structured reasoning
            explanation = ""
            reasoning_steps = []

            # First, try to extract reasoning steps and a fallback explanation from raw response JSON
            parsed_reasoning_steps = None
            parsed_explanation = None
            try:
                data = json.loads(result.raw_response.strip())
                thought = data.get("thought", "")
                physics_analysis = data.get("physics_analysis", [])
                algebraic_reasoning = data.get("algebraic_reasoning", [])

                # Build reasoning steps: thought + physics_analysis + algebraic_reasoning
                thought_list = [thought] if isinstance(thought, str) else (thought or [])
                thought_list = [t for t in thought_list if t]
                parsed_reasoning_steps = thought_list + physics_analysis + algebraic_reasoning

                # Build parsed explanation fallback
                explanation_parts = []
                if thought:
                    explanation_parts.append(thought)
                if physics_analysis:
                    explanation_parts.append(
                        "Physics Analysis:\n"
                        + "\n".join(f"- {step}" for step in physics_analysis)
                    )
                if algebraic_reasoning:
                    explanation_parts.append(
                        "Algebraic Reasoning:\n"
                        + "\n".join(f"- {step}" for step in algebraic_reasoning)
                    )
                parsed_explanation = "\n\n".join(explanation_parts)
            except Exception:
                pass

            # Determine final explanation (prefer result.explanation)
            if result.explanation and result.explanation.strip():
                explanation = result.explanation.strip()
            elif parsed_explanation:
                explanation = parsed_explanation
            else:
                explanation = (
                    result.raw_response
                    or result.error
                    or "Executed python code to compute answer."
                )

            if not explanation.strip():
                explanation = f"Calculated answer: {ans_str}."

            # Determine final reasoning steps (prefer parsed JSON steps)
            if parsed_reasoning_steps is not None:
                reasoning_steps = parsed_reasoning_steps
            else:
                reasoning_steps = [
                    line.strip() for line in explanation.splitlines() if line.strip()
                ]

            reasoning = None
            if reasoning_steps:
                reasoning = ReasoningObject(type="cot", steps=reasoning_steps)

            elapsed = time.time() - start_time
            print(
                f"[{request.query_id}] Type 2 processed in {elapsed:.2f}s. Answer: {ans_str} {unit_str}"
            )

            resp_items = [
                PredictResponseItem(
                    query_id=request.query_id,
                    answer=ans_str,
                    unit=unit_str,
                    explanation=explanation,
                    premises_used=[],
                    reasoning=reasoning,
                ).model_dump()
            ]
            print(f"[{request.query_id}] Response payload: {json.dumps(resp_items, ensure_ascii=False)}")
            return UTF8JSONResponse(content=resp_items)

        except Exception as e:
            print(f"[{request.query_id}] Error in Type 2 pipeline: {str(e)}")
            import traceback

            traceback.print_exc()
            resp_items = [
                PredictResponseItem(
                    query_id=request.query_id,
                    answer="0",
                    unit="",
                    explanation=f"Error occurred during physics pipeline execution: {str(e)}",
                    premises_used=[],
                    reasoning=None,
                ).model_dump()
            ]
            print(f"[{request.query_id}] Response payload (fallback): {json.dumps(resp_items, ensure_ascii=False)}")
            return UTF8JSONResponse(content=resp_items)

    else:
        raise HTTPException(
            status_code=400, detail=f"Invalid request type: {request.type}"
        )


if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8080, reload=True)
