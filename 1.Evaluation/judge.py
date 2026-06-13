"""
Project Veracity: Automated Hallucination Evaluation (Phase 1)
Script: judge.py

This script implements the LLM-as-a-Judge verification protocol. It reads the model-generated
answers from `data/generation_outputs.jsonl`, prompts a stronger evaluator model (Llama-3.1-70b-instruct)
to audit those answers against the reference context, and outputs structured audit verdicts.

Key features:
1. Enforces structured output shapes using Pydantic schemas.
2. Utilizes NVIDIA's guided_json schema extension, falling back to standard JSON mode with manual stripping.
3. Implements rate-limit retry handlers with exponential backoff.
4. Exporting summary metrics and detailed logs to JSON and Markdown reports without emojis.
"""

import os
import json
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI
import openai

# Define script directories and file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "data", "generation_outputs.jsonl")
MODEL_NAME = 'meta/llama-3.1-70b-instruct'

# Load API credentials from the project root .env file
ENV_PATH = os.path.join(SCRIPT_DIR, "..", ".env")
load_dotenv(ENV_PATH)

def log(msg, level="INFO"):
    """
    Helper function to print formatted logs to stdout.
    
    Args:
        msg (str): Message to display.
        level (str): Category prefix (e.g. INFO, WARNING, ERROR, SUCCESS).
    """
    print(f"[{level}] {msg}")

class AuditVerdict(BaseModel):
    """
    Pydantic schema defining the structured outputs returned by the judge model.
    """
    reasoning: str = Field(
        description="A step-by-step factuality analysis comparing target model claims against the reference context."
    )
    is_hallucinated: bool = Field(
        description="Boolean indicating whether the answer contains unverified facts, unsupported inferences, or contradictions."
    )

def generate_verdict_with_retry(client, model, messages, json_schema, max_retries=5, initial_delay=5.0, delay_between_calls=2.0):
    """
    Executes model generation using standard and guided JSON decoding configurations with robust 429 retries.
    
    This function handles transient rate-limiting issues (HTTP 429) using an exponential backoff strategy.
    It attempts to request structured outputs via the NVIDIA-specific `guided_json` extension.
    If the extension fails, it falls back to standard OpenAI JSON mode and strips code blocks.
    
    Args:
        client (OpenAI): OpenAI client instance.
        model (str): Name of the evaluator model.
        messages (list): Chat history format messages.
        json_schema (dict): Schema to enforce.
        max_retries (int): Maximum number of retry attempts.
        initial_delay (float): Starting backoff delay in seconds.
        delay_between_calls (float): Rate-limit prevention pause between consecutive API queries.
        
    Returns:
        str: Raw JSON output of the model verdict.
    """
    if delay_between_calls > 0:
        time.sleep(delay_between_calls)
        
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            # First attempt: Try NVIDIA guided JSON extension
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
                # Fallback attempt: Standard OpenAI JSON mode
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
                delay *= 2  # Exponential backoff scaling
            else:
                raise e

