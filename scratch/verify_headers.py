import os
from dotenv import load_dotenv
load_dotenv()

from src.llm.llm_client import LLMClient

print("--- Testing Modal Endpoint ---")
modal_client = LLMClient(
    use_local=False,
    api_key=None,
    base_url="https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run/v1"
)
modal_headers = modal_client.client.default_headers
print("Modal Client headers contain Modal-Key:", "Modal-Key" in modal_headers)
print("Modal Client headers contain Modal-Secret:", "Modal-Secret" in modal_headers)
print("Modal API Key:", modal_client.api_key)

print("\n--- Testing Hugging Face Endpoint ---")
# Temporarily clear HF_API_KEY to test standard behavior of raising RuntimeError
saved_hf_key = os.environ.get("HF_API_KEY")
if "HF_API_KEY" in os.environ:
    del os.environ["HF_API_KEY"]

try:
    hf_client = LLMClient(
        use_local=False,
        api_key=None,
        base_url="https://router.huggingface.co/v1"
    )
    print("HF Client headers contain Modal-Key:", "Modal-Key" in hf_client.client.default_headers)
except RuntimeError as e:
    print("HF Client successfully caught missing API key:", e)

# Restore
if saved_hf_key:
    os.environ["HF_API_KEY"] = saved_hf_key
