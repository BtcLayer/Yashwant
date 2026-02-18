"""
FRESH START RESET SCRIPT
Resets bot to clean state for testing cohort signal fixes
- Backs up old data
- Resets bandit state (unfreezes, PnL=0)
- Adjusts impact guard for paper trading validation
- Clears historical losses
"""

import json
import os
import shutil
from datetime import datetime

def backup_old_data():
    """Backup existing state files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"paper_trading_outputs/5m/backups/backup_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        "paper_trading_outputs/5m/runtime_bandit.json",
       "paper_trading_outputs/5m/execution_log.jsonl.gz",
        "paper_trading_outputs/5m/pnl_equity_log.jsonl.gz",
        "paper_trading_outputs/5m/cohort_state.json",
        "paper_trading_outputs/5m/sheets_fallback/executions_paper.csv"
    ]
    
    print("📦 Backing up old data...")
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"  ✅ Backed up: {os.path.basename(file_path)}")
    
    print(f"  📁 Backup saved to: {backup_dir}\n")
    return backup_dir


def reset_bandit_state():
    """Reset bandit to unfrozen state with fresh start"""
    bandit_path = "paper_trading_outputs/5m/runtime_bandit.json"
    
    if not os.path.exists(bandit_path):
        print(f"⚠️  Bandit state file not found: {bandit_path}")
        return
    
    with open(bandit_path, 'r') as f:
        state = json.load(f)
    
    print("🔄 Resetting bandit state...")
    
    # Show current state
    current_state = state['bandit_state']
    print(f"  Current - Frozen: {current_state['frozen']}")
    print(f"  Current - Cumulative PnL: ${current_state['cumulative_pnl']:.2f}")
    print(f"  Current - Peak PnL: ${current_state['peak_pnl']:.2f}")
    print(f"  Current - Freeze Reason: {current_state.get('freeze_reason', 'None')}")
    
    # Reset to fresh state
    state['bandit_state']['frozen'] = False
    state['bandit_state']['freeze_reason'] = None
    state['bandit_state']['cumulative_pnl'] = 0.0
    state['bandit_state']['peak_pnl'] = 0.0
    
    # Keep arm statistics but allow learning (don't reset means)
    # This preserves what the bandit learned about which arms work
    
    with open(bandit_path, 'w') as f:
        json.dump(state, f, indent=2)
    
    print("  ✅ Bandit UNFROZEN")
    print("  ✅ PnL reset to $0")
    print("  ✅ Drawdown tracking reset")
    print("  ℹ️  Arm statistics preserved (learned weights kept)\n")


def adjust_impact_guard():
    """Increase impact guard limits for paper trading validation"""
    config_path = "live_demo/config.json"
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("⚙️  Adjusting impact guard settings...")
    
    # Show current
    current_soft = config['risk_controls'].get('max_impact_bps', 50)
    current_hard = config['costs'].get('max_impact_bps_hard', 200)
    
    print(f"  Current - Soft limit: {current_soft} bps ({current_soft/100:.2f}%)")
    print(f"  Current - Hard limit: {current_hard} bps ({current_hard/100:.2f}%)")
    
    # Increase for paper trading (allow testing)
    config['risk_controls']['max_impact_bps'] = 150.0  # 1.5%
    config['costs']['max_impact_bps_hard'] = 500.0  # 5.0%
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"  ✅ New - Soft limit: 150 bps (1.5%) - More permissive")
    print(f"  ✅ New - Hard limit: 500 bps (5.0%) - Safety net")
    print("  ℹ️  These are suitable for paper trading validation\n")


def clear_stale_cohort_cache():
    """Clear old cohort cache for fresh data"""
    cohort_cache = "paper_trading_outputs/5m/cohort_state.json"
    
    if os.path.exists(cohort_cache):
        print("🗑️  Clearing old cohort cache...")
        os.remove(cohort_cache)
        print("  ✅ Cohort cache cleared (will rebuild from live data)\n")


def main():
    print("=" * 60)
    print("FRESH START RESET SCRIPT")
    print("Preparing bot for cohort signal validation")
    print("=" * 60)
    print()
    
    # Step 1: Backup
    backup_dir = backup_old_data()
    
    # Step 2: Reset bandit
    reset_bandit_state()
    
    # Step 3: Adjust impact guard
    adjust_impact_guard()
    
    # Step 4: Clear cohort cache
    clear_stale_cohort_cache()
    
    print("=" * 60)
    print("✅ RESET COMPLETE")
    print("=" * 60)
    print()
    print("📋 Summary of Changes:")
    print("  1. ✅ Old data backed up to:", backup_dir)
    print("  2. ✅ Bandit unfrozen (PnL reset to $0)")
    print("  3. ✅ Impact guard relaxed (50→150 bps soft, 200→500 bps hard)")
    print("  4. ✅ Cohort cache cleared (will rebuild from live data)")
    print()
    print("🚀 Next Steps:")
    print("  1. Restart bot: python -m live_demo.main")
    print("  2. Monitor for 24 hours")
    print("  3. Verify:")
    print("     - Cohort signals updating (pros/amateurs/mood non-zero)")
    print("     - Trades executing (not blocked by impact guard)")
    print("     - Bandit selecting from all 4 arms")
    print("     - PnL trending positive with cohort signals")
    print()
    print("⚠️  Note: This is paper trading - no real money at risk")
    print("=" * 60)


if __name__ == "__main__":
    main()
