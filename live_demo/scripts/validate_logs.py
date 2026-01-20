"""
Log Validator for MetaStackerBandit
Validates JSONL logs against JSON schemas

Usage:
    python validate_logs.py <logs_directory>
    python validate_logs.py <logs.zip>
"""

import json
import sys
import gzip
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import zipfile

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install jsonschema")
    sys.exit(1)


# Schema file mapping (stream name -> schema file)
SCHEMA_MAP = {
    "signals": "signals.schema.json",
    "execution": "execution.schema.json",
    "costs": "costs.schema.json",
    "health": "health.schema.json",
    "order_intent": "order_intent_pre_risk.schema.json",
    "risk": "risk_sizing.schema.json",
    "pnl_equity": "pnl_equity.schema.json",
    "overlay": "overlay.schema.json",
    "errors": "errors.schema.json",
}


class LogValidator:
    """Validates log files against JSON schemas"""
    
    def __init__(self, schema_dir: Path):
        self.schema_dir = schema_dir
        self.schemas = self._load_schemas()
        self.stats = defaultdict(lambda: {"total": 0, "valid": 0, "errors": []})
        
    def _load_schemas(self) -> Dict[str, Any]:
        """Load all available schemas"""
        schemas = {}
        for stream_name, schema_file in SCHEMA_MAP.items():
            schema_path = self.schema_dir / schema_file
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schemas[stream_name] = json.load(f)
                print(f"✓ Loaded schema: {stream_name}")
            else:
                print(f"⚠ Schema not found: {schema_file} (skipping {stream_name})")
        return schemas
    
    def _detect_stream_type(self, file_path: Path) -> Optional[str]:
        """Auto-detect stream type from filename"""
        name = file_path.stem.lower()
        
        # Remove common suffixes
        for suffix in ['.jsonl', '.gz']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        # Match against known stream types
        for stream_name in SCHEMA_MAP.keys():
            if stream_name in name:
                return stream_name
        
        return None
    
    def _read_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read JSONL file (handles .gz compression)"""
        records = []
        
        try:
            if file_path.suffix == '.gz':
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            records.append(json.loads(line))
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            records.append(json.loads(line))
        except Exception as e:
            print(f"✗ Error reading {file_path.name}: {e}")
            
        return records
    
    def validate_file(self, file_path: Path, stream_type: Optional[str] = None):
        """Validate a single log file"""
        
        # Auto-detect stream type if not provided
        if stream_type is None:
            stream_type = self._detect_stream_type(file_path)
        
        if stream_type is None:
            print(f"⚠ Skipping {file_path.name} (unknown stream type)")
            return
        
        if stream_type not in self.schemas:
            print(f"⚠ Skipping {file_path.name} (no schema for {stream_type})")
            return
        
        schema = self.schemas[stream_type]
        records = self._read_jsonl(file_path)
        
        if not records:
            print(f"⚠ {file_path.name} is empty")
            return
        
        print(f"\n📄 Validating {file_path.name} ({stream_type}): {len(records)} records")
        
        for i, record in enumerate(records):
            self.stats[stream_type]["total"] += 1
            
            try:
                validate(instance=record, schema=schema)
                self.stats[stream_type]["valid"] += 1
            except ValidationError as e:
                error_msg = f"Record {i+1}: {e.message}"
                self.stats[stream_type]["errors"].append(error_msg)
                
                # Only print first 3 errors per file
                if len(self.stats[stream_type]["errors"]) <= 3:
                    print(f"  ✗ {error_msg}")
    
    def validate_directory(self, log_dir: Path):
        """Validate all JSONL files in directory (recursive)"""
        jsonl_files = list(log_dir.rglob("*.jsonl")) + list(log_dir.rglob("*.jsonl.gz"))
        
        if not jsonl_files:
            print(f"⚠ No JSONL files found in {log_dir}")
            return
        
        print(f"Found {len(jsonl_files)} log files\n")
        
        for file_path in sorted(jsonl_files):
            self.validate_file(file_path)
    
    def validate_zip(self, zip_path: Path):
        """Validate logs inside a ZIP file"""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            print(f"Extracting {zip_path.name}...")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(tmpdir_path)
            
            self.validate_directory(tmpdir_path)
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        
        total_records = 0
        total_valid = 0
        total_errors = 0
        
        for stream_name in sorted(self.stats.keys()):
            stats = self.stats[stream_name]
            total_records += stats["total"]
            total_valid += stats["valid"]
            total_errors += len(stats["errors"])
            
            if stats["total"] > 0:
                pct = (stats["valid"] / stats["total"]) * 100
                status = "✓" if pct == 100 else "✗"
                print(f"{status} {stream_name:20s}: {stats['valid']:5d}/{stats['total']:5d} valid ({pct:5.1f}%)")
                
                if stats["errors"] and len(stats["errors"]) > 3:
                    print(f"    ... {len(stats['errors']) - 3} more errors (see details above)")
        
        print("="*60)
        if total_records > 0:
            overall_pct = (total_valid / total_records) * 100
            print(f"TOTAL: {total_valid}/{total_records} valid ({overall_pct:.1f}%)")
            print(f"Errors: {total_errors}")
            
            if overall_pct == 100:
                print("\n✅ ALL LOGS VALID!")
                return 0
            else:
                print(f"\n⚠️  {total_errors} validation errors found")
                return 1
        else:
            print("⚠️  No records validated")
            return 1


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_logs.py <logs_directory_or_zip>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    
    if not input_path.exists():
        print(f"ERROR: {input_path} does not exist")
        sys.exit(1)
    
    # Find schema directory
    script_dir = Path(__file__).parent
    schema_dir = script_dir.parent / "schemas" / "logs"
    
    if not schema_dir.exists():
        print(f"ERROR: Schema directory not found: {schema_dir}")
        sys.exit(1)
    
    print(f"Schema directory: {schema_dir}")
    print(f"Input: {input_path}\n")
    
    validator = LogValidator(schema_dir)
    
    if input_path.is_dir():
        validator.validate_directory(input_path)
    elif input_path.suffix == '.zip':
        validator.validate_zip(input_path)
    else:
        print(f"ERROR: Input must be a directory or .zip file")
        sys.exit(1)
    
    exit_code = validator.print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
