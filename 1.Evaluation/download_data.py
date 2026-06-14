"""
Project Veracity: Automated Hallucination Evaluation (Phase 1)
Script: download_data.py

This script implements the Ingestion Engine of the evaluation pipeline. It retrieves, streams,
parses, and normalizes the HaluEval QA benchmark dataset. To minimize memory overhead, it streams
the remote data line-by-line rather than buffering the entire payload.

Robustness features:
1. Sequentially attempts multiple endpoints (Primary URL -> Fallback URL -> Local Files).
2. Normalizes input data schema on-the-fly to a strict structure.
3. Implements buffer-based incremental JSON decoding.
"""

import os
import json
import urllib.request
import urllib.error
import sys

# Remote dataset source configurations
PRIMARY_URL = "https://raw.githubusercontent.com/RUCAIBox/HaluEval/master/data/qa_data.json"
FALLBACK_URL = "https://raw.githubusercontent.com/RUCAIBox/HaluEval/master/data/qa_data.json"

# Resolve absolute execution path to keep directory navigation robust across environments
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_FALLBACK_PATHS = [
    os.path.join(SCRIPT_DIR, "data", "qa_full.json"),
    os.path.join(SCRIPT_DIR, "data", "qa_100.json")
]
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "eval_set.jsonl")

# Capping size of the evaluation set for controlled inference testing
LIMIT = 50

def log(msg, level="INFO"):
    """
    Prints standard logging messages to stdout with a severity tag.
    
    Args:
        msg (str): Message to display.
        level (str): Tag detailing severity level (e.g. INFO, WARNING, ERROR, SUCCESS).
    """
    print(f"[{level}] {msg}")

def normalize_entry(entry, idx):
    """
    Transforms the raw source dataset entry schema into the standardized output layout.
    
    Args:
        entry (dict): Original parsed dict from HaluEval.
        idx (int): Record identifier.
        
    Returns:
        dict: Standardized record structure.
    """
    return {
        'id': idx,
        'knowledge': entry.get('knowledge', ''),
        'question': entry.get('question', ''),
        'right_answer': entry.get('right_answer', ''),
        'hallucinated_answer': entry.get('hallucinated_answer', '')
    }

def parse_stream(stream, limit=50):
    """
    Parses a streaming sequence of byte data line-by-line to avoid loading full payloads in RAM.
    Accumulates fragments within a buffer and decodes incremental elements on completion.
    
    Args:
        stream (file-like): Source byte stream (e.g. urllib response or local file).
        limit (int): Cap specifying the maximum number of items to ingest.
        
    Returns:
        list: Collection of structured, normalized dictionary entries.
    """
    entries = []
    buffer_lines = []
    count = 0

    for byte_line in stream:
        # Gracefully replace encoding anomalies during decoding
        line = byte_line.decode('utf-8', errors='replace').strip()
        
        # Bypass array boundaries in raw JSON arrays
        if not line or line in ('[', ']'):
            continue
        
        buffer_lines.append(line)
        buffer_str = "".join(buffer_lines).strip()
        
        # Remove trailing commas present inside JSON array structures
        if buffer_str.endswith(','):
            buffer_str = buffer_str[:-1].strip()
            
        try:
            # Attempt parsing the current contents of the buffer
            entry_data = json.loads(buffer_str)
            normalized = normalize_entry(entry_data, count)
            entries.append(normalized)
            count += 1
            buffer_lines = []  # Clear buffer on successful record compilation
            
            if count % 10 == 0 or count == limit:
                log(f"Parsed {count}/{limit} entries...")
                
            if count >= limit:
                break
        except json.JSONDecodeError:
            # If the buffer accumulates too many fragments without success, clear it to prevent lockup
            if len(buffer_lines) > 15:
                buffer_lines = []
            continue
            
    return entries

def download_data():
    """
    Ingests and normalizes the benchmark data.
    Attempts downloads from Primary HTTP URL -> Fallback HTTP URL -> Local File Fallbacks.
    Outputs normalized results to the local output JSONL file.
    """
    entries = None
    
    # Attempt 1: Fetch from primary URL
    log(f"Attempting to fetch data from primary URL: {PRIMARY_URL}")
    try:
        req = urllib.request.Request(
            PRIMARY_URL,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            log("Connected to primary URL. Streaming and parsing...")
            entries = parse_stream(response, LIMIT)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        log(f"Primary URL download failed: {e}", "WARNING")
    except Exception as e:
        log(f"An unexpected error occurred while accessing primary URL: {e}", "WARNING")

    # Attempt 2: Fetch from fallback URL
    if not entries:
        log(f"Attempting to fetch data from fallback URL: {FALLBACK_URL}")
        try:
            req = urllib.request.Request(
                FALLBACK_URL,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                log("Connected to fallback URL. Streaming and parsing...")
                entries = parse_stream(response, LIMIT)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            log(f"Fallback URL download failed: {e}", "WARNING")
        except Exception as e:
            log(f"An unexpected error occurred while accessing fallback URL: {e}", "WARNING")

    # Attempt 3: Local file fallbacks
    if not entries:
        log("Attempting local fallback...")
        for local_path in LOCAL_FALLBACK_PATHS:
            if os.path.exists(local_path):
                log(f"Found local file at: {local_path}. Streaming and parsing...")
                try:
                    with open(local_path, 'rb') as f:
                        entries = parse_stream(f, LIMIT)
                    if entries:
                        log(f"Successfully processed local fallback: {local_path}")
                        break
                except Exception as e:
                    log(f"Failed to parse local file {local_path}: {e}", "WARNING")
            else:
                log(f"Local file not found at: {local_path}", "DEBUG")

    # Exit if all retrieval avenues failed
    if not entries:
        log("Error: Could not retrieve dataset from any remote or local source.", "ERROR")
        sys.exit(1)

    # Save normalized payload
    if not os.path.exists(OUTPUT_DIR):
        log(f"Creating output directory: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    log(f"Writing {len(entries)} entries to {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        log("File successfully saved.", "SUCCESS")
    except Exception as e:
        log(f"Failed to write output file: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    download_data()
