# Phase 1: Automated Hallucination Evaluation

Welcome to the **Evaluation Pipeline** for Project Veracity. This folder implements Phase 1 of the architecture, focusing on shifting from subjective "vibe-checking" of Large Language Model (LLM) outputs to objective, reproducible, and statistically validated metrics.

The pipeline downloads a benchmark dataset, performs batch inference on a target LLM, audits the generations using a larger LLM-as-a-Judge under strict schema constraints, and validates the entire grading system via a meta-evaluation correlation check.

---

## Pipeline Workflow

The automated evaluation pipeline is executed in four sequential steps:

```mermaid
graph TD
    A[1. Ingestion: download_data.py] -->|Downloads & Normalizes HaluEval QA| B(data/eval_set.jsonl)
    B --> C[2. Inference: eval_runner.py]
    C -->|Generates Target Answers| D(data/generation_outputs.jsonl)
    D --> E[3. Verification: judge.py]
    E -->|Audits Outputs & Computes Metrics| F[4. Meta-Evaluation: meta_eval.py]
    F -->|Computes Correlation vs. Human Ground Truth| G{Validation Threshold: rho >= 0.75}

    style A fill:#4F46E5,stroke:#312E81,stroke-width:2px,color:#fff
    style C fill:#0D9488,stroke:#115E59,stroke-width:2px,color:#fff
    style E fill:#0284C7,stroke:#075985,stroke-width:2px,color:#fff
    style F fill:#F59E0B,stroke:#B45309,stroke-width:2px,color:#fff
```

---

## Directory Structure

```text
1.Evaluation/
├── data/
│   ├── eval_set.jsonl              # Streamed, parsed, and normalized HaluEval QA subset (50 samples)
│   └── generation_outputs.jsonl    # Target model responses with source context and ground truth
│
├── download_data.py                # Ingestion: Downloads, filters, and standardizes raw dataset
├── eval_runner.py                  # Inference: Runs batch queries on target model (Gemma 3) via NVIDIA API
├── judge.py                        # Audit: Stronger LLM-as-a-Judge (Llama 3 70B) scoring output factuality
└── meta_eval.py                    # Validation: Computes Spearman Rank Correlation Coefficient vs. Human Ground Truth
```

---

## Component Details

### 1. Ingestion ([download_data.py](file:///c:/Users/yahya/Desktop/Hallucination/1.Evaluation/download_data.py))
* **Objective**: Fetch and prepare evaluation samples.
* **Mechanism**:
  * Streams and parses the HaluEval QA benchmark from the official GitHub raw repository endpoints.
  * Normalizes the dataset schema on-the-fly, retaining standard keys: `id`, `knowledge`, `question`, `right_answer`, and `hallucinated_answer`.
  * Limits ingestion to the first **50 samples** to optimize iteration speed and control API costs.
  * **Resilience**: Features fallback loops to attempt a secondary remote URL, then checks for local JSON sources (`data/qa_full.json` or `data/qa_100.json`) if network connections are down.

### 2. Inference ([eval_runner.py](file:///c:/Users/yahya/Desktop/Hallucination/1.Evaluation/eval_runner.py))
* **Objective**: Generate factual answers under constrained conditions.
* **Model**: `google/gemma-3n-e2b-it` (run via NVIDIA API at temperature `0.0`).
* **Mechanism**:
  * Prompts the target model with a context-question structure.
  * Employs strict system instructions: *Answer the question using ONLY the provided Context. If the answer cannot be found in the context, say 'I do not know'.*
  * **Resilience**: Implements a robust `generate_with_retry` wrapper with proactive spacing and exponential backoff to handle API rate limits (`429` errors).

