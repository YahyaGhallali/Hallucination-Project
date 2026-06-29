"""
Project Veracity: Automated Hallucination Evaluation (Phase 1)
Script: eval_runner_perturbed.py

This script implements the Inference Engine of the evaluation pipeline for the perturbed evaluation dataset.
It reads the perturbed evaluation set, queries the target model (Gemma 2 2B IT) using NVIDIA API integration,
enforces strict system context boundaries, and records generations for subsequent auditing.

Core architecture:
1. Orchestrates execution of the target model with a deterministic temperature setting (0.01).
2. Intercepts and logs execution states.
3. Implements rate limiting and backoff routines to gracefully scale requests.
"""

import os
import json
import sys
import time
from dotenv import load_dotenv
from openai import OpenAI
import openai

# Define script directories and file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "data", "perturbed_eval_set.jsonl")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "generation_outputs_perturbed.jsonl")

# Target evaluation model configurations
MODEL_NAME = 'google/gemma-2-2b-it'

# Load API credentials from the project root .env file
ENV_PATH = os.path.join(SCRIPT_DIR, "..", ".env")
load_dotenv(ENV_PATH)

def log(msg, level="INFO"):
    """
    Standardized logger displaying messages to stdout.
    
    Args:
        msg (str): Message payload.
        level (str): Category tag (e.g. INFO, WARNING, ERROR, SUCCESS).
    """
    print(f"[{level}] {msg}")

def generate_with_retry(client, model, messages, temperature=0.01, max_retries=5, initial_delay=3.0, delay_between_calls=1.0):
    """
    Queries OpenAI API endpoint with rate limiting support and backoff logic.
    
    Sleeps for a politeness delay before executing to prevent aggressive API hitting.
    Catches rate limiting exceptions (429) and performs exponential backoff retries.
    
    Args:
        client (OpenAI): Configured OpenAI client.
        model (str): Name of the target model.
        messages (list): Chat history format messages.
        temperature (float): Generation temperature.
        max_retries (int): Maximum number of retry attempts.
        initial_delay (float): Starting backoff delay in seconds.
        delay_between_calls (float): Pause in seconds before every query to avoid triggering limits.
        
    Returns:
        ChatCompletion: Generation object returned by the API.
    """
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
                delay *= 2  # Exponential backoff scaling
            else:
                raise e

def run_evaluation():
    """
    Executes batch inference over the perturbed evaluation set:
    1. Validates presence of the NVIDIA API key.
    2. Initializes OpenAI client pointing to the NVIDIA integrated URL.
    3. Reads evaluation records from `perturbed_eval_set.jsonl`.
    4. Submits prompt instructions constraining output to reference context.
    5. Saves inference results to `generation_outputs_perturbed.jsonl`.
    """
    # Retrieve and validate NVIDIA API key
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        log("NVIDIA_API_KEY environment variable not found. Please ensure it is defined in your .env or environment.", "ERROR")
        sys.exit(1)

    # Initialize client targeting NVIDIA's API endpoint
    log("Initializing OpenAI client for NVIDIA API...")
    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
    except Exception as e:
        log(f"Failed to initialize OpenAI Client: {e}", "ERROR")
        sys.exit(1)

    # Verify that input evaluation file exists
    if not os.path.exists(INPUT_FILE):
        log(f"Input file not found at: {INPUT_FILE}. Please generate perturbed_eval_set.jsonl first.", "ERROR")
        sys.exit(1)

    # Load records
    log(f"Reading perturbed evaluation set from {INPUT_FILE}...")
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
    
    # Verify or create output folder structure
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Loop through evaluation items and execute inference
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
            for idx, item in enumerate(items):
                knowledge = item.get('knowledge', '')
                question = item.get('question', '')
                
                log(f"Processing item {idx+1}/{len(items)} (ID: {item.get('id')})...")
                
                # Enforce strict context limitations using prompt instructions
                system_instruction = (
                    "You are a strict, factual assistant. Answer the user's question using ONLY the provided Context. "
                    "If the answer cannot be found in the context, say 'I do not know'."
                )
                
                # Combine system instructions, knowledge, and question as user prompt
                prompt = f"{system_instruction}\n\nContext: {knowledge}\n\nQuestion: {question}"
                
                messages = [
                    {"role": "user", "content": prompt}
                ]
                
                # Query target model
                try:
                    response = generate_with_retry(
                        client=client,
                        model=MODEL_NAME,
                        messages=messages,
                        temperature=0.01
                    )
                    model_generated_answer = response.choices[0].message.content or ""
                except Exception as e:
                    log(f"API generation error on item {idx+1} (ID: {item.get('id')}): {e}", "ERROR")
                    model_generated_answer = f"ERROR: {e}"
                
                # Compile records to standardized target structure
                output_row = {
                    'id': item.get('id'),
                    'context': knowledge,
                    'question': question,
                    'ground_truth': item.get('right_answer', ''),
                    'known_hallucination_baseline': item.get('hallucinated_answer', ''),
                    'model_generated_answer': model_generated_answer.strip()
                }
                
                # Save item immediately to preserve state on execution interruptions
                out_f.write(json.dumps(output_row, ensure_ascii=False) + '\n')
                
        log(f"Inference completed successfully. Outputs saved to {OUTPUT_FILE}", "SUCCESS")
    except Exception as e:
        log(f"Failed to write outputs to file: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    run_evaluation()
