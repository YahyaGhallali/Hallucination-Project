import os
import json
import urllib.request
import urllib.error
import sys

# Define URLs
PRIMARY_URL = "https://raw.githubusercontent.com/Luk0w/HaluEval/main/data/qa_data.json"
FALLBACK_URL = "https://raw.githubusercontent.com/RUCAIBox/HaluEval/master/data/qa_data.json"

# Dynamically resolve directory of this script to keep paths robust
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_FALLBACK_PATHS = [
    os.path.join(SCRIPT_DIR, "data", "qa_full.json"),
    os.path.join(SCRIPT_DIR, "data", "qa_100.json")
]
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "eval_set.jsonl")
LIMIT = 50

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def normalize_entry(entry, idx):
    """Normalize the schema for each entry into the exact required keys."""
    return {
        'id': idx,
        'knowledge': entry.get('knowledge', ''),
        'question': entry.get('question', ''),
        'right_answer': entry.get('right_answer', ''),
        'hallucinated_answer': entry.get('hallucinated_answer', '')
    }

def parse_stream(stream, limit=50):
    """Stream and parse JSON objects line-by-line from a byte stream."""
    entries = []
    buffer_lines = []
    count = 0

    for byte_line in stream:
        # Decode stream line-by-line, handling potential encoding anomalies gracefully
        line = byte_line.decode('utf-8', errors='replace').strip()
        if not line or line in ('[', ']'):
            continue
        
        buffer_lines.append(line)
        buffer_str = "".join(buffer_lines).strip()
        
        # Strip trailing comma if it exists (for elements in a JSON array)
        if buffer_str.endswith(','):
            buffer_str = buffer_str[:-1].strip()
            
        try:
            # Try parsing the current accumulated buffer
            entry_data = json.loads(buffer_str)
            normalized = normalize_entry(entry_data, count)
            entries.append(normalized)
            count += 1
            buffer_lines = []  # Reset buffer after a successful parse
            
            if count % 10 == 0 or count == limit:
                log(f"Parsed {count}/{limit} entries...")
                
            if count >= limit:
                break
        except json.JSONDecodeError:
            # Buffer is incomplete, continue accumulating
            continue
            
    return entries

def download_data():
    entries = None
    
    # 1. Try the primary URL requested by the user
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

    # 2. Try the official repository fallback URL
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

    # 3. Fallback to local files if both network attempts failed or encountered issues
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

    if not entries:
        log("Error: Could not retrieve dataset from any remote or local source.", "ERROR")
        sys.exit(1)

    # 4. Save to data/eval_set.jsonl
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
