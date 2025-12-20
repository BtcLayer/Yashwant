import sys
import os

# Set up path
sys.path.insert(0, 'C:\\Users\\yashw\\MetaStackerBandit')
os.chdir('C:\\Users\\yashw\\MetaStackerBandit')

try:
    print("Starting 1h bot...")
    from live_demo_1h import main
    import asyncio
    asyncio.run(main.run_live('live_demo_1h/config.json'))
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to close...")
