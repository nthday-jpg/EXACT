# Monkey-patch pathlib.Path.read_text to prevent CP1252 decoder errors on Windows
import pathlib
original_read_text = pathlib.Path.read_text
def patched_read_text(self, encoding=None, errors=None):
    if encoding is None:
        encoding = 'utf-8'
    return original_read_text(self, encoding=encoding, errors=errors)
pathlib.Path.read_text = patched_read_text

import os
import sys
import json
import argparse
import pandas as pd
import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from trl import SFTTrainer, SFTConfig

def load_logic_dataset(filepath: str) -> list[dict]:
    """Loads and formats the logic-based dataset into conversational samples."""
    print(f"Loading logic dataset from: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    samples = []
    for item in data:
        premises_nl = item.get("premises-NL", [])
        premises_str = "\n".join([f"- {p}" for p in premises_nl])
        
        questions = item.get("questions", [])
        answers = item.get("answers", [])
        explanations = item.get("explanation", [])
        
        # Zip questions, answers, and explanations
        for question, answer, explanation in zip(questions, answers, explanations):
            system_prompt = "You are a logical reasoning assistant. Solve the user's question by outputting a JSON object with 'answer' and 'explanation' fields."
            user_content = f"Context (Premises):\n{premises_str}\n\nQuestion: {question}"
            
            # Format target output as a structured JSON string
            assistant_content = json.dumps({
                "answer": answer.strip(),
                "explanation": explanation.strip()
            }, ensure_ascii=False)
            
            samples.append({
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content}
                ]
            })
            
    print(f"Loaded {len(samples)} logical reasoning training instances.")
    return samples

def load_physics_dataset(filepath: str) -> list[dict]:
    """Loads and formats the physics dataset into conversational samples."""
    print(f"Loading physics dataset from: {filepath}")
    df = pd.read_csv(filepath)
    
    samples = []
    for _, row in df.iterrows():
        question = row.get("question", "")
        cot = row.get("cot", "")
        answer = row.get("answer", "")
        unit = row.get("unit", "")
        
        # Skip invalid or empty questions
        if pd.isna(question) or str(question).strip() == "":
            continue
            
        system_prompt = "You are a physics assistant. Solve the user's question by outputting a JSON object with 'answer' and 'explanation' fields."
        user_content = f"Question: {question}"
        
        # Clean answer and append unit if available
        ans_str = str(answer).strip()
        if pd.notna(unit) and str(unit).strip() not in ["", "-"]:
            ans_str = f"{ans_str} {str(unit).strip()}"
            
        assistant_content = json.dumps({
            "answer": ans_str,
            "explanation": str(cot).strip()
        }, ensure_ascii=False)
        
        samples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content}
            ]
        })
        
    print(f"Loaded {len(samples)} physics training instances.")
    return samples