def run_judge():
    """
    Executes the LLM-as-a-Judge verification pipeline:
    1. Validates presence of the NVIDIA API credential.
    2. Reads target outputs from `generation_outputs.jsonl`.
    3. Runs individual evaluations through Llama 3.1 70B under strict JSON rubrics.
    4. Logs verdicts to stdout.
    5. Computes statistics (hallucination rate).
    6. Outputs structured files (JSON & MD) summarizing the results professionally.
    """
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        log("NVIDIA_API_KEY environment variable not found. Please ensure it is defined in your .env or environment.", "ERROR")
        sys.exit(1)

    log("Initializing OpenAI client for NVIDIA API...")
    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
    except Exception as e:
        log(f"Failed to initialize OpenAI Client: {e}", "ERROR")
        sys.exit(1)

    if not os.path.exists(INPUT_FILE):
        log(f"Input file not found at: {INPUT_FILE}. Please run eval_runner.py first to generate outputs.", "ERROR")
        sys.exit(1)

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
    verdicts_list = []

    # Loop through each output item
    for idx, record in enumerate(records):
        context = record.get('context', '')
        question = record.get('question', '')
        model_answer = record.get('model_generated_answer', '')

        # Build prompt incorporating context, question, and candidate answer
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
            # Query the evaluator API
            verdict_text = generate_verdict_with_retry(
                client=client,
                model=MODEL_NAME,
                messages=messages,
                json_schema=json_schema
            )

            # Clean and isolate the raw JSON text from markdown wrappers if the model generated them
            verdict_text = verdict_text.strip()
            if verdict_text.startswith("```json"):
                verdict_text = verdict_text[7:]
            if verdict_text.startswith("```"):
                verdict_text = verdict_text[3:]
            if verdict_text.endswith("```"):
                verdict_text = verdict_text[:-3]
            verdict_text = verdict_text.strip()

            # Parse and validate schema matching
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

            # Store the resulting data for compilation
            verdicts_list.append({
                "id": record.get('id'),
                "question": question,
                "context": context,
                "ground_truth": record.get('ground_truth', ''),
                "model_generated_answer": model_answer,
                "reasoning": reasoning,
                "is_hallucinated": is_hallucinated
            })

        except Exception as e:
            log(f"Error auditing item {idx+1} (ID: {record.get('id')}): {e}", "ERROR")

    # Generate performance summaries
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

    # Make output directories if they do not exist
    os.makedirs(os.path.join(SCRIPT_DIR, "data"), exist_ok=True)
    
    # Export metrics as a structured JSON object
    summary_data = {
        "timestamp": datetime.now().isoformat(),
        "evaluator_model": MODEL_NAME,
        "metrics": {
            "total_evaluated": total_evaluated,
            "faithful_count": faithful_count,
            "hallucinated_count": hallucinated_count,
            "hallucination_rate_pct": round(hallucination_rate, 2)
        },
        "results": verdicts_list
    }
    
    try:
        report_json_path = os.path.join(SCRIPT_DIR, "data", "evaluation_report.json")
        with open(report_json_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        log(f"JSON evaluation report saved to {report_json_path}", "SUCCESS")
    except Exception as e:
        log(f"Failed to write JSON report: {e}", "ERROR")

    # Export metrics and logs as a professional Markdown document without emojis
    try:
        report_md_path = os.path.join(SCRIPT_DIR, "data", "evaluation_report.md")
        with open(report_md_path, 'w', encoding='utf-8') as f:
            f.write("# Project Veracity: Evaluation Report\n\n")
            f.write(f"Generated at: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  \n")
            f.write(f"Evaluator Model: `{MODEL_NAME}`\n\n")
            
            f.write("## Summary Metrics\n\n")
            f.write("| Metric | Value |\n")
            f.write("| :--- | :--- |\n")
            f.write(f"| **Total Records Evaluated** | {total_evaluated} |\n")
            f.write(f"| **Faithful (Non-Hallucinated)** | {faithful_count} |\n")
            f.write(f"| **Hallucinated** | {hallucinated_count} |\n")
            f.write(f"| **Hallucination Rate** | {hallucination_rate:.2f}% |\n\n")
            
            f.write("## Detailed Verdicts\n\n")
            f.write("| ID | Question | Verdict | Reasoning |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for v in verdicts_list:
                status = "Fail" if v["is_hallucinated"] else "Pass"
                # Truncate reasoning text for table representation
                short_reason = v["reasoning"][:100] + "..." if len(v["reasoning"]) > 100 else v["reasoning"]
                short_reason = short_reason.replace("\n", " ").replace("|", "\\|")
                question_escaped = v["question"].replace("\n", " ").replace("|", "\\|")
                f.write(f"| {v['id']} | {question_escaped} | {status} | {short_reason} |\n")
            
            f.write("\n---\n\n")
            f.write("## Individual Audit Logs\n\n")
            for v in verdicts_list:
                status = "Hallucinated" if v["is_hallucinated"] else "Faithful"
                f.write(f"### Sample ID: {v['id']}\n\n")
                f.write(f"- **Question**: {v['question']}\n")
                f.write(f"- **Verdict**: {status}\n")
                f.write(f"- **Ground Truth**: `{v['ground_truth']}`\n")
                f.write(f"- **Model Generated Answer**: `{v['model_generated_answer']}`\n\n")
                f.write(f"#### Context:\n```text\n{v['context']}\n```\n\n")
                f.write(f"#### Judge Reasoning:\n{v['reasoning']}\n\n")
                f.write("---\n\n")
                
        log(f"Markdown evaluation report saved to {report_md_path}", "SUCCESS")
    except Exception as e:
        log(f"Failed to write Markdown report: {e}", "ERROR")

if __name__ == "__main__":
    run_judge()
