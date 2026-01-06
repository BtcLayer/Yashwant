import sys
import os

# Set up path
sys.path.insert(0, os.getcwd())
# os.chdir(os.getcwd())

try:
    print("Starting 12h bot...")
    from live_demo_12h import main
    import asyncio
    asyncio.run(main.run_live('live_demo_12h/config.json'))
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to close...")
