import os
import json
import math
import sys
import argparse

def validate_row(stream_name, row_num, data, schema):
    """Validates a single row against the stream schema"""
    errors = []
    
    # 1. Check Required Fields
    for field in schema["required_fields"]:
        if field not in data:
            errors.append(f"Row {row_num}: Missing required field '{field}'")
            
    # 2. Check Types and Finite Numbers
    for field, value in data.items():
        if field not in schema["fields"]:
            # Optional: Allow extra fields or fail? 
            # Usually allowing extra fields is safer for forward compatibility
            continue
            
        field_schema = schema["fields"][field]
        observed_type = "null" if value is None else type(value).__name__
        
        # Mapping Python types to schema types
        type_map = {
            "int": "number",
            "float": "number",
            "str": "string",
            "bool": "boolean",
            "dict": "object",
            "list": "array",
            "NoneType": "null"
        }
        mapped_type = type_map.get(observed_type, observed_type)
        
        if mapped_type not in field_schema["types"]:
            # Special case for float/int both being "number"
            if mapped_type == "number" and "number" in field_schema["types"]:
                pass
            else:
                errors.append(f"Row {row_num}: Field '{field}' has wrong type '{mapped_type}' (expected {field_schema['types']})")
                
        # 3. Check Finite Numbers
        if mapped_type == "number" and value is not None:
            if not math.isfinite(value):
                errors.append(f"Row {row_num}: Field '{field}' is not finite (found {value})")
                
    return errors

def validate_logs(logs_dir, registry_path, verbose=False):
    """
    Validates logs against the schema registry.
    """
    if not os.path.exists(registry_path):
        print(f"❌ Error: Registry not found at {registry_path}")
        return False
        
    with open(registry_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)
        
    streams = registry.get("streams", {})
    total_errors = 0
    files_checked = 0
    
    print(f"🕵️  Validating logs in {logs_dir} against {registry_path}...")
    
    for root, dirs, files in os.walk(logs_dir):
        for file in files:
            if not file.endswith('.jsonl'):
                continue
                
            stream_name = file.replace('.jsonl', '')
            if stream_name not in streams:
                print(f"⚠️  Skipping unknown stream: {stream_name}")
                continue
                
            file_path = os.path.join(root, file)
            print(f"  🔍 Checking: {file_path}")
            files_checked += 1
            stream_schema = streams[stream_name]
            stream_errors = 0
            last_ts = -1
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    try:
                        data = json.loads(line)
                        row_errors = validate_row(stream_name, i, data, stream_schema)
                        
                        # Monotonic check for 'ts' field
                        if "ts" in data and isinstance(data["ts"], (int, float)):
                            current_ts = data["ts"]
                            if current_ts < last_ts:
                                row_errors.append(f"Row {i}: Timestamp decreased ({current_ts} < {last_ts})")
                            last_ts = current_ts
                            
                        if row_errors:
                            stream_errors += len(row_errors)
                            for err in row_errors:
                                print(f"  ❌ [{stream_name}] {err}")
                                
                    except json.JSONDecodeError:
                        print(f"  ❌ [{stream_name}] Row {i}: Invalid JSON")
                        stream_errors += 1
                        
            if stream_errors == 0:
                if verbose:
                    print(f"  ✅ {stream_name}: Validated ok.")
            else:
                total_errors += stream_errors
                
    print("\n" + "="*40)
    if total_errors == 0:
        print(f"✨ SUCCESS: {files_checked} files validated, 0 errors found.")
        return True
    else:
        print(f"🚨 FAILURE: {total_errors} schema violations found across {files_checked} files.")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate bot logs against schema registry")
    parser.add_argument("--logs_dir", default=os.path.join("paper_trading_outputs", "5m", "logs"), help="Path to logs directory")
    parser.add_argument("--registry", default=os.path.join("schemas", "registry.json"), help="Path to registry.json")
    parser.add_argument("--verbose", action="store_true", help="Print success for each file")
    
    args = parser.parse_args()
    
    success = validate_logs(args.logs_dir, args.registry, args.verbose)
    sys.exit(0 if success else 1)
