import os
import modal

# Define the Modal App
app = modal.App("exact-api-server")

# Define the container image with required dependencies and code directories
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "fastapi",
        "uvicorn",
        "pydantic",
        "requests",
        "z3-solver",
        "python-dotenv",
        "sympy",
        "pint",
        "openai",
        "torch",
        "transformers",
        "google-genai",
        "cowsay"
    )
    .add_local_dir("src", remote_path="/app/src")
    .add_local_dir("data", remote_path="/app/data")
    .add_local_file(".env", remote_path="/app/.env")
)

@app.function(
    image=image,
    cpu=1.0,
    memory=2048,
    secrets=[modal.Secret.from_dotenv()],
    min_containers=4,  # Keep 1 container warm for testing
)
@modal.asgi_app()
def api_server():
    import sys
    
    # Add /app to sys.path to ensure absolute src.* imports resolve correctly
    if "/app" not in sys.path:
        sys.path.append("/app")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="/app/.env")
    
    # Set remote vLLM endpoint configuration
    vllm_url = os.getenv("VLLM_BASE_URL", "https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run/v1")
    os.environ["VLLM_BASE_URL"] = vllm_url
    os.environ["MODEL_NAME"] = "fol_router"
    
    print("=" * 60)
    # Import the FastAPI application from our src/api_server.py
    from src.api_server import app as fastapi_app
    print("FastAPI app loaded successfully inside Modal container.")
    print("=" * 60)
    
    return fastapi_app
