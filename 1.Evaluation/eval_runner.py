import os
import json
import sys
import time
from dotenv import load_dotenv
from openai import OpenAI
import openai

# Dynamically resolve directory of this script to keep paths robust
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "data", "eval_set.jsonl")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "generation_outputs.jsonl")
MODEL_NAME = 'meta/llama-3.1-8b-instruct'

# Load environment variables explicitly from .env in the project root
ENV_PATH = os.path.join(SCRIPT_DIR, "..", ".env")
load_dotenv(ENV_PATH)

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def generate_with_retry(client, model, messages, temperature=0.0, max_retries=5, initial_delay=3.0, delay_between_calls=1.0):
    """Executes model generation using OpenAI client with proactive rate-limiting sleep and exponential backoff for 429s."""
    if delay_between_calls > 0:
        time.sleep(delay_between_calls)
        
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return response
        except Exception as e:
            err_str = str(e)
            is_rate_limit = (
                isinstance(e, openai.RateLimitError) or
                "429" in err_str or
                "rate limit" in err_str.lower() or
                "resource_exhausted" in err_str.lower() or
                "quota" in err_str.lower()
            )
            
            if is_rate_limit and attempt < max_retries - 1:
                log(f"Rate limit (429) hit. Retrying in {delay:.1f} seconds... (Attempt {attempt + 1}/{max_retries})", "WARNING")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                raise e

def run_evaluation():
    # Verify API key is present in environment after loading .env
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        log("NVIDIA_API_KEY environment variable not found. Please ensure it is defined in your .env or environment.", "ERROR")
        sys.exit(1)

    # Initialize OpenAI client pointed to NVIDIA's base URL
    log("Initializing OpenAI client for NVIDIA API...")
    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
    except Exception as e:
        log(f"Failed to initialize OpenAI Client: {e}", "ERROR")
        sys.exit(1)

    # Check input file exists
    if not os.path.exists(INPUT_FILE):
        log(f"Input file not found at: {INPUT_FILE}. Please run download_data.py first.", "ERROR")
        sys.exit(1)

    # Read inputs
    log(f"Reading evaluation set from {INPUT_FILE}...")
    items = []
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))
    except Exception as e:
        log(f"Failed to read input file: {e}", "ERROR")
        sys.exit(1)

    log(f"Found {len(items)} evaluation samples. Starting inference using {MODEL_NAME}...")
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Open output file for writing
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
            for idx, item in enumerate(items):
                knowledge = item.get('knowledge', '')
                question = item.get('question', '')
                
                # Build prompt combining background knowledge and question
                prompt = f"Context: {knowledge}\n\nQuestion: {question}"
                
                log(f"Processing item {idx+1}/{len(items)} (ID: {item.get('id')})...")
                
                system_instruction = (
                    "You are a strict, factual assistant. Answer the user's question using ONLY the provided Context. "
                    "If the answer cannot be found in the context, say 'I do not know'."
                )
                
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
                
                # Execute generation using the retry helper
                try:
                    response = generate_with_retry(
                        client=client,
                        model=MODEL_NAME,
                        messages=messages,
                        temperature=0.0
                    )
                    model_generated_answer = response.choices[0].message.content or ""
                except Exception as e:
                    log(f"API generation error on item {idx+1} (ID: {item.get('id')}): {e}", "ERROR")
                    model_generated_answer = f"ERROR: {e}"
                
                # Create output row mapping the original fields to requirements
                output_row = {
                    'id': item.get('id'),
                    'context': knowledge,
                    'question': question,
                    'ground_truth': item.get('right_answer', ''),
                    'known_hallucination_baseline': item.get('hallucinated_answer', ''),
                    'model_generated_answer': model_generated_answer.strip()
                }
                
                # Write each row as a self-contained JSON string on its own line
                out_f.write(json.dumps(output_row, ensure_ascii=False) + '\n')
                
        log(f"Inference completed successfully. Outputs saved to {OUTPUT_FILE}", "SUCCESS")
    except Exception as e:
        log(f"Failed to write outputs to file: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    run_evaluation()