### 3. Verification ([judge.py](file:///c:/Users/yahya/Desktop/Hallucination/1.Evaluation/judge.py))
* **Objective**: Audit the target model's generated answers for hallucinations.
* **Model**: `meta/llama-3.1-70b-instruct` (LLM-as-a-Judge).
* **Mechanism**:
  * Compares the `model_generated_answer` against the original `context` and `question`.
  * Defines a strict output structure using Pydantic (`AuditVerdict`).
  * **Resilience**: Configured to use NVIDIA's `guided_json` schema extension to guarantee JSON format alignment. If unsupported, it falls back to standard JSON mode with custom parsing blocks.
  * Outputs a step-by-step `reasoning` trace alongside a binary `is_hallucinated` boolean.
  * Computes and prints the **Model Baseline Hallucination Rate**.

### 4. Meta-Evaluation ([meta_eval.py](file:///c:/Users/yahya/Desktop/Hallucination/1.Evaluation/meta_eval.py))
* **Objective**: Validate the reliability of the automated judge against manual grading.
* **Mechanism**:
  * Compares judge classifications against a 30-sample human-annotated baseline.
  * Computes **Direct Accuracy Alignment %** and **Spearman Rank Correlation Coefficient** ($\rho$).
  * Calculates ranks natively (handling ties) or using `scipy.stats.spearmanr` if installed.
  * **Success Criteria**: A correlation coefficient of $\rho \ge 0.75$ indicates the judge matches human consensus and is certified for production.

---

## Data Schemas

### Evaluation Set (`data/eval_set.jsonl`)
Each line is a JSON object representing a normalized HaluEval sample:
```json
{
  "id": 0,
  "knowledge": "The 2008 Summer Olympics ... were held in Beijing, China.",
  "question": "Where were the 2008 Summer Olympics held?",
  "right_answer": "Beijing, China",
  "hallucinated_answer": "London, United Kingdom"
}
```

### Generation Outputs (`data/generation_outputs.jsonl`)
Each line is a JSON object mapping the generated responses and baselines:
```json
{
  "id": 0,
  "context": "The 2008 Summer Olympics ... were held in Beijing, China.",
  "question": "Where were the 2008 Summer Olympics held?",
  "ground_truth": "Beijing, China",
  "known_hallucination_baseline": "London, United Kingdom",
  "model_generated_answer": "Beijing, China"
}
```

### Judge Audit Verdict (Pydantic Schema)
The judge outputs structured JSON satisfying:
```json
{
  "reasoning": "Step-by-step factuality analysis comparing the target claims to the context...",
  "is_hallucinated": false
}
```

---

## Execution Guide

### Prerequisites
Ensure that the parent directory has a configured `.env` file containing:
```env
NVIDIA_API_KEY=your_nvidia_api_key_here
```

### Step 1: Download & Ingest Benchmark Data
Fetch the raw datasets and compile the evaluation set:
```bash
python 1.Evaluation/download_data.py
```
*Generates: `1.Evaluation/data/eval_set.jsonl`*

### Step 2: Run Target Inference
Run batch generation on the target model:
```bash
python 1.Evaluation/eval_runner.py
```
*Generates: `1.Evaluation/data/generation_outputs.jsonl`*

### Step 3: Run LLM-as-a-Judge Auditing
Grade target outputs and calculate the hallucination rate:
```bash
python 1.Evaluation/judge.py
```
*Calculates and prints the final pipeline metrics in the terminal.*

### Step 4: Validate via Meta-Evaluation
Verify that the judge's scoring correlates with human consensus:
```bash
python 1.Evaluation/meta_eval.py
```
*Outputs accuracy alignment and the Spearman Rank Correlation Coefficient ($\rho$).*

---

## R&D Resilience Patterns

* **Graceful Fallbacks**: `download_data.py` uses a sequence of primary remote HTTP -> fallback remote HTTP -> local full JSON file -> local 100-sample JSON file to prevent setup blockages.
* **Exponential Backoff**: Rates are heavily limited by API providers; the execution pipeline implements an automatic exponential retry loop on `429` / rate limit error codes.
* **Strict Schema Decoding**: Evaluators are locked to Pydantic objects using guided decoding mechanisms (or JSON format fallbacks) to prevent schema drift and format failures.
