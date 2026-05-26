import z3
from z3 import unsat, sat
import torch
from src.logic.reasoning.verifier import verify_with_z3

class ReasoningPipeline:
    """
    Pipeline that takes First-Order Logic (FOL) formulas, verifies them mathematically
    using Z3 (via contradiction proof), and generates step-by-step natural language reasoning
    explaining the Z3 result (unsat core or counterexample).
    
    Supports both local execution (via Hugging Face LoRA models) and remote API execution.
    """
    def __init__(self, use_local: bool = True, model_dir: str = None, llm_client = None):
        self.use_local = use_local
        self.model_dir = model_dir
        self.llm_client = llm_client
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None

    def load_local_model(self):
        """Loads Hugging Face tokenizer and PEFT LoRA model locally with NF4 4-bit quantization."""
        if not self.use_local:
            return
            
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel
        from pathlib import Path
        
        # Resolve default model directory if none provided
        if not self.model_dir:
            root_dir = Path(__file__).resolve().parents[3]
            self.model_dir = str(root_dir / "results")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        base_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen3-8B",
            quantization_config=bnb_config if torch.cuda.is_available() else None,
            device_map="cuda:0" if torch.cuda.is_available() else None,
            trust_remote_code=True,
            attn_implementation="sdpa" if torch.cuda.is_available() else None
        )
        
        self.model = PeftModel.from_pretrained(base_model, self.model_dir)
        self.model.eval()

    def _generate_text(self, system_prompt: str, user_prompt: str, max_new_tokens: int = 512) -> str:
        """Helper to generate text using either the local model or the LLM client."""
        if self.use_local:
            if not self.model:
                self.load_local_model()
                
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            chat_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            inputs = self.tokenizer(chat_prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    eos_token_id=self.tokenizer.eos_token_id,
                    pad_token_id=self.tokenizer.pad_token_id
                )
                
            response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            return response.strip()
        else:
            if not self.llm_client:
                raise ValueError("An LLMClient instance must be provided when use_local=False")
            
            # Temporarily override LLMClient's system prompt if necessary
            orig_system_prompt = self.llm_client.system_prompt
            self.llm_client.system_prompt = system_prompt
            
            try:
                res = self.llm_client.generate(user_prompt, max_tokens=max_new_tokens)
                return res["content"]
            finally:
                self.llm_client.system_prompt = orig_system_prompt

    def verify(self, premises_fol: list[str], conclusion_fol: str, negate_conclusion: bool = True) -> dict:
        """Parses FOL formulas, tracks them in Z3 solver, and checks for entailment via contradiction."""
        return verify_with_z3(premises_fol, conclusion_fol, negate_conclusion=negate_conclusion)

    def generate_reasoning(self, premises_nl: list[str], conclusion_nl: str, verification: dict) -> str:
        """Generates step-by-step reasoning explaining the Z3 verification result."""
        result = verification["result"]
        
        if result == unsat:
            # Extract indices from unsat core
            core_indices = []
            for var_str in verification["unsat_core"]:
                if var_str.startswith("p_"):
                    try:
                        idx = int(var_str.split("_")[1]) - 1
                        core_indices.append(idx)
                    except ValueError:
                        pass
            core_indices.sort()
            
            # Format core premises list
            core_premises_nl = []
            for idx in core_indices:
                core_premises_nl.append(f"- Premise {idx+1}: {premises_nl[idx]}")
            core_premises_text = "\n".join(core_premises_nl) if core_premises_nl else "\n".join(f"- {p}" for p in premises_nl)
            
            user_prompt = (
                f"We have proven that the following conclusion is LOGICALLY CORRECT (entailed) by the premises using formal verification (Z3 SMT solver).\n\n"
                f"Premises that directly contribute to the proof:\n"
                f"{core_premises_text}\n\n"
                f"Conclusion to prove:\n"
                f"- {conclusion_nl}\n\n"
                f"Explain step-by-step in clear, natural language why the premises logically entail the conclusion. "
                f"Keep the explanation concise, professional, and focused on the logical steps."
            )
        elif result == sat:
            model_str = str(verification["model"])
            user_prompt = (
                f"We have found that the following conclusion is NOT logically guaranteed (not entailed) by the premises.\n"
                f"The SMT solver found a counterexample scenario where all premises are TRUE, but the conclusion is FALSE.\n\n"
                f"Premises:\n"
                f"{chr(10).join(f'- {p}' for p in premises_nl)}\n\n"
                f"Conclusion to check:\n"
                f"- {conclusion_nl}\n\n"
                f"Counterexample scenario (Z3 Model):\n"
                f"{model_str}\n\n"
                f"Explain in clear, natural language why this counterexample shows that the conclusion is not guaranteed to be true "
                f"under the given premises."
            )
        else:
            user_prompt = (
                f"We could not determine if the conclusion is logically guaranteed by the premises.\n\n"
                f"Premises:\n"
                f"{chr(10).join(f'- {p}' for p in premises_nl)}\n\n"
                f"Conclusion:\n"
                f"- {conclusion_nl}\n\n"
                f"Provide a brief logical analysis of these statements and any potential missing links."
            )
            
        system_prompt = (
            "You are a logical reasoning assistant. Your task is to explain the logical deduction step-by-step in clear, natural language."
        )
        
        return self._generate_text(system_prompt, user_prompt, max_new_tokens=512)
