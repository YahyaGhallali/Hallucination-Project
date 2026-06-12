import os
import json
import sys
import time
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI
import openai

# Dynamically resolve directory of this script to keep paths robust
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "data", "generation_outputs.jsonl")
MODEL_NAME = 'meta/llama-3.1-70b-instruct'

# Load environment variables explicitly from .env in the project root
ENV_PATH = os.path.join(SCRIPT_DIR, "..", ".env")
load_dotenv(ENV_PATH)

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

# 1. Define the Pydantic schema for structured outputs
class AuditVerdict(BaseModel):
    reasoning: str = Field(
        description="Analyze the claims step-by-step against the reference context to check for alignment."
    )
    is_hallucinated: bool = Field(
        description="True if the answer contains unverified facts or contradictions; False otherwise."
    )

def generate_verdict_with_retry(client, model, messages, json_schema, max_retries=5, initial_delay=5.0, delay_between_calls=2.0):
    """Executes model generation using OpenAI client, attempting NVIDIA's guided_json, falling back to JSON mode, with retry logic for 429s."""
    if delay_between_calls > 0:
        time.sleep(delay_between_calls)
        
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            # Method 1: Try using Nvidia's nvext.guided_json for strict JSON validation
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.0,
                    extra_body={
                        "nvext": {
                            "guided_json": json_schema
                        }
                    }
                )
                return response.choices[0].message.content
            except Exception as e_nv:
                # Method 2: Fallback to standard OpenAI JSON mode
                log(f"NVIDIA guided_json extension failed ({e_nv}). Falling back to standard JSON mode...", "WARNING")
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
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

def run_judge():
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
        log(f"Input file not found at: {INPUT_FILE}. Please run eval_runner.py first to generate outputs.", "ERROR")
        sys.exit(1)

    # Read inputs
    log(f"Reading generation outputs from {INPUT_FILE}...")
    records = []
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except Exception as e:
        log(f"Failed to read input file: {e}", "ERROR")
        sys.exit(1)

    log(f"Found {len(records)} outputs to evaluate. Starting audit using {MODEL_NAME}...")

    total_evaluated = 0
    hallucinated_count = 0
    faithful_count = 0
    json_schema = AuditVerdict.model_json_schema()

    for idx, record in enumerate(records):
        context = record.get('context', '')
        question = record.get('question', '')
        model_answer = record.get('model_generated_answer', '')

        # Build prompt combining context, question, and generated answer
        prompt = (
            f"Reference Context:\n{context}\n\n"
            f"User Question:\n{question}\n\n"
            f"Model Generated Answer:\n{model_answer}\n\n"
            f"Task: Review the Model Generated Answer against the Reference Context. Analyze step-by-step and determine if the answer contains any hallucinations."
        )

        log(f"Auditing item {idx+1}/{len(records)} (ID: {record.get('id')})...")

        system_instruction = (
            "You are a strict, factual assistant. Answer the user's question by reviewing the Model Generated Answer against the Reference Context. "
            "You must return a JSON object containing exactly two fields:\n"
            '- "reasoning": str (analyze the claims step-by-step against the reference context)\n'
            '- "is_hallucinated": bool (True if the answer contains unverified facts or contradictions, False otherwise)\n'
            "Return ONLY the raw JSON object, without markdown formatting or code blocks."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]

        try:
            # Call generation API with structured output configuration
            verdict_text = generate_verdict_with_retry(
                client=client,
                model=MODEL_NAME,
                messages=messages,
                json_schema=json_schema
            )

            # Strip any markdown wrappers if the model generated them despite instructions
            verdict_text = verdict_text.strip()
            if verdict_text.startswith("```json"):
                verdict_text = verdict_text[7:]
            if verdict_text.startswith("```"):
                verdict_text = verdict_text[3:]
            if verdict_text.endswith("```"):
                verdict_text = verdict_text[:-3]
            verdict_text = verdict_text.strip()

            verdict_data = json.loads(verdict_text)
            verdict = AuditVerdict(**verdict_data)

            is_hallucinated = verdict.is_hallucinated
            reasoning = verdict.reasoning

            total_evaluated += 1
            if is_hallucinated:
                hallucinated_count += 1
                log(f"Verdict: HALLUCINATED | Reasoning: {reasoning[:80]}...")
            else:
                faithful_count += 1
                log(f"Verdict: FAITHFUL | Reasoning: {reasoning[:80]}...")

        except Exception as e:
            log(f"Error auditing item {idx+1} (ID: {record.get('id')}): {e}", "ERROR")

    # Print a final summary block
    log("="*60)
    log("EVALUATION RUN SUMMARY", "SUCCESS")
    log("="*60)
    log(f"Total Records Evaluated: {total_evaluated}")
    log(f"Faithful (Non-Hallucinated) Count: {faithful_count}")
    log(f"Hallucinated Count: {hallucinated_count}")
    
    hallucination_rate = 0.0
    if total_evaluated > 0:
        hallucination_rate = (hallucinated_count / total_evaluated) * 100
        
    log(f"Model Baseline Hallucination Rate %: {hallucination_rate:.2f}%")
    log("="*60)

if __name__ == "__main__":
    run_judge()
