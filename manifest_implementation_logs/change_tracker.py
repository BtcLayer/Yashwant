"""
Backup and Rollback Utility for Manifest Implementation
Provides safe file modification with automatic backup and rollback capability.
"""

import os
import shutil
from datetime import datetime
from typing import Optional, List, Dict
import json


class ChangeTracker:
    """Tracks all changes made during implementation with rollback capability."""
    
    def __init__(self, log_dir: str = "manifest_implementation_logs"):
        self.log_dir = log_dir
        self.backup_dir = os.path.join(log_dir, "backups")
        self.changes: List[Dict] = []
        self.run_number = self._get_next_run_number()
        
        # Ensure directories exist
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _get_next_run_number(self) -> int:
        """Get the next run number based on existing logs."""
        if not os.path.exists(self.log_dir):
            return 1
        
        existing = [f for f in os.listdir(self.log_dir) if f.startswith("run_")]
        if not existing:
            return 1
        
        numbers = []
        for f in existing:
            try:
                num = int(f.split("_")[1].split(".")[0])
                numbers.append(num)
            except (IndexError, ValueError):
                continue
        
        return max(numbers) + 1 if numbers else 1
    
    def backup_file(self, file_path: str) -> str:
        """
        Create a backup of a file before modification.
        Returns the backup file path.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Cannot backup non-existent file: {file_path}")
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        backup_name = f"{filename}.backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        # Copy file
        shutil.copy2(file_path, backup_path)
        
        # Log the backup
        self.log_change(
            action="BACKUP",
            path=file_path,
            backup_path=backup_path,
            status="SUCCESS",
            description=f"Backed up {filename}"
        )
        
        return backup_path
    
    def log_change(
        self,
        action: str,
        path: str,
        status: str = "SUCCESS",
        description: str = "",
        backup_path: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Log a change made during implementation."""
        change = {
            "run": self.run_number,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "path": path,
            "status": status,
            "description": description,
            "backup_path": backup_path,
            "error": error
        }
        self.changes.append(change)
    
    def rollback_file(self, backup_path: str, original_path: str) -> bool:
        """
        Rollback a file from its backup.
        Returns True if successful, False otherwise.
        """
        try:
            if not os.path.exists(backup_path):
                self.log_change(
                    action="ROLLBACK",
                    path=original_path,
                    status="FAILED",
                    description=f"Backup not found: {backup_path}"
                )
                return False
            
            shutil.copy2(backup_path, original_path)
            
            self.log_change(
                action="ROLLBACK",
                path=original_path,
                backup_path=backup_path,
                status="SUCCESS",
                description=f"Restored from backup"
            )
            return True
        
        except Exception as e:
            self.log_change(
                action="ROLLBACK",
                path=original_path,
                status="FAILED",
                error=str(e)
            )
            return False
    
    def save_log(self, phase: str = "unknown"):
        """Save the change log to a file."""
        log_filename = f"run_{self.run_number:02d}_{phase}.json"
        log_path = os.path.join(self.log_dir, log_filename)
        
        log_data = {
            "run_number": self.run_number,
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "total_changes": len(self.changes),
            "changes": self.changes,
            "summary": self._generate_summary()
        }
        
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        # Also create a human-readable text version
        txt_path = log_path.replace('.json', '.txt')
        with open(txt_path, 'w') as f:
            f.write(self._generate_text_report(phase))
        
        print(f"✅ Change log saved: {log_filename}")
        return log_path
    
    def _generate_summary(self) -> Dict:
        """Generate a summary of changes."""
        success = sum(1 for c in self.changes if c['status'] == 'SUCCESS')
        failed = sum(1 for c in self.changes if c['status'] == 'FAILED')
        
        actions = {}
        for change in self.changes:
            action = change['action']
            actions[action] = actions.get(action, 0) + 1
        
        return {
            "total_changes": len(self.changes),
            "successful": success,
            "failed": failed,
            "actions_breakdown": actions
        }
    
    def _generate_text_report(self, phase: str) -> str:
        """Generate a human-readable text report."""
        summary = self._generate_summary()
        
        report = f"""
{'='*80}
MANIFEST IMPLEMENTATION CHANGE LOG
Run #{self.run_number} - Phase: {phase}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

SUMMARY
-------
Total Changes: {summary['total_changes']}
Successful: {summary['successful']}
Failed: {summary['failed']}

Actions Breakdown:
"""
        
        for action, count in summary['actions_breakdown'].items():
            report += f"  - {action}: {count}\n"
        
        report += f"\n{'='*80}\nDETAILED CHANGES\n{'='*80}\n\n"
        
        for i, change in enumerate(self.changes, 1):
            report += f"{i}. [{change['status']}] {change['action']}\n"
            report += f"   Path: {change['path']}\n"
            report += f"   Time: {change['timestamp']}\n"
            if change['description']:
                report += f"   Description: {change['description']}\n"
            if change['backup_path']:
                report += f"   Backup: {change['backup_path']}\n"
            if change['error']:
                report += f"   Error: {change['error']}\n"
            report += "\n"
        
        report += f"{'='*80}\n"
        report += "END OF REPORT\n"
        report += f"{'='*80}\n"
        
        return report
    
    def print_summary(self):
        """Print a summary of changes to console."""
        summary = self._generate_summary()
        print(f"\n{'='*60}")
        print(f"Run #{self.run_number} Summary")
        print(f"{'='*60}")
        print(f"Total Changes: {summary['total_changes']}")
        print(f"✅ Successful: {summary['successful']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"{'='*60}\n")


# Example usage
if __name__ == "__main__":
    # Test the change tracker
    tracker = ChangeTracker()
    
    print(f"Starting Run #{tracker.run_number}")
    
    # Simulate some changes
    tracker.log_change(
        action="CREATE_DIRECTORY",
        path="manifest_implementation_logs",
        description="Created tracking directory"
    )
    
    tracker.log_change(
        action="CREATE_DIRECTORY",
        path="manifest_implementation_logs/backups",
        description="Created backups directory"
    )
    
    # Save the log
    tracker.save_log(phase="setup")
    tracker.print_summary()
