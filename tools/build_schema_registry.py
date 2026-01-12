import os
import json
import math
import sys
from collections import defaultdict

def infer_type(val):
    """Infors the basic type of a value for schema validation"""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "boolean"
    if isinstance(val, (int, float)):
        return "number"
    if isinstance(val, str):
        return "string"
    if isinstance(val, dict):
        return "object"
    if isinstance(val, list):
        return "array"
    return "unknown"

def build_registry(logs_dir, output_path, sample_size=100):
    """
    Scans a directory of .jsonl logs and builds a schema registry.
    """
    registry = {}
    
    if not os.path.exists(logs_dir):
        print(f"Error: Logs directory not found: {logs_dir}")
        return
        
    print(f"🔍 Scanning logs in: {logs_dir}")
    
    # Walk through the logs directory
    for root, dirs, files in os.walk(logs_dir):
        for file in files:
            if not file.endswith('.jsonl'):
                continue
                
            stream_name = file.replace('.jsonl', '')
            file_path = os.path.join(root, file)
            
            print(f"  📄 Processing stream: {stream_name}")
            
            field_observations = defaultdict(set)
            required_fields = None
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    count = 0
                    for line in f:
                        if count >= sample_size:
                            break
                        
                        try:
                            data = json.loads(line)
                            current_fields = set(data.keys())
                            
                            # Initialize required fields with the first row
                            if required_fields is None:
                                required_fields = current_fields
                            else:
                                # Required fields are those present in ALL sampled rows
                                required_fields = required_fields.intersection(current_fields)
                            
                            # Observe types for each field
                            for k, v in data.items():
                                field_observations[k].add(infer_type(v))
                                
                            count += 1
                        except json.JSONDecodeError:
                            continue
                
                if not field_observations:
                    continue
                
                # Build schema for this stream
                stream_schema = {
                    "required_fields": sorted(list(required_fields)) if required_fields else [],
                    "fields": {}
                }
                
                for field, types in field_observations.items():
                    # If multiple types observed (excluding null), it's a "mixed" type
                    types_list = sorted(list(types))
                    stream_schema["fields"][field] = {
                        "types": types_list,
                        "is_optional": field not in required_fields
                    }
                
                registry[stream_name] = stream_schema
                
            except Exception as e:
                print(f"    ❌ Error processing {file}: {e}")

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "version": "1.0",
            "generated_at": str(sys.modules['datetime'].datetime.now() if 'datetime' in sys.modules else "now"),
            "streams": registry
        }, f, indent=2)
        
    print(f"\n✅ Registry built successfully: {output_path}")
    print(f"📊 Captured {len(registry)} log streams.")

if __name__ == "__main__":
    import datetime
    
    # Default behavior: scan the most recent 5m logs
    # You can override this via CLI args if needed
    logs_path = os.path.join("paper_trading_outputs", "5m", "logs")
    registry_path = os.path.join("schemas", "registry.json")
    
    build_registry(logs_path, registry_path)
