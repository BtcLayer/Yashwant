import os
import zipfile
from pathlib import Path

# Configuration
INCLUDE_EXTENSIONS = {'.py', '.js', '.ts', '.json', '.yaml', '.yml'}
EXCLUDE_DIRS = {
    '.venv', 'venv', '__pycache__', '.pytest_cache', 'dist', 'build', '.git',
    'logs', 'paper_trading_outputs', 'live_demo_1h', 'live_demo_12h', 'live_demo_24h',
    'live_demo', 'live_core', 'models', 'data', 'test_models', 'tests', 'plans', 'scripts', 'tools', 'ops', 'backend', 'frontend', 'core', 'docs', 'AUDIT_EXTRACT_TEMP', '.venv_old'
}
EXCLUDE_FILES_STARTSWITH = {'live_demo', 'run_', 'start_', 'test_', 'check_', 'evaluate_', 'create_', 'add_', 'restart_', 'monitor_', 'setup_', '.env', '.git', 'README', 'requirements', 'nginx', 'quickwins', 'temp_file', 'filtered_files', '5M_', 'ACCESS_', 'ADD_', 'BINANCE_', 'BOT_', 'check_', 'CI_', 'cohort_', 'data_', 'debug_', 'DEPLOYMENT_', 'equity_', 'FINAL_', 'GITHUB_', 'ISSUES_', 'issues_', 'MetaStackerBandit_', 'metrics_', 'MONITORING_', 'OBSERVABILITY_', 'PRODUCTION_', 'readiness_', 'restart_', 'signals_', 'start_', 'summary_', 'SYSTEM_', 'test_'}
EXCLUDE_EXTENSIONS = {'.joblib', '.pkl', '.csv', '.parquet', '.zip', '.md', '.ps1', '.sh', '.bat'}
EXCLUDE_FILES = {'create_code_snapshot.py', 'create_handoff_package.ps1'}
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1MB

ZIP_FILENAME = "latest_code_snapshot.zip"
WORKSPACE_DIR = "."  # Assumes the script is run from the workspace root

def should_include_file(file_path: Path) -> bool:
    """Determines if a file should be included in the ZIP based on the rules."""
    if file_path.name in EXCLUDE_FILES:
        return False
    if any(file_path.name.startswith(prefix) for prefix in EXCLUDE_FILES_STARTSWITH):
        return False
    if file_path.suffix in EXCLUDE_EXTENSIONS:
        return False
    if file_path.suffix not in INCLUDE_EXTENSIONS:
        return False
    
    # Check if file is in an excluded directory (by checking its parents)
    for parent in file_path.parents:
        if parent.name in EXCLUDE_DIRS and parent != Path(WORKSPACE_DIR):
            return False
            
    # Check file size
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            return False
    except FileNotFoundError:
        # File might be a symlink or broken, skip it
        return False
        
    return True

def create_zip():
    """Creates the ZIP archive with the specified rules."""
    included_files_count = 0
    included_folders = set()
    
    # For reporting, we'll list all directories that are explicitly defined as excluded,
    # and also check which ones actually exist.
    excluded_folders_reported = set()
    for d_name in EXCLUDE_DIRS:
        if Path(WORKSPACE_DIR, d_name).is_dir():
            excluded_folders_reported.add(d_name)

    with zipfile.ZipFile(ZIP_FILENAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(WORKSPACE_DIR):
            # IMPORTANT: Modify dirs in-place to prevent os.walk from traversing excluded directories.
            # This is based on the directory name itself.
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            current_dir_path = Path(root)
            # If the current root is not the workspace root itself and not an excluded dir, add it for reporting
            if current_dir_path.name and current_dir_path.name not in EXCLUDE_DIRS:
                 included_folders.add(str(current_dir_path.relative_to(WORKSPACE_DIR)))

            for filename in files:
                file_path = Path(root) / filename
                
                if should_include_file(file_path):
                    arcname = file_path.relative_to(WORKSPACE_DIR)
                    zipf.write(file_path, arcname)
                    included_files_count += 1
                    # Add parent directories of the included file to the included_folders set
                    for parent in arcname.parents:
                        if parent.name: # Ensure it's not the '.' root
                            included_folders.add(str(parent))

    # --- Confirmation Output ---
    print("ZIP file created.")
    print(f"ZIP filename: {ZIP_FILENAME}")
    print(f"Included folders (list): {sorted(list(included_folders)) if included_folders else ['None (root files only)']}")
    print(f"Excluded folders (list): {sorted(list(excluded_folders_reported)) if excluded_folders_reported else ['None']}")
    print(f"Total files included: {included_files_count}")

if __name__ == "__main__":
    create_zip()