def main():
    parser = argparse.ArgumentParser(description="EXACT LLM Fine-Tuning Pipeline")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen2.5-7B-Instruct", help="Pretrained model ID on Hugging Face")
    parser.add_argument("--dataset_type", type=str, choices=["logic", "physics", "both"], default="both", help="Dataset to train on")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=1, help="Training batch size per device")
    parser.add_argument("--grad_accum", type=int, default=8, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora_r", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha parameter")
    parser.add_argument("--max_length", type=int, default=512, help="Maximum sequence length")
    parser.add_argument("--output_dir", type=str, default="./results", help="Directory to save checkpoint adapters")
    parser.add_argument("--val_split", type=float, default=0.1, help="Validation split fraction")
    parser.add_argument("--test_prompt", type=str, default=None, help="If provided, run inference on this prompt and exit")
    parser.add_argument("--max_steps", type=int, default=-1, help="If > 0, overrides epoch-based training length")
    args = parser.parse_args()

    # Determine root directory dynamically
    root_dir = pathlib.Path(__file__).resolve().parents[3]
    
    # Resolve dataset paths
    logic_path = root_dir / "data" / "processed" / "logic_based.json"
    if not logic_path.exists():
        logic_path = root_dir / "data" / "logic_based.json"

    # 1. Load data
    raw_samples = []
    if args.dataset_type in ["logic", "both"] and logic_path.exists():
        raw_samples.extend(load_logic_dataset(str(logic_path)))
        
    if not raw_samples:
        print("Error: No training data found. Make sure data files exist in the data/ directory.")
        sys.exit(1)
        
    print(f"Total training dataset size: {len(raw_samples)} instances.")
    
    # 2. Setup Quantization and Tokenizer
    print(f"Initializing model and tokenizer for {args.model_id}...")
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16,
        bnb_4bit_use_double_quant=True
    )
    
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    # 3. Handle single inference test if requested
    if args.test_prompt:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Running baseline inference on device: {device}")
        
        # Load baseline model in 4-bit (or normal if CPU)
        model = AutoModelForCausalLM.from_pretrained(
            args.model_id,
            quantization_config=bnb_config if device == "cuda" else None,
            device_map="auto" if device == "cuda" else None,
            trust_remote_code=True
        )
        
        messages = [
            {"role": "system", "content": "You are a helpful reasoning assistant."},
            {"role": "user", "content": args.test_prompt}
        ]
        
        inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model.generate(inputs, max_new_tokens=256, eos_token_id=tokenizer.eos_token_id)
        
        response = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
        print("\n--- Model Response ---")
        print(response)
        print("----------------------")
        return

    # 4. Prepare HF Dataset and Chat Templates
    dataset = Dataset.from_list(raw_samples)
    
    # Map chat template to raw strings for training
    def apply_template(batch):
        texts = []
        for messages in batch["messages"]:
            # Format completion target with EOF/EOS token
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        return {"text": texts}
        
    dataset = dataset.map(apply_template, batched=True, remove_columns=["messages"])
    
    # Shuffle and split train/val
    dataset = dataset.shuffle(seed=42)
    split_dataset = dataset.train_test_split(test_size=args.val_split)
    train_dataset = split_dataset["train"]
    val_dataset = split_dataset["test"]
    
    print(f"Train split size: {len(train_dataset)}, Val split size: {len(val_dataset)}")

    # 5. Load model with PEFT QLoRA
    device_map = "auto" if torch.cuda.is_available() else None
    print(f"Loading base model to device: {device_map}")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        quantization_config=bnb_config if torch.cuda.is_available() else None,
        device_map=device_map,
        trust_remote_code=True
    )
    
    # Setup for LoRA training
    if torch.cuda.is_available():
        model = prepare_model_for_kbit_training(model)
        
    # Standard target modules for Qwen/Llama attention + MLP
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    
    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=target_modules,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 6. Configure SFT Training Arguments
    sft_config = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        eval_strategy="steps" if args.max_steps <= 0 else "no",
        eval_steps=100,
        save_strategy="steps" if args.max_steps <= 0 else "no",
        save_steps=100,
        learning_rate=args.lr,
        fp16=not (torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        logging_steps=5 if args.max_steps > 0 else 10,
        optim="paged_adamw_8bit" if torch.cuda.is_available() else "adamw_torch",
        gradient_checkpointing=True if torch.cuda.is_available() else False,
        report_to="none",
        load_best_model_at_end=True if args.max_steps <= 0 else False,
        metric_for_best_model="loss" if args.max_steps <= 0 else None,
        greater_is_better=False,
        save_total_limit=2,
        dataset_text_field="text",
        max_length=args.max_length
    )

    # 7. SFT Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        args=sft_config
    )

    # 8. Run Training
    print("Starting SFT training pipeline...")
    trainer.train()
    
    # Save the final adapter weights and tokenizer
    print(f"Saving final adapter model to {args.output_dir}...")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("Fine-tuning pipeline completed successfully!")

if __name__ == "__main__":
    main()
